# Hướng Dẫn Export Cookies Facebook

Bot cần cookies đăng nhập Facebook để truy cập nhóm. Bạn chỉ cần làm **1 lần** (cookies thường hợp lệ 30-90 ngày).

## Cách 1: Dùng Extension "Cookie Editor" (Khuyên dùng)

### Bước 1: Cài extension
- Chrome: Tìm **"Cookie Editor"** trên Chrome Web Store → Install
- Firefox: Tìm **"Cookie Editor"** trên Firefox Add-ons → Install

### Bước 2: Export cookies
1. Mở trình duyệt, đăng nhập Facebook bình thường
2. Vào trang `https://www.facebook.com`
3. Click icon extension **Cookie Editor** trên thanh toolbar
4. Click nút **"Export"** (icon mũi tên xuống hoặc chữ Export)
5. Chọn format **JSON**
6. Copy toàn bộ nội dung

### Bước 3: Lưu file
1. Tạo file mới: `fb_cookies.json` trong thư mục dự án
2. Paste nội dung cookies vào
3. Lưu file

---

## Cách 2: Dùng Chrome DevTools (Không cần cài extension)

### Bước 1: Mở DevTools
1. Đăng nhập Facebook trên Chrome
2. Nhấn `F12` hoặc `Ctrl+Shift+I` để mở DevTools
3. Chuyển sang tab **Application** (hoặc **Storage**)
4. Bên trái, mở **Cookies** → click `https://www.facebook.com`

### Bước 2: Copy cookies
Bạn cần copy các cookies quan trọng sau:
- `c_user` — ID người dùng
- `xs` — session token (quan trọng nhất)
- `fr` — tracking cookie
- `datr` — browser cookie
- `sb` — browser cookie

### Bước 3: Tạo file JSON
Tạo file `fb_cookies.json` với format sau:

```json
[
  {
    "name": "c_user",
    "value": "GIÁ TRỊ TỪ DEVTOOLS",
    "domain": ".facebook.com",
    "path": "/",
    "secure": true,
    "httpOnly": true,
    "sameSite": "None"
  },
  {
    "name": "xs",
    "value": "GIÁ TRỊ TỪ DEVTOOLS",
    "domain": ".facebook.com",
    "path": "/",
    "secure": true,
    "httpOnly": true,
    "sameSite": "None"
  },
  {
    "name": "fr",
    "value": "GIÁ TRỊ TỪ DEVTOOLS",
    "domain": ".facebook.com",
    "path": "/",
    "secure": true,
    "httpOnly": false,
    "sameSite": "None"
  },
  {
    "name": "datr",
    "value": "GIÁ TRỊ TỪ DEVTOOLS",
    "domain": ".facebook.com",
    "path": "/",
    "secure": true,
    "httpOnly": true,
    "sameSite": "None"
  },
  {
    "name": "sb",
    "value": "GIÁ TRỊ TỪ DEVTOOLS",
    "domain": ".facebook.com",
    "path": "/",
    "secure": true,
    "httpOnly": true,
    "sameSite": "None"
  }
]
```

---

## Kiểm tra cookies hoạt động

Sau khi tạo file `fb_cookies.json`, chạy thử:

```bash
python fb_job_bot.py
```

Nếu terminal hiện `Đăng nhập Facebook thành công bằng cookies.` → thành công!

Nếu hiện `Cookies đã hết hạn!` → cần export lại cookies mới.

---

## Lưu ý quan trọng

> ⚠️ **KHÔNG** chia sẻ file `fb_cookies.json` với bất kỳ ai! File này tương đương mật khẩu Facebook của bạn.

> ⚠️ Nếu bạn đổi mật khẩu Facebook hoặc đăng xuất trên trình duyệt → cookies sẽ hết hạn, cần export lại.

> ⚠️ Nên dùng **tài khoản phụ** để chạy bot, phòng trường hợp bị Facebook tạm khóa.
