# 03 — Kiến trúc & Tổ chức mã nguồn

## Kiến trúc tổng thể

```
┌────────────┐      HTTP/JSON       ┌────────────────────┐
│   React    │ ───────────────────► │      NestJS API     │
│  (Vite)    │ ◄─────────────────── │  Controller         │
└────────────┘   { data } / { error }│   → Service         │
                                     │     → Prisma (Repo) │
                                     └─────────┬───────────┘
                                               │ SQL
                                         ┌─────▼──────┐
                                         │ PostgreSQL │
                                         └────────────┘
                 OcrProvider (interface)
                       │ HTTP
                 ┌─────▼─────────┐
                 │ OCR service   │  (đã có sẵn, độc lập)
                 └───────────────┘
```

## Nguyên tắc phân lớp

```
Controller  →  chỉ nhận request, validate (DTO), gọi service. KHÔNG chứa logic.
Service     →  toàn bộ logic nghiệp vụ (tính ngân sách, map OCR, kiểm tra quyền sở hữu).
Prisma      →  truy cập dữ liệu (đóng vai Repository).
```

- Controller mỏng, Service dày, truy vấn tách bạch.
- Mọi service nhận `userId` và **chỉ thao tác trên dữ liệu của user đó** (cô lập tenant).

## Cross-cutting concerns

| Concern | Cách xử lý |
|---------|-----------|
| Validation | `ValidationPipe` toàn cục (whitelist, transform) + DTO |
| Error format | `HttpExceptionFilter` toàn cục → envelope `{ statusCode, message, error, path, timestamp }` |
| Response format | `TransformInterceptor` → bọc `{ data }` (list trả `{ data, meta }`) |
| Auth | `JwtAuthGuard` + `JwtStrategy`, decorator `@CurrentUser()` |
| Config | `@nestjs/config` đọc `.env` |

## Tổ chức theo Feature Module

```
money-manager/
├─ docker-compose.yml          # PostgreSQL
├─ README.md
├─ docs/                       # tài liệu thiết kế (file này)
├─ server/                     # NestJS API
│  ├─ prisma/
│  │  ├─ schema.prisma
│  │  └─ seed.ts               # user demo + danh mục + dữ liệu mẫu
│  └─ src/
│     ├─ main.ts               # bootstrap: pipe, filter, interceptor, CORS
│     ├─ app.module.ts
│     ├─ prisma/               # PrismaModule (global) + PrismaService
│     ├─ common/               # filters, interceptors, decorators
│     ├─ auth/                 # F1: controller, service, dto, guard, strategy
│     ├─ categories/           # F2
│     ├─ transactions/         # F3, F4
│     ├─ receipts/             # F5: OCR (controller + OcrProvider interface)
│     ├─ budgets/              # F6, F7
│     └─ reports/              # F8: dashboard/summary
└─ web/                        # React + Vite
   └─ src/
      ├─ api/                  # axios client + react-query hooks
      ├─ components/           # UI tái sử dụng
      ├─ features/             # transactions, budgets, dashboard, receipts
      ├─ pages/                # Login, Dashboard, Transactions, Budgets
      ├─ lib/                  # helpers (format tiền, ngày)
      └─ App.tsx
```

> Tổ chức theo **feature** (không theo loại file) → mỗi tính năng tự chứa, dễ tìm, dễ mở rộng.

## Quyết định kiến trúc nổi bật (ADR rút gọn)

1. **OCR ẩn sau `OcrProvider` interface** (Dependency Inversion): nghiệp vụ không biết OCR chạy bằng gì; đổi nhà cung cấp chỉ thay 1 adapter. Xem [06-ocr-feature.md](./06-ocr-feature.md).
2. **`Decimal(14,2)` cho tiền** (không dùng float) → tránh sai số tài chính.
3. **Tách `occurredAt` (ngày giao dịch) khỏi `createdAt` (ngày nhập)** → báo cáo theo đúng thời điểm phát sinh.
4. **Denormalize `type` trên Transaction** → query/report theo loại nhanh, không cần join Category.
