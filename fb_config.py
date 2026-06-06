"""
Cấu hình tập trung cho Facebook Job Scraper Bot.
Chỉnh sửa file này để thay đổi hành vi của bot.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 1. ĐƯỜNG DẪN FILE
# ============================================================
DATA_DIR = "/app/data" if os.path.exists("/app/data") else BASE_DIR
COOKIES_PATH = os.path.join(DATA_DIR, "fb_cookies.json")
DATABASE_PATH = os.path.join(DATA_DIR, "jobs.db")
CV_PATH = os.path.join(DATA_DIR, "cv.txt") if os.path.exists(os.path.join(DATA_DIR, "cv.txt")) else os.path.join(BASE_DIR, "cv.txt")
CV_VI_PATH = os.path.join(DATA_DIR, "cv_vi.txt") if os.path.exists(os.path.join(DATA_DIR, "cv_vi.txt")) else os.path.join(BASE_DIR, "cv_vi.txt")
REPORT_DIR = DATA_DIR  # Thư mục xuất báo cáo
DASHBOARD_PATH = os.path.join(BASE_DIR, "job_dashboard.html")


# ============================================================
# 2. DANH SÁCH NHÓM FACEBOOK CẦN THEO DÕI
#    Thêm/xóa URL nhóm ở đây.
#    Chỉ cần đường dẫn dạng: https://www.facebook.com/groups/<tên-nhóm>
# ============================================================
FACEBOOK_GROUPS = [
    # URL tìm kiếm bài viết công khai trên Facebook (Hiệu quả cho tài khoản phụ chưa vào nhóm)
    "https://www.facebook.com/search/posts/?q=tuy%E1%BB%83n+d%E1%BB%A5ng+python+fresher",
    "https://www.facebook.com/search/posts/?q=tuy%E1%BB%83n+d%E1%BB%A5ng+python+intern",
    "https://www.facebook.com/search/posts/?q=tuy%E1%BB%83n+d%E1%BB%A5ng+ai+fresher",
    # Bạn có thể bật lại các nhóm bên dưới khi tài khoản clone đã gia nhập nhóm thành công:
    # "https://www.facebook.com/groups/VietnamITcommunity",
    # "https://www.facebook.com/groups/pythonvietnam",
]

# ============================================================
# 3. TỪ KHÓA LỌC BÀI VIẾT TUYỂN DỤNG
#    Bot sẽ ưu tiên phân tích bài có chứa ít nhất 1 từ khóa.
#    Viết thường hết (so sánh case-insensitive).
# ============================================================
JOB_KEYWORDS = [
    # Vị trí
    "tuyển dụng", "tuyển", "recruiting", "hiring", "looking for",
    "intern", "thực tập", "fresher", "junior",
    # Kỹ năng liên quan đến profile bạn
    "python", "ai", "machine learning", "deep learning",
    "ml", "data", "backend", "fullstack", "full-stack",
    "react", "fastapi", "flask", "django",
    "pytorch", "tensorflow",
    # Tín hiệu khác
    "cv", "resume", "apply", "ứng tuyển", "nộp hồ sơ",
    "lương", "salary", "jd", "mô tả công việc",
]

# ============================================================
# 4. CÀI ĐẶT HÀNH VI BOT (Anti-detection)
#    Delay random giữa mỗi thao tác để giả lập người thật.
# ============================================================
SCROLL_DELAY_MIN = 2.0      # Giây tối thiểu giữa mỗi lần cuộn
SCROLL_DELAY_MAX = 5.0      # Giây tối đa
ACTION_DELAY_MIN = 1.0      # Delay tối thiểu giữa các thao tác khác
ACTION_DELAY_MAX = 3.0      # Delay tối đa
MAX_SCROLLS_PER_GROUP = 15  # Số lần cuộn tối đa mỗi nhóm
POSTS_PER_GROUP_LIMIT = 30  # Giới hạn bài viết mỗi nhóm
MAX_POST_AGE_DAYS = 7       # Chỉ quét bài viết trong vòng 7 ngày gần đây


# Viewport giả lập (giống màn hình laptop thật)
VIEWPORT_WIDTH = 1366
VIEWPORT_HEIGHT = 768

# User-Agent giả lập Chrome trên Windows
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# ============================================================
# 5. CÀI ĐẶT GEMINI AI
# ============================================================
GEMINI_MODEL = "gemini-3.1-flash-lite"  # Sử dụng gemini-3.1-flash-lite để tránh giới hạn quota của các model khác

# Prompt phân loại bài viết
CLASSIFY_PROMPT = """Bạn là chuyên gia phân tích bài viết mạng xã hội.
Đọc bài viết Facebook bên dưới và trả lời DUY NHẤT bằng JSON:

{{"is_job_posting": true/false, "confidence": 0.0-1.0, "reason": "lý do ngắn gọn"}}

Quy tắc:
- is_job_posting = true NẾU bài viết đang tuyển dụng, tìm nhân sự, hoặc rao vị trí thực tập/việc làm
- is_job_posting = false NẾU bài viết chỉ chia sẻ kiến thức, hỏi đáp, quảng cáo sản phẩm, hoặc nội dung khác
- confidence: mức độ chắc chắn từ 0.0 đến 1.0

Bài viết:
\"\"\"
{post_text}
\"\"\"
"""

# Prompt trích xuất thông tin tuyển dụng
EXTRACT_PROMPT = """Trích xuất thông tin tuyển dụng từ bài viết Facebook bên dưới.
Trả lời DUY NHẤT bằng JSON với các trường sau (để null nếu không có):

{{
  "company": "tên công ty",
  "position": "vị trí tuyển dụng",
  "requirements": ["yêu cầu 1", "yêu cầu 2"],
  "salary": "mức lương (nếu có)",
  "location": "địa điểm làm việc",
  "contact": "thông tin liên hệ (email/phone/link)",
  "deadline": "hạn nộp hồ sơ",
  "work_type": "fulltime/parttime/intern/remote/hybrid",
  "experience_level": "intern/fresher/junior/mid/senior"
}}

Bài viết:
\"\"\"
{post_text}
\"\"\"
"""

# Prompt so sánh CV với job
MATCH_PROMPT = """So sánh CV ứng viên với tin tuyển dụng bên dưới.
Trả lời DUY NHẤT bằng JSON:

{{
  "match_score": 0-100,
  "matched_skills": ["kỹ năng phù hợp 1", "kỹ năng 2"],
  "missing_skills": ["kỹ năng thiếu 1", "kỹ năng 2"],
  "recommendation": "nhận xét ngắn gọn, nên/không nên ứng tuyển và lý do"
}}

CV ứng viên:
\"\"\"
{cv_text}
\"\"\"

Thông tin tuyển dụng:
\"\"\"
Công ty: {company}
Vị trí: {position}
Yêu cầu: {requirements}
\"\"\"
"""
