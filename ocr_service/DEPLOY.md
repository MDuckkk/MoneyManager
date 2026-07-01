# ocr_service — deploy notes (Money Manager)

Port of the `ocr_demo_v2` Vietnamese-invoice OCR pipeline, packaged as a **single
CPU-only, keyless, stateless HTTP service** that Money Manager's backend calls via
`OCR_SERVICE_URL`. The pipeline logic is unchanged; only device/config/packaging
were adapted for deployment. For Windows/GPU development use the original two-venv
flow in `CLAUDE.md`.

## What the backend uses

Only two endpoints matter for Money Manager:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET`  | `/health` | `{ok, surya_ok, paddle_ready, ...}` — readiness probe |
| `POST` | `/scan`   | multipart `file` (PDF **or** JPG/PNG) → **ParsedReceipt** JSON |

`/scan` already returns the shape the backend consumes — the field mapping
(`tong_thanh_toan → amount`, `ngay_lap → occurredAt`, `ten_nguoi_ban → merchant`,
`danh_sach_dong_hang → lineItems`) happens inside the service (`receipts.py`), so the
NestJS `HttpOcrProvider` just forwards the JSON. `POST /ocr` stays as a debug endpoint
returning raw per-page fields. The old DB/review/web endpoints were removed (stateless).

## Run locally with Docker

```bash
cd ocr_service
docker build -t mm-ocr .
docker run --rm -p 8000:8000 -v mm-ocr-models:/models mm-ocr
# first boot downloads ~1.5 GB of models into the /models volume (slow once, fast after)

curl http://localhost:8000/health
curl -F "file=@test/mcocr_val_145114aszbc.jpg" http://localhost:8000/scan
```

Một tiến trình duy nhất: `app.py` warm Paddle + Surya (in-process, CPU nên không đụng cuDNN)
rồi phục vụ HTTP. Cấu hình đọc từ `.env` (tự nạp qua python-dotenv). Pipeline nằm trong
`services/`; `PYTHONPATH=/app/services` để import phẳng resolve.

## Run locally without Docker (một venv, một lệnh)

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install paddlepaddle==3.3.1
pip install -r requirements.txt
python app.py         # đọc .env, warm model, phục vụ ở :8000
```

## Deploying to a PaaS

Any Docker host works. Notes:

- **Memory:** needs ~4–8 GB RAM (Paddle + Surya CPU). Pick a plan accordingly.
- **Cold start / latency:** CPU inference for one receipt is ~15–60 s. Mount a
  persistent volume at `/models` (or bake models via `RUN python warmup.py`) so the
  ~1.5 GB download happens once. The backend's `/receipts/scan` call should use a
  generous timeout (60–90 s) and the UI a spinner.
- **Port:** the container honors `$PORT` (Render/Railway/Fly inject it).
- **Fly.io:** `fly launch --no-deploy` then set VM to `shared-cpu-2x` / 8 GB, add a
  volume mounted at `/models`, `fly deploy`.
- **Render:** New Web Service → Docker → set disk mounted at `/models`, health check
  path `/health`.

If CPU latency is unacceptable, this same image runs on a GPU host by overriding
`PADDLE_DEVICE=gpu TORCH_DEVICE=cuda` (and installing GPU wheels) — the backend
contract does not change, only `OCR_SERVICE_URL`.

## Config

See `.env.example`. Deploy defaults: `PADDLE_DEVICE=cpu`, `TORCH_DEVICE=cpu`,
`OCR_ENABLE_POLICY=0` (no Gemini), `OCR_DB_URL=` (stateless).
