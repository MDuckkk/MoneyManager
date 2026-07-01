# OCR service — single Linux container, CPU-only, keyless, ONE process.
# Paddle + Surya chạy chung 1 tiến trình (CPU nên không đụng cuDNN). Entry: app.py.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # --- device: CPU everywhere ---
    PADDLE_DEVICE=cpu \
    TORCH_DEVICE=cpu \
    SURYA_QUANT=int8 \
    FLAGS_use_mkldnn=0 \
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
    PADDLE_TEXT_DET=PP-OCRv5_mobile_det \
    # --- keyless + stateless ---
    OCR_ENABLE_POLICY=0 \
    OCR_DB_URL= \
    # --- pipeline dùng import phẳng, code nằm trong services/ ---
    PYTHONPATH=/app/services \
    # --- model cache (mount a volume here to persist across restarts) ---
    HF_HOME=/models/hf

# System libs: libglib for opencv-headless, libgomp for paddle/torch, fonts for viz text.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgomp1 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Heavy, rarely-changing layers first (better build cache):
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install paddlepaddle==3.3.1

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# OPTIONAL: pre-download models at build time so the first request is fast
# (bloats the image ~1.5 GB but avoids a slow cold start). Enable if your host
# has no persistent volume for /models:
# RUN python warmup.py

EXPOSE 8000

# Một tiến trình duy nhất: app.py warm Paddle + Surya (in-process) rồi phục vụ HTTP.
# ${PORT} để Render/Fly/Railway inject cổng public; mặc định 8000.
CMD ["/bin/sh","-c","exec python -m uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
