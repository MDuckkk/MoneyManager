# -*- coding: utf-8 -*-
"""
Visualization renderers (tách khỏi run.py): vẽ overlay layout/box + panel text cuối.
Behavior-preserving — copy nguyên từ run.py. Phụ thuộc PIL (+ font Việt qua OCR_FONT_PATH).
"""
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont


def _font(size: int):
    # OCR_FONT_PATH cho phép chỉ định font Việt hoá rõ ràng (không đoán theo OS);
    # nếu không đặt -> thử lần lượt DejaVu (Linux) rồi các font Windows phổ biến.
    candidates = [c for c in (os.environ.get("OCR_FONT_PATH", ""),) if c] + [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux — hỗ trợ tiếng Việt
        "arial.ttf", "segoeui.ttf", "tahoma.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _viz_layout(img, title_boxes, table_boxes, out_path, visual_objects=None):
    """① LAYOUT (TITLE xanh + TABLE do + LOGO/SIGN neu co — ducbm). Phan con lai khong dung."""
    cv = img.convert("RGB").copy(); d = ImageDraw.Draw(cv); ft = _font(16)
    for b in title_boxes:
        d.rectangle(b, outline=(30, 90, 230), width=3); d.text((b[0], max(0, b[1]-18)), "TITLE", fill=(30, 90, 230), font=ft)
    for b in table_boxes:
        d.rectangle(b, outline=(220, 0, 0), width=3); d.text((b[0], max(0, b[1]-18)), "TABLE", fill=(220, 0, 0), font=ft)
    for obj in visual_objects or []:
        bb = obj.get("bbox")
        if not bb:
            continue
        typ = obj.get("type", "")
        if "signature" in typ:
            lab, col = "SIGN", (0, 120, 220)
        elif "logo" in typ:
            lab, col = "LOGO", (0, 150, 80)
        else:
            lab, col = "OBJ", (160, 0, 170)
        d.rectangle(bb, outline=col, width=2); d.text((bb[0], max(0, bb[1]-18)), lab, fill=col, font=ft)
    out_path.parent.mkdir(parents=True, exist_ok=True); cv.save(str(out_path))


def _viz_final(img, final_text, out_path):
    """Viz 2-panel: TRÁI = ảnh gốc | PHẢI = ĐÚNG text ĐƯA LLM (full_text ĐÃ BỎ dòng tag=table
    + <bang_du_lieu> pipe). Dòng trong <bang_du_lieu> tô xanh cho dễ soi cột."""
    W, H = img.size
    MARGIN = 14
    LINE_H = 26
    FONT_SZ = 20
    ft = _font(FONT_SZ)

    # Ước lượng số ký tự/dòng dựa trên width font (DejaVu Sans ~11px/char ở 20px)
    max_chars = max(30, (W - MARGIN * 2) // 11)

    lines_to_draw: list[tuple[str, tuple[int, int, int]]] = []
    in_table = False
    for raw in (final_text or "").split("\n"):
        s = raw.strip()
        if s.startswith("<bang_du_lieu>"):
            in_table = True
        elif s.startswith("</bang_du_lieu>"):
            in_table = False
        color = (0, 90, 200) if in_table else (0, 0, 0)
        if not s:
            lines_to_draw.append(("", (0, 0, 0)))
            continue
        wrapped = textwrap.wrap(raw, width=max_chars) or [""]
        first = True
        for seg in wrapped:
            lines_to_draw.append((seg if first else "  " + seg, color))
            first = False

    total_h = max(H, MARGIN * 2 + len(lines_to_draw) * LINE_H)
    panel = Image.new("RGB", (W, total_h), (255, 255, 255))
    d = ImageDraw.Draw(panel)
    y = MARGIN
    for txt, color in lines_to_draw:
        if txt:
            d.text((MARGIN, y), txt, fill=color, font=ft)
        y += LINE_H

    combo_h = max(H, total_h)
    combo = Image.new("RGB", (W * 2 + 12, combo_h), (210, 210, 210))
    combo.paste(img.convert("RGB"), (0, 0))
    combo.paste(panel, (W + 12, 0))
    out_path.parent.mkdir(parents=True, exist_ok=True); combo.save(str(out_path))


def _viz_boxes(img, entries, out_path, with_text=True):
    """② text-det / ③ OCR / ④ table-cell: box + (text). Mau theo prob."""
    cv = img.convert("RGB").copy(); d = ImageDraw.Draw(cv); ft = _font(14)
    for i, e in enumerate(entries):
        p = e.get("prob", 1.0)
        c = (0, 160, 0) if p >= 0.9 else (220, 140, 0) if p >= 0.7 else (210, 0, 0)
        x1, y1, x2, y2 = e["bbox"]
        d.rectangle([x1, y1, x2, y2], outline=c, width=2)
        if with_text:
            d.text((x1, max(0, y1 - 15)), f"{i}:{e.get('text','')}", fill=c, font=ft)
    out_path.parent.mkdir(parents=True, exist_ok=True); cv.save(str(out_path))


def _viz_llm_io(llm_input: str, fields: dict, out_path):
    """⑥ LLM I/O: 2-panel — TRÁI = text gửi vào LLM | PHẢI = fields JSON trả về."""
    import json
    FONT_SZ, LINE_H, MARGIN, PW = 18, 24, 12, 900
    ft = _font(FONT_SZ); ft_hd = _font(FONT_SZ + 2)
    max_chars = max(30, (PW - MARGIN * 2) // 10)

    def make_panel(header: str, body: str, hdr_color, body_color) -> Image.Image:
        raw_lines = body.split("\n")
        wrapped = []
        for line in raw_lines:
            segs = textwrap.wrap(line, width=max_chars) if line.strip() else [""]
            wrapped.extend(segs or [""])
        h = MARGIN * 3 + LINE_H + len(wrapped) * LINE_H
        panel = Image.new("RGB", (PW, max(h, 400)), (248, 248, 252))
        d = ImageDraw.Draw(panel)
        d.rectangle([0, 0, PW, LINE_H + MARGIN * 2], fill=(230, 232, 240))
        d.text((MARGIN, MARGIN), header, fill=hdr_color, font=ft_hd)
        y = LINE_H + MARGIN * 2
        for seg in wrapped:
            d.text((MARGIN, y), seg, fill=body_color, font=ft)
            y += LINE_H
        return panel

    left  = make_panel("⑤ LLM INPUT (full_text + <bang_du_lieu>)", llm_input,
                        (20, 60, 180), (30, 30, 30))
    right_body = json.dumps(fields, ensure_ascii=False, indent=2)
    right = make_panel("⑥ LLM OUTPUT (fields JSON)", right_body,
                        (0, 130, 60), (0, 80, 0))

    H = max(left.height, right.height)
    combo = Image.new("RGB", (PW * 2 + 8, H), (180, 180, 190))
    left_exp  = Image.new("RGB", (PW, H), (248, 248, 252)); left_exp.paste(left,  (0, 0))
    right_exp = Image.new("RGB", (PW, H), (248, 250, 248)); right_exp.paste(right, (0, 0))
    combo.paste(left_exp,  (0,       0))
    combo.paste(right_exp, (PW + 8,  0))
    out_path.parent.mkdir(parents=True, exist_ok=True); combo.save(str(out_path))


def _viz_table_html(tables, table_text, out_path, vision_text=None):
    """Dump bảng ĐÃ DỰNG ra HTML để soi cấu trúc (debug cột lệch):
    - lưới SLANet (mỗi tables[i]['html'] đã thay text VietOCR),
    - <bang_du_lieu> = pipe text đưa vào LLM,
    - table_text_vision (nếu vision đọc lại bảng).
    Mở file .html này trong trình duyệt để thấy bảng dựng như nào."""
    import html as _html
    css = ("<style>body{font:13px sans-serif;margin:16px}"
           "table{border-collapse:collapse;margin:8px 0}"
           "td,th{border:1px solid #999;padding:2px 6px}"
           "h3{margin:18px 0 4px}pre{background:#f4f4f4;padding:8px;white-space:pre-wrap;"
           "font:12px monospace;border:1px solid #ddd}</style>")
    parts = ["<!doctype html><meta charset='utf-8'>", css]
    for i, t in enumerate(tables or []):
        parts.append(f"<h3>Table {i} — SLANet pred_html (đã thay text)</h3>")
        parts.append(t.get("html") or "<i>(no html)</i>")
    parts.append("<h3>&lt;bang_du_lieu&gt; — pipe text ĐƯA LLM</h3>")
    parts.append("<pre>" + _html.escape(table_text or "(rỗng)") + "</pre>")
    if vision_text:
        parts.append("<h3>table_text_vision — vision đọc lại bảng</h3>")
        parts.append("<pre>" + _html.escape(vision_text) + "</pre>")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
