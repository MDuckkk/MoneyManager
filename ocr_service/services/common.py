"""
THU VIEN CHUNG cho ca 4 tool OCR (Gemini/Tesseract/EasyOCR/Paddle+VietOCR).
- Phan loai trang (classify_page_api / classify_page_regex)
- Trich xuat field theo template (extract_fields_from_template + cac handler dac biet)
- build_record / compute_confidences / write_results_csv

Moi truong dinh nghia trong templates/<doc_type>.json (ocr_label_en / ocr_label_vi /
ocr_special). Engine doc template + chay generic extraction — khong hardcode ten truong.
Cac tool runner nam o tools/<tool>/run.py va import tu day.
"""

from textnorm import ensure_utf8_stdout
ensure_utf8_stdout()

import csv
import json
import logging
import re
import unicodedata
from pathlib import Path

from config import CONFIDENCE_THRESHOLD, CLASSIFY_FALLBACK
from field_policy import evaluate_page as _evaluate_page, soft_string_fields

log = logging.getLogger("ocr.common")

_ROOT         = Path(__file__).parent
TEMPLATES_DIR = _ROOT / "templates"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def strip_tones(text: str) -> str:
    """Bo dau thanh, giu lai ky tu co so Latin (a, o, u, ...) de match robust hon.
    Luu y: 'đ/Đ' (U+0111/0110) khong decompose qua NFD -> map tay ve d/D."""
    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def _normalize_money(s: str | None) -> int | None:
    if s is None:
        return None
    # Lay CUM SO DAU TIEN (chu so + dau phan cach . ,) roi bo dau phan cach.
    # Tranh gop rac duoi nhu "60.258.000 VNĐ.1960" -> 602580001960 (chi lay 60258000).
    m = re.search(r"\d[\d.,]*\d|\d", s)
    if not m:
        return None
    cleaned = re.sub(r"\D", "", m.group(0))
    return int(cleaned) if cleaned else None


def _extract_bao_hanh(text: str) -> str | None:
    """'Bao hanh: 12 thang' hoac '... bao hanh 12 thang ke tu ...' (co/khong dau hai cham)."""
    m = re.search(r"b[aả]o\s*h[aà]nh[:\s]+(\d+)\s*th[aá]ng", text.lower())
    return f"{m.group(1)} tháng" if m else None


def _extract_company_top(text: str) -> str | None:
    """Ten nha thau = dong 'CONG TY ...' (hoac CTY/Doanh nghiep/Ho kinh doanh) dau trang."""
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"(c[oô]ng\s*ty|cty|doanh\s*nghi[eệ]p|h[oộ]\s*kinh\s*doanh)\b", s.lower()):
            return s
    return None


def _clean_bang_chu(s: str | None) -> str | None:
    """So tien bang chu: cat RAC VietOCR sinh sau tu ket (')... 19990', '/.', '].' ...).
    Tu ket chuan la 'dong chẵn' — OCR hay sai dau o chu 'chẵn' (chắn/chẫn/chằn) -> chuan
    hoa ve 'chẵn' (tu cố định trong ke toan, sua loi dau co he thong, khong bia text)."""
    if not s:
        return s
    m = re.search(r"(.*?đồng)(\s+ch\wn)?", s, re.IGNORECASE | re.UNICODE)
    if not m:
        return s.strip()
    base = m.group(1).strip()
    return f"{base} chẵn" if m.group(2) else base


def _extract_cong_subtotal(text: str) -> int | None:
    """Tong truoc thue: nhan 'Cong:' + so (thuong o dong ngay sau), KHONG bat 'Tong cong'."""
    st = strip_tones(text.lower())
    m = re.search(r"(?<!tong )cong\s*:?\s*\n?\s*([\d.,]+)", st)
    return _normalize_money(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Phan loai loai chung tu (buoc PHAN LOAI cua so do de bai)
# Kien truc hybrid: nhanh OCR truyen thong (Tesseract/EasyOCR/PaddleOCR) goi
# 1 con vision nho qua API (Gemini Flash-Lite) phan loai tung trang tu ANH
# -> khong phu thuoc chat luong OCR text. Regex tren tieu de la FALLBACK khi
# API loi. Luu y: vi co buoc goi API nay, nhanh OCR truyen thong khong con
# offline thuan (chap nhan: phan loai re hon nhieu so voi trich xuat).
# ---------------------------------------------------------------------------

# page_type == doc_type == ten file template (1-1, KHONG remap mo ho). 'hoa_don_gtgt'
# la ten chinh xac (hoa don GTGT/TT78) — khong dung nhan ngan 'hoa_don' nua. Registry
# nay = danh sach loai HO TRO; them template = them 1 dong (key=value=ten file .json).
TEMPLATE_BY_PAGE_TYPE = {
    "hoa_don_gtgt":        "hoa_don_gtgt",
    "bao_gia":             "bao_gia",
    "bien_ban_nghiem_thu": "bien_ban_nghiem_thu",
    "bang_ke_uu_dai":      "bang_ke_uu_dai",
}

# Rule regex lop FREE dung TU template (classify_keywords + classify_priority) — KHONG
# hardcode o day. Them/sua loai = sua template. Priority nho check truoc (BBNT truoc
# bao_gia vi body BBNT co nhac "bao gia"). Build lazy: load_template dinh nghia phia duoi.
_PAGE_TYPE_RULES = None


def _page_type_rules() -> list[tuple[str, "re.Pattern"]]:
    global _PAGE_TYPE_RULES
    if _PAGE_TYPE_RULES is None:
        ranked = []
        for page_type, tmpl_name in TEMPLATE_BY_PAGE_TYPE.items():
            t = load_template(tmpl_name)
            prio = t.get("classify_priority", 99)
            for pat in (t.get("classify_keywords") or []):
                ranked.append((prio, page_type, re.compile(pat)))
        ranked.sort(key=lambda r: r[0])
        _PAGE_TYPE_RULES = [(pt, pat) for _, pt, pat in ranked]
    return _PAGE_TYPE_RULES


def classify_page_regex(text: str, fallback: str | None = None) -> tuple[str, float]:
    """Lop FREE: phan loai bang keyword TIEU DE (text da bo dau thanh) — 0 chi phi.
    Tieu de 3 loai chung tu rat phan biet (HOA DON / BAO GIA / BIEN BAN NGHIEM THU).
    Tra (page_type, conf): match tieu de -> 0.95; khong match -> (fallback, 0.0).
    #3 unknown-gate: fallback mac dinh = CLASSIFY_FALLBACK ('unknown') -> KHONG ep hoa_don."""
    head = strip_tones(text.lower())[:400]
    for page_type, pat in _page_type_rules():
        if pat.search(head):
            return page_type, 0.95
    return (fallback if fallback is not None else CLASSIFY_FALLBACK), 0.0


def classify_page_api(title_text: str, image_bytes: bytes | None = None) -> tuple[str, float, str]:
    """Phan loai theo keyword tieu de (regex, free) — ban khong-LLM (da bo nhanh vision).
    `image_bytes` giu trong chu ky cho tuong thich nhung khong dung.
    Tra (page_type, confidence, method)."""
    page_type, confidence = classify_page_regex(title_text)
    if confidence >= 0.9:
        return page_type, confidence, "keyword"
    return "unknown", 0.0, "keyword"


# ---------------------------------------------------------------------------
# Template loader
# ---------------------------------------------------------------------------

_template_cache: dict[str, dict] = {}

def load_template(doc_type: str) -> dict:
    if doc_type not in _template_cache:
        path = TEMPLATES_DIR / f"{doc_type}.json"
        _template_cache[doc_type] = json.loads(path.read_text(encoding="utf-8"))
    return _template_cache[doc_type]


# ---------------------------------------------------------------------------
# Special-case extractors (fields that cannot use generic label approach)
# ---------------------------------------------------------------------------

def _extract_so_hoa_don(text_lower: str, text_orig: str) -> tuple[str | None, bool]:
    """Tra ve (gia_tri, da_dung_fallback). Fallback = doan heuristic, can user review."""
    # Detector co the tach 'So:' + so thanh box chong cat cut (vd '0000778' vs
    # '00007781'). re.search lay match DAU -> de dinh box ngan. Lay dai nhat.
    matches = [m.group(1) for m in re.finditer(r"s[o\xf4ố\xf6][:\s]+(\d{5,8})\b", text_lower)]
    if matches:
        return max(matches, key=len), False
    # Fallback: so hoa don la day 6-8 chu so PAD so 0 dau, dung rieng 1 dong — khi
    # detector tach 'So:' va so thanh 2 box roi nhau thi pattern cung-dong tren khong bat.
    # Lay day DAI NHAT (detector co the sinh box chong cat cut, vd '0000778' vs '00007781').
    cands = [s for line in text_orig.splitlines()
             if re.fullmatch(r"0\d{5,7}", (s := line.strip()))]
    return (max(cands, key=len), True) if cands else (None, False)


def _extract_ky_hieu(text_stripped: str, text_orig: str) -> tuple[str | None, bool]:
    """Ky hieu: OCR thuong doc '1' thanh 'I'/'l', can normalize. Khop nhan tren text
    DA BO DAU (ben voi moi bien the dau OCR doc: Ky/Kỳ/Kỷ...). Tra (gia_tri, fallback)."""
    fallback = False
    val = _search(r"ky\s*hieu[^:]*:\s*([0-9il][a-z0-9]{5,8})\b", text_stripped, text_orig)
    if not val:
        # Fallback: "hide:" la OCR garble pho bien cua "Ky hieu:"
        val = _search(r"hide[^:]*:\s*([0-9il][a-z0-9]{5,8})\b", text_stripped, text_orig)
        fallback = bool(val)
    if val:
        val = val.upper()
        if val[0] in ("I", "L"):
            val = "1" + val[1:]
    return val, fallback


def _extract_ngay_lap(text: str) -> str | None:
    lo = text.lower()
    m = re.search(r"ng[a\xe0]y\s+(\d{1,2})\s+th[a\xe1]ng\s+(\d{1,2})\s+n[aă]m\s+(\d{4})", lo)
    if m:
        d, mo, y = m.group(1), m.group(2), m.group(3)
        return f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
    m2 = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", text)
    if m2:
        return f"{m2.group(3)}-{m2.group(2)}-{m2.group(1)}"
    return None


def _search(pattern: str, text_lower: str, text_orig: str) -> str | None:
    m = re.search(pattern, text_lower)
    if not m:
        return None
    return text_orig[m.start(1):m.end(1)].strip()


# ---------------------------------------------------------------------------
# Generic label-based extractor (engine cho moi truong trong template)
# ---------------------------------------------------------------------------

def _extract_by_label(
    text_lower: str,
    text_stripped: str,
    text_orig: str,
    label_en: str | None,
    label_vi: str | None,
    occurrence: int = 0,
) -> str | None:
    """
    Thu tu: English label truoc (ASCII - OCR khong garble), sau do VI stripped.
    occurrence: thu tu xuat hien (0=lan dau, 1=lan 2) -- dung cho MST, Dia chi xuat hien 2 lan.
    Tra ve raw text ngay sau dau hai cham, truoc |, └, dong moi.
    """
    attempts = []

    if label_en:
        # "(English label)": value  -- rat on dinh vi ASCII
        pat = r"\(" + re.escape(label_en.lower()) + r"\)[^:]*:\s*(.+?)(?=\s*[|│\n]|$)"
        attempts.append((text_lower, pat))

    if label_vi:
        # Stripped VI label: bo dau thanh de match moi bien the OCR
        vi_stripped = strip_tones(label_vi.lower())
        pat = re.escape(vi_stripped) + r"[^:]*:\s*(.+?)(?=\n|$)"
        attempts.append((text_stripped, pat))

    for search_text, pattern in attempts:
        all_matches = list(re.finditer(pattern, search_text))
        if len(all_matches) > occurrence:
            m = all_matches[occurrence]
            # Lay span tu text_orig de giu nguyen dau thanh
            raw = text_orig[m.start(1):m.end(1)].strip()
            # Bo duoi "./" (ky hieu ket thuc "so tien bang chu")
            raw = re.sub(r"\s*\./\.?\s*$", "", raw).strip()
            if raw:
                return raw

    return None


# ---------------------------------------------------------------------------
# Template-driven main extractor
# ---------------------------------------------------------------------------

def extract_fields_from_template(text: str, template_type: str) -> tuple[dict, set]:
    """
    Doc template (da duoc classify_page chon dung loai) -> lay danh sach truong
    -> chay generic extraction. Khong hardcode per-field ngoai cac ocr_special.
    `template_type` la mot trong TEMPLATE_BY_PAGE_TYPE.values().
    """
    template   = load_template(template_type)
    fields_def = template["json_schema"]["fields"]

    lo       = text.lower()
    stripped = strip_tones(lo)
    result   = {}
    review: set[str] = set()   # field trich bang fallback/heuristic -> can user review

    # Dem so lan moi (label_en, label_vi) da duoc dung -- de xu ly truong xuat hien nhieu lan
    _seen: dict[str, int] = {}

    for field_name, fdef in fields_def.items():
        ftype   = fdef.get("type", "string")
        special = fdef.get("ocr_special")

        # -- Truong dac biet: dung handler rieng --
        if special == "unsupported":
            result[field_name] = None
            continue
        if special == "percent":
            # thue_suat tren bao gia nam trong "Thue GTGT (10%):" -> bat % truc tiep
            m = re.search(r"(\d+)\s*%", text)
            result[field_name] = f"{m.group(1)}%" if m else None
            continue
        if special == "ngay_lap" or field_name == "ngay_lap":
            result[field_name] = _extract_ngay_lap(text)
            continue
        if special == "ky_hieu" or field_name == "ky_hieu_hoa_don":
            val, fb = _extract_ky_hieu(stripped, text)
            result[field_name] = val
            if fb:
                review.add(field_name)
            continue
        if special == "so_hoa_don" or field_name == "so_hoa_don":
            val, fb = _extract_so_hoa_don(lo, text)
            result[field_name] = val
            if fb:
                review.add(field_name)
            continue
        if special == "bao_hanh":
            result[field_name] = _extract_bao_hanh(text)
            continue
        if special == "company_top":
            result[field_name] = _extract_company_top(text)
            continue
        if special == "cong_subtotal":
            result[field_name] = _extract_cong_subtotal(text)
            continue

        # -- Generic: doc label tu template --
        label_en = fdef.get("ocr_label_en")
        label_vi = fdef.get("ocr_label_vi")

        # Key de dem occurrence: dung normalized labels
        key = f"{(label_en or '').lower()}|{strip_tones((label_vi or '').lower())}"
        occurrence = _seen.get(key, 0)
        _seen[key] = occurrence + 1

        raw = _extract_by_label(lo, stripped, text, label_en, label_vi, occurrence=occurrence)

        # -- Post-process theo kieu du lieu --
        if ftype == "integer":
            result[field_name] = _normalize_money(raw)
        elif field_name == "thue_suat" and raw:
            m = re.search(r"(\d+)\s*%", raw)
            result[field_name] = f"{m.group(1)}%" if m else raw
        elif field_name == "so_tien_bang_chu":
            result[field_name] = _clean_bang_chu(raw)
        elif field_name == "ma_co_quan_thue" and raw:
            result[field_name] = re.sub(r"\s+", "", raw)   # ma la chuoi lien -> bo space OCR chen
        else:
            result[field_name] = raw

    return result, review


# ---------------------------------------------------------------------------
# Gom dong theo vi tri (run.py dung de dung lai text doc-order)
# ---------------------------------------------------------------------------

def _group_rows(items: list, overlap: float = 0.4) -> list:
    """Gom items thanh HANG bang chong-lan y thuc (interval overlap), khong
    lam tron dai-y. Tra list[row], moi row sort theo x, cac row sort theo y."""
    rows: list[list] = []
    for it in sorted(items, key=lambda t: (t[1] + t[3]) / 2):
        h = it[3] - it[1]
        for row in rows:
            ry1 = min(r[1] for r in row); ry2 = max(r[3] for r in row)
            ov = max(0, min(it[3], ry2) - max(it[1], ry1))
            if ov > overlap * min(h, ry2 - ry1):
                row.append(it); break
        else:
            rows.append([it])
    for row in rows:
        row.sort(key=lambda t: t[0])
    rows.sort(key=lambda row: min(r[1] for r in row))
    return rows


# ---------------------------------------------------------------------------
# Confidence tung truong (parity voi pipeline Gemini)
# Gemini tu khai confidence; OCR truyen thong khong co -> ta lay confidence
# ma chinh engine OCR bao cao cho cac token tao nen gia tri truong do.
# ---------------------------------------------------------------------------

def _field_confidence(value, tokens: list[tuple[str, float]]) -> float:
    """confidence 1 truong = trung binh confidence cua cac token OCR khop voi gia tri.
    Truong rong/None -> 0.0 (khong doc duoc / khong co tren trang)."""
    if value is None or value == "" or value == []:
        return 0.0
    if not tokens:
        return 0.0
    words = re.findall(r"\w+", strip_tones(str(value).lower()))
    if not words:
        return 0.0
    confs = []
    for w in words:
        best, found = 0.0, False
        for tok_text, tok_conf in tokens:
            if w and (w in tok_text or tok_text in w):
                best, found = max(best, tok_conf), True
        if found:
            confs.append(best)
    return round(sum(confs) / len(confs), 3) if confs else 0.5


def compute_confidences(fields: dict, tokens: list[tuple[str, float]]) -> dict:
    norm_tokens = [(strip_tones(str(t).lower()), c) for t, c in (tokens or [])]
    return {name: _field_confidence(val, norm_tokens) for name, val in fields.items()}


# Cac bo (truoc_thue, thue, tong) theo tung schema template — cross-check ke toan
_TOTAL_KEY_SETS = [
    ("tong_tien_truoc_thue",    "tien_thue", "tong_tien_thanh_toan"),   # hoa_don_gtgt
    ("tong_gia_tri_truoc_thue", "tien_thue", "tong_gia_tri_bao_gia"),   # bao_gia
]


def cross_check_totals(fields: dict) -> list:
    """Rang buoc ke toan: tong = truoc_thue + thue. Tra ve list truong can review
    neu LECH (hoac khong parse duoc so); [] neu khop hoac thieu du lieu. Tin hieu
    DOC LAP voi confidence — bat loi OCR/LLM doc sai 1 trong 3 con so."""
    for k_truoc, k_thue, k_tong in _TOTAL_KEY_SETS:
        truoc, thue, tong = fields.get(k_truoc), fields.get(k_thue), fields.get(k_tong)
        if truoc is None or thue is None or tong is None:
            continue
        try:
            return [] if int(truoc) + int(thue) == int(tong) else [k_truoc, k_thue, k_tong]
        except (TypeError, ValueError):
            return [k_truoc, k_thue, k_tong]
    return []


def build_record(filename: str, doc_type: str, page_idx: int,
                 text: str, tokens: list[tuple[str, float]], elapsed: float,
                 page_type: str, classify_confidence: float,
                 classify_method: str = "vision-api") -> dict:
    """Dung 1 record theo dung so do de bai (parity voi pipeline Gemini):
    PDF->anh -> PHAN LOAI (vision-API) -> template tuong ung -> JSON + confidence tung truong.
    `page_type`/`classify_confidence` do classify_page_api tinh truoc o vong main."""
    # #3 unknown-gate: khong nhan dang duoc loai -> record toi thieu, ca trang vao review +
    # danh dau unknown (parse_page co the trich TEXT tu do neu OCR_EXTRACT_UNKNOWN=1). KHONG crash.
    if page_type not in TEMPLATE_BY_PAGE_TYPE:
        return {
            "file": filename, "doc_type": doc_type, "page_type": "unknown",
            "classify_confidence": classify_confidence, "classify_method": classify_method,
            "template_used": None, "page": page_idx,
            "fields": {}, "confidence": {},
            "needs_review": ["__unclassified__"],
            "needs_review_reasons": {"__unclassified__": ["không nhận dạng được loại chứng từ"]},
            "vision_candidates": [],
            "unknown": True, "cross_check_failed": False,
            "raw_text": text, "elapsed": elapsed,
        }
    template_type = TEMPLATE_BY_PAGE_TYPE[page_type]
    tmpl = load_template(template_type)
    fields, review_flags = extract_fields_from_template(text, template_type)
    conf   = compute_confidences(fields, tokens)
    # Field trich bang fallback/heuristic: ha confidence xuong duoi nguong de phan anh
    # do bat dinh + chac chan vao needs_review (du token-confidence co the cao).
    for f in review_flags:
        conf[f] = min(conf.get(f, 0.0), 0.5)

    # Phục hồi dấu (LLM Gemini) cho field text; no-op nếu thiếu service_account.
    from diacritics import restore_fields as _restore_diacritics, restore_listfield
    fields, diac_original = _restore_diacritics(fields, soft_string_fields(tmpl, fields))
    if isinstance(fields.get("danh_sach_dong_hang"), list):
        restore_listfield(fields["danh_sach_dong_hang"])

    rec = build_record_from_fields(filename, doc_type, page_idx, fields, conf, elapsed,
                                   page_type, classify_confidence, classify_method,
                                   extra_review=review_flags, fields_original=diac_original)
    rec["raw_text"] = text
    return rec


def build_record_from_fields(filename: str, doc_type: str, page_idx: int,
                             fields: dict, conf: dict, elapsed: float,
                             page_type: str, classify_confidence: float,
                             classify_method: str = "vision-api",
                             *, extra_review=None, fields_original=None) -> dict:
    """Dựng record từ fields/conf ĐÃ trích (dùng chung cho regex VÀ LLM-extract).
    Chạy cross-check + policy (validator/needs_review/vision) — KHÔNG tự trích xuất."""
    from config import ENABLE_POLICY
    tmpl = load_template(TEMPLATE_BY_PAGE_TYPE[page_type])
    if ENABLE_POLICY:
        cross = cross_check_totals(fields)
        policy = _evaluate_page(tmpl, fields, conf, threshold=CONFIDENCE_THRESHOLD)
        needs_review = sorted((set(extra_review) if extra_review else set())
                              | set(cross) | set(policy["needs_review"]))
        reasons = policy["reasons"]
        vision_candidates = policy["vision_candidates"]
    else:
        cross = []
        needs_review = sorted(set(extra_review) if extra_review else set())
        reasons = {}
        vision_candidates = []

    return {
        "file":                filename,
        "doc_type":            doc_type,
        "page_type":           page_type,
        "classify_confidence": classify_confidence,
        "classify_method":     classify_method,
        "template_used":       TEMPLATE_BY_PAGE_TYPE[page_type],
        "page":                page_idx,
        "fields":              fields,
        "confidence":          conf,
        "needs_review":        needs_review,
        "needs_review_reasons": reasons,
        "vision_candidates":   vision_candidates,
        "fields_original":     fields_original or {},
        "cross_check_failed":  bool(cross),
        "raw_text":            "",
        "elapsed":             elapsed,
    }


# ---------------------------------------------------------------------------
# results -> CSV (flatten, parity voi results.csv cua Gemini)
# ---------------------------------------------------------------------------

_CSV_META_COLS = ["file", "page", "page_type", "doc_type", "template_used", "classify_confidence"]


def write_results_csv(all_results: list[dict], csv_path: Path) -> Path:
    field_cols: list[str] = []
    for rec in all_results:
        for k in rec.get("fields", {}):
            if k not in field_cols:
                field_cols.append(k)
    header = _CSV_META_COLS + field_cols + ["needs_review"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for rec in all_results:
            fields = rec.get("fields", {})
            row = [rec.get(c, "") for c in _CSV_META_COLS]
            for col in field_cols:
                v = fields.get(col)
                if isinstance(v, (list, dict)):
                    v = json.dumps(v, ensure_ascii=False)
                elif v is None:
                    v = ""
                row.append(v)
            row.append("; ".join(rec.get("needs_review", [])))
            writer.writerow(row)
    return csv_path
