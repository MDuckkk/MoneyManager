"""Guardrails 2 tầng cho pipeline OCR.

Tier 1 chạy trên ảnh render trước Paddle và chỉ chặn trang trắng / ảnh rõ ràng
không phải tài liệu. Tier 2 chạy sau Paddle layout nhưng trước Surya, dùng box và
layout geometry, không dùng OCR text.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from PIL import Image

from config import (
    ENABLE_TEMPLATE_GUARD,
    TEMPLATE_GUARD_MODE,
    TEMPLATE_GUARD_TIER1_MIN_CONTENT_AREA,
    TEMPLATE_GUARD_TIER1_MIN_INK,
    TEMPLATE_GUARD_TIER2_ALLOW_UNCERTAIN_DOCUMENT,
    TEMPLATE_GUARD_TIER2_MIN_DOCUMENT_SCORE,
    TEMPLATE_GUARD_TIER2_MIN_TEMPLATE_SCORE,
)


@dataclass
class GuardResult:
    allowed: bool
    stage: str
    page_type: str | None
    score: float
    reason: str
    details: dict[str, Any]


def guard_dict(guard: GuardResult | dict | None) -> dict | None:
    if guard is None:
        return None
    if isinstance(guard, dict):
        return guard
    data = asdict(guard)
    data["score"] = round(float(data["score"]), 3)
    return data


def should_reject(guard: GuardResult | dict | None) -> bool:
    if not guard or not ENABLE_TEMPLATE_GUARD:
        return False
    if TEMPLATE_GUARD_MODE == "off":
        return False
    if TEMPLATE_GUARD_MODE == "audit":
        return False
    data = guard_dict(guard)
    return not bool(data and data["allowed"])


def _box_area(box) -> float:
    x1, y1, x2, y2 = [float(v) for v in box]
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _union_bbox(boxes: list) -> list[float] | None:
    if not boxes:
        return None
    return [
        min(float(b[0]) for b in boxes),
        min(float(b[1]) for b in boxes),
        max(float(b[2]) for b in boxes),
        max(float(b[3]) for b in boxes),
    ]


def _norm_box(box, w: float, h: float) -> dict[str, float]:
    x1, y1, x2, y2 = [float(v) for v in box]
    return {
        "x1": x1 / max(w, 1.0),
        "y1": y1 / max(h, 1.0),
        "x2": x2 / max(w, 1.0),
        "y2": y2 / max(h, 1.0),
        "width": max(0.0, x2 - x1) / max(w, 1.0),
        "height": max(0.0, y2 - y1) / max(h, 1.0),
        "area": _box_area(box) / max(w * h, 1.0),
        "cy": ((y1 + y2) / 2.0) / max(h, 1.0),
    }


def tier1_visual_guard(img: Image.Image) -> GuardResult:
    arr = np.asarray(img.convert("L"), dtype=np.uint8)
    h, w = arr.shape[:2]
    mean = float(arr.mean())
    std = float(arr.std())

    dark_ratio = float((arr < 30).mean())
    bright_ratio = float((arr > 245).mean())
    ink = float((arr < 235).mean())

    # Content mask nhẹ: khác nền trắng hoặc khác trung vị toàn ảnh. Giữ ngưỡng rộng
    # để ảnh chụp điện thoại hơi tối/vàng vẫn qua Tier 1.
    median = float(np.median(arr))
    content = (arr < 245) & (np.abs(arr.astype(np.int16) - int(median)) > 8)
    ys, xs = np.where(content)
    if len(xs):
        bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
        content_area = _box_area(bbox) / max(w * h, 1)
    else:
        bbox = None
        content_area = 0.0

    details = {
        "ink_ratio": round(ink, 5),
        "content_area": round(content_area, 5),
        "mean": round(mean, 2),
        "std": round(std, 2),
        "dark_ratio": round(dark_ratio, 5),
        "bright_ratio": round(bright_ratio, 5),
        "content_bbox": bbox,
    }

    if std < 3.0 or ink < TEMPLATE_GUARD_TIER1_MIN_INK:
        return GuardResult(False, "tier1_visual", None, ink, "blank_or_low_content", details)
    if (mean < 18 and dark_ratio > 0.92) or (mean > 252 and bright_ratio > 0.985):
        return GuardResult(False, "tier1_visual", None, ink, "blank_or_low_content", details)
    if content_area < TEMPLATE_GUARD_TIER1_MIN_CONTENT_AREA and ink < TEMPLATE_GUARD_TIER1_MIN_INK * 2:
        return GuardResult(False, "tier1_visual", None, max(ink, content_area), "non_document_obvious", details)
    return GuardResult(True, "tier1_visual", None, min(1.0, max(ink * 20, content_area)), "allowed_visual_candidate", details)


def _layout_boxes_by_label(layout_boxes) -> tuple[list, list]:
    title_boxes, table_boxes = [], []
    for item in layout_boxes or []:
        if isinstance(item, dict):
            label = str(item.get("label", "")).lower()
            box = item.get("coordinate") or item.get("bbox") or item.get("box")
        else:
            label = ""
            box = item
        if not box:
            continue
        ibox = [int(v) for v in box]
        if "title" in label:
            title_boxes.append(ibox)
        elif "table" in label:
            table_boxes.append(ibox)
    return title_boxes, table_boxes


@dataclass
class LayoutMetrics:
    text_count: int
    text_coverage: float
    bbox_area: float
    long_text_count: int
    long_text_ratio: float
    top_text: int
    mid_text: int
    bottom_text: int
    spread_bands: int
    title_box_count: int
    table_box_count: int
    cell_count: int
    table_width: float
    table_cy: float
    has_table: bool
    big_table: bool
    table_middle_lower: bool
    small_table_or_no_big_table: bool
    header_density: float


def _extract_layout_metrics(img_size, rects, layout_boxes, table_cells) -> LayoutMetrics:
    w, h = img_size
    page_area = max(float(w * h), 1.0)
    rects = [list(r) for r in (rects or []) if _box_area(r) > 0]
    title_boxes, table_boxes = _layout_boxes_by_label(layout_boxes)
    table_cells = [list(c) for c in (table_cells or []) if _box_area(c) > 0]

    text_count = len(rects)
    cell_count = len(table_cells)
    bbox = _union_bbox(rects)
    text_coverage = sum(_box_area(r) for r in rects) / page_area
    bbox_area = (_box_area(bbox) / page_area) if bbox else 0.0
    table_bbox = _union_bbox(table_cells or table_boxes)
    table_norm = _norm_box(table_bbox, w, h) if table_bbox else None

    top = sum(1 for r in rects if ((r[1] + r[3]) / 2) < h * 0.33)
    mid = sum(1 for r in rects if h * 0.33 <= ((r[1] + r[3]) / 2) < h * 0.66)
    bottom = text_count - top - mid
    spread_bands = sum(1 for n in (top, mid, bottom) if n >= 2)
    long_text_count = sum(1 for r in rects if (float(r[2]) - float(r[0])) / max(float(w), 1.0) >= 0.30)
    long_text_ratio = long_text_count / max(text_count, 1)

    table_width = table_norm["width"] if table_norm else 0.0
    table_cy = table_norm["cy"] if table_norm else 0.0
    has_table = bool(table_boxes or cell_count >= 4)
    big_table = has_table and table_width >= 0.45 and (cell_count >= 8 or bool(table_boxes))
    table_middle_lower = 0.25 <= table_cy <= 0.90 if table_norm else False
    header_density = top / max(text_count, 1)

    return LayoutMetrics(
        text_count=text_count,
        text_coverage=text_coverage,
        bbox_area=bbox_area,
        long_text_count=long_text_count,
        long_text_ratio=long_text_ratio,
        top_text=top,
        mid_text=mid,
        bottom_text=bottom,
        spread_bands=spread_bands,
        title_box_count=len(title_boxes),
        table_box_count=len(table_boxes),
        cell_count=cell_count,
        table_width=table_width,
        table_cy=table_cy,
        has_table=has_table,
        big_table=big_table,
        table_middle_lower=table_middle_lower,
        small_table_or_no_big_table=(not big_table or cell_count <= 18),
        header_density=header_density,
    )


def _metric_value(metrics: LayoutMetrics, feature: str):
    aliases = {
        "text_bbox_area": "bbox_area",
        "top_text_boxes": "top_text",
        "mid_text_boxes": "mid_text",
        "bottom_text_boxes": "bottom_text",
        "table_cell_count": "cell_count",
        "table_width_ratio": "table_width",
        "title_boxes": "title_box_count",
        "table_boxes": "table_box_count",
        "long_text_boxes": "long_text_count",
    }
    attr = aliases.get(feature, feature)
    if not hasattr(metrics, attr):
        raise ValueError(f"Unknown Tier 2 layout feature: {feature}")
    return getattr(metrics, attr)


def _rule_matches(metrics: LayoutMetrics, rule: dict[str, Any]) -> bool:
    val = _metric_value(metrics, str(rule["feature"]))
    if "equals" in rule and val != rule["equals"]:
        return False
    if "min" in rule and float(val) < float(rule["min"]):
        return False
    if "max" in rule and float(val) > float(rule["max"]):
        return False
    return True


def _score_rule(metrics: LayoutMetrics, rule: dict[str, Any]) -> float:
    weight = float(rule.get("weight", 0.0))
    if weight <= 0:
        return 0.0

    val = _metric_value(metrics, str(rule["feature"]))
    if rule.get("invert"):
        val = not bool(val)

    if "equals" in rule:
        return weight if val == rule["equals"] else 0.0
    if isinstance(val, bool):
        return weight if val else 0.0

    fval = float(val)
    if "min" in rule and fval >= float(rule["min"]):
        return weight
    if "max" in rule and fval <= float(rule["max"]):
        return weight
    if "target" in rule:
        target = max(float(rule["target"]), 1e-9)
        return min(weight, max(0.0, fval / target * weight))
    if "min" in rule or "max" in rule:
        return 0.0
    return min(weight, max(0.0, fval * weight))


def _score_template_layout(metrics: LayoutMetrics, tier2_layout: dict[str, Any]) -> tuple[float, list[str]]:
    score = sum(_score_rule(metrics, rule) for rule in tier2_layout.get("scoring", []))
    evidence = []
    for rule in tier2_layout.get("negative_evidence", []):
        conditions = rule.get("conditions", [])
        if conditions and all(_rule_matches(metrics, cond) for cond in conditions):
            evidence.append(str(rule.get("name", "negative_evidence")))
            effect = rule.get("effect", {}) or {}
            if "cap_score" in effect:
                score = min(score, float(effect["cap_score"]))
            if "subtract" in effect:
                score = max(0.0, score - float(effect["subtract"]))
    return min(1.0, max(0.0, score)), evidence


def _compute_document_score(metrics: LayoutMetrics) -> float:
    score = 0.0
    score += min(0.35, metrics.text_count / 80.0)
    score += min(0.25, metrics.bbox_area * 1.2)
    score += min(0.20, metrics.text_coverage * 6.0)
    score += 0.10 if metrics.spread_bands >= 2 else 0.0
    score += 0.10 if (metrics.title_box_count or metrics.table_box_count or metrics.cell_count >= 6) else 0.0
    return min(1.0, score)


def _legacy_hoa_don_score(metrics: LayoutMetrics) -> float:
    score = 0.0
    score += 0.25 if metrics.text_count >= 18 else metrics.text_count / 72.0
    score += 0.25 if metrics.has_table else 0.0
    score += 0.20 if metrics.cell_count >= 8 else min(0.20, metrics.cell_count / 40.0)
    score += 0.15 if metrics.table_middle_lower else 0.0
    score += 0.15 if metrics.bottom_text >= 4 else min(0.15, metrics.bottom_text / 30.0)
    return min(1.0, score)


def _legacy_bao_gia_score(metrics: LayoutMetrics) -> float:
    score = 0.0
    score += 0.30 if metrics.big_table else (0.15 if metrics.has_table else 0.0)
    score += 0.25 if metrics.cell_count >= 12 else min(0.25, metrics.cell_count / 48.0)
    score += 0.20 if metrics.text_count >= 22 else metrics.text_count / 110.0
    score += 0.15 if metrics.header_density >= 0.18 else min(0.15, metrics.header_density)
    score += 0.10 if metrics.table_width >= 0.55 else 0.0
    return min(1.0, score)


def _legacy_bbnt_score(metrics: LayoutMetrics) -> float:
    score = 0.0
    score += 0.30 if metrics.text_count >= 20 else metrics.text_count / 67.0
    score += 0.20 if metrics.spread_bands >= 2 else 0.0
    score += 0.15 if metrics.title_box_count else 0.0
    score += 0.20 if not metrics.big_table or metrics.cell_count <= 18 else 0.05
    score += 0.15 if metrics.bottom_text >= 3 else min(0.15, metrics.bottom_text / 20.0)
    return min(1.0, score)


def _legacy_score(page_type: str, metrics: LayoutMetrics) -> tuple[float, list[str]]:
    if page_type == "hoa_don":
        return _legacy_hoa_don_score(metrics), []
    if page_type == "bao_gia":
        return _legacy_bao_gia_score(metrics), []
    if page_type == "bien_ban_nghiem_thu":
        score = _legacy_bbnt_score(metrics)
        sparse_ui_like_text = (
            not metrics.has_table
            and metrics.text_count >= 20
            and metrics.long_text_count <= 4
            and metrics.long_text_ratio <= 0.15
        )
        if sparse_ui_like_text:
            return min(score, 0.35), ["sparse_ui_like_text"]
        dense_text_no_table = (
            not metrics.has_table
            and metrics.text_count >= 60
            and metrics.title_box_count >= 4
            and metrics.bbox_area >= 0.65
            and metrics.text_coverage >= 0.08
            and metrics.mid_text >= 20
            and metrics.bottom_text >= 15
        )
        if dense_text_no_table:
            return min(score, 0.35), ["dense_text_no_table"]
        return score, []
    return 0.0, []


def tier2_layout_guard(img_size, rects, layout_boxes, table_cells) -> GuardResult:
    from common import TEMPLATE_BY_PAGE_TYPE, load_template

    metrics = _extract_layout_metrics(img_size, rects, layout_boxes, table_cells)
    document_score = _compute_document_score(metrics)

    class_scores = {}
    negative_evidence = []
    metadata_mismatches = []
    for page_type, template_name in TEMPLATE_BY_PAGE_TYPE.items():
        template = load_template(template_name)
        tier2_layout = template.get("tier2_layout")
        if tier2_layout:
            configured_page_type = tier2_layout.get("page_type")
            if configured_page_type and configured_page_type != page_type:
                metadata_mismatches.append({"template": template_name, "expected": page_type, "actual": configured_page_type})
            score, evidence = _score_template_layout(metrics, tier2_layout)
        else:
            score, evidence = _legacy_score(page_type, metrics)
        class_scores[page_type] = round(min(1.0, score), 3)
        for item in evidence:
            if item not in negative_evidence:
                negative_evidence.append(item)

    page_type, template_score = max(class_scores.items(), key=lambda kv: kv[1])

    details = {
        "text_count": metrics.text_count,
        "text_coverage": round(metrics.text_coverage, 5),
        "text_bbox_area": round(metrics.bbox_area, 5),
        "long_text_count": metrics.long_text_count,
        "long_text_ratio": round(metrics.long_text_ratio, 3),
        "top_text_boxes": metrics.top_text,
        "mid_text_boxes": metrics.mid_text,
        "bottom_text_boxes": metrics.bottom_text,
        "title_box_count": metrics.title_box_count,
        "table_box_count": metrics.table_box_count,
        "table_cell_count": metrics.cell_count,
        "table_width_ratio": round(metrics.table_width, 3),
        "document_score": round(document_score, 3),
        "class_scores": class_scores,
        "negative_evidence": negative_evidence,
    }
    if metadata_mismatches:
        details["metadata_page_type_mismatch"] = metadata_mismatches

    enough_document = document_score >= TEMPLATE_GUARD_TIER2_MIN_DOCUMENT_SCORE
    enough_template = template_score >= TEMPLATE_GUARD_TIER2_MIN_TEMPLATE_SCORE
    if negative_evidence and not enough_template:
        return GuardResult(False, "tier2_layout", None, max(document_score, template_score), "unsupported_layout_candidate", details)
    if enough_document and enough_template:
        return GuardResult(True, "tier2_layout", page_type, template_score, "supported_layout_candidate", details)
    if enough_document and TEMPLATE_GUARD_TIER2_ALLOW_UNCERTAIN_DOCUMENT:
        return GuardResult(True, "tier2_layout", None, document_score, "unknown_supported_candidate", details)
    reason = "low_document_evidence" if not enough_document else "unsupported_layout_candidate"
    return GuardResult(False, "tier2_layout", page_type if enough_template else None, max(document_score, template_score), reason, details)


def guard_result_to_record(filename: str, doc_type: str, page_idx: int, guard: GuardResult | dict, elapsed: float) -> dict:
    return {
        "file": filename,
        "doc_type": doc_type,
        "page_type": None,
        "classify_confidence": 0.0,
        "classify_method": "guard",
        "template_used": None,
        "page": page_idx,
        "status": "rejected",
        "supported": False,
        "fields": {},
        "confidence": {},
        "needs_review": [],
        "guard": guard_dict(guard),
        "elapsed": elapsed,
    }


def guard_result_to_api_page(page_idx: int, guard: GuardResult | dict, elapsed: float) -> dict:
    return {
        "page": page_idx,
        "status": "rejected",
        "supported": False,
        "page_type": None,
        "fields": {},
        "confidence": {},
        "needs_review": [],
        "elapsed_s": elapsed,
        "viz_file": None,
        "guard": guard_dict(guard),
    }
