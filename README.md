# 💰 Money Manager — Ứng dụng Quản lý Chi tiêu Cá nhân

Ứng dụng full-stack giúp người dùng theo dõi **thu nhập, chi tiêu** và **quản lý ngân sách** hằng tháng, kèm dashboard trực quan.

> Bài take-home cho vị trí Junior Fullstack Developer.

![stack](https://img.shields.io/badge/Backend-NestJS%20%2B%20TypeORM-E0234E) ![stack](https://img.shields.io/badge/Frontend-React%2019%20%2B%20Vite-61DAFB) ![db](https://img.shields.io/badge/DB-PostgreSQL-336791)

### 🌐 Sản phẩm đang chạy (live)

- **Web:** https://money.mduckkk.me
- **Tài khoản demo:** `demo@money.app` / `password123`

> ⚠️ **Lưu ý quan trọng về OCR trên production**
> Tính năng **Quét hóa đơn (OCR)** đã được **phát triển đầy đủ và chạy được ở môi trường local** (service riêng trong `ocr_service/`, pipeline PaddleOCR + Surya), nhưng **KHÔNG được deploy lên production** vì **hạ tầng hiện tại chưa có GPU**. Trên CPU, mô hình nhận dạng Surya mất tới vài phút cho mỗi ảnh nên không đáp ứng thời gian phản hồi thực tế.
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

Bản đang chạy tại `money.mduckkk.me` được deploy bằng Docker Compose (Caddy tự cấp TLS):

```bash
cd deploy
cp .env.example .env         # điền domain + secret (JWT, DB password)
docker compose -f docker-compose.prod.yml up -d --build
```

- Truy cập tại `money.mduckkk.me` (Caddy làm reverse proxy + tự cấp TLS).
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

## 📌 Giả định & Giới hạn

> 📝 *Theo góp ý của mentor: các tính năng chưa kịp hoàn thiện, cùng giả định, giới hạn và hướng phát triển được ghi rõ dưới đây.*

**Giả định**
- 1 người dùng – 1 loại tiền tệ (VND) – không chia ví/tài khoản.
- Số tiền lưu bằng `Decimal` (không dùng float) để tránh sai số.

**Giới hạn hiện tại**
- **OCR chưa deploy production:** đã hiện thực đầy đủ và chạy được ở local, nhưng hạ tầng chưa có **GPU** nên trên CPU quá chậm (Surya ~vài phút/ảnh) để phục vụ thật. Bản online chỉ gồm FE + BE + DB.
- `DB_SYNCHRONIZE=true` đang bật cho cả dev lẫn bản demo (TypeORM tự tạo bảng). Production thực tế nên chuyển sang **migration** trước khi tắt cờ này.
- Chưa có: giao dịch định kỳ, đa tệ, export CSV.

**Hướng phát triển**
- Đưa OCR lên production khi có GPU (hoặc dùng recognizer nhẹ `OCR_RECOGNIZER=paddle` để chạy CPU nhanh hơn, đánh đổi độ chính xác).
- Bổ sung migration cho DB; thêm giao dịch định kỳ, đa tệ và export dữ liệu.

## 🎯 Điểm nhấn thiết kế

1. **Vòng phản hồi ngân sách → Dashboard:** logic tính đã-chi/hạn-mức ở backend nuôi trực quan ở frontend.
2. **Decimal cho tiền tệ** (không dùng float), tách `occurredAt`/`createdAt`, ràng buộc unique chống trùng.
3. **OCR ẩn sau interface** (Dependency Inversion) sẵn sàng cắm pipeline HTTP — dễ mở rộng.
4. **UI/UX:** design system light/dark, số căn theo `tabular-nums`, animation count-up & progress fill, biểu đồ Recharts.
