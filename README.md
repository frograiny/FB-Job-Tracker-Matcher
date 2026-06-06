# 🔍 Facebook Job Scraper Bot & CV Matcher

Hệ thống tự động quét tin tuyển dụng từ các nhóm Facebook, phân tích bằng Gemini AI, chấm điểm mức độ phù hợp với CV và quản lý qua giao diện Web Dashboard tương tác.

---

## 🌟 Tính năng Nổi bật

1. **Playwright Stealth Scraper**: Sử dụng trình duyệt giả lập với cơ chế chống phát hiện (anti-detection), tự động đăng nhập bằng cookies và cào bài viết từ các nhóm Facebook được cấu hình.
2. **Gemini AI Analysis**: Tích hợp mô hình AI mới nhất (`gemini-3.1-flash-lite`) thực hiện phân tích 3-trong-1 chỉ với một lượt gọi API:
   - Phân loại xem bài đăng có phải tin tuyển dụng thực sự hay không.
   - Trích xuất thông tin có cấu trúc (Công ty, vị trí, lương, yêu cầu, hạn nộp, liên hệ).
   - So sánh với CV của ứng viên để chấm điểm `% Match Score` và đưa ra lời khuyên ứng tuyển chi tiết.
3. **SQLite Database**: Lưu trữ dữ liệu bài viết thô và tin tuyển dụng để theo dõi lâu dài và tránh phân tích trùng lặp.
4. **Interactive Web Dashboard**: Giao diện tối giản hiện đại (FastAPI + HTML5/CSS3) cho phép:
   - Theo dõi trạng thái quét tin thời gian thực.
   - Lọc và tìm kiếm các công việc theo điểm số, công ty, từ khóa.
   - Xem chi tiết từng công việc, các kỹ năng phù hợp và còn thiếu.
   - Tải lên CV động trực tiếp từ giao diện để chấm điểm lại ngay lập tức.
5. **AI Job Application Agent**: Tích hợp Google Antigravity SDK để tạo ra Agent thông minh hỗ trợ người dùng viết Cover Letter cá nhân hóa và tự động ghi nhận lịch sử ứng tuyển.

---

## 📁 Cấu trúc Thư mục Dự án

Dự án được tổ chức theo cấu trúc chuẩn, tách biệt rõ ràng giữa mã nguồn, cấu hình, dữ liệu và tài liệu:

```text
my_agent_project/
├── config/                     # Cấu hình systemd template
│   └── fb_job_tracker.service.template
├── data/                       # Thư mục chứa dữ liệu động (bị Git ignore)
│   ├── fb_cookies.json         # Cookies đăng nhập Facebook
│   ├── jobs.db                 # Cơ sở dữ liệu SQLite
│   └── job_dashboard.html      # Dashboard HTML tĩnh sinh ra
├── docs/                       # Tài liệu hướng dẫn
│   ├── export_cookies.md       # Hướng dẫn lấy cookies Facebook
│   └── internet_deploy.md      # Hướng dẫn triển khai lên Internet
├── reports/                    # Báo cáo được xuất ra (CSV, MD, HTML)
├── resume/                     # CV và lịch sử ứng tuyển của bạn
│   ├── cv.txt                  # CV tiếng Anh
│   ├── cv_vi.txt               # CV tiếng Việt
│   └── applications_tracker.csv # File ghi nhận lịch sử ứng tuyển
├── scripts/                    # Các script tiện ích và kiểm thử
│   ├── auto_login.py           # Tiện ích tự động đăng nhập FB để lấy cookies
│   ├── check_joined_groups.py  # Kiểm tra các nhóm FB tài khoản đã tham gia
│   ├── test_run.py             # Script kiểm thử Agent tự động
│   └── run_batch_applications.py # Tự động tạo Cover Letter hàng loạt
├── src/                        # Mã nguồn ứng dụng cốt lõi
│   ├── app.py                  # API Server FastAPI
│   ├── fb_config.py            # Cấu hình tập trung cho Bot & AI
│   ├── fb_job_bot.py           # Script chạy chính (Scrape -> Analyze -> Report)
│   ├── fb_scraper.py           # Playwright Scraper
│   ├── job_analyzer.py         # AI Gemini Analyzer
│   ├── job_storage.py          # Quản lý SQLite DB và xuất báo cáo
│   └── job_app_agent.py        # Kịch bản AI Agent viết Cover Letter
├── Dockerfile                  # Cấu hình build Docker image
├── docker-compose.yml          # Cấu hình chạy container Docker
├── deploy.sh                   # Script tự động hóa triển khai (Local/Docker)
├── render.yaml                 # Cấu hình Deploy Blueprint trên Render.com
└── requirements.txt            # Danh sách thư viện Python phụ thuộc
```

---

## 🚀 Hướng dẫn Cài đặt & Sử dụng Cục bộ

### 1. Cài đặt môi trường
Yêu cầu Python >= 3.10.

```bash
# Tạo môi trường ảo
python3 -m venv .venv
source .venv/bin/activate

# Cài đặt các thư viện
pip install -r requirements.txt

# Cài đặt Playwright Chromium
playwright install chromium
playwright install-deps chromium
```

### 2. Cấu hình biến môi trường
Tạo tệp `.env` ở thư mục gốc của dự án:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Chuẩn bị Cookies đăng nhập Facebook
Đọc kỹ hướng dẫn tại [docs/export_cookies.md](file:///home/truongan/my_agent_project/docs/export_cookies.md). Sau khi export cookies bằng extension, hãy lưu file này tại đường dẫn `data/fb_cookies.json`.

Hoặc bạn có thể dùng script tự động đăng nhập bằng giao diện:
```bash
python scripts/auto_login.py
```

### 4. Chuẩn bị CV cá nhân
Lưu nội dung CV của bạn dạng text vào:
- [resume/cv.txt](file:///home/truongan/my_agent_project/resume/cv.txt) (Tiếng Anh)
- [resume/cv_vi.txt](file:///home/truongan/my_agent_project/resume/cv_vi.txt) (Tiếng Việt)

### 5. Chạy Bot quét tin
```bash
# Quét tất cả các nhóm đã cấu hình trong src/fb_config.py
python src/fb_job_bot.py

# Chỉ hiển thị các job có Match Score >= 50%
python src/fb_job_bot.py --min-score 50

# Chỉ xuất báo cáo từ DB có sẵn, không cào tin mới
python src/fb_job_bot.py --report
```

### 6. Khởi chạy Web Dashboard
```bash
python -m uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```
Truy cập giao diện Web tại địa chỉ: `http://localhost:8000`.

---

## 🐳 Hướng dẫn Triển khai lên Server Internet

Đọc chi tiết hướng dẫn tại [docs/internet_deploy.md](file:///home/truongan/my_agent_project/docs/internet_deploy.md) để biết cách triển khai lên Render hoặc VPS riêng.

### Triển khai nhanh bằng Docker Compose:
```bash
# Khởi chạy trong chế độ chạy ngầm
docker compose up -d --build
```
Hệ thống sẽ chạy ngầm và tự động mount thư mục `data/`, `resume/`, `reports/` để bảo toàn dữ liệu.

### Triển khai tự động qua deploy.sh:
Cấp quyền và chạy tệp kịch bản triển khai:
```bash
chmod +x deploy.sh
./deploy.sh
```
Sau đó, chọn các tùy chọn thích hợp (Local service, Docker Compose, thiết lập Cron Job hàng ngày).