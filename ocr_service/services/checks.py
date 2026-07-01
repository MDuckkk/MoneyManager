# -*- coding: utf-8 -*-
"""
Đánh giá ràng buộc số học khai trong template (`checks`). Tổng quát hóa
`common.cross_check_totals`: thay vì hardcode bộ khoá, template tự khai.

Thuần stdlib — test offline 100%.

Định dạng check trong template:
  {"sum": ["a","b"], "equals": "c", "tol": 0}            # a + b == c
  {"percent": "thue_suat", "of": "a", "equals": "b", "tol": 1}   # a * suất% == b

Trả: {"failed_fields": set(...), "results": [{check, status: pass|fail|skip}]}
- skip = thiếu dữ liệu (None) -> KHÔNG flag (tránh oan).
- fail -> mọi trường liên quan vào failed_fields (đẩy needs_review).
"""
import re


def _to_int(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    digits = re.sub(r"\D", "", str(v))
    return int(digits) if digits else None


def _to_pct(v):
    if v is None:
        return None
    m = re.search(r"\d+(?:[.,]\d+)?", str(v))
    return float(m.group().replace(",", ".")) if m else None


def evaluate_checks(fields: dict, checks: list) -> dict:
    failed = set()
    results = []
    for chk in checks or []:
        if "sum" in chk and "equals" in chk:
            parts = [_to_int(fields.get(f)) for f in chk["sum"]]
            target = _to_int(fields.get(chk["equals"]))
            involved = list(chk["sum"]) + [chk["equals"]]
            if target is None or any(p is None for p in parts):
                results.append({"check": chk, "status": "skip"})
                continue
            ok = abs(sum(parts) - target) <= chk.get("tol", 0)
            results.append({"check": chk, "status": "pass" if ok else "fail"})
            if not ok:
                failed.update(involved)

        elif "percent" in chk and "of" in chk and "equals" in chk:
            rate = _to_pct(fields.get(chk["percent"]))
            base = _to_int(fields.get(chk["of"]))
            target = _to_int(fields.get(chk["equals"]))
            involved = [chk["percent"], chk["of"], chk["equals"]]
            if rate is None or base is None or target is None:
                results.append({"check": chk, "status": "skip"})
                continue
            ok = abs(base * rate / 100.0 - target) <= chk.get("tol", 1)
            results.append({"check": chk, "status": "pass" if ok else "fail"})
            if not ok:
                failed.update(involved)

        else:
            results.append({"check": chk, "status": "skip"})

    return {"failed_fields": failed, "results": results}
