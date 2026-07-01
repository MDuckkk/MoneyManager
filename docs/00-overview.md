# 00 — Tổng quan

## Bối cảnh

Bài kiểm tra kỹ thuật (Take-home Assignment) cho vị trí **Junior Fullstack Developer**: xây dựng ứng dụng **Quản lý Chi tiêu Cá nhân (Money Manager)** cho phép người dùng theo dõi thu nhập, chi tiêu và quản lý ngân sách hằng tháng.

## Mục tiêu

Đánh giá khả năng phát triển một ứng dụng full-stack hoàn chỉnh:
- Thiết kế cơ sở dữ liệu
- Xây dựng API
- Phát triển giao diện người dùng
- Tổ chức mã nguồn theo nguyên tắc kỹ thuật phần mềm

## Tiêu chí được chấm (và cách bài này đáp ứng)

| Tiêu chí | Cách đáp ứng |
|----------|--------------|
| Tư duy thiết kế | Kiến trúc phân lớp, OCR ẩn sau interface, mô hình dữ liệu rõ ràng |
| Chất lượng mã nguồn | DTO + validation, error handling tập trung, đặt tên nhất quán, unit test phần logic |
| Khả năng giải quyết vấn đề | Budget feedback loop, OCR human-in-the-loop có fallback |
| Cấu trúc rõ ràng, dễ bảo trì, dễ mở rộng | Tổ chức theo feature module, Dependency Inversion, tài liệu đầy đủ |

## Triết lý phạm vi

> Ưu tiên **hoàn thiện chức năng cốt lõi**, đảm bảo ứng dụng chạy ổn định, hơn là nhồi nhiều tính năng làm vội.

- Làm **chắc** các chức năng MUST.
- Một quyết định kỹ thuật được giải thích kỹ > năm tính năng dở.
- Tính năng chưa làm → ghi rõ ở [07-roadmap-assumptions.md](./07-roadmap-assumptions.md).

## Người dùng & phạm vi

- **Actor duy nhất:** Người dùng cá nhân (User).
- Mỗi người dùng chỉ thấy & thao tác trên dữ liệu của chính mình (cô lập theo `userId`).
- Giả định đơn giản hóa: 1 user – 1 loại tiền tệ (VND) – không chia ví/tài khoản (xem chi tiết ở file roadmap).
