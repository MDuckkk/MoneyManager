# -*- coding: utf-8 -*-
"""
Chuẩn hoá / làm sạch text OCR (tách khỏi run.py để test độc lập) + tiện ích encoding
dùng chung. KHÔNG phụ thuộc model/PIL — chỉ stdlib.
"""
import re
import sys


def ensure_utf8_stdout():
    """Bật UTF-8 cho stdout (in tiếng Việt ra console không vỡ). Gom 1 chỗ thay vì
    lặp `sys.stdout.reconfigure(...)` ở nhiều module. An toàn nếu stream không hỗ trợ."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _strip_tags(txt: str) -> str:
    """Surya recog chèn tag format cho chữ in đậm/nghiêng (vd 'Số: <b>00002154</b>')
    -> bỏ tag HTML + markdown **/__ để regex trích field không vỡ."""
    txt = re.sub(r"</?[a-zA-Z][^>]*>", "", txt)   # <b> </b> <i> <sub> ...
    return txt.replace("**", "").replace("__", "")


# Homoglyph: Surya doi khi tra ky tu Hy Lap/Cyrillic GIONG HET chu Latin
# (vd 'Bộ' -> Greek Beta 'Βộ'). Hai bang nay tach roi hoan toan voi ky tu Latin
# tieng Viet nen quy ve Latin la an toan (chi bo khac biet hinh thuc vo nghia).
_HOMOGLYPH = str.maketrans({
    # Greek (uppercase) -> Latin
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K",
    "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
    # Greek (lowercase nhin giong Latin)
    "ο": "o", "ν": "v", "ρ": "p",
    # Cyrillic (uppercase) -> Latin
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O",
    "Р": "P", "С": "C", "Т": "T", "Х": "X", "У": "Y",
    # Cyrillic (lowercase) -> Latin
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y",
})


def _fix_homoglyphs(txt: str) -> str:
    return txt.translate(_HOMOGLYPH)


def _clean_text(txt: str) -> str:
    """Khu loi lap cua VietOCR tren box dai (vd 'Ha Noi Noi Nha Noi')
    + quy ky tu homoglyph Hy Lap/Cyrillic ve Latin."""
    txt = _fix_homoglyphs(txt)
    ws = txt.split(); u = []
    for w in ws:
        if u and w.lower() == u[-1].lower():
            continue
        u.append(w)
    out, i = [], 0
    while i < len(u):
        if (i + 3 < len(u) and u[i].lower() == u[i+2].lower() and u[i+1].lower() == u[i+3].lower()):
            out += [u[i], u[i+1]]; i += 4
        else:
            out.append(u[i]); i += 1
    return " ".join(out)
