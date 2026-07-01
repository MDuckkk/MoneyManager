# -*- coding: utf-8 -*-
"""
Helper hình học thuần (box/polygon/băng-hàng) tách khỏi run.py để test được độc lập
và tái dùng. KHÔNG phụ thuộc PaddleOCR/torch/PIL — chỉ stdlib.

box = (x1, y1, x2, y2). "line"/"cell" = dict có khoá "bbox" (và "text"/"prob").
"""


def _poly_rect(poly, ox=0, oy=0):
    xs = [float(p[0]) for p in poly]; ys = [float(p[1]) for p in poly]
    return (int(min(xs)) + ox, int(min(ys)) + oy, int(max(xs)) + ox, int(max(ys)) + oy)


def _center_in(box, outer, m=2):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return outer[0] - m <= cx <= outer[2] + m and outer[1] - m <= cy <= outer[3] + m


def _iou(a, b):
    """Tra (iou, contain) — contain = intersection / dien tich box NHO hon
    (>~1 nghia la 1 box nam gan tron trong box kia)."""
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0, 0.0
    aa = (a[2] - a[0]) * (a[3] - a[1])
    ab = (b[2] - b[0]) * (b[3] - b[1])
    union = aa + ab - inter
    return (inter / union if union else 0.0), (inter / min(aa, ab) if min(aa, ab) else 0.0)


def _dedup_overlapping_lines(lines, iou_thr=0.6, contain_thr=0.8, cell=64):
    """Detector (PP-StructureV3) doi khi sinh 2 box CHONG cung 1 vung text -> Surya
    recog ra 2 ban khac nhau (vd '0000778' vs '00007781' bi cat cut). Tang tren KHONG
    co NMS nen ca hai song sot -> gop o day: 2 box chong nhau (IoU cao HOAC 1 box nam
    gan tron trong box kia) coi la trung; giu ban TEXT DAI HON (tie-break prob cao hon),
    bo ban con lai. Giu nguyen thu tu goc cua list.

    Toi uu: spatial grid thay vi so MOI box voi MOI box kept (O(n^2)). Ket qua Y HET
    brute-force — 2 box chong nhau LUON chung >=1 o luoi, nen khong bo sot cap trung."""
    order = sorted(range(len(lines)),
                   key=lambda i: (-len(lines[i]["text"]), -lines[i].get("prob", 0.0)))

    def _cells(box):
        x1, y1, x2, y2 = box
        for cx in range(int(x1) // cell, int(x2) // cell + 1):
            for cy in range(int(y1) // cell, int(y2) // cell + 1):
                yield (cx, cy)

    grid: dict = {}      # o luoi -> list index kept trong o do
    kept_idx, drop = [], set()
    for i in order:
        bi = lines[i]["bbox"]
        is_dup, seen = False, set()
        for c in _cells(bi):
            for j in grid.get(c, ()):
                if j in seen:
                    continue
                seen.add(j)
                iou, contain = _iou(bi, lines[j]["bbox"])
                if iou >= iou_thr or contain >= contain_thr:
                    is_dup = True
                    break
            if is_dup:
                break
        if is_dup:
            drop.add(i)
        else:
            kept_idx.append(i)
            for c in _cells(bi):
                grid.setdefault(c, []).append(i)
    return [e for k, e in enumerate(lines) if k not in drop]


def _rowbands(boxes, ov_ratio=0.4):
    """Gom moi ô thanh BANG-HANG theo chong-lan y -> list [y_top, y_bot] (da sap)."""
    bands = []
    for b in sorted(boxes, key=lambda b: (b[1] + b[3]) / 2):
        y1, y2 = b[1], b[3]; h = y2 - y1
        for band in bands:
            ov = max(0, min(y2, band[1]) - max(y1, band[0]))
            if ov > ov_ratio * min(h, band[1] - band[0]):
                band[0] = min(band[0], y1); band[1] = max(band[1], y2); break
        else:
            bands.append([y1, y2])
    bands.sort()
    return bands


def _cells_to_rows(cells):
    """Gom ô bảng thành HÀNG (theo băng-hàng) -> list[list[str]] (cột sort theo x).
    Dùng cho parse danh_sach: hàng dữ liệu = ô đầu (STT) bắt đầu bằng chữ số."""
    if not cells:
        return []
    bands = _rowbands([c["bbox"] for c in cells])
    rows = []
    for bd in bands:
        inrow = [c for c in cells if bd[0] - 1 <= (c["bbox"][1] + c["bbox"][3]) / 2 <= bd[1] + 1]
        inrow.sort(key=lambda c: c["bbox"][0])
        rows.append([c["text"] for c in inrow])
    return rows


def table_well_formed(tables) -> bool:
    """Cờ 'bảng DỰNG ĐƯỢC' (SLANet/M2 không trả sẵn -> suy ra từ cấu trúc đã dựng).
    BASIC: dựng được hàng/ô nào (có nội dung) -> True, bất kể ít/nhiều cột-hàng;
    trả RỖNG (không ô/không hàng) -> False. False -> caller crop ảnh bảng cho LLM vision đọc."""
    rows = [r for t in (tables or []) for r in _cells_to_rows(t["cells"])]
    return any(any(str(c).strip() for c in r) for r in rows)


def _split_cell_by_bands(box, bands):
    """M2: ô (do RT-DETR) trùm >1 băng-hàng -> CẮT tại biên giữa các băng -> ô con
    khớp từng hàng. Dùng băng-hàng từ CÁC Ô KHÁC làm mốc (cột bên cạnh tách đúng)."""
    x1, y1, x2, y2 = box
    cov = sorted([bd for bd in bands if min(y2, bd[1]) - max(y1, bd[0]) > 0.5 * (bd[1] - bd[0])])
    if len(cov) <= 1:
        return [box]
    cuts = [y1] + [int((cov[i][1] + cov[i + 1][0]) / 2) for i in range(len(cov) - 1)] + [y2]
    return [[x1, cuts[i], x2, cuts[i + 1]] for i in range(len(cov))]
