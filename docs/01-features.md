# 01 — Chức năng & Use cases

## Danh sách chức năng (đã chốt)

| Nhóm | Mã | Chức năng | Khoe điều gì |
|------|----|-----------|--------------|
| **Tài khoản** | F1 | Đăng ký / đăng nhập (JWT), lấy thông tin user | Bảo mật cơ bản, cô lập dữ liệu |
| **Danh mục** | F2 | CRUD danh mục thu/chi + danh mục mặc định | Quan hệ dữ liệu, ràng buộc |
| **Giao dịch** | F3 | CRUD giao dịch + validation nghiệp vụ | CRUD chuẩn |
| | F4 | Lọc & phân trang (tháng/năm, loại, danh mục, tìm ghi chú) | Query động, hiệu năng |
| | F5 | 🧾 **Quét hóa đơn (OCR) → tạo giao dịch** | Điểm nhấn khác biệt |
| **Ngân sách** | F6 | CRUD ngân sách tháng theo danh mục | Logic nghiệp vụ |
| | F7 | Theo dõi tiến độ + cảnh báo vượt | Tính toán backend |
| **Tổng quan** | F8 | Dashboard: thu/chi/số dư + biểu đồ + tiến độ + so sánh tháng | Trực quan hóa frontend |

### Xuyên suốt (chất lượng kỹ thuật)
Kiến trúc phân lớp · DTO/validation · response envelope nhất quán · error handling tập trung · OCR ẩn sau interface · unit test phần logic · Docker · README.

---

## Use cases chính

```
Actor: Người dùng (User)

UC1 - Đăng ký / Đăng nhập
UC2 - Quản lý danh mục thu/chi (tạo, sửa, xóa)
UC3 - Ghi nhận giao dịch thu nhập / chi tiêu
UC4 - Xem & lọc danh sách giao dịch (theo tháng, loại, danh mục)
UC5 - Sửa / xóa giao dịch
UC6 - Quét hóa đơn để tạo giao dịch (OCR)
UC7 - Thiết lập ngân sách hằng tháng theo danh mục
UC8 - Theo dõi tiến độ ngân sách (đã chi vs giới hạn)
UC9 - Xem tổng quan tài chính tháng (dashboard + biểu đồ)
```

### Chi tiết một số luồng chính

**UC3 — Ghi giao dịch (manual)**
1. User chọn loại (thu/chi) → chọn danh mục → nhập số tiền, ngày, ghi chú.
2. Hệ thống validate: số tiền > 0; danh mục thuộc về user; loại giao dịch khớp loại danh mục.
3. Lưu giao dịch → cập nhật dashboard & tiến độ ngân sách.

**UC6 — Quét hóa đơn (OCR)** → xem chi tiết tại [06-ocr-feature.md](./06-ocr-feature.md).
1. User upload ảnh hóa đơn.
2. Backend gọi OCR service → nhận số tiền, ngày, người bán.
3. App tạo "bản nháp giao dịch" + gợi ý danh mục.
4. User **xem lại, chỉnh sửa** rồi mới lưu (human-in-the-loop).

**UC8 — Theo dõi ngân sách**
1. Với mỗi ngân sách (danh mục + tháng), hệ thống tính tổng đã chi của danh mục đó trong tháng.
2. Tính `% đã dùng = đã chi / hạn mức`.
3. Sinh trạng thái: `SAFE` (<80%), `WARNING` (80–100%), `EXCEEDED` (>100%).
4. Hiển thị thanh tiến độ + badge cảnh báo trên dashboard.

---

## Phân loại ưu tiên (MoSCoW)

- **MUST (làm chắc):** F1, F2, F3, F4, F6, F7, F8.
- **DIFFERENTIATOR (điểm nhấn):** F5 (OCR).
- **COULD / tương lai:** giao dịch định kỳ, đa ví/đa tệ, export CSV, refresh token, gợi ý danh mục bằng ML → [07-roadmap-assumptions.md](./07-roadmap-assumptions.md).
