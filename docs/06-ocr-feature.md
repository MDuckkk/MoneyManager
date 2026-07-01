# 06 — Chức năng Quét hóa đơn (OCR) — F5

> Điểm nhấn khác biệt của ứng dụng: chụp hóa đơn → tự điền giao dịch.

## Luồng người dùng

```
Chụp/upload hóa đơn
        ↓
Backend gọi OCR service (HTTP) → trích: số tiền, ngày, người bán, line items
        ↓
App tạo "bản nháp giao dịch" + gợi ý danh mục
        ↓
Người dùng XEM LẠI, chỉnh sửa nếu cần   ←── human-in-the-loop
        ↓
Bấm Lưu → tạo Transaction (source = OCR, đính kèm ảnh)
```

## Vì sao "nháp → duyệt → lưu" thay vì tự lưu thẳng?

OCR không bao giờ chính xác 100%. Thiết kế **human-in-the-loop**:
- Đặt trải nghiệm & độ chính xác của người dùng lên trên.
- Thể hiện hiểu biết về giới hạn của AI/OCR.
- An toàn dữ liệu: không ghi rác vào sổ chi tiêu.

## Tích hợp: OCR là dịch vụ HTTP riêng

```
[React] → POST /api/receipts/scan (ảnh)
            ↓
[NestJS]  HttpOcrProvider ──HTTP──► [OCR service]  (OCR_SERVICE_URL)
            ↓ (ParsedReceipt)
          map + gợi ý danh mục → trả "bản nháp" cho FE
            ↓
[React] user duyệt → POST /api/transactions (source=OCR)
```

Cấu hình: thêm `OCR_SERVICE_URL` vào `.env`.

## Thiết kế kiến trúc: ẩn OCR sau interface (Dependency Inversion)

Nghiệp vụ **không** gọi OCR trực tiếp. Định nghĩa một cổng trừu tượng:

```ts
// Cổng trừu tượng — nghiệp vụ không biết OCR chạy bằng gì
interface OcrProvider {
  parseReceipt(file: Buffer): Promise<ParsedReceipt>;
}

interface ParsedReceipt {
  amount: number | null;
  occurredAt: string | null;       // ISO date
  merchant: string | null;
  lineItems?: { name: string; price: number }[];
  rawText: string;
  confidence: number;              // 0..1
}
```

Hai implementation:
- **`HttpOcrProvider`** → gọi OCR service thật qua HTTP.
- **`MockOcrProvider`** → trả dữ liệu mẫu, dùng khi chấm/test không có pipeline.

Chọn implementation qua DI / biến môi trường.

**Lợi ích (ghi vào README):** đổi nhà cung cấp OCR chỉ cần thay 1 adapter, không động vào nghiệp vụ → đúng tiêu chí "dễ bảo trì, dễ mở rộng".

## Chịu lỗi (resilience)

- Gọi OCR có **timeout** (vd 10s).
- OCR lỗi/chậm → trả `422` mềm + thông điệp → người dùng nhập tay.
- OCR là **enhancement**, không phải điểm chết của luồng ghi giao dịch.

## Gợi ý danh mục thông minh (rule-based)

Map từ khóa người bán → danh mục:

| Từ khóa (merchant) | Danh mục gợi ý |
|--------------------|----------------|
| highlands, starbucks, coffee, quán, nhà hàng | Ăn uống |
| grab, be, taxi, xăng | Di chuyển |
| điện, nước, internet, hóa đơn | Hóa đơn |
| circle k, vinmart, mart, shop | Mua sắm |

Đơn giản, dễ mở rộng. README ghi: *"có thể nâng cấp lên mô hình ML phân loại sau"*.

## Tầng dữ liệu

Thêm vào `Transaction` (không cần bảng riêng):
- `source`: `MANUAL` | `OCR` — truy vết nguồn gốc.
- `receiptImageUrl`: ảnh hóa đơn đã lưu.
- `ocrConfidence`: độ tin cậy (tùy chọn, để FE hiển thị).

## API liên quan

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/receipts/scan` | Upload ảnh → trả ParsedReceipt (không lưu) |
| POST | `/api/transactions` | Lưu giao dịch đã duyệt (`source: "OCR"`) |

Xem [05-api.md](./05-api.md) để biết shape response.
