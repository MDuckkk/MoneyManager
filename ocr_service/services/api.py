# -*- coding: utf-8 -*-
"""
Money Manager OCR service — trích thông tin hoá đơn từ ảnh chụp / PDF.

Đây là API duy nhất backend cần gọi. Pipeline OCR (Paddle PP-StructureV3 + Surya) chạy
CHUNG 1 tiến trình (in-process); file này là tầng HTTP mỏng: ảnh -> pipeline -> ParsedReceipt.

Khởi động (1 lệnh, từ thư mục gốc ocr_service):
    python app.py

Endpoints:
    GET  /health   -> readiness ({ok, surya_ready, paddle_ready, ...})
    POST /scan     -> upload ảnh/PDF hoá đơn -> ParsedReceipt  ◀── backend dùng cái này
    POST /ocr      -> (debug) field thô từng trang + confidence + needs_review
"""
import os
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("PADDLE_TEXT_DET", "PP-OCRv5_mobile_det")

import re, sys, time, subprocess, uuid, asyncio, logging
from contextlib import asynccontextmanager
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fitz
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Depends, Request

import obs
from ratelimit import RateLimiter
from receipts import to_parsed_receipt

_BASE       = Path(__file__).resolve().parent
API_DIR     = _BASE / "results_api"
API_VIZ_DIR = API_DIR / "viz"                 # predict_page cần 1 thư mục viz để ghi ảnh debug
API_VIZ_DIR.mkdir(parents=True, exist_ok=True)

# predict_page/parse_page nằm trong run.py (import kéo theo Paddle stack — KHÔNG import torch ở đây).
from run import detect_page, recognize_page, parse_page

PADDLE_DEVICE = os.environ.get("PADDLE_DEVICE", "cpu")
MAX_UPLOAD_MB = int(os.environ.get("OCR_MAX_UPLOAD_MB", "50"))
MAX_PDF_PAGES = int(os.environ.get("OCR_MAX_PDF_PAGES", "30"))
API_KEY       = os.environ.get("OCR_API_KEY", "")          # bật auth khi đặt (header X-API-Key)
LLM_CONCURRENCY = max(1, int(os.environ.get("OCR_LLM_CONCURRENCY", "4")))
# /scan mặc định KHÔNG chặn: hoá đơn bán lẻ không khớp template doanh nghiệp; 'audit' chỉ ghi nhận,
# không reject -> luôn OCR và trả kết quả (chất lượng để human-in-the-loop ở Money Manager lo).
SCAN_GUARD_MODE = os.environ.get("OCR_SCAN_GUARD_MODE", "audit")

obs.setup_logging()
log = logging.getLogger("ocr.api")

# OCR nặng chạy trong thread; lock để mỗi lúc chỉ 1 request dùng PP-StructureV3 (Paddle singleton).
_ocr_lock   = asyncio.Lock()
SURYA_CONCURRENCY = max(1, int(os.environ.get("OCR_SURYA_CONCURRENCY", "2")))
_surya_sem  = asyncio.Semaphore(SURYA_CONCURRENCY)
SPLIT_LOCK  = os.environ.get("OCR_SPLIT_LOCK", "1") != "0"
_paddle_ready = False
_paddle_error = None
_surya_ready = False

ACCEPTED_EXT = (".pdf", ".jpg", ".jpeg", ".png")   # fitz mở ảnh như doc 1 trang -> pipeline y hệt


def _accepted_upload(filename: str | None) -> bool:
    return bool(filename) and filename.lower().endswith(ACCEPTED_EXT)


def _require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "Thiếu hoặc sai X-API-Key")


RATE_PER_MIN = int(os.environ.get("OCR_RATE_PER_MIN", "0"))
_rate_limiter = RateLimiter(RATE_PER_MIN, window_s=60)


def _rate_limit(request: Request, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    if RATE_PER_MIN <= 0:
        return
    key = x_api_key or (request.client.host if request.client else "anon")
    if not _rate_limiter.allow(key):
        raise HTTPException(429, "Quá nhiều request — thử lại sau",
                            headers={"Retry-After": str(int(_rate_limiter.retry_after(key)) + 1)})


# ---------------------------------------------------------------------------
# Lifespan — warm model (Paddle + Surya) IN-PROCESS lúc khởi động (1 tiến trình duy nhất)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(app):
    global _paddle_ready, _paddle_error, _surya_ready
    _use_surya = os.environ.get("OCR_RECOGNIZER", "paddle").lower() == "surya"
    log.info("Warm up models (Paddle%s)…", " + Surya" if _use_surya else "")
    import numpy as np
    from paddle_common import get_engine
    try:
        eng = get_engine()
        eng.predict(np.ones((64, 64, 3), dtype=np.uint8) * 255)   # ép load hết sub-model Paddle
        _paddle_ready = True
        log.info("Paddle ready.")
    except Exception as e:
        _paddle_error = f"{type(e).__name__}: {e}"
        log.exception("Paddle warmup lỗi -> paddle_ready=False")
    if _use_surya:
        try:
            from run import _get_surya
            _get_surya()      # load Surya model (lần đầu tải ~1.5GB) — chỉ khi recognizer=surya
            _surya_ready = True
            log.info("Surya ready.")
        except Exception:
            log.exception("Surya warmup lỗi -> surya_ready=False")
    else:
        _surya_ready = True   # recognizer=paddle -> KHÔNG cần Surya
        log.info("Recognizer=paddle -> bỏ qua Surya.")

    yield


app = FastAPI(title="Money Manager OCR service", lifespan=_lifespan)


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

_TOGGLE_NAMES = ("preprocess", "img_enhance", "table_vision", "table_deskew", "enhance", "extract_unknown")


async def _read_validated(file: UploadFile) -> bytes:
    if not _accepted_upload(file.filename):
        raise HTTPException(400, "Chỉ nhận PDF hoặc ảnh (.jpg/.jpeg/.png)")
    if not (_paddle_ready and _surya_ready):
        raise HTTPException(503, "Model chưa sẵn sàng — kiểm tra /health")
    data = await file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File quá lớn (> {MAX_UPLOAD_MB} MB)")
    return data


async def _run_pipeline(data: bytes, filename: str, guard_mode: str, toggles: dict) -> list[dict]:
    """Chạy pipeline cho cả file -> list record từng trang (đã parse). Stateless: không lưu DB."""
    from options import set_options
    from enhance import maybe_enhance_record
    set_options(toggles)
    rid = uuid.uuid4().hex
    obs.set_request_id(rid)

    base = re.sub(r"[^\w._-]", "_", filename or "upload")
    tmp_path = API_DIR / f"{rid[:8]}_{base}"
    tmp_path.write_bytes(data)
    try:
        # PDF -> đếm trang bằng fitz; ẢNH -> 1 trang (mở bằng PIL ở detect_page). Validate sớm
        # để file hỏng/định dạng lạ trả 400 gọn thay vì 500.
        if tmp_path.suffix.lower() == ".pdf":
            try:
                n_pages = len(fitz.open(str(tmp_path)))
            except Exception as e:
                raise HTTPException(400, f"PDF không đọc được ({type(e).__name__})")
        else:
            from PIL import Image as _PILImage
            try:
                with _PILImage.open(str(tmp_path)) as _im:
                    _im.verify()
            except Exception as e:
                raise HTTPException(400, f"Ảnh không đọc được / định dạng không hỗ trợ ({type(e).__name__})")
            n_pages = 1
        if n_pages > MAX_PDF_PAGES:
            raise HTTPException(413, f"Quá nhiều trang ({n_pages} > {MAX_PDF_PAGES})")
        log.info("nhận '%s' (%d KB, %d trang) guard=%s", filename, len(data) // 1024, n_pages, guard_mode)

        # PHA 1 — OCR (GPU/CPU): PP serialize dưới lock; Surya ngoài lock, cap bởi semaphore.
        raws = [None] * n_pages
        for pg in range(n_pages):
            if SPLIT_LOCK:
                async with _ocr_lock:
                    det = await asyncio.to_thread(detect_page, tmp_path, pg, API_VIZ_DIR, guard_mode)
                async with _surya_sem:
                    raws[pg] = await asyncio.to_thread(recognize_page, det)
            else:
                async with _ocr_lock:
                    det = await asyncio.to_thread(detect_page, tmp_path, pg, API_VIZ_DIR, guard_mode)
                    raws[pg] = await asyncio.to_thread(recognize_page, det)

        # PHA 2 — parse/trích field: song song giữa các trang.
        sem = asyncio.Semaphore(LLM_CONCURRENCY)

        async def _parse_one(pg, raw):
            async with sem:
                rec = await asyncio.to_thread(parse_page, raw, raw["page_type"], 0.0, API_VIZ_DIR)
                rec = await asyncio.to_thread(maybe_enhance_record, rec, tmp_path, pg)
                return rec

        records = await asyncio.gather(*[_parse_one(pg, raws[pg]) for pg in range(n_pages)])
        return list(records)
    finally:
        tmp_path.unlink(missing_ok=True)


def _page_view(pg: int, r: dict) -> dict:
    return {
        "page": pg,
        "page_type": r.get("page_type"),
        "unknown": bool(r.get("unknown", False)),
        "template_used": r.get("template_used"),
        "fields": r.get("fields", {}),
        "confidence": r.get("confidence", {}),
        "needs_review": r.get("needs_review", []),
        "needs_review_reasons": r.get("needs_review_reasons", {}),
        "raw_text": r.get("raw_text"),
        "rejected": r.get("rejected"),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"ok": True, "surya_ready": _surya_ready,
            "paddle_ready": _paddle_ready, "paddle_device": PADDLE_DEVICE,
            "paddle_error": _paddle_error}


@app.post("/scan", dependencies=[Depends(_require_api_key), Depends(_rate_limit)])
async def scan(file: UploadFile = File(...)):
    """Backend gọi endpoint này. Upload ảnh/PDF hoá đơn -> ParsedReceipt (trang đầu).

    Không chặn ảnh (guard=audit): luôn cố đọc & trả kết quả; nếu không tìm được tổng tiền
    thì vẫn trả về (amount=null) kèm cờ review để người dùng nhập tay ở Money Manager.
    """
    t0 = time.time()
    data = await _read_validated(file)
    toggles = {n: None for n in _TOGGLE_NAMES}
    # Giữ trang chưa phân loại (hoá đơn bán lẻ không khớp template doanh nghiệp) thay vì reject
    # -> vẫn trả record kèm raw_text để fallback lấy tổng tiền. KHÔNG gọi LLM (đã bỏ).
    toggles["extract_unknown"] = True
    records = await _run_pipeline(data, file.filename, SCAN_GUARD_MODE, toggles)
    page = next((r for r in records if not r.get("rejected")), records[0] if records else None)
    if page is None:
        raise HTTPException(422, "Không đọc được nội dung hoá đơn")
    receipt = to_parsed_receipt(page)
    if receipt["amount"] is None and "amount" not in receipt["needsReview"]:
        receipt["needsReview"].append("amount")
    receipt["elapsedMs"] = int((time.time() - t0) * 1000)
    log.info("/scan '%s' -> amount=%s merchant=%s conf=%s (%dms)",
             file.filename, receipt["amount"], receipt["merchant"], receipt["confidence"],
             receipt["elapsedMs"])
    return receipt


@app.post("/ocr", dependencies=[Depends(_require_api_key), Depends(_rate_limit)])
async def ocr(file: UploadFile = File(...), guard_mode: str = Form("audit"),
              preprocess: bool | None = Form(None), img_enhance: bool | None = Form(None),
              table_vision: bool | None = Form(None), table_deskew: bool | None = Form(None),
              enhance: bool | None = Form(None), extract_unknown: bool | None = Form(None)):
    """(Debug) Trả field thô từng trang. guard_mode: strict | audit | off."""
    guard_mode = (guard_mode or "audit").strip().lower()
    if guard_mode not in ("strict", "audit", "off"):
        raise HTTPException(400, "guard_mode phải là strict, audit hoặc off")
    data = await _read_validated(file)
    toggles = {"preprocess": preprocess, "img_enhance": img_enhance, "table_vision": table_vision,
               "table_deskew": table_deskew, "enhance": enhance, "extract_unknown": extract_unknown}
    records = await _run_pipeline(data, file.filename, guard_mode, toggles)
    return {"filename": file.filename, "n_pages": len(records),
            "guard_mode": guard_mode, "pages": [_page_view(i, r) for i, r in enumerate(records)]}
