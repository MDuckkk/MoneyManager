"""
Dung chung cho 2 tool dung PaddleOCR PP-StructureV3:
  - tools/paddle/run.py          (PaddleOCR thuan)
  - tools/paddle_vietocr/run.py  (Paddle detection + VietOCR recognition)
Gom: engine PP-StructureV3 (lazy) + cac helper doc bang (so_dong_hang / danh_sach).
paddleocr chi import ben trong get_engine -> cac tool khac khong bi keo paddle.
"""
import os
os.environ.setdefault("FLAGS_use_mkldnn", "0")                      # tranh bug oneDNN PIR tren CPU
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

import re

_engine = None
# GPU (GTX 1650) cho nhanh; PADDLE_DEVICE=cpu de quay ve CPU.
PADDLE_DEVICE = os.environ.get("PADDLE_DEVICE", "gpu")
# Text detector (DB++). Mac dinh server; PADDLE_TEXT_DET=PP-OCRv5_mobile_det -> box chat hon.
TEXT_DET_MODEL = os.environ.get("PADDLE_TEXT_DET", "PP-OCRv5_server_det")


def get_engine():
    global _engine
    if _engine is None:
        from paddleocr import PPStructureV3
        # use_seal_recognition: nhan dau/seal do (ducbm 'detect sign') — mac dinh OFF cho nhe GPU,
        # bat bang OCR_SEAL_RECOGNITION=1 khi can soi con dau.
        _use_seal = os.environ.get("OCR_SEAL_RECOGNITION", "0") == "1"
        # Bảng SLANet nặng trên CPU. Chỉ cần tổng tiền -> tắt bằng OCR_TABLE_RECOGNITION=0.
        _use_table = os.environ.get("OCR_TABLE_RECOGNITION", "1") == "1"
        _engine = PPStructureV3(
            device=PADDLE_DEVICE,
            text_detection_model_name=TEXT_DET_MODEL,
            enable_mkldnn=False,                 # chi anh huong CPU; GPU bo qua
            use_doc_orientation_classify=False, use_doc_unwarping=False,
            use_formula_recognition=False, use_seal_recognition=_use_seal,
            use_chart_recognition=False, use_textline_orientation=False,
            use_table_recognition=_use_table,
        )
    return _engine


def _to_int(s: str):
    digits = re.sub(r"\D", "", s or "")
    return int(digits) if digits else None


def _count_line_items(rows: list[list[str]]) -> int:
    """So dong hang = tong so token-so trong o STT cac dong du lieu
    -> chiu duoc loi gop o cua model (vd o STT '2 3' -> 2 dong)."""
    return sum(len(re.findall(r"\d+", r[0])) for r in rows)


def _table_layout(cells: list[dict], lines: list[dict]):
    """Tinh bo-cuc bang de dung hang TU LINE: cot = tu hang HEADER (cell bang tren cung),
    lrows = LINE trong bang (duoi header, tren day) gom theo bang-y. -> (cols, lrows) | None."""
    from common import _group_rows
    if not cells or not lines:
        return None
    cb = [(c["bbox"][0], c["bbox"][1], c["bbox"][2], c["bbox"][3]) for c in cells]
    cell_rows = _group_rows(cb)
    if not cell_rows:
        return None
    header = sorted(cell_rows[0], key=lambda b: b[0])     # hang dau = header -> bien cot
    cols = [(b[0], b[2]) for b in header]
    if len(cols) < 2:
        return None
    tx1, tx2 = min(b[0] for b in cb), max(b[2] for b in cb)
    ty2 = max(b[3] for b in cb)
    hdr_bot = max(b[3] for b in header)
    cols[0] = (min(cols[0][0], tx1), cols[0][1])          # noi rong cot dau/cuoi bat line lech
    cols[-1] = (cols[-1][0], max(cols[-1][1], tx2))
    tl = [l for l in lines                                 # line TRONG bang (dai-x), DUOI header, TREN day bang
          if l["bbox"][0] >= tx1-4 and l["bbox"][2] <= tx2+4
          and hdr_bot < (l["bbox"][1]+l["bbox"][3])/2 < ty2+4]
    if not tl:
        return None
    lrows = _group_rows([(l["bbox"][0], l["bbox"][1], l["bbox"][2], l["bbox"][3], l["text"]) for l in tl])
    return cols, lrows


def _rows_from_lines(cells: list[dict], lines: list[dict]) -> list[list[str]]:
    """Dung lai hang bang TU LINE da doc (khong dinh loi SLANet gop CA hang).
    Moi line gan vao cot theo x. Line wrap (ten hang xuong dong) -> noi vao item truoc."""
    lay = _table_layout(cells, lines)
    if not lay:
        return []
    cols, lrows = lay
    out = []
    for lr in lrows:
        row = [""] * len(cols)
        for it in lr:
            cx = (it[0] + it[2]) / 2
            ci = next((i for i, (a, b) in enumerate(cols) if a-6 <= cx <= b+6), None)
            if ci is None:
                ci = min(range(len(cols)), key=lambda i: abs((cols[i][0]+cols[i][1])/2 - cx))
            row[ci] = (row[ci] + " " + it[4]).strip()
        if re.match(r"^\s*\d", row[0]) or not out:
            out.append(row)
        elif len(row) > 1 and row[1] and not row[-1]:      # khong STT + co ten + KHONG co tien cot cuoi
            out[-1][1] = (out[-1][1] + " " + row[1]).strip()   # -> ten hang wrap, noi item truoc (loai footer co tien)
    return [r for r in out if r and re.match(r"^\s*\d", r[0])]


def viz_table_split(img, cells: list[dict], lines: list[dict], out_path):
    """Viz tach hang bang TU LINE (khop danh_sach sau fix): vach COT (xanh duong) +
    moi BANG-HANG line to 1 mau xoay vong -> thay ro hang 2&3 da tach (khong con o gop)."""
    from PIL import ImageDraw, ImageFont
    cv = img.convert("RGB").copy(); d = ImageDraw.Draw(cv)
    for _fn in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "arial.ttf"):
        try:
            ft = ImageFont.truetype(_fn, 13)
            break
        except Exception:
            ft = ImageFont.load_default()
    lay = _table_layout(cells, lines)
    if lay:
        cols, lrows = lay
        for a, b in cols:                                  # vach bien cot
            d.line([(a, 0), (a, cv.height)], fill=(0, 0, 255), width=1)
        d.line([(cols[-1][1], 0), (cols[-1][1], cv.height)], fill=(0, 0, 255), width=1)
        PAL = [(220, 0, 0), (0, 150, 0), (200, 110, 0), (160, 0, 170), (0, 140, 150), (90, 90, 0)]
        for i, lr in enumerate(lrows):                     # moi bang-hang 1 mau
            c = PAL[i % len(PAL)]
            for it in lr:
                d.rectangle([it[0], it[1], it[2], it[3]], outline=c, width=2)
                d.text((it[0], max(0, it[1]-13)), it[4][:18], fill=c, font=ft)
    out_path.parent.mkdir(parents=True, exist_ok=True); cv.save(str(out_path))


def split_merged_rows(data_rows: list[list[str]], cells: list[dict], lines: list[dict]) -> list[list[str]]:
    """Neu data_rows co hang GOP (o STT chua >=2 so, vd '2 3' do SLANet gop ca hang)
    -> dung lai hang TU LINE de tach. Khong gop -> giu nguyen (cell-based + M2)."""
    if not any(len(re.findall(r"\d+", r[0])) >= 2 for r in data_rows if r):
        return data_rows
    return _rows_from_lines(cells, lines) or data_rows


# Bảng sửa lỗi OCR cho đơn vị tính (dvt) — các từ common bị mất/sai dấu thường gặp.
_DVT_FIX = {
    "thang": "tháng", "họp đồng": "hợp đồng", "hop dong": "hợp đồng",
    "nam": "năm", "lan": "lần", "cai": "cái", "quay": "quý",
}
_DVT_RE = re.compile(r'\b(\d+)\s+thang\b', re.IGNORECASE)


def _fix_cell_ocr(text: str | None, is_dvt: bool = False) -> str | None:
    """Sửa lỗi OCR phổ biến trong cell text (rule-based, không cần LLM)."""
    if not isinstance(text, str) or not text.strip():
        return text
    if is_dvt:
        lo = text.strip().lower()
        if lo in _DVT_FIX:
            return _DVT_FIX[lo]
    # Fix "04 thang" -> "04 tháng" trong ten_hang
    return _DVT_RE.sub(r'\1 tháng', text)


def _parse_line_items(rows: list[list[str]]) -> list[dict]:
    """Trich chi tiet tung dong hang: STT | ten_hang | dvt | so_luong | don_gia | thanh_tien.
    Best-effort theo vi tri cot; o thieu -> None."""
    items = []
    for c in rows:
        it = {
            "ten_hang":   _fix_cell_ocr(c[1] if len(c) > 1 else None),
            "dvt":        _fix_cell_ocr(c[2] if len(c) > 2 else None, is_dvt=True),
            "so_luong":   _to_int(c[3]) if len(c) > 3 else None,
            "don_gia":    _to_int(c[4]) if len(c) > 4 else None,
            "thanh_tien": _to_int(c[5]) if len(c) > 5 else None,
        }
        # Detector doi khi bo sot box so_luong (digit '1' don le o o trang rong) -> o rong.
        # Suy lai bang SO HOC tu thanh_tien = don_gia x so_luong (chi khi chia het). Per-row,
        # khong doan bua: thieu don_gia / khong chia het -> giu None (se vao needs_review).
        if it["so_luong"] is None and it["don_gia"] and it["thanh_tien"] \
                and it["thanh_tien"] % it["don_gia"] == 0:
            it["so_luong"] = it["thanh_tien"] // it["don_gia"]
        items.append(it)
    return items
