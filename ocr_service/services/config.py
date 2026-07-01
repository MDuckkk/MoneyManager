"""
Cấu hình chung cho OCR service. Bản không-LLM: KHÔNG còn Vertex/Gemini.
- Ngưỡng confidence, unknown-gate
- Guardrails 2 tầng (pixel + layout, KHÔNG dùng vision-API)
- Danh sách PDF mẫu (chỉ cho batch run.py / đối chiếu — service không dùng)
"""

import os
from pathlib import Path

_ROOT = Path(__file__).parent


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() not in ("0", "false", "no", "off", "")


# --- Trích xuất ---
CONFIDENCE_THRESHOLD = float(os.environ.get("OCR_CONFIDENCE_THRESHOLD", "0.85"))
# unknown-class gate: trang không khớp keyword/loại nào -> giá trị này (mặc định "unknown"
# -> đẩy review). Đặt "hoa_don_gtgt" nếu muốn ép về hoá đơn GTGT (legacy).
CLASSIFY_FALLBACK = os.environ.get("OCR_CLASSIFY_FALLBACK", "unknown")

# --- Dữ liệu mẫu (chỉ cho batch run.py; service HTTP không dùng) ---
DOCS_DIR  = _ROOT / "sample_documents"
PHONE_DIR = DOCS_DIR / "anh_chup_dien_thoai"
PDF_FILES: list[tuple[Path, str]] = []

# --- Guardrails 2 tầng ---
# tier1: pixel (trang trắng/ảnh rõ ràng không phải tài liệu). tier2: layout-geometry
# (chấm điểm bố cục vs template, KHÔNG dùng vision-API).
ENABLE_TEMPLATE_GUARD = _env_bool("ENABLE_TEMPLATE_GUARD", True)
TEMPLATE_GUARD_MODE = os.environ.get("TEMPLATE_GUARD_MODE", "strict")  # strict | audit | off
TEMPLATE_GUARD_TIER1_MIN_INK = float(os.environ.get("TEMPLATE_GUARD_TIER1_MIN_INK", "0.002"))
TEMPLATE_GUARD_TIER1_MIN_CONTENT_AREA = float(os.environ.get("TEMPLATE_GUARD_TIER1_MIN_CONTENT_AREA", "0.01"))
TEMPLATE_GUARD_TIER2_MIN_DOCUMENT_SCORE = float(os.environ.get("TEMPLATE_GUARD_TIER2_MIN_DOCUMENT_SCORE", "0.35"))
TEMPLATE_GUARD_TIER2_MIN_TEMPLATE_SCORE = float(os.environ.get("TEMPLATE_GUARD_TIER2_MIN_TEMPLATE_SCORE", "0.45"))
TEMPLATE_GUARD_TIER2_ALLOW_UNCERTAIN_DOCUMENT = _env_bool("TEMPLATE_GUARD_TIER2_ALLOW_UNCERTAIN_DOCUMENT", False)

# --- POLICY engine (format/ngày/MST/cross-check/confidence). Mặc định tắt. ---
ENABLE_POLICY = _env_bool("OCR_ENABLE_POLICY", False)
