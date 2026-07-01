# 📚 Tài liệu thiết kế — Money Manager

Bộ tài liệu thiết kế cho ứng dụng **Quản lý Chi tiêu Cá nhân (Money Manager)**.

## Mục lục

| File | Nội dung |
|------|----------|
| [00-overview.md](./00-overview.md) | Tổng quan, mục tiêu, phạm vi, tiêu chí đánh giá |
| [01-features.md](./01-features.md) | Danh sách chức năng & use cases |
| [02-tech-stack.md](./02-tech-stack.md) | Tech stack & lý do lựa chọn |
| [03-architecture.md](./03-architecture.md) | Kiến trúc hệ thống & tổ chức mã nguồn |
| [04-database.md](./04-database.md) | Thiết kế CSDL (ERD + schema) |
| [05-api.md](./05-api.md) | Đặc tả API (endpoints) |
| [06-ocr-feature.md](./06-ocr-feature.md) | Thiết kế chức năng quét hóa đơn (OCR) |
| [07-roadmap-assumptions.md](./07-roadmap-assumptions.md) | Lộ trình, giả định & hướng phát triển |

## Tóm tắt nhanh

- **Mục tiêu:** App full-stack theo dõi thu/chi và quản lý ngân sách hằng tháng.
- **Tech:** NestJS + Prisma + PostgreSQL (backend) · React + Vite + TS (frontend).
- **3 điểm nhấn:**
  1. 🧾 Quét hóa đơn bằng OCR (human-in-the-loop) → tạo giao dịch.
  2. 🧩 OCR ẩn sau interface (Dependency Inversion) → dễ thay thế, dễ mở rộng.
  3. 💰 Vòng phản hồi ngân sách → Dashboard trực quan.
