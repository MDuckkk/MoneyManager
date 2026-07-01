# -*- coding: utf-8 -*-
"""Entry point — Money Manager OCR service.

Chạy:  uvicorn app:app --host 0.0.0.0 --port 8000

Toàn bộ pipeline nằm trong package `services/`. Ta thêm nó vào sys.path để giữ import
phẳng (`from common import ...`) như thiết kế gốc, rồi expose FastAPI app từ services/api.py.
(api.py tự set env Paddle + tự khởi động Surya service khi cần.)
"""
import os
import sys
from pathlib import Path

_SERVICES = Path(__file__).resolve().parent / "services"
if str(_SERVICES) not in sys.path:
    sys.path.insert(0, str(_SERVICES))

# Nạp .env TRƯỚC khi import api/config (chúng đọc os.environ ngay lúc import).
# Surya được api.py spawn sẽ kế thừa các biến này qua os.environ.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ModuleNotFoundError:
    pass

from api import app  # noqa: E402

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
