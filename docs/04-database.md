# 04 — Thiết kế Cơ sở dữ liệu

## Sơ đồ quan hệ (ERD)

```
User (1) ───< (n) Category
User (1) ───< (n) Transaction
User (1) ───< (n) Budget
Category (1) ───< (n) Transaction
Category (1) ───< (n) Budget
```

- Mọi entity nghiệp vụ gắn `userId` → cô lập dữ liệu theo người dùng.
- `Transaction` và `Budget` đều tham chiếu `Category`.

## Bảng & cột

### User
| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| id | uuid (PK) | |
| email | string (unique) | |
| passwordHash | string | bcrypt |
| name | string? | |
| createdAt | datetime | |

### Category
| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| id | uuid (PK) | |
| userId | uuid (FK) | onDelete: Cascade |
| name | string | |
| type | enum `INCOME`/`EXPENSE` | |
| icon | string? | emoji/icon |

Ràng buộc: `@@unique([userId, name, type])` — không trùng tên danh mục cùng loại trong 1 user.

### Transaction
| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| id | uuid (PK) | |
| userId | uuid (FK) | Cascade |
| categoryId | uuid (FK) | Restrict (không xóa danh mục đang có giao dịch) |
| type | enum | denormalized từ Category để query nhanh |
| amount | **Decimal(14,2)** | **không dùng float** |
| note | string? | |
| occurredAt | datetime | ngày giao dịch (khác createdAt) |
| createdAt | datetime | ngày nhập liệu |
| source | enum `MANUAL`/`OCR` | truy vết nguồn gốc (cho F5) |
| receiptImageUrl | string? | ảnh hóa đơn (cho F5) |
| ocrConfidence | Decimal? | độ tin cậy OCR (tùy chọn) |

Index: `@@index([userId, occurredAt])`, `@@index([userId, categoryId])`.

### Budget
| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| id | uuid (PK) | |
| userId | uuid (FK) | Cascade |
| categoryId | uuid (FK) | Cascade |
| month | int | 1–12 |
| year | int | |
| limit | **Decimal(14,2)** | hạn mức |

Ràng buộc: `@@unique([userId, categoryId, month, year])` — 1 hạn mức / danh mục / tháng.

## Quyết định thiết kế (ghi vào README)

1. **`Decimal(14,2)` cho tiền** — float gây sai số khi cộng dồn → không bao giờ dùng cho tài chính.
2. **Tách `occurredAt` / `createdAt`** — báo cáo phải theo ngày phát sinh, không theo ngày nhập.
3. **`@@unique` ngân sách & danh mục** — chống dữ liệu trùng ở tầng DB, không chỉ ở app.
4. **`onDelete` có chủ đích** — xóa user xóa sạch dữ liệu (Cascade); không cho xóa danh mục còn giao dịch (Restrict).
5. **Trường OCR nằm trong Transaction** (không tách bảng riêng) — gọn, đủ truy vết nguồn gốc.

## Lược đồ Prisma

> Lược đồ Prisma đầy đủ nằm tại `server/prisma/schema.prisma`.
