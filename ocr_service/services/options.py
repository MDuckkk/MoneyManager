# -*- coding: utf-8 -*-
"""
Per-request feature flags — override env theo TỪNG request (web UI bật/tắt).

Cơ chế: ContextVar. `asyncio.to_thread` COPY context sang worker thread, và mỗi
request FastAPI chạy trong task riêng (context riêng) -> set_options() ở handler chỉ
ảnh hưởng request đó, an toàn khi nhiều request chạy song song. Không set (vd batch
run.py) -> rơi về env như cũ.

Dùng:
    from options import flag
    if flag("preprocess", "OCR_PREPROCESS", True): ...
"""
import contextvars
import os

_overrides: "contextvars.ContextVar[dict | None]" = contextvars.ContextVar(
    "ocr_request_options", default=None)


def set_options(opts: dict | None) -> None:
    """Đặt override cho request hiện tại (None/key vắng -> dùng env)."""
    _overrides.set(dict(opts) if opts else {})


def _as_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() not in ("0", "false", "no", "off", "")


def flag(key: str, env_name: str, default: bool) -> bool:
    """Bật/tắt 1 tính năng: override request > env > default.
    key: tên trong dict override (web gửi lên). env_name: biến môi trường tương ứng."""
    ov = _overrides.get()
    if ov is not None and ov.get(key) is not None:
        return _as_bool(ov[key])
    raw = os.environ.get(env_name)
    if raw is None:
        return default
    return _as_bool(raw)


def explicit(key: str) -> bool | None:
    """Giá trị override TƯỜNG MINH của request (True/False) khi web có gửi key này;
    None nếu không gửi (-> rơi về env/default). Dùng khi cần phân biệt 'user CHỦ ĐỘNG
    bật' với 'mặc định bật' — vd ép chạy table-vision trên trang known dù bảng vẫn ok."""
    ov = _overrides.get()
    if ov is not None and ov.get(key) is not None:
        return _as_bool(ov[key])
    return None
