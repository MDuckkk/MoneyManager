# -*- coding: utf-8 -*-
"""
Định vị field trên trang: từ fields đã extract (LLM/regex) + OCR lines/cells,
tìm bbox [x1,y1,x2,y2] tương ứng trên ảnh.

Dùng cho vision cross-check: thay vì gửi full-page, crop chính xác vùng chứa
field đó -> Gemini đọc chuẩn hơn, ít bị nhiễu từ nội dung xung quanh.
"""
import re
from common import strip_tones


def _norm(s) -> str:
    """Strip tones + lowercase + chỉ giữ alphanumeric.
    Dùng để fuzzy-match: LLM sửa dấu (QUẨN->QUẢN) nhưng sau strip_tones đều giống nhau."""
    return re.sub(r'[^a-z0-9]', '', strip_tones(str(s)).lower())


def _merge_bboxes(bboxes: list) -> list:
    return [min(b[0] for b in bboxes), min(b[1] for b in bboxes),
            max(b[2] for b in bboxes), max(b[3] for b in bboxes)]


def _fmt_vn(n: int) -> str:
    """22000000 -> '22.000.000' (dấu chấm ngàn kiểu Việt Nam)."""
    return f"{n:,}".replace(",", ".")


def _date_variants(date_iso: str) -> list[str]:
    """'2026-05-05' -> normalized forms của '05/05/2026' và '05-05-2026'."""
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_iso)
    if not m:
        return []
    y, mo, d = m.groups()
    return [_norm(f"{d}/{mo}/{y}"), _norm(f"{d}-{mo}-{y}")]


def _find_line(search_norm: str, lines: list) -> dict | None:
    """Tìm dòng OCR ngắn nhất chứa search_norm (substring). Min length 4 để tránh false positive."""
    if not search_norm or len(search_norm) < 4:
        return None
    best, best_len = None, 9999
    for line in lines:
        nl = _norm(line["text"])
        if search_norm in nl and len(nl) < best_len:
            best, best_len = line, len(nl)
    return best


def _find_date_line(date_iso: str, lines: list) -> dict | None:
    """Tìm dòng chứa ngày theo kiểu Việt Nam: 'Ngày 08 tháng 06 năm 2026'.
    Kiểm tra dòng chứa CẢ 3 phần: năm, tháng, ngày."""
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_iso)
    if not m:
        return None
    y, mo, d = m.groups()
    d_int, mo_int = str(int(d)), str(int(mo))   # bỏ leading zero ("08" -> "8")
    for line in lines:
        t = line["text"]
        if y in t and (mo in t or mo_int in t) and (d in t or d_int in t):
            return line
    return None


def _bbox_for_value(name: str, value, lines: list) -> list | None:
    """Thử các biểu diễn khác nhau của value để tìm bbox trong OCR lines."""
    if value is None:
        return None

    # Date ISO: "Ngày 08 tháng 06 năm 2026" — không thể normalize bình thường
    if isinstance(value, str) and re.match(r'\d{4}-\d{2}-\d{2}', value):
        line = _find_date_line(value, lines)
        if line:
            return line["bbox"]
        # fallback: thử d/m/y format
        for s in _date_variants(value):
            line = _find_line(s, lines)
            if line:
                return line["bbox"]
        return None

    searches = []
    if isinstance(value, str) and value.strip():
        searches.append(_norm(value))
    elif isinstance(value, int) and value > 0:
        searches.append(_norm(str(value)))
        searches.append(_norm(_fmt_vn(value)))
    elif isinstance(value, float):
        searches.append(_norm(str(int(value))))

    for s in searches:
        line = _find_line(s, lines)
        if line:
            return line["bbox"]

    # Fallback cho string dài nhiều từ: tìm các từ dài (>=5 char), merge bbox
    if isinstance(value, str) and ' ' in value:
        long_words = [w for w in _norm(value).split() if len(w) >= 5]
        if long_words:
            matched = [l for l in lines if any(w in _norm(l["text"]) for w in long_words)]
            if matched:
                return _merge_bboxes([l["bbox"] for l in matched])

    return None


def match_field_bboxes(fields: dict, lines: list, tables: list) -> dict:
    """Trả {field_name: [x1,y1,x2,y2]} cho các field định vị được trong OCR lines.
    danh_sach_dong_hang bỏ qua (list — không map 1-1 vào 1 bbox)."""
    result = {}
    for name, value in fields.items():
        if name == "danh_sach_dong_hang":
            continue
        bbox = _bbox_for_value(name, value, lines)
        if bbox:
            result[name] = bbox
    return result


def crop_field_images(field_bboxes: dict, img, padding: int = 15) -> dict:
    """Crop PIL Image tại mỗi bbox, thêm padding, trả {field_name: PNG bytes}.
    Dùng khi có field_bboxes để chuẩn bị ảnh cho vision cross-check."""
    import io
    W, H = img.size
    crops = {}
    for name, bbox in field_bboxes.items():
        x1, y1, x2, y2 = bbox
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(W, x2 + padding)
        y2 = min(H, y2 + padding)
        if x2 <= x1 or y2 <= y1:
            continue
        crop = img.crop((x1, y1, x2, y2))
        buf = io.BytesIO()
        crop.save(buf, format="PNG")
        crops[name] = buf.getvalue()
    return crops
