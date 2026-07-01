# 💰 Money Manager — Ứng dụng Quản lý Chi tiêu Cá nhân

Ứng dụng full-stack giúp người dùng theo dõi **thu nhập, chi tiêu** và **quản lý ngân sách** hằng tháng, kèm dashboard trực quan.

> Bài take-home cho vị trí Junior Fullstack Developer. Tài liệu thiết kế chi tiết ở thư mục [`docs/`](./docs).

![stack](https://img.shields.io/badge/Backend-NestJS%20%2B%20TypeORM-E0234E) ![stack](https://img.shields.io/badge/Frontend-React%2019%20%2B%20Vite-61DAFB) ![db](https://img.shields.io/badge/DB-PostgreSQL-336791)

---

## ✨ Tính năng

| Nhóm | Chức năng |
|------|-----------|
| **Tài khoản** | Đăng ký / đăng nhập (JWT access + refresh), dữ liệu cô lập theo người dùng |
| **Danh mục** | CRUD danh mục thu/chi, danh mục mặc định khi tạo tài khoản, icon + màu |
| **Giao dịch** | CRUD, lọc theo tháng/loại/danh mục, tìm kiếm, phân trang, nhóm theo ngày |
| **Ngân sách** | Đặt hạn mức theo tháng, theo dõi tiến độ + cảnh báo vượt (SAFE/WARNING/EXCEEDED) |
| **Tổng quan** | KPI thu/chi/số dư, biểu đồ cơ cấu chi (donut), thu-chi theo tháng (bar), so sánh tháng trước |

> 🧾 **Quét hóa đơn (OCR)** đã được thiết kế sẵn (tách sau interface `OcrProvider`) và sẽ triển khai sau — xem [`docs/06-ocr-feature.md`](./docs/06-ocr-feature.md).

## 🛠️ Công nghệ

- **Backend:** NestJS 11, TypeORM 0.3, PostgreSQL, JWT (Passport-less guard), class-validator, Swagger.
- **Frontend:** React 19, Vite, React Router 7, Axios, Recharts. CSS thuần với design system (light/dark).
- **Kiến trúc:** phân lớp Controller → Service → Repository; tổ chức theo **feature module** (BE) và **feature folder** (FE).

Cấu trúc thư mục tuân theo dự án tham chiếu (module/feature-based). Chi tiết: [`docs/03-architecture.md`](./docs/03-architecture.md).

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
npm run start:dev            # API: http://localhost:1111/api  (Swagger: /api/docs)
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
├─ docs/                     # tài liệu thiết kế (overview → API → OCR → roadmap)
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

- 1 người dùng – 1 loại tiền tệ (VND) – không chia ví/tài khoản.
- `DB_SYNCHRONIZE=true` cho môi trường dev (TypeORM tự tạo bảng). Production nên dùng migration.
- Chưa có: giao dịch định kỳ, đa tệ, export CSV, OCR (đã thiết kế, triển khai sau).

Chi tiết & hướng phát triển: [`docs/07-roadmap-assumptions.md`](./docs/07-roadmap-assumptions.md).

## 🎯 Điểm nhấn thiết kế

1. **Vòng phản hồi ngân sách → Dashboard:** logic tính đã-chi/hạn-mức ở backend nuôi trực quan ở frontend.
2. **Decimal cho tiền tệ** (không dùng float), tách `occurredAt`/`createdAt`, ràng buộc unique chống trùng — xem [`docs/04-database.md`](./docs/04-database.md).
3. **OCR ẩn sau interface** (Dependency Inversion) sẵn sàng cắm pipeline HTTP — dễ mở rộng.
4. **UI/UX:** design system light/dark, số căn theo `tabular-nums`, animation count-up & progress fill, biểu đồ Recharts.
