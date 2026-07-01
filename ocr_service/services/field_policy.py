# -*- coding: utf-8 -*-
"""
Policy engine (concern #1): với 1 trang đã trích (fields + confidence), quyết định
mỗi trường:
  - DANGEROUS nghi ngờ -> needs_review (CẤM LLM sửa); nếu vision_verify -> vision_candidates
  - SOFT confidence thấp -> soft_fix_candidates (LLM sửa dấu, giữ gốc)

Policy đọc từ template; thiếu khai -> DEFAULT theo tên/type (xem _default_sensitivity).
Thuần stdlib + validators/checks/vn_num (đều thuần) -> test offline 100%.
"""
import validators as V
import vn_num
from checks import evaluate_checks

# Trường mã định danh: luôn nguy hiểm dù type=string
_IDENTIFIER = {"so_hoa_don", "ky_hieu_hoa_don", "ma_co_quan_thue"}
# Mặc định bật vision đối chiếu (Tier 1 = trường không có guard tin cậy)
_VISION_TIER1 = {"so_hoa_don", "ma_co_quan_thue", "ky_hieu_hoa_don", "gia_tri_nghiem_thu"}


def _default_sensitivity(name: str, meta: dict) -> str:
    t = meta.get("type")
    if name in _IDENTIFIER or name.startswith("mst") or name.startswith("ngay"):
        return "dangerous"
    if name in ("thue_suat", "so_dong_hang", "danh_sach_dong_hang"):
        return "dangerous"
    if t in ("integer", "number"):
        return "dangerous"
    return "soft"


def resolve_field_policy(name: str, meta: dict) -> dict:
    """Gộp khai báo template + default -> policy hiệu lực cho 1 trường."""
    meta = meta or {}
    sens = meta.get("sensitivity") or _default_sensitivity(name, meta)
    vision = meta.get("vision_verify")
    if vision is None:   # default: Tier1 + (mst/ngay = Tier2 backstop), chỉ khi dangerous
        vision = (name in _VISION_TIER1 or name.startswith(("mst", "ngay"))) and sens == "dangerous"
    return {
        "sensitivity": sens,
        "format": meta.get("format"),
        "vision_verify": bool(vision),
        "date_check": name.startswith("ngay"),
        "mst_check": name.startswith("mst"),
    }


def evaluate_page(template: dict, fields: dict, confidences: dict | None = None,
                  *, threshold: float = 0.85, mst_checksum: bool = False) -> dict:
    """Trả: needs_review (list), reasons {field:[..]}, vision_candidates, soft_fix_candidates."""
    confidences = confidences or {}
    metas = (template.get("json_schema") or {}).get("fields", {})
    failed = evaluate_checks(fields, template.get("checks"))["failed_fields"]

    wc = template.get("words_check")  # {"words":"so_tien_bang_chu","equals":"tong_..."}
    words_field = wc["words"] if wc else None
    words_bad = bool(wc) and vn_num.amount_matches_words(
        fields.get(wc["equals"]), fields.get(wc["words"])) is False

    needs_review, reasons, vision_c = [], {}, []
    for name, meta in metas.items():
        pol = resolve_field_policy(name, meta)
        val = fields.get(name)
        conf = confidences.get(name, 1.0)

        # HARD signal: giá trị sai/dị dạng một cách KHÁCH QUAN (validator/cross-check/words)
        # -> luôn review, BẤT KỂ soft/dangerous (format khai tường minh là hợp đồng phải giữ).
        hard = []
        if name in failed:
            hard.append("cross-check số học lệch")
        if pol["format"] and val is not None and not V.valid_format(val, pol["format"]):
            hard.append("sai format")
        if pol["date_check"] and val is not None and not V.valid_date(val):
            hard.append("ngày không hợp lệ")
        if pol["mst_check"] and val is not None:
            if not V.valid_mst_format(val):
                hard.append("MST sai format")
            elif mst_checksum and not V.mst_checksum_ok(val):
                hard.append("MST sai checksum")
        if name == "thue_suat" and val is not None and not V.valid_thue_suat(val):
            hard.append("thuế suất ngoài chuẩn {0,5,8,10}%")
        if name == words_field and words_bad:
            hard.append("tiền bằng chữ ≠ tổng")

        if hard:
            needs_review.append(name)
            reasons[name] = hard
            if pol["vision_verify"]:
                vision_c.append(name)
        elif conf < threshold and pol["sensitivity"] == "dangerous":
            # Confidence thấp CHỈ flag với trường nguy hiểm (cần chính xác). Field text
            # KHÔNG vào review vì sai dấu -> để bước phục hồi dấu offline (diacritics) lo.
            needs_review.append(name)
            reasons[name] = [f"confidence {conf:.2f} < {threshold}"]
            if pol["vision_verify"]:
                vision_c.append(name)

    return {
        "needs_review": sorted(needs_review),
        "reasons": reasons,
        "vision_candidates": sorted(vision_c),
    }


def soft_string_fields(template: dict, fields: dict) -> list[str]:
    """Field SOFT (text) có giá trị chuỗi không rỗng -> đích phục hồi dấu offline."""
    metas = (template.get("json_schema") or {}).get("fields", {})
    out = []
    for name, meta in metas.items():
        if resolve_field_policy(name, meta)["sensitivity"] == "soft":
            v = fields.get(name)
            if isinstance(v, str) and v.strip():
                out.append(name)
    return out
