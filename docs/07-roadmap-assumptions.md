# 07 — Lộ trình, Giả định & Hướng phát triển

## Lộ trình triển khai (theo giai đoạn)

Mỗi giai đoạn phải **chạy được** mới sang bước sau → luôn có sản phẩm demo.

1. **Setup** — monorepo, Docker (PostgreSQL), Prisma schema + migrate, seed dữ liệu mẫu.
2. **F1 Auth** — register/login/JWT guard + trang login FE.
3. **F2 + F3 + F4** — Categories & Transactions (CRUD + lọc + phân trang). Xương sống.
4. **F6 + F7** — Budget + theo dõi tiến độ/cảnh báo.
5. **F8** — Dashboard: summary + biểu đồ + so sánh tháng.
6. **F5 OCR** — `OcrProvider` interface + `/receipts/scan` + luồng nháp-duyệt ở FE.
7. **Đánh bóng** — error/empty/loading states, unit test (budget calc, OCR mapping), README.

## Giả định (Assumptions)

- 1 người dùng – **1 loại tiền tệ (VND)** – không chia ví/tài khoản.
- Ngân sách theo **tháng dương lịch**.
- Thời gian xử lý theo timezone server.
- OCR pipeline đã tồn tại và expose qua HTTP (ngoài phạm vi bài này phải tự xây).
- Lưu ảnh hóa đơn: lưu cục bộ / thư mục uploads (không tích hợp cloud storage trong scope).

## Giới hạn đã biết (Limitations)

- Chưa có **refresh token** (chỉ access token; hết hạn thì đăng nhập lại).
- Chưa hỗ trợ **đa ví / đa tài khoản / đa tiền tệ**.
- Chưa có **giao dịch định kỳ** (recurring).
- Gợi ý danh mục từ OCR là **rule-based**, chưa dùng ML.
- Chưa có phân quyền nhiều vai trò (chỉ 1 loại user).

## Hướng phát triển (Future work)

| Hạng mục | Mô tả |
|----------|-------|
| Đa ví & đa tiền tệ | Thêm `Account`/`Wallet`, tỉ giá |
| Giao dịch định kỳ | Lịch tự sinh giao dịch (lương, hóa đơn hằng tháng) |
| Export / Import | Xuất CSV/PDF, nhập sao kê ngân hàng |
| Mục tiêu tiết kiệm | Đặt goal + theo dõi tiến độ |
| Refresh token + RBAC | Bảo mật nâng cao |
| OCR + ML | Phân loại danh mục bằng mô hình học máy |
| Thông báo | Cảnh báo vượt ngân sách qua email/push |
| CI/CD | Pipeline test + build + deploy |

## Tài khoản demo (seed)

```
email:    demo@money.app
password: password123
```
Kèm danh mục mặc định + vài giao dịch & ngân sách mẫu trong tháng hiện tại.
