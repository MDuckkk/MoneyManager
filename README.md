# 💰 Money Manager — Ứng dụng Quản lý Chi tiêu Cá nhân

Ứng dụng full-stack giúp người dùng theo dõi **thu nhập, chi tiêu** và **quản lý ngân sách** hằng tháng, kèm dashboard trực quan.

![stack](https://img.shields.io/badge/Backend-NestJS%20%2B%20TypeORM-E0234E) ![stack](https://img.shields.io/badge/Frontend-React%2019%20%2B%20Vite-61DAFB) ![db](https://img.shields.io/badge/DB-PostgreSQL-336791)

### 🌐 Sản phẩm đang chạy (live)

- **Web:** https://money.mduckkk.me
- **Tài khoản demo:** `demo@money.app` / `password123`

> ⚠️ **Lưu ý quan trọng về OCR trên production**
> Tính năng **Quét hóa đơn (OCR)** đã được **phát triển đầy đủ và chạy được ở môi trường local** (service riêng trong `ocr_service/`, pipeline PaddleOCR + Surya), nhưng **KHÔNG được deploy lên production** vì **hạ tầng hiện tại chưa có GPU**.
> ➡️ Vì vậy bản deploy tại `money.mduckkk.me` chỉ gồm **Frontend + Backend + PostgreSQL**; OCR chạy/demo ở local. Chi tiết ở mục [Giả định & Giới hạn](#-giả-định--giới-hạn).

---

## ✨ Tính năng

| Nhóm | Chức năng |
|------|-----------|
| **Tài khoản** | Đăng ký / đăng nhập (JWT access + refresh), dữ liệu cô lập theo người dùng |
| **Danh mục** | CRUD danh mục thu/chi, danh mục mặc định khi tạo tài khoản, icon + màu |
| **Giao dịch** | CRUD, lọc theo tháng/loại/danh mục, tìm kiếm, phân trang, nhóm theo ngày |
| **Ngân sách** | Đặt hạn mức theo tháng, theo dõi tiến độ + cảnh báo vượt (SAFE/WARNING/EXCEEDED) |
| **Tổng quan** | KPI thu/chi/số dư, biểu đồ cơ cấu chi (donut), thu-chi theo tháng (bar), so sánh tháng trước |

> 🧾 **Quét hóa đơn (OCR)** — đã hiện thực đầy đủ dưới dạng service riêng (`ocr_service/`) và ẩn sau interface `OcrProvider`. **Chạy được ở local**, nhưng chưa deploy production do chưa có GPU (xem lưu ý ở đầu README).

## 🛠️ Công nghệ

- **Backend:** NestJS 11, TypeORM 0.3, PostgreSQL, JWT (Passport-less guard), class-validator.
- **Frontend:** React 19, Vite, React Router 7, Axios, Recharts. CSS thuần với design system (light/dark).
- **Kiến trúc:** phân lớp Controller → Service → Repository; tổ chức theo **feature module** (BE) và **feature folder** (FE).

---

## 🚀 Chạy dự án

### Yêu cầu
- Node.js ≥ 20, npm
- Docker (cho PostgreSQL) — hoặc PostgreSQL cài sẵn

### 1. Khởi động database
```bash
docker compose up -d        # PostgreSQL trên cổng 5544 (user/pass/db = money)
```

### 2. Backend
```bash
cd backend
cp .env.example .env         # đã có sẵn .env mặc định khớp docker-compose
npm install
npm run seed                 # tạo dữ liệu mẫu + tài khoản demo
npm run start:dev            # chạy tại http://localhost:1111
```

### 3. Frontend
```bash
cd frontend
cp .env.example .env
npm install
npm run dev                  # Web: http://localhost:5173
```

### Tài khoản demo (sau khi seed)
```
Email:    demo@money.app
Mật khẩu: password123
```

### 4. (Tùy chọn) OCR service — chỉ chạy local
```bash
cd ocr_service
cp .env.example .env         # OCR_RECOGNIZER=surya + OCR_TABLE_RECOGNITION=1 (pipeline đầy đủ)
python app.py                # FastAPI: POST /scan trả ParsedReceipt
# Backend trỏ tới service qua biến OCR_SERVICE_URL
```
> ⚠️ Trên CPU, một ảnh mất tới **vài phút** để nhận dạng (Surya là transformer OCR). Vì vậy service này **chỉ dùng ở local để demo**, chưa deploy production (cần GPU để đạt tốc độ thực tế).

---

## ☁️ Deploy production

Bản đang chạy tại `money.mduckkk.me` được deploy bằng Docker Compose:

```bash
cd deploy
cp .env.example .env         # điền domain + secret (JWT, DB password)
docker compose -f docker-compose.prod.yml up -d --build
```

- Truy cập tại `money.mduckkk.me`.
- Thành phần deploy: **Frontend + Backend (NestJS) + PostgreSQL**. **Không gồm OCR** (xem lưu ý ở đầu README).

---

## 🧪 Kiểm thử

```bash
cd backend
npm test                     # unit test cho logic ngân sách (status, percentage)
```

---

## 📁 Cấu trúc

```
Money_manager/
├─ docker-compose.yml        # PostgreSQL
├─ backend/                  # NestJS + TypeORM
│  └─ src/
│     ├─ config/             # cấu hình theo concern (app/database/jwt)
│     ├─ common/             # guards, filters, decorators, transformers
│     ├─ database/           # data-source + seed
│     └─ modules/            # auth, users, categories, transactions, budgets, reports
└─ frontend/                 # React + Vite
   └─ src/
      ├─ core/               # axios + BaseApi
      ├─ contexts/           # Auth, Toast
      ├─ app/                # providers + routes
      ├─ shared/             # ui, components, layout, hooks, utils
      └─ features/           # auth, dashboard, transactions, budgets, categories
```

---

## 🧾 Về tính năng Quét hóa đơn (OCR)

Tính năng quét hóa đơn đã được phát triển hoàn chỉnh và kiểm thử, hiện chạy được ở môi trường local.

- **Cách hoạt động:** một service OCR riêng trong `ocr_service/` (FastAPI, `POST /scan` trả về `ParsedReceipt`) đọc ảnh hóa đơn và trích xuất tổng tiền. Backend gọi service này qua interface `OcrProvider` (`HttpOcrProvider` cho pipeline thật, `MockOcrProvider` để chạy khi không có service). Luồng có người xác nhận: quét → tạo bản nháp giao dịch → người dùng duyệt → lưu.
- **Đã kiểm thử:** chạy pipeline PaddleOCR + Surya trên ảnh hóa đơn bán lẻ chụp bằng điện thoại và trích đúng tổng tiền; phần map dữ liệu OCR → giao dịch.
- **Cách chạy thử:** xem [mục 4 phần Chạy dự án](#4-tùy-chọn-ocr-service--chỉ-chạy-local).

Tính năng chưa bật trên bản online vì mô hình nhận dạng (Surya) cần GPU để đạt tốc độ dùng thật, trong khi hạ tầng host hiện tại chỉ có CPU — mỗi ảnh mất tới vài phút. Khi có máy GPU (hoặc chuyển sang recognizer nhẹ hơn, đánh đổi độ chính xác), service có thể bật lên và tích hợp vào backend production mà không cần thay đổi mã.
