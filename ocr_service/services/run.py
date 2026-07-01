# -*- coding: utf-8 -*-
"""
PIPELINE OCR — PP-StructureV3 (pipeline build san) + SURYA recog thay text-recog.

  GIONG HET tools/paddle_vietocr NHUNG thay khoi recognizer VietOCR -> Surya recog:
  PP-StructureV3 (1 call .predict): layout + text-det + table (cls/SLANet/cells) + reading order
     │  GIU LAI detect/layout/table cua no; CHI THAY text-recog:
     ├─► overall_ocr_res.rec_polys ─► truyen polygon vao SURYA recog (bo qua det Surya) doc lai
     ├─► layout_det_res ─► chi giu TITLE + TABLE ─► gan tag moi dong (table>title>text)
     └─► table_res_list.cell_box_list ─► M2 (cat o gop theo bang-hang) ─► map dong vao o
  PHAN LOAI: keyword tren dong TITLE (vision-API khi can).
  PARSING: header = key-value theo NHAN (extract_fields); danh_sach/so_dong = tu LUOI bang.
  -> results.json/csv + raw/ (lines+tables) + viz/ (5 anh).

So voi paddle_vietocr: Surya recog (model nen) co tot/te hon VietOCR ONNX khong.
GTX 1650 Surya fp16->0 box -> recog ep CPU (Paddle detect/table van GPU). Can surya-ocr trong .venv.

Usage: PADDLE_DEVICE=gpu ../.venv/Scripts/python.exe tools/paddle_surya/run.py [--only HS01]  (tu 01_ocr)
"""
import os
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("PADDLE_TEXT_DET", "PP-OCRv5_mobile_det")
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))   # repo root: config/common/surya_engine...
from textnorm import ensure_utf8_stdout, _strip_tags, _fix_homoglyphs, _clean_text, _esc
ensure_utf8_stdout()

import io, json, time, argparse, threading, subprocess, base64, logging
from urllib import request as _urlreq

import fitz
import numpy as np
from PIL import Image

import obs

# Trace pipeline qua logging (thống nhất với api): summary = info, dump chi tiết = debug.
# OCR_LOG_LEVEL=DEBUG để xem dump dòng/field. main() gọi obs.setup_logging().
log = logging.getLogger("ocr.run")

from viz import _font, _viz_layout, _viz_final, _viz_boxes, _viz_llm_io, _viz_table_html
from common import classify_page_api, classify_page_regex, _group_rows, build_record, write_results_csv, TEMPLATE_BY_PAGE_TYPE
from paddle_common import get_engine, _parse_line_items, _count_line_items, split_merged_rows, viz_table_split
from config import PDF_FILES
from visual_objects import basename_for_url
from geometry import (
    _poly_rect, _center_in, _iou, _rowbands, _split_cell_by_bands,
    _dedup_overlapping_lines, _cells_to_rows, table_well_formed,
)

RESULTS_DIR  = Path(__file__).resolve().parent / "results"
RAW_DIR      = RESULTS_DIR / "raw"
VIZ_DIR      = RESULTS_DIR / "viz"
RESULTS_FILE = RESULTS_DIR / "results.json"
RESULTS_CSV  = RESULTS_DIR / "results.csv"
PADDLE_DEVICE = os.environ.get("PADDLE_DEVICE", "gpu")
# DPI render trang -> ảnh (cao hơn = ô bảng nét hơn cho bảng dày, nhưng chậm + tốn VRAM).
# Mặc định 144 (= Matrix 2× cũ, nhẹ VRAM). Tăng qua OCR_RENDER_DPI khi cần bảng dày nét hơn.
RENDER_DPI = int(os.environ.get("OCR_RENDER_DPI", "144"))
# Surya recog chạy IN-PROCESS (xem _get_surya / _recognize_remote bên dưới). CPU nên không
# đụng cuDNN. SURYA_URL chỉ còn dùng làm metadata thông tin, không gọi HTTP nữa.
SURYA_URL = os.environ.get("SURYA_URL", "in-process")


# ---------------------------------------------------------------------------
# Resource monitor — đo PEAK GPU mem/util (nvidia-smi) + RAM tiến trình (psutil),
# lấy mẫu ở thread nền 0.5s/lần trong lúc chạy.
# ---------------------------------------------------------------------------
class ResMon:
    def __init__(self):
        self.peak_gpu = self.peak_util = self.peak_ram = 0.0
        self._stop = False
        try:
            import psutil
            self._proc = psutil.Process()
        except Exception:
            self._proc = None

    @staticmethod
    def _gpu():
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
                stderr=subprocess.DEVNULL, timeout=3).decode()
            mem, util = out.splitlines()[0].split(",")
            return float(mem), float(util)
        except Exception:
            return None, None

    def _sample(self):
        g, u = self._gpu()
        if g is not None: self.peak_gpu = max(self.peak_gpu, g)
        if u is not None: self.peak_util = max(self.peak_util, u)
        if self._proc is not None:
            try: self.peak_ram = max(self.peak_ram, self._proc.memory_info().rss / 1e6)
            except Exception: pass

    def _loop(self):
        while not self._stop:
            self._sample(); time.sleep(0.5)

    def start(self):
        self._t = threading.Thread(target=self._loop, daemon=True); self._t.start(); return self

    def stop(self):
        self._stop = True; self._sample()
        return {"gpu_mem_mb": round(self.peak_gpu), "gpu_util_pct": round(self.peak_util),
                "ram_mb": round(self.peak_ram)}

# ---------------------------------------------------------------------------
# SURYA recog = IN-PROCESS (cùng tiến trình với Paddle). Chạy CPU nên KHÔNG đụng cuDNN
# (xung đột torch-CUDA vs paddle-GPU chỉ xảy ra khi CẢ HAI dùng CUDA/Windows). Nếu sau này
# chạy GPU, tách Surya ra process riêng trở lại.
# ---------------------------------------------------------------------------
_surya_eng = None
_surya_lock = threading.Lock()


def _get_surya():
    """SuryaEngine lazy + cache (load model 1 lần). Device theo TORCH_DEVICE (mặc định cpu)."""
    global _surya_eng
    if _surya_eng is None:
        from surya_engine import SuryaEngine
        dev = os.environ.get("TORCH_DEVICE", "cpu")
        _surya_eng = SuryaEngine(langs=["vi", "en"], profile="service", device=dev)
        if os.environ.get("SURYA_QUANT", "") == "int8" and dev == "cpu":
            import torch   # dynamic-INT8 (CPU) -> nhanh hơn fp32
            fp = _surya_eng.rec_predictor.foundation_predictor
            fp.model = torch.quantization.quantize_dynamic(fp.model, {torch.nn.Linear}, dtype=torch.qint8)
    return _surya_eng


def _recognize_remote(img: "Image.Image", polygons: list) -> list:
    """Nhận dạng text từng polygon bằng Surya — IN-PROCESS. Trả list {text, prob} theo thứ tự polygon."""
    if not polygons:
        return []
    e = _get_surya()
    rgb = img.convert("RGB")
    with _surya_lock:      # serialize forward Surya (1 lần 1 predict) — né chồng nhau
        out = e.rec_predictor([rgb], task_names=[e.ocr_task_name], highres_images=[rgb],
                              polygons=[polygons], math_mode=False, sort_lines=False)
    tlines = getattr(out[0], "text_lines", None) or []
    return [{"text": getattr(t, "text", "") or "", "prob": getattr(t, "confidence", None)}
            for t in tlines]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _refill_html(html, cbs, lines):
    """Giữ NGUYÊN structure pred_html của PP-StructureV3 (SLANet), chỉ THAY text trong
    mỗi <td> = VietOCR (map dòng đã đọc theo cell_box). <td> khớp thứ tự cell_box_list."""
    import re as _re
    tds = list(_re.finditer(r"(<td[^>]*>)(.*?)(</td>)", html, _re.S))
    if not tds or len(tds) != len(cbs):
        return html
    out, last = [], 0
    for m, cb in zip(tds, cbs):
        inside = sorted([e for e in lines if _center_in(e["bbox"], cb)],
                        key=lambda e: (round(e["bbox"][1] / 10), e["bbox"][0]))
        txt = " ".join(e["text"] for e in inside).strip()
        out.append(html[last:m.start()] + m.group(1) + _esc(txt) + m.group(3))
        last = m.end()
    out.append(html[last:])
    return "".join(out)


# ---------------------------------------------------------------------------
# PIPELINE 1 trang  (viz renderers -> viz.py: _font/_viz_layout/_viz_final/_viz_boxes)
# ---------------------------------------------------------------------------

def _guard_reject(guard, mode: str) -> bool:
    """Chặn? CHỈ ở 'strict' và guard.allowed=False (off/audit: ghi verdict, KHÔNG chặn).
    Tôn trọng ENABLE_TEMPLATE_GUARD (config)."""
    from config import ENABLE_TEMPLATE_GUARD
    from guardrails import guard_dict
    if not ENABLE_TEMPLATE_GUARD or mode in ("off", "audit"):
        return False
    d = guard_dict(guard)
    return bool(d) and not d.get("allowed", True)


def detect_page(pdf_path: Path, page_idx: int, viz_dir: Path | None = None,
                guard_mode: str = "off") -> dict:
    """① Render + PP-StructureV3 (Paddle GPU SINGLETON — phải chạy dưới _ocr_lock ở api).
    Guardrails 2 tầng (port nhánh thanh): tier1 (pixel, trước PP) + tier2_layout (layout-geometry
    chấm điểm bố cục vs template, sau PP). 'strict' + không khớp -> reject (recognize short-circuit)."""
    vdir = viz_dir if viz_dir is not None else VIZ_DIR
    vdir.mkdir(parents=True, exist_ok=True)
    # Ảnh (jpg/png/webp/…) mở bằng PIL (đa định dạng, khỏe hơn mupdf); PDF mới render qua fitz.
    if str(pdf_path).lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")):
        img = Image.open(str(pdf_path)).convert("RGB")
        _mx = int(os.environ.get("OCR_IMAGE_MAX_SIDE", "2000"))   # downscale ảnh to -> nhanh trên CPU
        if _mx and max(img.size) > _mx:
            img.thumbnail((_mx, _mx))                            # giữ tỉ lệ
    else:
        pix = fitz.open(str(pdf_path))[page_idx].get_pixmap(dpi=RENDER_DPI)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

    # GUARD tier1 (pixel) — chặn trang trắng/ảnh rõ ràng không phải tài liệu TRƯỚC PP (rẻ nhất).
    _verdicts = []
    if guard_mode != "off":
        from guardrails import tier1_visual_guard, guard_dict
        g1 = tier1_visual_guard(img)
        _verdicts.append(g1)
        if _guard_reject(g1, guard_mode):
            log.info("[guard] tier1 reject: %s", g1.reason)
            return {"pdf_path": pdf_path, "page_idx": page_idx, "vdir": vdir,
                    "guard_mode": guard_mode, "rejected": guard_dict(g1), "guard": guard_dict(g1)}

    # Tiền xử lý: deskew ảnh chụp nghiêng (OCR_PREPROCESS=0 để tắt; thiếu jdeskew -> ảnh gốc).
    from preprocess import preprocess_page
    img = preprocess_page(img)
    arr = np.array(img); H, W = arr.shape[:2]
    log.info("[1/render] %s p%d: %d×%dpx", pdf_path.name, page_idx, W, H)

    # ① PP-StructureV3 (1 call) -> text CẢ TRANG + layout (title/table) + table cells.
    res = get_engine().predict(arr)[0].json; res = res.get("res", res)
    ocr = res.get("overall_ocr_res", {}) or {}
    polys = ocr.get("rec_polys") or ocr.get("dt_polys") or []
    _texts = ocr.get("rec_texts") or []       # text PaddleOCR đã đọc (dùng cho recognizer=paddle)
    _scores = ocr.get("rec_scores") or []
    rects, ptexts, pscores = [], [], []
    for _i, _p in enumerate(polys):
        _r = _poly_rect(_p)
        if _r[2]-_r[0] >= 6 and _r[3]-_r[1] >= 6:
            rects.append(_r)
            ptexts.append(_texts[_i] if _i < len(_texts) else "")
            pscores.append(_scores[_i] if _i < len(_scores) else None)
    n_tables_raw = len(res.get("table_res_list", []))
    log.info("[2/paddle-det] %d text-box, %d bảng detected", len(rects), n_tables_raw)

    # GUARD tier2 (layout-geometry, GIỐNG nhánh thanh) — chấm điểm bố cục vs template từ box/cell,
    # KHÔNG dùng OCR text/vision. ALLOW_UNCERTAIN_DOCUMENT=False -> trang không khớp layout reject.
    if guard_mode != "off":
        from guardrails import tier2_layout_guard, guard_dict
        layout_boxes = (res.get("layout_det_res", {}) or {}).get("boxes", [])
        table_cells = [[int(v) for v in c] for t in res.get("table_res_list", [])
                       for c in (t.get("cell_box_list") or [])]
        g2 = tier2_layout_guard((W, H), rects, layout_boxes, table_cells)
        _verdicts.append(g2)
        if _guard_reject(g2, guard_mode):
            log.info("[guard] tier2 layout reject: %s (score=%.2f)", g2.reason, g2.score)
            return {"pdf_path": pdf_path, "page_idx": page_idx, "vdir": vdir,
                    "guard_mode": guard_mode, "rejected": guard_dict(g2), "guard": guard_dict(g2)}

    # Verdict surface (audit): gate ĐẦU TIÊN không-allowed (would-block), else gate cuối (passed).
    from guardrails import guard_dict as _gd
    _surface = next((g for g in _verdicts if not g.allowed), _verdicts[-1] if _verdicts else None)
    return {"pdf_path": pdf_path, "page_idx": page_idx, "vdir": vdir, "guard_mode": guard_mode,
            "guard": _gd(_surface) if _surface is not None else None,
            "img": img, "H": H, "W": W, "res": res, "rects": rects,
            "paddle_texts": ptexts, "paddle_scores": pscores}


def predict_page(pdf_path: Path, page_idx: int, viz_dir: Path | None = None,
                 guard_mode: str = "off") -> dict:
    """Wrapper TUẦN TỰ (cho benchmark run.py): detect (PP) -> recognize (Surya + ...)."""
    return recognize_page(detect_page(pdf_path, page_idx, viz_dir, guard_mode))


def recognize_page(det: dict) -> dict:
    """② Surya recog (PROCESS RIÊNG) + ③④⑤ table/classify/viz. CHẠY NGOÀI _ocr_lock
    -> Surya của request này gối lên PP (Paddle) của request khác trên cùng GPU."""
    # GUARD đã chặn ở detect_page (tier1/text-presence) -> raw 'rejected' tối thiểu, bỏ qua OCR.
    if det.get("rejected"):
        return {"file": det["pdf_path"].name, "page": det["page_idx"],
                "page_type": "rejected", "rejected": det["rejected"], "guard": det.get("guard"),
                "classify_confidence": 0.0, "classify_method": "guard",
                "size": [0, 0], "title_text": "", "full_text": "",
                "lines": [], "tables": [], "table_ok": False,
                "table_text_vision": None, "visual_objects": []}
    pdf_path = det["pdf_path"]; page_idx = det["page_idx"]; vdir = det["vdir"]
    img = det["img"]; H = det["H"]; W = det["W"]; res = det["res"]; rects = det["rects"]

    # ② Nhận dạng text. MẶC ĐỊNH dùng recognizer của PaddleOCR (đã đọc sẵn ở detect_page ->
    # nhanh, hợp CPU). Đặt OCR_RECOGNIZER=surya để dùng Surya (chính xác hơn cho tiếng Việt
    # nhưng transformer -> NÊN chạy GPU; trên CPU rất chậm).
    if os.environ.get("OCR_RECOGNIZER", "paddle").lower() == "surya":
        spolys = [[[r[0], r[1]], [r[2], r[1]], [r[2], r[3]], [r[0], r[3]]] for r in rects]
        tlines = _recognize_remote(img, spolys)
    else:
        tlines = [{"text": t, "prob": s}
                  for t, s in zip(det.get("paddle_texts", []), det.get("paddle_scores", []))]
    lines = []
    for r, tl in zip(rects, tlines):
        txt = _strip_tags(tl.get("text", "") or "")
        prob = tl.get("prob")
        t = _clean_text(txt.strip()) if txt else ""
        if t:
            lines.append({"bbox": list(r), "text": t,
                          "prob": round(float(prob), 3) if prob is not None else 1.0, "tag": "text"})

    # ②b DEDUP box CHONG vi tri (detector khong NMS) -> giu ban text dai nhat. Sua loi
    # vd so_hoa_don '00007781' bi box cat cut '0000778' chen mat o regex lay match dau.
    lines = _dedup_overlapping_lines(lines)
    log.info("[3/surya-OCR] %d dòng sau dedup (input: %d box)", len(lines), len(rects))
    for i, e in enumerate(lines[:8]):
        log.debug("    %02d: %r  (prob=%.2f)", i, e["text"], e["prob"])
    if len(lines) > 8:
        log.debug("    ... (%d dòng nữa)", len(lines) - 8)

    # ③ LAYOUT (từ chính PP-StructureV3) -> chỉ giữ TITLE + TABLE
    title_boxes, table_boxes = [], []
    for b in (res.get("layout_det_res", {}) or {}).get("boxes", []):
        lab = b["label"].lower(); box = [int(v) for v in b["coordinate"]]
        if "title" in lab:
            title_boxes.append(box)
        elif "table" in lab:
            table_boxes.append(box)

    # gan tag cho moi dong: table > title > text
    for e in lines:
        if any(_center_in(e["bbox"], tb) for tb in table_boxes):
            e["tag"] = "table"
        elif any(_center_in(e["bbox"], tb) for tb in title_boxes):
            e["tag"] = "title"

    # ③b VISUAL OBJECTS (logo / chữ ký / dấu) từ layout PP — TRỰC GIAO text/table (ducbm).
    # collect (box image/figure theo vị trí) -> enrich (gắn text brand cạnh logo) -> crop ra ảnh.
    from visual_objects import (collect_visual_objects, enrich_logo_objects_with_text,
                                 crop_visual_objects, dedup_visual_objects)
    _layout_boxes = (res.get("layout_det_res", {}) or {}).get("boxes", [])
    _vo_stem = f"{pdf_path.name}_page{page_idx}"
    visual_objects = enrich_logo_objects_with_text(
        collect_visual_objects(_layout_boxes, (W, H)), lines, (W, H))
    # Gộp logo/sign TRÙNG NHAU CAO (logo_candidate ⊂ logo_block...) -> 1 đại diện, đỡ nhân đôi nhãn
    visual_objects = dedup_visual_objects(visual_objects)
    visual_objects = crop_visual_objects(img, visual_objects, vdir, _vo_stem)
    # ③c CON DẤU: lọc visual object ĐỎ (stamp). Lưu crop seal riêng (_seal_N.png) vào viz.
    from visual_objects import detect_seals
    import base64 as _b64
    seals = detect_seals(img, visual_objects)
    for _i, _s in enumerate(seals):
        _sf = f"{_vo_stem}_seal_{_i}.png"
        try:
            (vdir / _sf).write_bytes(_b64.b64decode(_s["image_b64"]))
            _s["crop_file"] = _sf
        except Exception as _se:
            log.warning("lưu crop seal lỗi: %s", _se)
    if seals:
        log.info("[3c/seal] %d con dấu (đỏ) phát hiện", len(seals))
    # ③d LOGO: lấy crop logo + khớp brand (GT_logo: vinfast/vinmec/...). Crop đã lưu bởi crop_visual_objects.
    from logo_matcher import match_logo_image
    logos = []
    for _o in visual_objects:
        if _o.get("type") not in ("logo_candidate", "logo_block"):
            continue
        _cp = _o.get("crop_path")
        if not _cp:
            continue
        try:
            _cimg = Image.open(_cp).convert("RGB")
        except Exception:
            continue
        _m = match_logo_image(_cimg, _o.get("text", "") or "")
        _buf = io.BytesIO(); _cimg.save(_buf, format="PNG")
        logos.append({
            "type": _o["type"], "bbox": _o.get("bbox"),
            "crop_file": basename_for_url(_cp), "text": _o.get("text"),
            "brand": (_m or {}).get("brand"), "match_score": (_m or {}).get("final_score"),
            "matched": (_m or {}).get("matched", False),
            "image_b64": _b64.b64encode(_buf.getvalue()).decode(),
        })
    if logos:
        _mk = [f"{l['brand']}({l['match_score']})" for l in logos if l.get("matched")]
        log.info("[3d/logo] %d logo phát hiện%s", len(logos),
                 (" -> khớp: " + ", ".join(_mk)) if _mk else "")

    # ④ TABLE: cell_box_list (PP-StructureV3, toạ độ CẢ TRANG) -> M2 chuẩn hoá ô -> map dòng
    tables = []
    for t in res.get("table_res_list", []):
        cbs = [[int(v) for v in c] for c in (t.get("cell_box_list") or [])]
        if not cbs:
            continue
        # M2: băng-hàng dựng từ ô CHIỀU CAO BÌNH THƯỜNG (loại ô gộp cao ra), cắt ô cao theo băng.
        hs = sorted((b[3]-b[1]) for b in cbs) or [20]
        hmed = hs[len(hs)//2]
        bands = _rowbands([b for b in cbs if (b[3]-b[1]) <= 1.4*hmed] or cbs)
        split_cbs = [sc for cb in cbs for sc in _split_cell_by_bands(cb, bands)]
        import re as _re2
        def _is_num(s):                       # dòng "toàn số" (tiền/sl/đơn giá) — để tách an toàn
            d = _re2.sub(r"[.,%\s]", "", s or "")
            return len(d) >= 3 and sum(c.isdigit() for c in d) >= 0.8 * len(d)
        _TOTAL_KW = ("cộng", "tổng", "thuế", "total", "vat", "grand", "thanh toán", "thanh toan")
        def _is_total_label(s):               # ô NHÃN tổng tiền footer (Cộng/Tổng/Thuế...) bị gộp
            lo = (s or "").lower()
            return any(k in lo for k in _TOTAL_KW)
        _hb = max(1.0, 0.7 * hmed)            # ngưỡng gộp dòng cùng hàng
        cells = []
        _used = set()
        for cb in split_cbs:
            inside = sorted([e for e in lines if _center_in(e["bbox"], cb)],
                            key=lambda e: ((e["bbox"][1] + e["bbox"][3]) / 2, e["bbox"][0]))
            if not inside:
                cells.append({"bbox": cb, "text": ""})
                continue
            for e in inside:
                _used.add(id(e))
            # Ô GỘP nhiều dòng ở các HÀNG khác nhau -> tách mỗi dòng 1 ô (để _cells_to_rows gom
            # lại theo y -> khớp nhãn↔giá trị). Áp cho: (a) ô TOÀN SỐ (footer tiền), (b) ô NHÃN
            # tổng tiền (Cộng/Tổng/Thuế...). Ô tên hàng wrap nhiều dòng -> GIỮ nguyên.
            _rowsy = {round(((e["bbox"][1] + e["bbox"][3]) / 2) / _hb) for e in inside}
            _txt = " ".join(e["text"] for e in inside)
            if len(inside) >= 2 and len(_rowsy) >= 2 and (
                    all(_is_num(e["text"]) for e in inside) or _is_total_label(_txt)):
                for e in inside:
                    cells.append({"bbox": [cb[0], e["bbox"][1], cb[2], e["bbox"][3]], "text": e["text"]})
            else:
                cells.append({"bbox": cb, "text": _txt.strip()})
        bx = [min(c[0] for c in cbs), min(c[1] for c in cbs), max(c[2] for c in cbs), max(c[3] for c in cbs)]
        # Line trong VÙNG BẢNG mà SLANet KHÔNG tạo ô (mồ côi, vd grand total bị bỏ) -> thêm thành ô.
        for e in lines:
            if (id(e) not in _used and e.get("tag") == "table"
                    and _center_in(e["bbox"], [bx[0] - 4, bx[1] - 4, bx[2] + 4, bx[3] + 4])):
                cells.append({"bbox": list(e["bbox"]), "text": e["text"]})
                _used.add(id(e))
        # html: GIỮ structure SLANet của PP, THAY text từng <td> = VietOCR (dùng cell_box GỐC)
        html_vt = _refill_html(t.get("pred_html", "") or "", cbs, lines)
        tables.append({"bbox": bx, "html": html_vt, "cells": cells})
    total_cells = sum(len(t["cells"]) for t in tables)
    log.info("[4/table-M2] %d bảng, %d cells sau split", len(tables), total_cells)

    table_ok = table_well_formed(tables)

    # ⑤ PHAN LOAI 2 lop: keyword tieu de (free) -> truot thi VISION doc CA TRANG.
    title_txt = " ".join(e["text"] for e in lines if e["tag"] == "title")
    # full_text doc-order (gom hang chong-lan y)
    rows = _group_rows([(e["bbox"][0], e["bbox"][1], e["bbox"][2], e["bbox"][3], e["text"], e["prob"])
                        for e in lines])
    full_text = "\n".join(" ".join(it[4] for it in row) for row in rows)
    _pbuf = io.BytesIO(); img.save(_pbuf, format="PNG")   # ảnh ĐÃ deskew -> lớp 2 vision
    page_png = _pbuf.getvalue()
    page_type, cls_conf, method = classify_page_api(title_txt or full_text, image_bytes=page_png)
    # Layout co the gan nham tag tieu de: quoc hieu 'CONG HOA...' chiem vung 'title', con
    # tieu de chung tu that su (vd 'BANG KE CHUONG TRINH...') roi xuong vung text/table ->
    # keyword tren title_txt truot du chung tu hop le. Thu lai keyword tren full_text (van
    # la regex tieu de phan biet + giu thu tu priority -> khong nham BBNT/bao_gia) TRUOC khi
    # chap nhan ket qua vision. Chi chay khi title da co nhung keyword title khong khop.
    if method != "keyword" and title_txt:
        pt2, conf2 = classify_page_regex(full_text)
        if conf2 >= 0.9:
            page_type, cls_conf, method = pt2, conf2, "keyword_fulltext"
    log.info("[5/classify] %s  (conf=%.2f, method=%s)", page_type, cls_conf, method)

    # GUARD reject (classify vision): 'không phải chứng từ'. Verdict luôn ghi (trừ off);
    # CHỈ 'strict' mới CHẶN. audit -> ghi guard nhưng coi như unknown (vẫn xử lý/trả kết quả).
    _mode = det.get("guard_mode", "off")
    _reject_verdict = {"stage": "classify", "reason": "not_a_document",
                       "allowed": False, "score": round(float(cls_conf), 4)}
    if page_type == "reject":
        if _mode == "strict":
            log.info("[5/classify] reject -> không phải chứng từ, chặn")
            return {"file": pdf_path.name, "page": page_idx, "page_type": "reject",
                    "rejected": _reject_verdict, "guard": _reject_verdict,
                    "classify_confidence": cls_conf, "classify_method": method,
                    "size": [W, H], "title_text": title_txt, "full_text": full_text,
                    "lines": lines, "tables": tables, "table_ok": table_ok,
                    "table_text_vision": None, "visual_objects": visual_objects}
        # audit/off: không chặn -> hạ về unknown; audit thì ghi verdict đè lên guard từ detect.
        log.info("[5/classify] reject (mode=%s) -> không chặn, coi như unknown", _mode)
        page_type = "unknown"
        if _mode == "audit":
            det["guard"] = _reject_verdict

    # ④b Vision đọc lại BẢNG (thay <bang_du_lieu> SLANet) khi cells không tin được:
    #   - bảng dựng KHÔNG được (table_ok=False), HOẶC
    #   - trang UNKNOWN (vd bảng kê chụp nghiêng -> SLANet gán ô sai hàng/cột từ gốc).
    # Trang KNOWN + bảng dựng được -> GIỮ text SLANet (đang đúng, khỏi tốn vision).
    table_text_vision = None
    # Tự động cần: bảng dựng hỏng HOẶC trang unknown. Ngoài ra nếu user BẬT TƯỜNG MINH
    # toggle table_vision trên web -> ÉP chạy kể cả trang known + bảng ok (để demo / khi
    # muốn vision đọc lại bảng chụp nghiêng). Mặc định (không gửi toggle) -> giữ nguyên:
    # known + table_ok=True thì bỏ qua, khỏi tốn thêm 1 call Gemini/trang.
    from options import flag as _flag, explicit as _explicit
    auto_need = bool(tables) and (not table_ok or page_type not in TEMPLATE_BY_PAGE_TYPE)
    forced = bool(tables) and _explicit("table_vision") is True
    need_table_vision = auto_need or forced
    # (table-vision qua LLM đã bỏ — luôn dùng bảng SLANet của PP-StructureV3)

    # VIZ
    stem = f"{pdf_path.name}_page{page_idx}"
    _viz_layout(img, title_boxes, table_boxes, vdir / f"{stem}_1layout.png", visual_objects=visual_objects)
    _viz_boxes(img, lines, vdir / f"{stem}_2textdet.png", with_text=False)
    _viz_boxes(img, lines, vdir / f"{stem}_3ocr.png", with_text=True)
    if tables:
        # _4table: tách hàng TỪ LINE (khớp danh_sach sau fix split_merged_rows) — vạch cột + màu/hàng
        viz_table_split(img, [c for t in tables for c in t["cells"]], lines, vdir / f"{stem}_4table.png")
        # _4table.html: lưới HTML đã dựng + pipe text đưa LLM (+ vision nếu có) -> soi chỗ lệch cột
        try:
            _viz_table_html(tables, _tables_to_text({"tables": tables, "lines": lines}),
                            vdir / f"{stem}_4table.html", vision_text=table_text_vision)
        except Exception as _te:
            log.warning("viz-table-html lỗi: %s", _te)
    # Viz Final = ĐÚNG text đưa LLM: full_text đã bỏ dòng tag=table + <bang_du_lieu> pipe.
    _final_raw = {"lines": lines, "tables": tables,
                  "table_text_vision": table_text_vision, "full_text": full_text}
    _viz_final(img, _llm_ocr_text(_final_raw, full_text)[0], vdir / f"{stem}_5final.png")

    return {
        "file": pdf_path.name, "page": page_idx,
        "page_type": page_type, "classify_confidence": cls_conf, "classify_method": method,
        "size": [W, H],
        "title_text": title_txt,
        "full_text": full_text,
        "lines": lines,
        "tables": tables,
        "table_ok": table_ok,                      # bảng SLANet dựng được lưới chắc?
        "table_text_vision": table_text_vision,    # vision đọc lại bảng (khi table_ok=False)
        "visual_objects": visual_objects,          # logo / chữ ký / dấu (ducbm)
        "has_seal": bool(seals),                    # có con dấu (đỏ) không
        "seals": seals,                             # crop con dấu (file viz + base64 lưu DB)
        "has_logo": bool(logos),                    # có logo không
        "logos": logos,                             # crop logo + brand khớp (file viz + base64)
        "guard": det.get("guard"),                 # verdict guard (audit: ghi dù không chặn)
    }


# ---------------------------------------------------------------------------
# PARSING — raw (lines+tables) -> JSON theo template + confidence
# ---------------------------------------------------------------------------

def _extract_client():
    """LLM-extract đã TẮT (bản không-LLM) -> luôn None => pipeline dùng regex + bảng SLANet."""
    return None


def _tables_to_text(raw: dict) -> str:
    """Format bảng PP-StructureV3 (đã dựng cell) thành pipe-delimited text có cột rõ ràng.
    Header row + data rows (đã split merged). Trả '' nếu không có bảng.
    Nếu SLANet dựng KHÔNG được (table_ok=False) và vision đã đọc lại -> DÙNG bản vision."""
    if raw.get("table_text_vision"):
        return raw["table_text_vision"]
    if not raw.get("tables"):
        return ""
    all_cells = [c for t in raw["tables"] for c in t["cells"]]
    parts = []
    for t in raw["tables"]:
        rows = _cells_to_rows(t["cells"])           # đã theo thứ tự TRÊN→DƯỚI (band-hàng)
        if not rows:
            continue
        # GIỮ THỨ TỰ tài liệu: header (trên data) -> data rows -> footer tổng (dưới data),
        # thay vì gom mọi hàng-không-bắt-đầu-số lên đầu (làm footer nhảy lên trước data).
        data_idx = [i for i, r in enumerate(rows) if r and r[0][:1].isdigit()]
        if data_idx:
            i0, i1 = data_idx[0], data_idx[-1]
            head = rows[:i0]                          # hàng header cột
            foot = rows[i1 + 1:]                      # hàng footer (Cộng/Thuế/Tổng)
            data = split_merged_rows([r for r in rows[i0:i1 + 1] if r and r[0][:1].isdigit()],
                                     all_cells, raw["lines"])
            ordered = head + data + foot
        else:
            ordered = rows
        for row in ordered:
            parts.append(" | ".join(str(c) for c in row))
    return "\n".join(parts)


def _llm_ocr_text(raw: dict, fallback: str) -> tuple[str, str]:
    """Text đưa LLM. Nếu có bảng cấu trúc (<bang_du_lieu>): LOẠI dòng tag='table' ĐÃ ĐƯỢC BẢNG
    PHỦ (tránh bảng flatten lộn xộn làm LLM bỏ/nhân đôi dòng) — NHƯNG GIỮ dòng table mà bảng
    BỎ SÓT (vd ô tổng tiền/grand total bị M2 gộp/mất) để LLM vẫn thấy. Append <bang_du_lieu>.
    Trả (ocr_text, table_text)."""
    table_text = _tables_to_text(raw)
    if not table_text:
        return (raw.get("full_text") or fallback), ""
    import re as _re
    _tbl_tokens = {t for t in _re.sub(r"\|", " ", table_text).split() if t}
    def _covered(e):                      # dòng table đã có ĐỦ token trong bảng cấu trúc?
        toks = {t for t in str(e.get("text", "")).split() if t}
        return bool(toks) and toks <= _tbl_tokens
    nontab = [e for e in raw.get("lines", [])
              if e.get("tag") != "table" or not _covered(e)]
    its = sorted(nontab, key=lambda e: (round(e["bbox"][1] / 20) * 20, e["bbox"][0]))
    head = "\n".join(e["text"] for e in its)
    return head + "\n\n<bang_du_lieu>\n" + table_text + "\n</bang_du_lieu>", table_text


def parse_page(raw: dict, doc_type: str, elapsed: float, viz_dir: "Path | None" = None) -> dict:
    """Trích xuất field. Mặc định: đưa FULL OCR TEXT + bảng có cột cho LLM (1 call).
    Không có creds -> fallback regex header + bảng (LƯỚI ô) như cũ."""
    page_type = raw["page_type"]

    # GUARD: trang bị chặn (tier1/text-presence/reject) -> record tối thiểu, KHÔNG trích xuất.
    if raw.get("rejected") or page_type in ("rejected", "reject"):
        rec = build_record(raw["file"], "unknown", raw["page"], raw.get("full_text", ""),
                           [], elapsed, "rejected",
                           raw.get("classify_confidence", 0.0), raw.get("classify_method", "guard"))
        rec["page_type"] = "rejected"
        rec["rejected"] = raw.get("rejected") or {"stage": "classify", "reason": "not_a_document",
                                                  "allowed": False}
        rec["unknown"] = True
        rec["raw_text"] = raw.get("full_text", "")
        return rec

    lines = raw["lines"]
    tokens = [(w, e["prob"]) for e in lines for w in e["text"].split()]
    its = sorted(lines, key=lambda e: (round(e["bbox"][1] / 20) * 20, e["bbox"][0]))
    text_parse = "\n".join(e["text"] for e in its)
    vdir = viz_dir if viz_dir is not None else VIZ_DIR
    stem = f"{raw['file']}_page{raw['page']}"

    # (Đường LLM-extract đã bỏ — chỉ còn trích xuất regex + bảng SLANet bên dưới.)

    # GATE chỉ-template do GUARD tier2 (detect_page) đảm nhiệm — giống nhánh thanh. Ở đây chỉ
    # còn nhánh trích unknown theo toggle (khi guard off / trang lọt tier2 mà classify=unknown).
    # --- Trang UNKNOWN + OCR_EXTRACT_UNKNOWN=1: trích TEXT tự do (giữ 'unknown', không template) ---
    from options import flag as _flag

    # --- Trang KHÔNG vào template + toggle extract_unknown TẮT -> CHẶN (reject) ---
    if page_type not in TEMPLATE_BY_PAGE_TYPE and not _flag("extract_unknown", "OCR_EXTRACT_UNKNOWN", False):
        rec = build_record(raw["file"], "unknown", raw["page"], raw.get("full_text", ""),
                           [], elapsed, "rejected",
                           raw.get("classify_confidence", 0.0), raw.get("classify_method", "vision"))
        rec["page_type"] = "rejected"
        rec["rejected"] = {"stage": "classify", "reason": "unknown_not_extracted", "allowed": False}
        rec["unknown"] = True
        rec["raw_text"] = raw.get("full_text", "")
        log.info("[6] trang unknown + extract_unknown TẮT -> reject (chặn)")
        return rec

    # --- Fallback: regex header + bảng (LƯỚI ô) ---
    record = build_record(raw["file"], doc_type, raw["page"], text_parse, tokens, elapsed,
                          raw["page_type"], raw["classify_confidence"], raw["classify_method"])
    from field_locator import match_field_bboxes
    record["field_bboxes"] = match_field_bboxes(
        record.get("fields", {}), raw["lines"], raw.get("tables", []))

    # danh_sach + so_dong tu LƯỚI bảng (hàng dữ liệu = ô STT bắt đầu bằng chữ số)
    if raw["page_type"] in ("hoa_don_gtgt", "bao_gia"):
        rows = [r for t in raw["tables"] for r in _cells_to_rows(t["cells"])]
        data_rows = [r for r in rows if r and r[0][:1].isdigit()]
        # Ca SLANet gop CA hang (o STT '2 3') -> dung lai hang tu LINE de tach
        all_cells = [c for t in raw["tables"] for c in t["cells"]]
        data_rows = split_merged_rows(data_rows, all_cells, raw["lines"])
        so_dong = _count_line_items(data_rows) or None
        line_items = _parse_line_items(data_rows) or None
        if so_dong and "so_dong_hang" in record["fields"]:
            record["fields"]["so_dong_hang"] = so_dong
            record["confidence"]["so_dong_hang"] = 0.9
            record["needs_review"] = [f for f in record.get("needs_review", []) if f != "so_dong_hang"]
        if line_items and "danh_sach_dong_hang" in record["fields"]:
            record["fields"]["danh_sach_dong_hang"] = line_items
            record["confidence"]["danh_sach_dong_hang"] = 0.85
            record["needs_review"] = [f for f in record.get("needs_review", []) if f != "danh_sach_dong_hang"]
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    obs.setup_logging()          # bật logging cho batch (OCR_LOG_LEVEL=DEBUG để xem dump)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    VIZ_DIR.mkdir(parents=True, exist_ok=True)

    if args.only:
        files = [(p, d) for (p, d) in PDF_FILES if args.only in p.name]
    elif args.limit:
        files = PDF_FILES[:args.limit]
    else:
        files = PDF_FILES
    partial = bool(args.only or args.limit)

    all_results = []
    file_times = []   # (ten_file, giay, so_trang)
    lat = []          # latency từng trang CHẠY MỚI (giây) — cho min/avg/max
    mon = ResMon().start()
    for i, (pdf_path, doc_type) in enumerate(files, 1):
        n_pages = len(fitz.open(str(pdf_path)))
        log.info("[%02d/%d] %s (%d trang)", i, len(files), pdf_path.name, n_pages)
        ft0 = time.time()
        for pg in range(n_pages):
            raw_path = RAW_DIR / f"{pdf_path.name}_page{pg}.json"
            t0 = time.time()
            if raw_path.exists():
                # raw/ = CACHE output OCR (predict_page nặng) -> có rồi khỏi chạy lại, chỉ parse (rẻ).
                # Xoá raw/ để chạy MỚI (cần khi đo thời gian thật).
                raw = json.loads(raw_path.read_text(encoding="utf-8")); cached = True
                # Regenerate viz từ raw JSON + ảnh PDF (render nhanh, OCR đã có sẵn).
                # PHẢI deskew y như predict_page — box trong raw['lines'] ở toạ độ ảnh ĐÃ nắn.
                from preprocess import preprocess_page
                pix = fitz.open(str(pdf_path))[pg].get_pixmap(dpi=RENDER_DPI)
                img_c = preprocess_page(Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB"))
                stem = f"{pdf_path.name}_page{pg}"
                _viz_layout(img_c, raw.get("title_boxes", []), raw.get("table_boxes", []),
                            VIZ_DIR / f"{stem}_1layout.png", visual_objects=raw.get("visual_objects"))
                _viz_boxes(img_c, raw.get("lines", []), VIZ_DIR / f"{stem}_2textdet.png", with_text=False)
                _viz_boxes(img_c, raw.get("lines", []), VIZ_DIR / f"{stem}_3ocr.png", with_text=True)
                tbls = raw.get("tables", [])
                if tbls:
                    viz_table_split(img_c, [c for t in tbls for c in t["cells"]],
                                    raw.get("lines", []), VIZ_DIR / f"{stem}_4table.png")
                    _viz_table_html(tbls, _tables_to_text({"tables": tbls, "lines": raw.get("lines", [])}),
                                    VIZ_DIR / f"{stem}_4table.html", vision_text=raw.get("table_text_vision"))
                _viz_final(img_c, _llm_ocr_text(raw, raw.get("full_text", ""))[0],
                           VIZ_DIR / f"{stem}_5final.png")
            else:
                raw = predict_page(pdf_path, pg)
                raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
                cached = False
            dt = round(time.time() - t0, 2)
            if not cached:
                lat.append(dt)
            record = parse_page(raw, doc_type, dt, viz_dir=VIZ_DIR)
            # Tầng enhance (vision đối chiếu + full-vision unknown) — default OFF,
            # bật bằng OCR_ENHANCE=1 (cần Gemini creds). OFF -> record y nguyên.
            from enhance import maybe_enhance_record
            record = maybe_enhance_record(record, pdf_path, pg)
            all_results.append(record)
            nrev = len(record.get("needs_review", []))
            log.info("  page %d: [%s]  %d field, %d cần review  (%ss%s)",
                     pg, record["page_type"], len(record["fields"]), nrev, dt,
                     " · cached" if cached else "")
        file_times.append((pdf_path.name, round(time.time() - ft0, 2), n_pages))
    res = mon.stop()

    # --- Thống kê thời gian ---
    if file_times:
        total = sum(t for _, t, _ in file_times)
        npages = sum(n for _, _, n in file_times)
        print("\n── Thời gian ──")
        for name, t, n in file_times:
            print(f"  {name:42} {t:6.2f}s  ({n} trang, {t/n:.2f}s/trang)")
        print(f"  {'TỔNG':42} {total:6.2f}s  ({len(file_times)} file, {npages} trang)")
        print(f"  → TB {total/len(file_times):.2f}s/file · {total/npages:.2f}s/trang")

    # --- Latency từng trang (bỏ trang đầu = cold-start load model) ---
    if lat:
        warm = lat[1:] if len(lat) > 1 else lat
        print("\n── Latency/trang ──")
        print(f"  trang đầu (cold-start, gồm load model): {lat[0]:.2f}s")
        print(f"  warm: min {min(warm):.2f}s · TB {sum(warm)/len(warm):.2f}s · max {max(warm):.2f}s  ({len(warm)} trang)")

    # --- Tài nguyên (peak) ---
    print("\n── Tài nguyên (peak) ──")
    print(f"  GPU mem: {res['gpu_mem_mb']} MB (toàn card) · GPU util: {res['gpu_util_pct']}% · "
          f"RAM tiến trình: {res['ram_mb']} MB")

    if partial:
        print("\n[chạy thử] KHÔNG ghi đè results.json.")
        return
    RESULTS_FILE.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    write_results_csv(all_results, RESULTS_CSV)
    # lưu metrics CHỈ khi có trang chạy THẬT (lat) — reparse từ cache (lat rỗng) KHÔNG clobber metric cũ
    if lat:
        warm = lat[1:] or lat
        (RESULTS_DIR / f"metrics_{PADDLE_DEVICE}.json").write_text(json.dumps({
            "engine": "paddle_surya", "paddle_device": PADDLE_DEVICE, "surya_url": SURYA_URL,
            "n_files": len(file_times), "n_pages": sum(n for _, _, n in file_times),
            "total_s": round(sum(t for _, t, _ in file_times), 2),
            "avg_s_per_file": round(sum(t for _, t, _ in file_times) / max(1, len(file_times)), 2),
            "latency_warm_s": {"min": round(min(warm), 2), "avg": round(sum(warm) / len(warm), 2),
                               "max": round(max(warm), 2)},
            "cold_start_s": round(lat[0], 2),
            "peak": res,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDone. {len(all_results)} trang. results.json/csv + raw/ + viz/{' + metrics.json' if lat else ''} ghi xong.")


if __name__ == "__main__":
    main()
