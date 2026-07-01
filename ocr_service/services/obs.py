# -*- coding: utf-8 -*-
"""
Observability: cấu hình logging tập trung + correlation theo request-id.

- Mọi log line mang [req=<id>] -> grep được toàn bộ log của 1 request /ocr.
- request_id lưu trong contextvars -> an toàn khi chạy nhiều request (mỗi context riêng).
- Tùy chọn log JSON (OCR_LOG_JSON=1) + ghi file (OCR_LOG_FILE=...) để đẩy ELK/Loki.

Dùng: gọi setup_logging() 1 lần lúc khởi động (api lifespan / run.main);
set_request_id(rid) đầu mỗi request.
"""
import contextvars
import json
import logging
import os
import sys
from collections import OrderedDict, deque

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
_configured = False

# Buffer log in-memory theo request_id -> web demo poll xem pipeline đang đến đâu (LIVE) + log.
_LOG_MAX_REQUESTS = 200
_LOG_MAX_LINES = 800
_log_buffers: "OrderedDict[str, deque]" = OrderedDict()


class _BufferHandler(logging.Handler):
    """Giữ N dòng log gần nhất cho mỗi request_id (ring-buffer, evict request cũ)."""
    def emit(self, record: logging.LogRecord) -> None:
        rid = getattr(record, "request_id", "-")
        if not rid or rid == "-":
            return
        try:
            line = self.format(record)
        except Exception:
            return
        buf = _log_buffers.get(rid)
        if buf is None:
            buf = deque(maxlen=_LOG_MAX_LINES)
            _log_buffers[rid] = buf
            while len(_log_buffers) > _LOG_MAX_REQUESTS:
                _log_buffers.popitem(last=False)
        _log_buffers.move_to_end(rid)
        buf.append(line)


def get_request_log(rid: str) -> list[str]:
    """Các dòng log đã buffer của 1 request (rỗng nếu chưa có / đã evict)."""
    buf = _log_buffers.get(rid)
    return list(buf) if buf else []


def set_request_id(rid) -> None:
    _request_id.set(rid or "-")


def get_request_id() -> str:
    return _request_id.get()


class _RequestIdFilter(logging.Filter):
    """Gắn request_id hiện tại vào mọi log record -> formatter dùng được %(request_id)s."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "msg": record.getMessage(),
        }, ensure_ascii=False)


def setup_logging(force: bool = False) -> None:
    """Cấu hình root logger (idempotent). Level=OCR_LOG_LEVEL, JSON=OCR_LOG_JSON, file=OCR_LOG_FILE."""
    global _configured
    if _configured and not force:
        return
    level = os.environ.get("OCR_LOG_LEVEL", "INFO").upper()
    fmt: logging.Formatter = (
        _JsonFormatter() if os.environ.get("OCR_LOG_JSON") == "1"
        else logging.Formatter("%(asctime)s %(levelname)s [%(name)s] [req=%(request_id)s] %(message)s")
    )
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    logfile = os.environ.get("OCR_LOG_FILE", "")
    if logfile:
        handlers.append(logging.FileHandler(logfile, encoding="utf-8"))
    # Buffer handler: luôn dùng formatter text dễ đọc (web hiển thị), kể cả khi OCR_LOG_JSON=1.
    _buf = _BufferHandler()
    _buf.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    handlers.append(_buf)

    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)
    f = _RequestIdFilter()
    for h in handlers:
        h.setFormatter(fmt)
        h.addFilter(f)            # filter ở handler -> mọi record (kể cả lib khác) có request_id
        root.addHandler(h)
    _configured = True
