# 02 — Tech Stack & Lý do lựa chọn

## Tổng quan

Fullstack một ngôn ngữ (**TypeScript**) cho cả backend và frontend → giảm context-switch, chia sẻ kiểu dữ liệu.

## Backend

| Thành phần | Công nghệ | Lý do |
|-----------|-----------|-------|
| Framework | **NestJS** | Module/DI/DTO sẵn có → thể hiện clean architecture rõ ràng |
| ORM | **Prisma** | Schema rõ, migration tự sinh, type-safe |
| Database | **PostgreSQL** | Quan hệ tốt cho dữ liệu tài chính, hỗ trợ `Decimal` chính xác |
| Auth | **JWT** (`@nestjs/jwt`, `passport-jwt`) | Đủ cho scope, stateless |
| Hash mật khẩu | **bcryptjs** | Chuẩn ngành |
| Validation | **class-validator** + **class-transformer** | Validate input tại biên API qua DTO |
| Test | **Jest** + **Supertest** | Unit test service + e2e API |

## Frontend

| Thành phần | Công nghệ | Lý do |
|-----------|-----------|-------|
| Framework | **React + Vite + TypeScript** | Phổ biến, dev nhanh |
| Server state | **TanStack Query (React Query)** | Cache, loading/error chuẩn, ít boilerplate |
| UI | **Tailwind CSS** (+ component nhẹ) | Nhanh, gọn, dễ kiểm soát |
| Biểu đồ | **Recharts** | Vẽ pie/bar/line đơn giản cho dashboard |
| HTTP client | **Axios** | Interceptor gắn JWT tiện lợi |
| Form | **React Hook Form** + zod (tùy chọn) | Form gọn, validate phía client |

## Hạ tầng / DevEx

| Thành phần | Công nghệ |
|-----------|-----------|
| Database (local) | **Docker Compose** (PostgreSQL) |
| OCR | **Dịch vụ HTTP riêng** (đã có sẵn), gọi qua `OCR_SERVICE_URL` |
| Quản lý cấu hình | `@nestjs/config` + `.env` |

## Vì sao Node/TS thay vì Python?

- Một ngôn ngữ cho cả FE/BE → ít chuyển ngữ cảnh, có thể chia sẻ type.
- NestJS "ép" vào cấu trúc sạch (module, service, DI) — hợp tiêu chí chấm "dễ bảo trì, dễ mở rộng".
- OCR pipeline (Python) vẫn dùng được vì đã là HTTP service độc lập → ngôn ngữ backend không ảnh hưởng.

> **Lưu ý:** Phương án thay thế tương đương là **FastAPI + SQLAlchemy + Alembic** (Python). Quyết định chọn NestJS để tối ưu cho việc trình bày kiến trúc phân lớp.
