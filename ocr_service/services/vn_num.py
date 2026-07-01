# -*- coding: utf-8 -*-
"""
Parse "số tiền bằng chữ" tiếng Việt -> int, để cross-check `so_tien_bang_chu`
với tổng tiền dạng số. Thuần stdlib — test offline 100%.

Trả None nếu không parse được (KHÔNG đoán bừa) -> policy coi như "không có tín
hiệu", không flag oan. Yêu cầu giữ DẤU (không strip tone) vì 'mười'(10) và
'mươi'(hàng chục) trùng nhau sau khi bỏ dấu.
"""
import re

# Đơn vị 0-9 + biến thể theo vị trí (mốt=1, tư=4, lăm/nhăm=5) và OCR (bẩy=7)
_UNIT = {
    "không": 0, "một": 1, "hai": 2, "ba": 3, "bốn": 4, "năm": 5,
    "sáu": 6, "bảy": 7, "bẩy": 7, "tám": 8, "chín": 9,
    "mốt": 1, "tư": 4, "lăm": 5, "nhăm": 5,
}
_SCALE = {"nghìn": 1000, "ngàn": 1000, "triệu": 1_000_000, "tỷ": 1_000_000_000, "tỉ": 1_000_000_000}
_SKIP = {"lẻ", "linh"}           # filler hàng 0
_STOP = {"đồng", "chẵn", "chăn"}  # kết thúc phần số


def words_to_int(text):
    """'Sáu triệu một trăm bốn mươi ba nghìn năm trăm đồng chẵn' -> 6143500.
    None nếu rỗng/không nhận dạng được."""
    if not text:
        return None
    toks = re.sub(r"[^\w\sàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]",
                  " ", str(text).lower()).split()
    total = 0      # cộng dồn các block-scale đã chốt
    block = 0      # giá trị block hiện tại (0..999)
    unit = None    # chữ số đơn đang chờ
    seen = False   # đã gặp token số nào chưa
    for t in toks:
        if t in _STOP:
            break
        if t in _UNIT:
            unit = _UNIT[t]; seen = True
        elif t == "mười":
            block += 10; unit = None; seen = True
        elif t == "mươi":
            block += (unit or 0) * 10; unit = None; seen = True
        elif t == "trăm":
            block += (unit or 0) * 100; unit = None; seen = True
        elif t in _SCALE:
            block += (unit or 0); unit = None
            total += block * _SCALE[t]; block = 0; seen = True
        elif t in _SKIP:
            unit = None
        # token lạ -> bỏ qua (không phá parse)
    if not seen:
        return None
    block += (unit or 0)
    return total + block


def amount_matches_words(number, text, tol: int = 0):
    """So tổng tiền (số) với số tiền bằng chữ. Trả:
      True  = khớp (chênh <= tol)
      False = parse được nhưng LỆCH (đáng ngờ)
      None  = không parse được chữ / number None -> không có tín hiệu."""
    if number is None:
        return None
    parsed = words_to_int(text)
    if parsed is None:
        return None
    return abs(int(number) - parsed) <= tol
