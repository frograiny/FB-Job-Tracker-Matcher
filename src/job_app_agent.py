import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import csv
from dotenv import load_dotenv

try:
    from google.antigravity import Agent, LocalAgentConfig
except ImportError:
    Agent = None
    LocalAgentConfig = None

from cv_profile import extract_cv_profile, score_text_against_profile, summarize_profile
from fb_config import BASE_DIR, CV_PATH
from job_storage import JobDatabase

# Tải biến môi trường từ file .env
load_dotenv()

# Đường dẫn các file liên quan (BASE_DIR là thư mục gốc dự án)
TRACKER_PATH = os.getenv(
    "APPLICATION_TRACKER_PATH",
    os.path.join(BASE_DIR, "resume", "applications_tracker.csv"),
)

# 1. Định nghĩa các công cụ (Tools) cho Agent

def read_cv() -> str:
    """Đọc thông tin CV cá nhân của người dùng từ file cv.txt.
    
    Returns:
        Nội dung CV của người dùng dưới dạng văn bản.
    """
    if not os.path.exists(CV_PATH):
        return "Không tìm thấy file cv.txt. Vui lòng tạo file cv.txt chứa thông tin lý lịch của bạn."
    with open(CV_PATH, "r", encoding="utf-8") as f:
        return f.read()

def search_job_postings(query: str) -> str:
    """Tìm kiếm các tin tuyển dụng/thực tập trên mạng dựa trên từ khóa truy vấn.
    
    Args:
        query: Từ khóa tìm kiếm, ví dụ: 'Thực tập sinh Python', 'AI Intern'.
    """
    # 1. Thử tìm kiếm trong SQLite Database thực tế trước
    try:
        with JobDatabase() as db:
            db_jobs = db.get_jobs(min_score=0, limit=100)
            result_jobs = []
            for job in db_jobs:
                title = (job.get("position") or "").lower()
                company = (job.get("company") or "").lower()
                desc = (job.get("requirements") or "").lower()
                q = query.lower()
                if q in title or q in company or q in desc:
                    result_jobs.append(job)
            
            if result_jobs:
                output = []
                for job in result_jobs[:10]:
                    output.append(
                        f"- ID: {job.get('id')}\n"
                        f"  Công ty: {job.get('company') or 'Unknown'}\n"
                        f"  Vị trí: {job.get('position') or 'Unknown'}\n"
                        f"  Địa điểm: {job.get('location') or 'Chưa xác định'}\n"
                        f"  Mô tả: {job.get('requirements') or 'Không có mô tả chi tiết'}\n"
                        f"  Link: {job.get('post_url') or ''}\n"
                    )
                return "\n".join(output)
    except Exception:
        pass

    # 2. Fallback sang dữ liệu mẫu tiêu biểu nếu database trống
    jobs = [
        {
            "id": "1",
            "company": "FPT Software",
            "position": "Python Developer Intern",
            "location": "Hà Nội / TP.HCM",
            "description": "Yêu cầu kiến thức về Python cơ bản, FastAPI/Django, cơ sở dữ liệu SQL, Git."
        },
        {
            "id": "2",
            "company": "VinAI",
            "position": "AI Research Intern",
            "location": "Hà Nội",
            "description": "Yêu cầu kiến thức về Học sâu (Deep Learning), PyTorch/TensorFlow, toán tối ưu."
        },
        {
            "id": "3",
            "company": "VNG Corporation",
            "position": "Machine Learning Engineer Intern",
            "location": "TP.HCM",
            "description": "Phát triển và tối ưu hóa các mô hình ML, xử lý dữ liệu lớn bằng Python, Pandas."
        }
    ]
    
    result = []
    for job in jobs:
        if query.lower() in job["position"].lower() or query.lower() in job["company"].lower():
            result.append(f"- ID: {job['id']}\n  Công ty: {job['company']}\n  Vị trí: {job['position']}\n  Địa điểm: {job['location']}\n  Mô tả: {job['description']}\n")
    
    if not result:
        return f"Không tìm thấy công việc nào khớp với từ khóa '{query}'. Thử từ khóa khác như 'Python' hoặc 'AI'."
    
    return "\n".join(result)

def log_application(company: str, position: str, status: str = "Đã lên kế hoạch") -> str:
    """Ghi nhận và lưu thông tin ứng tuyển của một công việc vào file quản lý applications_tracker.csv.
    
    Args:
        company: Tên công ty tuyển dụng.
        position: Vị trí ứng tuyển.
        status: Trạng thái (Ví dụ: 'Đã viết Cover Letter', 'Đã ứng tuyển', 'Chờ phản hồi').
    """
    file_exists = os.path.exists(TRACKER_PATH)
    with open(TRACKER_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Công ty", "Vị trí", "Trạng thái"])
        writer.writerow([company, position, status])
    return f"Đã ghi nhận thành công: Công ty {company} - Vị trí {position} vào danh sách theo dõi."

# 2. Cấu hình hệ thống chỉ dẫn cho Agent
SYSTEM_INSTRUCTIONS = """
Bạn là một AI Agent chuyên nghiệp hỗ trợ người dùng tìm kiếm việc làm và thực tập.
Quy trình làm việc của bạn:
1. Luôn bắt đầu bằng việc đọc CV của người dùng bằng công cụ `read_cv` để hiểu rõ năng lực.
2. Tìm kiếm các vị trí thực tập thích hợp bằng công cụ `search_job_postings`.
3. Soạn thảo một bức thư xin việc (Cover Letter) được cá nhân hóa cao, kết hợp thông tin từ CV của người dùng và Mô tả công việc của vị trí tuyển dụng. Cover Letter phải chuyên nghiệp, hấp dẫn bằng tiếng Việt.
4. Ghi nhận lịch sử ứng tuyển bằng công cụ `log_application` với trạng thái "Đã viết Cover Letter".
5. Phản hồi đầy đủ thông tin vị trí tuyển dụng cùng thư Cover Letter đã soạn thảo cho người dùng.
"""

# 3. Hàm chạy vòng lặp tương tác tự động
async def run_interactive_loop(agent):
    print("Bắt đầu vòng lặp tương tác. Gõ 'exit' hoặc 'quit' để thoát.")
    while True:
        try:
            # Chạy input() đồng bộ trong executor để tránh chặn event loop
            user_input = await asyncio.get_event_loop().run_in_executor(None, input, "User: ")
            if user_input.strip().lower() in ["exit", "quit"]:
                print("Đang thoát...")
                break
            if not user_input.strip():
                continue
            
            response = await agent.chat(user_input)
            print("Agent: ", end="", flush=True)
            async for chunk in response:
                print(chunk, end="", flush=True)
            print("\n")
        except (KeyboardInterrupt, EOFError):
            print("\nĐang thoát...")
            break

# 4. Hàm chạy Agent chính
async def run_agent():
    if Agent is None or LocalAgentConfig is None:
        raise RuntimeError(
            "Google Antigravity SDK is not installed. Install/configure it before running job_app_agent.py."
        )

    config = LocalAgentConfig(
        tools=[read_cv, search_job_postings, log_application],
        system_instructions=SYSTEM_INSTRUCTIONS,
    )
    
    print("=" * 60)
    print("Khởi chạy Job Application Agent...")
    print("=" * 60)
    
    async with Agent(config) as agent:
        await run_interactive_loop(agent)

if __name__ == "__main__":
    asyncio.run(run_agent())
