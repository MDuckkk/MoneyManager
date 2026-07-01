# -*- coding: utf-8 -*-
"""Map a pipeline page record -> ParsedReceipt (the shape Money Manager's backend consumes).

Pure functions, no heavy deps -> unit-testable offline. The pipeline record keys are
Vietnamese invoice fields; we surface only what a personal expense tracker needs, with a
raw-text fallback so a receipt that classifies as `unknown` still yields the total.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date

# Từ khóa (không dấu) báo hiệu dòng chứa tổng tiền — dùng cho fallback raw-text.
_TOTAL_HINTS = ("tong cong", "thanh toan", "thanh tien", "tong tien", "tong", "cong", "total")


def _deaccent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()

# Ưu tiên "tổng thanh toán"; fallback "cộng tiền hàng" nếu thiếu.
_AMOUNT_KEYS = ("tong_thanh_toan", "cong_tien_hang")
_DATE_KEYS = ("ngay_lap",)
_MERCHANT_KEYS = ("ten_nguoi_ban",)


def _to_amount(value) -> int | None:
    """'6.143.500' / '6,143,500 đ' -> 6143500. Trả None nếu không có chữ số."""
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    return int(digits) if digits else None


def _parse_date(value) -> str | None:
    """'05/05/2026' -> '2026-05-05' (ISO). Chấp nhận cả sẵn-ISO."""
    if not value:
        return None
    s = str(value)
    m = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", s)
    if m:
        d, mo, y = (int(x) for x in m.groups())
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    return m.group(0) if m else None


def _money_candidates(s: str) -> list[int]:
    """Các số TIỀN hợp lệ trong 1 chuỗi. Loại mã vạch/mã hàng (>=11 chữ số liền, không có
    dấu phân cách nghìn) và số ngoài khoảng 1.000 .. 10 tỷ."""
    out = []
    for tok in re.findall(r"\d[\d.,]*\d", s):
        digits = re.sub(r"\D", "", tok)
        if not digits:
            continue
        if len(digits) >= 11 and "." not in tok and "," not in tok:
            continue  # barcode / mã hàng (vd 8936084590026)
        n = int(digits)
        if 1000 <= n <= 10_000_000_000:
            out.append(n)
    return out


def _amount_from_text(text: str | None) -> int | None:
    """Fallback khi không có field. Ưu tiên dòng có từ khóa 'tổng/thanh toán' và lấy số tiền
    trên CHÍNH dòng đó hoặc 1-2 dòng kế (nhãn và số thường nằm khác dòng trên hoá đơn bán lẻ);
    nếu không có, lấy số tiền hợp lệ lớn nhất (đã loại mã vạch)."""
    if not text:
        return None
    lines = [ln.strip() for ln in text.splitlines()]
    for i, ln in enumerate(lines):
        if any(h in _deaccent(ln) for h in _TOTAL_HINTS):
            cand = _money_candidates(ln)
            if not cand:
                for j in (i + 1, i + 2):
                    if 0 <= j < len(lines):
                        cand = _money_candidates(lines[j])
                        if cand:
                            break
            if cand:
                return max(cand)
    allc = [n for ln in lines for n in _money_candidates(ln)]
    return max(allc) if allc else None


def _first(fields: dict, keys) -> object | None:
    for k in keys:
        v = fields.get(k)
        if v not in (None, "", []):
            return v
    return None


def to_parsed_receipt(record: dict) -> dict:
    """record = 1 page do build_record/parse_page dựng ra."""
    fields = record.get("fields") or {}
    conf = record.get("confidence") or {}

    amount, amount_key = None, None
    for k in _AMOUNT_KEYS:
        amount = _to_amount(fields.get(k))
        if amount is not None:
            amount_key = k
            break
    if amount is None:
        amount = _amount_from_text(record.get("raw_text"))

    line_items = []
    ds = fields.get("danh_sach_dong_hang")
    if isinstance(ds, list):
        for it in ds:
            if isinstance(it, dict):
                line_items.append({
                    "name": it.get("ten_hang") or it.get("name"),
                    "price": _to_amount(it.get("thanh_tien") or it.get("price")),
                })

    # confidence: của field tổng tiền nếu có; else độ tin cậy phân loại trang.
    confidence = conf.get(amount_key) if amount_key else None
    if confidence is None:
        confidence = record.get("classify_confidence")

    return {
        "amount": amount,
        "occurredAt": _parse_date(_first(fields, _DATE_KEYS)),
        "merchant": _first(fields, _MERCHANT_KEYS),
        "lineItems": line_items,
        "confidence": confidence,
        "needsReview": [f for f in (record.get("needs_review") or []) if f != "__unclassified__"],
        "pageType": record.get("page_type"),
        "rawText": record.get("raw_text") or "",
        "rawFields": fields,   # để backend/debug đối chiếu field gốc
    }
