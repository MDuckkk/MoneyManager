# -*- coding: utf-8 -*-
"""Detect/crop non-text visual objects from Paddle layout output."""

from pathlib import Path
import re

from PIL import Image


VISUAL_IMAGE_LABELS = ("image", "figure", "pic", "picture")
IGNORED_LAYOUT_LABELS = ("title", "text", "table", "paragraph", "caption")


def normalize_label(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (label or "").strip().lower()).strip("_")


def basename_for_url(path: str | Path) -> str:
    """Return a filename for either Windows or POSIX path separators."""
    return re.split(r"[\\/]", str(path))[-1]


def visual_type_for_label(label: str, bbox: list[int], page_size: tuple[int, int]) -> str | None:
    """Map Paddle generic image layout boxes to visual candidates by page position."""
    lab = normalize_label(label)
    if not lab or any(h in lab for h in IGNORED_LAYOUT_LABELS):
        return None
    if not any(h in lab for h in VISUAL_IMAGE_LABELS):
        return None

    _, page_h = page_size
    y_mid = (bbox[1] + bbox[3]) / 2
    if y_mid <= page_h * 0.35:
        return "logo_candidate"
    if y_mid >= page_h * 0.55:
        return "signature_candidate"
    return "visual_candidate"


def _score(box: dict) -> float | None:
    for key in ("score", "confidence", "prob"):
        val = box.get(key)
        if val is not None:
            try:
                return round(float(val), 4)
            except (TypeError, ValueError):
                return None
    return None


def _coordinate(box: dict) -> list[int] | None:
    raw = box.get("coordinate") or box.get("bbox") or box.get("box")
    if not raw or len(raw) != 4:
        return None
    try:
        x1, y1, x2, y2 = [int(round(float(v))) for v in raw]
    except (TypeError, ValueError):
        return None
    if x2 <= x1 or y2 <= y1:
        return None
    return [x1, y1, x2, y2]


def _clamp_bbox(bbox: list[int], size: tuple[int, int], pad: int = 0) -> list[int] | None:
    w, h = size
    x1 = max(0, bbox[0] - pad)
    y1 = max(0, bbox[1] - pad)
    x2 = min(w, bbox[2] + pad)
    y2 = min(h, bbox[3] + pad)
    if x2 <= x1 or y2 <= y1:
        return None
    return [x1, y1, x2, y2]


LOGO_OBJECT_TYPES = ("logo_candidate",)
TEXT_LABEL_REJECT_HINTS = (
    "seller", "buyer", "address", "tax", "invoice", "account", "tel",
    "ngay", "mst", "cong", "tong",
)


def _union_bbox(boxes: list[list[int]]) -> list[int]:
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def _horizontal_overlap_ratio(a: list[int], b: list[int]) -> float:
    overlap = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    width = max(1, min(a[2] - a[0], b[2] - b[0]))
    return overlap / width


def _looks_like_brand_text(text: str) -> bool:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean or any(ch in clean for ch in ":/\\|@"):
        return False
    words = clean.split()
    if len(words) > 3:
        return False
    letters = [ch for ch in clean if ch.isalpha()]
    alnum = [ch for ch in clean if ch.isalnum()]
    if len(alnum) < 2 or len(alnum) > 24:
        return False
    if len(letters) / max(1, len(alnum)) < 0.7:
        return False
    compact = normalize_label(clean)
    if any(hint in compact for hint in TEXT_LABEL_REJECT_HINTS):
        return False
    return True


def _logo_text_candidates(logo_bbox: list[int], lines: list[dict]) -> list[dict]:
    logo_w = logo_bbox[2] - logo_bbox[0]
    logo_h = logo_bbox[3] - logo_bbox[1]
    logo_cx = (logo_bbox[0] + logo_bbox[2]) / 2
    x_pad = max(24, logo_w * 0.35)
    y_top = logo_bbox[1] - max(8, logo_h * 0.20)
    y_bottom = logo_bbox[3] + max(18, logo_h * 0.55)
    candidates = []
    for line in lines or []:
        if line.get("tag") in ("table", "title"):
            continue
        try:
            bbox = [int(v) for v in line.get("bbox", [])]
        except (TypeError, ValueError):
            continue
        if len(bbox) != 4 or bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            continue
        text = str(line.get("text", "")).strip()
        if not _looks_like_brand_text(text):
            continue
        prob = line.get("prob", 1.0)
        try:
            prob_float = float(prob)
        except (TypeError, ValueError):
            continue
        if prob_float < 0.65:
            continue

        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        if not (logo_bbox[0] - x_pad <= cx <= logo_bbox[2] + x_pad and y_top <= cy <= y_bottom):
            continue

        overlap = _horizontal_overlap_ratio(logo_bbox, bbox)
        cx_delta = abs(cx - logo_cx)
        line_w = bbox[2] - bbox[0]
        if overlap < 0.35 and cx_delta > max(36, logo_w * 0.75):
            continue
        if line_w > max(logo_w * 3.5, 260):
            continue

        candidates.append({
            "bbox": bbox,
            "text": text,
            "prob": round(prob_float, 3),
            "tag": line.get("tag", "text"),
        })

    candidates.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
    return candidates


def enrich_logo_objects_with_text(objects: list[dict], lines: list[dict], page_size: tuple[int, int]) -> list[dict]:
    """Add safe logo text/block objects when nearby OCR looks like brand text.

    The OCR text is only a supporting signal. Geometry and simple label rejection keep
    invoice fields such as tax code, address, or seller lines from being merged.
    """
    enriched = [dict(obj) for obj in (objects or [])]
    for obj in objects or []:
        if obj.get("type") not in LOGO_OBJECT_TYPES:
            continue
        bbox = obj.get("bbox")
        if not bbox:
            continue
        logo_bbox = [int(v) for v in bbox]
        text_lines = _logo_text_candidates(logo_bbox, lines)
        if not text_lines:
            continue
        line_boxes = [line["bbox"] for line in text_lines]
        text_bbox = _clamp_bbox(_union_bbox(line_boxes), page_size)
        block_bbox = _clamp_bbox(_union_bbox([logo_bbox, *line_boxes]), page_size)
        if text_bbox is None or block_bbox is None:
            continue
        text_value = " ".join(line["text"] for line in text_lines)
        text_confidence = min(line["prob"] for line in text_lines)
        enriched.append({
            "type": "logo_text_candidate",
            "source_label": "ocr_near_logo",
            "bbox": text_bbox,
            "confidence": text_confidence,
            "text": text_value,
            "parent_bbox": logo_bbox,
            "components": line_boxes,
        })
        confidence_values = [v for v in (obj.get("confidence"), text_confidence) if v is not None]
        enriched.append({
            "type": "logo_block",
            "source_label": "logo_plus_ocr_text",
            "bbox": block_bbox,
            "confidence": min(confidence_values) if confidence_values else text_confidence,
            "text": text_value,
            "components": [logo_bbox, *line_boxes],
        })
    return enriched

def collect_visual_objects(layout_boxes: list[dict], page_size: tuple[int, int]) -> list[dict]:
    objects = []
    for box in layout_boxes or []:
        bbox = _coordinate(box)
        if bbox is None:
            continue
        bbox = _clamp_bbox(bbox, page_size)
        if bbox is None:
            continue
        label = str(box.get("label", ""))
        obj_type = visual_type_for_label(label, bbox, page_size)
        if not obj_type:
            continue
        objects.append({
            "type": obj_type,
            "source_label": label,
            "bbox": bbox,
            "confidence": _score(box),
        })
    return objects


def crop_visual_objects(
    img: Image.Image,
    objects: list[dict],
    out_dir: Path,
    stem: str,
    pad: int = 8,
) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    cropped = []
    for obj in objects:
        obj_type = obj["type"]
        idx = counts.get(obj_type, 0)
        counts[obj_type] = idx + 1
        crop_bbox = _clamp_bbox(obj["bbox"], img.size, pad=pad)
        if crop_bbox is None:
            continue
        out_path = out_dir / f"{stem}_{obj_type}_{idx}.png"
        img.crop(tuple(crop_bbox)).save(str(out_path))
        copied = dict(obj)
        copied["crop_bbox"] = crop_bbox
        copied["crop_path"] = str(out_path)
        cropped.append(copied)
    return cropped




def detect_seals(img: "Image.Image", cropped_objects: list[dict],
                 red_thresh: float = 0.015) -> list[dict]:
    """Nhận diện CON DẤU (stamp đỏ) trong các visual object đã crop.

    Con dấu doanh nghiệp VN thường là dấu ĐỎ (vòng/hình + chữ). Lọc visual object có
    tỷ lệ pixel đỏ >= red_thresh -> coi là con dấu. Trả list {type:'seal', bbox, red_ratio,
    crop_file (basename), crop_path, image_b64 (PNG base64 để lưu DB)}.
    Không có numpy/lỗi -> trả [] (degrade, không vỡ pipeline)."""
    import base64
    import io
    try:
        import numpy as np
    except Exception:
        return []
    seals = []
    for obj in cropped_objects or []:
        # KHÔNG coi LOGO là con dấu (logo có thể đỏ -> tránh nhầm/lặp logo↔dấu).
        # Con dấu nằm vùng chữ ký (signature/visual_candidate), không phải vùng logo (trên).
        if "logo" in (obj.get("type") or ""):
            continue
        bbox = obj.get("crop_bbox") or obj.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        try:
            crop = img.crop(tuple(int(v) for v in bbox)).convert("RGB")
            arr = np.asarray(crop).astype("int16")
            r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
            # pixel đỏ (nới cho dấu scan bị nhạt/hồng): R trội hơn G,B
            red = (r > 90) & (r - g > 20) & (r - b > 20)
            ratio = float(red.mean()) if red.size else 0.0
        except Exception:
            continue
        if ratio < red_thresh:
            continue
        buf = io.BytesIO()
        crop.save(buf, format="PNG")
        crop_path = obj.get("crop_path") or ""
        seals.append({
            "type": "seal",
            "bbox": [int(v) for v in bbox],
            "red_ratio": round(ratio, 4),
            "source_type": obj.get("type"),
            "crop_path": crop_path,
            "crop_file": basename_for_url(crop_path) if crop_path else None,
            "image_b64": base64.b64encode(buf.getvalue()).decode(),
        })
    return seals


_VO_PRIORITY = {                      # ưu tiên giữ khi gộp (box gọn, hợp khớp brand/seal)
    "signature_candidate": 5, "logo_candidate": 4,
    "logo_block": 3, "logo_text_candidate": 2, "visual_candidate": 1,
}


def _vo_area(b) -> int:
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1]) if b and len(b) == 4 else 0


def _vo_overlap(a, b) -> float:
    """intersection / min(area) — bắt cả TRƯỜNG HỢP BAO NHAU (box nhỏ nằm trong box lớn)."""
    if not a or not b or len(a) != 4 or len(b) != 4:
        return 0.0
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter <= 0:
        return 0.0
    return inter / max(1, min(_vo_area(a), _vo_area(b)))


def dedup_visual_objects(objects: list[dict], overlap_thresh: float = 0.6) -> list[dict]:
    """Gộp visual object TRÙNG NHAU CAO (logo/sign chồng nhau, vd logo_candidate ⊂ logo_block)
    -> giữ box TO NHẤT (bbox lớn nhất, vd logo_block bao cả logo+text), bỏ box nhỏ chồng lên nó.
    overlap = intersection/min(area) >= overlap_thresh thì coi là trùng. Bằng diện tích -> ưu
    tiên type (signature/logo_candidate)."""
    kept: list[dict] = []
    for obj in sorted(objects or [],
                      key=lambda o: (-_vo_area(o.get("bbox")), -_VO_PRIORITY.get(o.get("type"), 0))):
        bb = obj.get("bbox")
        if not bb:
            continue
        if any(_vo_overlap(bb, k.get("bbox")) >= overlap_thresh for k in kept):
            continue
        kept.append(obj)
    return kept
