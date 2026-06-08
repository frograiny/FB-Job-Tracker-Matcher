"""
AI Job Analyzer — phân tích bài viết bằng Gemini AI.

Sử dụng SDK mới: google.genai (thay thế google.generativeai đã deprecated).

Chức năng:
1. Phân loại bài viết: có phải tin tuyển dụng không?
2. Trích xuất thông tin tuyển dụng (công ty, vị trí, yêu cầu...)
3. So sánh với CV → tính % phù hợp
"""
import json
import logging
import os
import asyncio
from typing import Optional

from google import genai
from google.genai import types
from dotenv import load_dotenv

from fb_config import (
    GEMINI_MODEL,
    CLASSIFY_PROMPT,
    EXTRACT_PROMPT,
    MATCH_PROMPT,
    CV_PATH,
)

load_dotenv()
logger = logging.getLogger(__name__)

_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """Create the Gemini client lazily so imports do not require credentials."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        _client = genai.Client(api_key=api_key)
    return _client


def _parse_json_response(text: str) -> Optional[dict]:
    """Parse JSON từ response text, xử lý các trường hợp edge."""
    text = text.strip()

    # Xóa markdown code block nếu có
    if text.startswith("```"):
        lines = text.split("\n")
        # Bỏ dòng đầu (```json) và dòng cuối (```)
        text = "\n".join(lines[1:-1])

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Thử tìm JSON trong text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return None


async def _call_gemini_with_retry(prompt: str, max_retries: int = 3) -> Optional[str]:
    """
    Gọi Gemini API với retry logic.
    
    Xử lý rate limit bằng exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            response = await asyncio.to_thread(
                _get_client().models.generate_content,
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,          # Giảm sáng tạo, tăng chính xác
                    max_output_tokens=1024,
                    response_mime_type="application/json",  # Bắt buộc trả JSON
                ),
            )
            if response.text:
                return response.text
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate" in error_str or "quota" in error_str:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 5  # 5s, 10s
                    logger.warning(f"Rate limit! Đợi {wait_time}s rồi thử lại... (lần {attempt+1})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Đã thử lại {max_retries} lần nhưng vẫn bị rate limit: {e}")
                    raise
            else:
                logger.error(f"Lỗi gọi Gemini (lần {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    raise
    return None


# ============================================================
# 1. Phân loại bài viết
# ============================================================
async def classify_post(post_text: str) -> dict:
    """
    Phân loại bài viết có phải tin tuyển dụng không.
    
    Returns:
        {
            "is_job_posting": True/False,
            "confidence": 0.0-1.0,
            "reason": "lý do"
        }
    """
    # Cắt bớt nếu bài quá dài (tiết kiệm token)
    truncated = post_text[:3000] if len(post_text) > 3000 else post_text
    prompt = CLASSIFY_PROMPT.format(post_text=truncated)

    result_text = await _call_gemini_with_retry(prompt)

    if result_text:
        parsed = _parse_json_response(result_text)
        if parsed:
            return parsed

    # Fallback nếu AI không trả lời được
    return {"is_job_posting": False, "confidence": 0.0, "reason": "Không phân tích được"}


# ============================================================
# 2. Trích xuất thông tin tuyển dụng
# ============================================================
async def extract_job_info(post_text: str) -> dict:
    """
    Trích xuất thông tin có cấu trúc từ tin tuyển dụng.
    
    Returns:
        {
            "company": "...",
            "position": "...",
            "requirements": [...],
            "salary": "...",
            "location": "...",
            "contact": "...",
            "deadline": "...",
            "work_type": "...",
            "experience_level": "..."
        }
    """
    truncated = post_text[:4000] if len(post_text) > 4000 else post_text
    prompt = EXTRACT_PROMPT.format(post_text=truncated)

    result_text = await _call_gemini_with_retry(prompt)

    if result_text:
        parsed = _parse_json_response(result_text)
        if parsed:
            return parsed

    # Fallback
    return {
        "company": None,
        "position": None,
        "requirements": [],
        "salary": None,
        "location": None,
        "contact": None,
        "deadline": None,
        "work_type": None,
        "experience_level": None,
    }


# ============================================================
# 3. So sánh CV với job
# ============================================================
def _load_cv() -> str:
    """Đọc nội dung CV."""
    if os.path.exists(CV_PATH):
        with open(CV_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return ""


async def match_with_cv(job_info: dict, cv_text: str = "") -> dict:
    """
    So sánh thông tin tuyển dụng với CV ứng viên.
    
    Args:
        job_info: Dict thông tin tuyển dụng (từ extract_job_info)
        cv_text: Nội dung CV (nếu không truyền, tự đọc từ file)
        
    Returns:
        {
            "match_score": 0-100,
            "matched_skills": [...],
            "missing_skills": [...],
            "recommendation": "..."
        }
    """
    if not cv_text:
        cv_text = _load_cv()
    if not cv_text:
        return {
            "match_score": 0,
            "matched_skills": [],
            "missing_skills": [],
            "recommendation": "Không tìm thấy file CV.",
        }

    requirements_str = ", ".join(job_info.get("requirements", [])) if job_info.get("requirements") else "Không rõ"

    prompt = MATCH_PROMPT.format(
        cv_text=cv_text[:2000],
        company=job_info.get("company", "Không rõ"),
        position=job_info.get("position", "Không rõ"),
        requirements=requirements_str,
    )

    result_text = await _call_gemini_with_retry(prompt)

    if result_text:
        parsed = _parse_json_response(result_text)
        if parsed:
            return parsed

    return {
        "match_score": 0,
        "matched_skills": [],
        "missing_skills": [],
        "recommendation": "Không phân tích được.",
    }


# ============================================================
# 4. Pipeline đầy đủ: Phân tích tích hợp trong 1 API Call (Tối ưu)
# ============================================================
COMBINED_PROMPT = """Bạn là chuyên gia tuyển dụng và phân tích bài viết.
Đọc bài viết Facebook và so sánh với CV ứng viên bên dưới để trả về kết quả phân tích tích hợp dạng JSON duy nhất.

CV ứng viên:
\"\"\"
{cv_text}
\"\"\"

Bài viết Facebook:
\"\"\"
{post_text}
\"\"\"

Quy tắc phân tích:
1. Xác định "is_job_posting" (true/false) xem bài viết có phải tin tuyển dụng/tìm người làm việc/thực tập không.
2. Nếu là tin tuyển dụng, hãy trích xuất thông tin chi tiết vào "job_info" và thực hiện so sánh với CV vào "cv_match".
3. Nếu KHÔNG phải tin tuyển dụng, hãy set "is_job_posting": false, điền "reason" và để các phần khác là null.

Hãy trả về JSON theo cấu trúc sau:
{{
  "is_job_posting": true/false,
  "confidence": 0.0-1.0,
  "reason": "lý do phân loại ngắn gọn",
  "job_info": {{
    "company": "tên công ty hoặc null",
    "position": "vị trí tuyển dụng hoặc null",
    "requirements": ["yêu cầu 1", "yêu cầu 2"],
    "salary": "mức lương hoặc null",
    "location": "địa điểm làm việc hoặc null",
    "contact": "email/phone/link liên hệ hoặc null",
    "deadline": "hạn nộp hồ sơ hoặc null",
    "work_type": "fulltime/parttime/intern/remote/hybrid hoặc null",
    "experience_level": "intern/fresher/junior/mid/senior hoặc null"
  }},
  "cv_match": {{
    "match_score": 0-100 (điểm phù hợp từ 0 đến 100),
    "matched_skills": ["kỹ năng phù hợp 1", "kỹ năng 2"],
    "missing_skills": ["yêu cầu công việc chưa có trong CV"],
    "recommendation": "nhận xét ngắn gọn, khuyên ứng viên có nên ứng tuyển hay không và lý do"
  }}
}}
"""


async def analyze_post(post_text: str, cv_text: str = "") -> Optional[dict]:
    """
    Phân tích bài viết bằng 1 cuộc gọi Gemini duy nhất (Tối ưu hóa API quota).
    
    Returns:
        None nếu không phải tin tuyển dụng hoặc confidence thấp.
        Dict đầy đủ nếu là tin tuyển dụng.
    """
    if not cv_text:
        cv_text = _load_cv()
        
    truncated_post = post_text[:3000] if len(post_text) > 3000 else post_text
    prompt = COMBINED_PROMPT.format(cv_text=cv_text[:2000], post_text=truncated_post)
    
    result_text = await _call_gemini_with_retry(prompt)
    if not result_text:
        return None
        
    parsed = _parse_json_response(result_text)
    if not parsed:
        return None
        
    is_job = parsed.get("is_job_posting", False)
    confidence = parsed.get("confidence", 0.0)
    
    logger.info(f"  Phân loại: is_job={is_job}, confidence={confidence}")
    
    if not is_job or confidence < 0.6:
        return None
        
    # Tạo cấu trúc trả về tương thích với db.save_job
    classification = {
        "is_job_posting": is_job,
        "confidence": confidence,
        "reason": parsed.get("reason", "")
    }
    
    return {
        "classification": classification,
        "job_info": parsed.get("job_info", {}),
        "cv_match": parsed.get("cv_match", {})
    }
