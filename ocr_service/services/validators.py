# -*- coding: utf-8 -*-
"""
Validator format/checksum cho các trường "nguy hiểm" (concern #1).

Thuần stdlib — test offline 100%. Dùng bởi field_policy để quyết một trường có
đáng ngờ không (đẩy needs_review) MÀ KHÔNG cho LLM sửa.

LƯU Ý dữ liệu demo synthetic: MST mẫu (vd 0101230004) KHÔNG thỏa checksum mod-11
thật. Vì vậy `mst_checksum_ok` chỉ là tiện ích — policy mặc định CHỈ kiểm format
MST (10/13 số); bật checksum qua cấu hình khi chạy dữ liệu thật.
"""
import re
from datetime import datetime


def valid_format(value, pattern: str) -> bool:
    """Khớp regex (pattern lấy từ template). None/rỗng -> False."""
    if value is None:
        return False
    return re.fullmatch(pattern, str(value).strip()) is not None


def valid_date(value, min_year: int = 2015, max_year: int = 2035) -> bool:
    """Chấp nhận DD/MM/YYYY hoặc YYYY-MM-DD; ngày lịch hợp lệ + năm trong [min,max]."""
    if value is None:
        return False
    s = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            d = datetime.strptime(s, fmt)
        except ValueError:
            continue
        return min_year <= d.year <= max_year
    return False


def valid_thue_suat(value, allowed=(0, 5, 8, 10)) -> bool:
    """thue_suat dạng '10%' / '10' / 10 -> phải thuộc tập suất hợp lệ."""
    if value is None:
        return False
    m = re.search(r"\d+", str(value))
    return bool(m) and int(m.group()) in allowed


def valid_mst_format(value) -> bool:
    """MST: 10 số, hoặc 13 số (10 + '-' + 3 số chi nhánh)."""
    if value is None:
        return False
    return re.fullmatch(r"\d{10}(-\d{3})?", str(value).strip()) is not None


# --- MST checksum (mod-11, theo trọng số GDT) — TIỆN ÍCH, off mặc định cho demo ---

_MST_WEIGHTS = (31, 29, 23, 19, 17, 13, 7, 5, 3)


def mst_check_digit(first9: str) -> int:
    """Chữ số kiểm của MST 10 số từ 9 số đầu (11 - (Σ dᵢ·wᵢ mod 11); 11->0)."""
    s = sum(int(c) * w for c, w in zip(first9, _MST_WEIGHTS))
    cd = 11 - (s % 11)
    return 0 if cd == 11 else cd


def mst_checksum_ok(value) -> bool:
    """True nếu MST 10 số (hoặc phần 10 số của MST 13) thỏa checksum. cd==10 -> không hợp lệ."""
    if not valid_mst_format(value):
        return False
    digits = str(value).strip().replace("-", "")[:10]
    cd = mst_check_digit(digits[:9])
    return cd != 10 and cd == int(digits[9])
