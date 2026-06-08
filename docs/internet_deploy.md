# Hướng dẫn Triển khai Hệ thống lên Internet (Cloud / VPS Deployment)

Để đưa hệ thống FB Job Tracker & Matcher lên internet nhằm truy cập từ xa mọi lúc mọi nơi, bạn có thể áp dụng 2 phương án phổ biến dưới đây:

---

## Phương án 1: Triển khai lên Render.com (Nhanh chóng & Tự động)

Render hỗ trợ triển khai trực tiếp từ kho lưu trữ GitHub (liên kết với repository `frograiny/FB-Job-Tracker-Matcher`). Render sẽ tự động dựng ứng dụng từ `Dockerfile` và `docker-compose.yml` mà ta đã tạo.

### Bước 1: Chuẩn bị tệp cấu hình Render Blueprint
Chúng tôi đã khởi tạo tệp cấu hình [render.yaml](../render.yaml) định nghĩa dịch vụ Web Service chạy FastAPI kèm theo ổ đĩa vật lý lưu trữ để lưu cơ sở dữ liệu `jobs.db` và cookies.

### Bước 2: Các bước triển khai trên Dashboard Render
1. Truy cập [Render.com](https://render.com/) và đăng nhập/đăng ký.
2. Nhấp vào **"New +"** ở góc trên cùng bên phải và chọn **"Blueprint"**.
3. Kết nối với tài khoản GitHub của bạn và chọn repository `FB-Job-Tracker-Matcher`.
4. Render sẽ đọc tệp `render.yaml` và yêu cầu bạn cung cấp giá trị cho biến môi trường:
   - `GEMINI_API_KEY`: API Key để chấm điểm CV và phân tích bài viết.
5. Nhấp vào **"Apply"** để bắt đầu build và deploy. 

> ⚠️ **Lưu ý quan trọng trên Render Free Tier:** 
> Do Facebook chặn các dải IP của các dịch vụ Cloud lớn (AWS, Render, Heroku) rất nghiêm ngặt, việc chạy bot Playwright để cào bài viết trực tiếp từ máy chủ Render có khả năng cao sẽ bị Facebook yêu cầu xác minh danh tính (Checkpoint) hoặc chặn đăng nhập.
> Do đó, khuyến khích sử dụng **Phương án 2 (VPS cá nhân)** hoặc cấu hình proxy dân cư (residential proxy).

---

## Phương án 2: Triển khai lên VPS riêng (Khuyên dùng - Độ ổn định cao nhất)

Sử dụng một VPS riêng (như DigitalOcean, Linode, Vultr hoặc AWS EC2 chạy Ubuntu) giúp bạn có toàn quyền kiểm soát hệ thống, giữ được database lâu dài và ít bị Facebook chặn IP hơn so với các dịch vụ PaaS công cộng.

### Cách triển khai tự động lên VPS qua Docker:

1. **Kết nối SSH vào VPS của bạn:**
   ```bash
   ssh root@ip_cua_vps
   ```

2. **Cài đặt Docker và Docker Compose trên VPS:**
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose
   sudo systemctl enable --now docker
   ```

3. **Clone mã nguồn từ GitHub:**
   ```bash
   git clone https://github.com/frograiny/FB-Job-Tracker-Matcher.git
   cd FB-Job-Tracker-Matcher
   ```

4. **Sao chép file cookies Facebook (`fb_cookies.json`) lên VPS:**
   * Bạn có thể sử dụng lệnh `scp` từ máy local để chuyển file cookies sang VPS một cách an toàn:
     ```bash
     scp fb_cookies.json root@ip_cua_vps:/root/FB-Job-Tracker-Matcher/data/fb_cookies.json
     ```

5. **Tạo tệp `.env` chứa API Key trên VPS:**
   ```bash
   echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
   ```

6. **Khởi chạy hệ thống bằng Docker Compose:**
   ```bash
   docker-compose up -d --build
   ```

Hệ thống sẽ chạy ngầm và mở cổng `8000`. Bạn có thể truy cập dashboard trực tuyến qua: `http://ip_cua_vps:8000`.

---

## 💡 Giải pháp tránh bị Facebook chặn (Anti-bot Bypass on Server)

Khi chạy trên máy chủ Internet, để bot không bị Facebook khóa tài khoản clone, hãy áp dụng các mẹo sau:

1. **Sử dụng Proxy dân cư (Residential Proxy):**
   Trong [fb_scraper.py](../src/fb_scraper.py), cấu hình Proxy trong Playwright:
   ```python
   context = await browser.new_context(
       proxy={
           "server": "http://ip_proxy:port",
           "username": "user",
           "password": "pass"
       }
   )
   ```
2. **Cập nhật Cookies định kỳ:**
   Mỗi khi cookies hết hạn, hãy xuất lại từ trình duyệt cá nhân bằng extension "Cookie Editor" và ghi đè lên file `fb_cookies.json` trên server.
