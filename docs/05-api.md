# 05 — Đặc tả API

- Base URL: `/api`
- Auth: `Authorization: Bearer <accessToken>` (mọi route trừ `/auth/register`, `/auth/login`).
- Response envelope:
  - Thành công: `{ "data": ... }` · List: `{ "data": [...], "meta": { ... } }`
  - Lỗi: `{ "statusCode", "message", "error", "path", "timestamp" }`

## Auth (F1)

| Method | Endpoint | Body | Mô tả |
|--------|----------|------|-------|
| POST | `/auth/register` | `{ email, password, name? }` | Đăng ký, trả `{ accessToken, user }` |
| POST | `/auth/login` | `{ email, password }` | Đăng nhập, trả `{ accessToken, user }` |
| GET | `/auth/me` | — | Thông tin user hiện tại |

## Categories (F2)

| Method | Endpoint | Body / Query | Mô tả |
|--------|----------|--------------|-------|
| GET | `/categories` | `?type=INCOME\|EXPENSE` | Danh sách danh mục |
| POST | `/categories` | `{ name, type, icon? }` | Tạo danh mục |
| PATCH | `/categories/:id` | `{ name?, type?, icon? }` | Sửa danh mục |
| DELETE | `/categories/:id` | — | Xóa (chặn nếu còn giao dịch) |

## Transactions (F3, F4)

| Method | Endpoint | Body / Query | Mô tả |
|--------|----------|--------------|-------|
| GET | `/transactions` | `?month=&year=&type=&categoryId=&search=&page=&limit=` | Lọc + phân trang |
| POST | `/transactions` | `{ categoryId, amount, occurredAt, note?, source?, receiptImageUrl? }` | Tạo giao dịch |
| GET | `/transactions/:id` | — | Chi tiết |
| PATCH | `/transactions/:id` | `{ ...partial }` | Sửa |
| DELETE | `/transactions/:id` | — | Xóa |

Validation: `amount > 0`; `categoryId` phải thuộc user; `type` suy ra từ category.

`GET /transactions` trả:
```json
{
  "data": [ /* transactions */ ],
  "meta": { "page": 1, "limit": 20, "total": 57, "totalPages": 3 }
}
```

## Receipts / OCR (F5)

| Method | Endpoint | Body | Mô tả |
|--------|----------|------|-------|
| POST | `/receipts/scan` | `multipart/form-data: image` | Gọi OCR, trả **bản nháp** (KHÔNG lưu DB) |

Response:
```json
{
  "data": {
    "amount": 152000,
    "occurredAt": "2026-06-28",
    "merchant": "Highlands Coffee",
    "suggestedCategoryId": "uuid-an-uong",
    "lineItems": [{ "name": "Phin sữa đá", "price": 45000 }],
    "confidence": 0.92,
    "rawText": "..."
  }
}
```
→ Client cho user duyệt rồi gọi `POST /transactions` với `source: "OCR"`. Chi tiết: [06-ocr-feature.md](./06-ocr-feature.md).

## Budgets (F6, F7)

| Method | Endpoint | Body / Query | Mô tả |
|--------|----------|--------------|-------|
| GET | `/budgets` | `?month=&year=` | Danh sách ngân sách của tháng |
| POST | `/budgets` | `{ categoryId, month, year, limit }` | Tạo ngân sách |
| PATCH | `/budgets/:id` | `{ limit? }` | Sửa hạn mức |
| DELETE | `/budgets/:id` | — | Xóa |
| GET | `/budgets/status` | `?month=&year=` | **Tiến độ + cảnh báo** (đã chi vs hạn mức) |

`GET /budgets/status` trả mỗi mục:
```json
{
  "categoryId": "uuid",
  "categoryName": "Ăn uống",
  "limit": 3000000,
  "spent": 2400000,
  "percentage": 80,
  "status": "WARNING"
}
```
(`status`: `SAFE` <80%, `WARNING` 80–100%, `EXCEEDED` >100%)

## Reports / Dashboard (F8)

| Method | Endpoint | Query | Mô tả |
|--------|----------|-------|-------|
| GET | `/reports/summary` | `?month=&year=` | Tổng thu / chi / số dư + so sánh tháng trước |
| GET | `/reports/by-category` | `?month=&year=&type=EXPENSE` | Cơ cấu theo danh mục (cho pie chart) |

`GET /reports/summary`:
```json
{
  "data": {
    "income": 20000000,
    "expense": 5400000,
    "balance": 14600000,
    "previousMonth": { "income": 18000000, "expense": 6000000 },
    "expenseChangePct": -10
  }
}
```

## Mã lỗi HTTP dùng
`400` validation · `401` chưa auth · `403` không có quyền · `404` không tìm thấy · `409` trùng (email/ngân sách) · `422` không xử lý được (OCR fail mềm).
