# ocr_service — Money Manager OCR

HTTP service đọc **hoá đơn** (ảnh chụp điện thoại hoặc PDF) và trả về thông tin giao dịch
để backend Money Manager tạo bản nháp. Lõi là pipeline PaddleOCR PP-StructureV3 + Surya
(port từ `ocr_demo_v2`, giữ nguyên logic); chạy **CPU, keyless, stateless**.

## API (backend chỉ cần 2 endpoint)

### `GET /health`
```json
{ "ok": true, "surya_ready": true, "paddle_ready": true, "paddle_device": "cpu" }
```

### `POST /scan`  ← endpoint chính
Multipart `file` = ảnh (`.jpg/.jpeg/.png`) hoặc `.pdf`. Trả **ParsedReceipt**:
```json
{
  "amount": 6143500,
  "occurredAt": "2026-05-05",
  "merchant": "CÔNG TY TNHH ...",
  "lineItems": [{ "name": "Cước dịch vụ ...", "price": 4350000 }],
  "confidence": 0.93,
  "needsReview": ["amount"],
  "pageType": "hoa_don_gtgt",
  "rawText": "…",
  "rawFields": { "tong_thanh_toan": "6.143.500", "ngay_lap": "05/05/2026", ... }
}
```
- Không chặn ảnh (guard=`audit`): luôn cố đọc. Không tìm được tổng tiền → `amount: null` +
  `needsReview` chứa `"amount"` (người dùng nhập tay ở Money Manager — human-in-the-loop).
- Backend map 1:1: `amount, occurredAt, merchant, lineItems, confidence` → bản nháp giao dịch.

### `POST /ocr` (debug)
Trả field thô từng trang (`fields`, `confidence`, `needs_review`) — để soi khi cần.

## Chạy nhanh (Docker)
```bash
docker build -t mm-ocr .
docker run --rm -p 8000:8000 -v mm-ocr-models:/models mm-ocr
curl -F "file=@test/mcocr_val_145114aszbc.jpg" http://localhost:8000/scan
```
Lần đầu tải ~1.5 GB model vào volume `/models` (chậm 1 lần). Xem **DEPLOY.md** để deploy.

## Cấu hình
Xem `.env.example`. Mặc định deploy: `PADDLE_DEVICE=cpu`, `TORCH_DEVICE=cpu`,
`OCR_ENABLE_POLICY=0` (không Gemini), `OCR_DB_URL=` (stateless), `OCR_SCAN_GUARD_MODE=audit`.

## Cấu trúc
```
ocr_service/
├── app.py                 # entry: uvicorn app:app (nạp services/ vào path)
├── warmup.py              # (tuỳ chọn) pre-load model
├── requirements.txt · Dockerfile · .dockerignore · .env.example · README · DEPLOY
├── services/              # toàn bộ pipeline (import phẳng)
│   ├── api.py             # tầng HTTP: /health · /scan · /ocr
│   ├── receipts.py        # record -> ParsedReceipt (hàm thuần)
│   ├── surya_engine.py    # Surya recog (gọi in-process, cùng tiến trình Paddle)
│   ├── run.py · common.py · paddle_common.py · config.py · … (pipeline OCR)
│   └── templates/         # schema field theo loại chứng từ
└── test/                  # ảnh hoá đơn mẫu (smoke test)
```
Bản này **không dùng LLM** (đã bỏ Gemini): phân loại bằng keyword/regex, không cần key.
