# -*- coding: utf-8 -*-
"""Match cropped invoice logos against GT logo images."""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from difflib import SequenceMatcher

import numpy as np
from PIL import Image, ImageOps


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
DEFAULT_GT_DIR = Path("sample_documents") / "GT_logo"
DEFAULT_CROP_DIR = Path("results") / "crops"
DEFAULT_RAW_DIR = Path("results") / "raw"
DEFAULT_OUT_JSON = Path("results") / "logo_match_results.json"
DEFAULT_OUT_CSV = Path("results") / "logo_match_results.csv"


@dataclass(frozen=True)
class ImageScore:
    hash_score: float
    template_score: float
    score: float


@dataclass(frozen=True)
class MatchResult:
    crop: str
    crop_type: str
    crop_text: str
    best_gt: str
    best_brand: str
    text_score: float | None
    visual_score: float
    hash_score: float
    template_score: float
    final_score: float
    matched: bool
    reason: str


def normalize_brand_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def brand_from_gt_path(path: Path) -> str:
    stem = path.stem.lower()
    for prefix in ("logo_", "gt_", "brand_"):
        if stem.startswith(prefix):
            stem = stem[len(prefix):]
            break
    return stem


def text_similarity(observed: str, expected_brand: str) -> float:
    obs = normalize_brand_text(observed)
    exp = normalize_brand_text(expected_brand)
    if not obs or not exp:
        return 0.0
    if exp in obs:
        return 1.0
    if obs in exp:
        return min(len(obs), len(exp)) / max(len(obs), len(exp))
    return SequenceMatcher(None, obs, exp).ratio()


def _load_image(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def _fit_to_canvas(img: Image.Image, size: tuple[int, int] = (256, 128)) -> Image.Image:
    img = ImageOps.exif_transpose(img).convert("L")
    img = ImageOps.autocontrast(img)
    canvas_w, canvas_h = size
    scale = min(canvas_w / max(1, img.width), canvas_h / max(1, img.height))
    new_size = (max(1, int(round(img.width * scale))), max(1, int(round(img.height * scale))))
    resized = img.resize(new_size, Image.Resampling.LANCZOS)
    canvas = Image.new("L", size, 255)
    canvas.paste(resized, ((canvas_w - new_size[0]) // 2, (canvas_h - new_size[1]) // 2))
    return canvas


def _dhash(img: Image.Image, hash_size: int = 16) -> np.ndarray:
    small = img.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    arr = np.asarray(small, dtype=np.int16)
    return arr[:, 1:] > arr[:, :-1]


def _hash_similarity(a: Image.Image, b: Image.Image) -> float:
    ha = _dhash(a)
    hb = _dhash(b)
    distance = np.count_nonzero(ha != hb)
    return 1.0 - (distance / ha.size)


def _template_similarity(a: Image.Image, b: Image.Image) -> float:
    aa = np.asarray(a, dtype=np.float32) / 255.0
    bb = np.asarray(b, dtype=np.float32) / 255.0
    mse_score = 1.0 - float(np.mean((aa - bb) ** 2))

    av = aa.reshape(-1) - float(aa.mean())
    bv = bb.reshape(-1) - float(bb.mean())
    denom = float(np.linalg.norm(av) * np.linalg.norm(bv))
    corr = 0.0 if denom == 0.0 else float(np.dot(av, bv) / denom)
    corr_score = (corr + 1.0) / 2.0
    return max(0.0, min(1.0, 0.55 * mse_score + 0.45 * corr_score))


def compare_images(crop: Image.Image, gt: Image.Image) -> ImageScore:
    crop_norm = _fit_to_canvas(crop)
    gt_norm = _fit_to_canvas(gt)
    hash_score = _hash_similarity(crop_norm, gt_norm)
    template_score = _template_similarity(crop_norm, gt_norm)
    score = max(0.0, min(1.0, 0.45 * hash_score + 0.55 * template_score))
    return ImageScore(
        hash_score=round(hash_score, 4),
        template_score=round(template_score, 4),
        score=round(score, 4),
    )


def _image_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)


def _crop_type(path: Path) -> str:
    m = re.search(r"_(logo_block|logo_candidate|logo_text_candidate|signature_candidate)_", path.name)
    return m.group(1) if m else "unknown"


def _raw_stem_from_crop(path: Path) -> str | None:
    m = re.match(r"(.+?)_(logo_block|logo_candidate|logo_text_candidate|signature_candidate)_\d+\.[^.]+$", path.name)
    return m.group(1) if m else None


def crop_text_from_raw(crop_path: Path, raw_dir: Path) -> str:
    stem = _raw_stem_from_crop(crop_path)
    if not stem:
        return ""
    raw_path = raw_dir / f"{stem}.json"
    if not raw_path.exists():
        return ""
    try:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    crop_name = crop_path.name
    for obj in raw.get("visual_objects", []):
        if Path(str(obj.get("crop_path", ""))).name == crop_name:
            return str(obj.get("text", "") or "")
    if _crop_type(crop_path) == "logo_block":
        for obj in raw.get("visual_objects", []):
            if obj.get("type") == "logo_block":
                return str(obj.get("text", "") or "")
    return ""


def match_crop_to_gt(
    crop_path: Path,
    gt_paths: list[Path],
    raw_dir: Path = DEFAULT_RAW_DIR,
    threshold: float = 0.72,
) -> MatchResult:
    crop_img = _load_image(crop_path)
    crop_text = crop_text_from_raw(crop_path, raw_dir)
    if not gt_paths:
        raise ValueError("No GT images provided")

    best_text: tuple[float, Path, str] | None = None
    for gt_path in gt_paths:
        brand = brand_from_gt_path(gt_path)
        txt_score = text_similarity(crop_text, brand) if crop_text else 0.0
        if best_text is None or txt_score > best_text[0]:
            best_text = (txt_score, gt_path, brand)

    assert best_text is not None
    txt_score, gt_path, brand = best_text
    visual = compare_images(crop_img, _load_image(gt_path))
    final = float(visual.score)
    return MatchResult(
        crop=str(crop_path),
        crop_type=_crop_type(crop_path),
        crop_text=crop_text,
        best_gt=str(gt_path),
        best_brand=brand,
        text_score=float(round(txt_score, 4)),
        visual_score=float(visual.score),
        hash_score=float(visual.hash_score),
        template_score=float(visual.template_score),
        final_score=float(round(final, 4)),
        matched=bool(final >= threshold),
        reason="filename_text_candidate_visual_verify",
    )


def match_all(
    gt_dir: Path = DEFAULT_GT_DIR,
    crop_dir: Path = DEFAULT_CROP_DIR,
    raw_dir: Path = DEFAULT_RAW_DIR,
    threshold: float = 0.72,
) -> list[MatchResult]:
    gt_paths = [p for p in _image_files(gt_dir) if p.name.lower().startswith("logo_")]
    crop_paths = sorted(crop_dir.glob("*_logo_block_*.png"))
    return [
        match_crop_to_gt(crop_path, gt_paths, raw_dir=raw_dir, threshold=threshold)
        for crop_path in crop_paths
    ]


def write_results(results: list[MatchResult], out_json: Path, out_csv: Path) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(r) for r in results]
    out_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    if rows:
        with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt-dir", type=Path, default=DEFAULT_GT_DIR)
    ap.add_argument("--crop-dir", type=Path, default=DEFAULT_CROP_DIR)
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    ap.add_argument("--threshold", type=float, default=0.72)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV)
    args = ap.parse_args()

    results = match_all(
        gt_dir=args.gt_dir,
        crop_dir=args.crop_dir,
        raw_dir=args.raw_dir,
        threshold=args.threshold,
    )
    write_results(results, args.out_json, args.out_csv)
    for r in results:
        print(
            f"{Path(r.crop).name}: best={Path(r.best_gt).name} "
            f"text_candidate={r.text_score} visual={r.visual_score:.3f} final={r.final_score:.3f} "
            f"matched={r.matched}"
        )
    print(f"Wrote {args.out_json} and {args.out_csv}")


if __name__ == "__main__":
    main()


def match_logo_image(crop_img: "Image.Image", crop_text: str = "",
                     gt_dir: "Path | str" = DEFAULT_GT_DIR,
                     threshold: float = 0.72) -> dict | None:
    """Khớp 1 logo crop (PIL, in-memory) với mẫu GT_logo -> brand + score.
    Dùng trong pipeline (không cần file trên đĩa). Trả None nếu không có GT/lỗi."""
    try:
        gt_paths = [p for p in _image_files(Path(gt_dir)) if p.name.lower().startswith("logo_")]
    except Exception:
        return None
    if not gt_paths:
        return None
    has_text = bool((crop_text or "").strip())
    best = None
    for gt in gt_paths:
        brand = brand_from_gt_path(gt)
        try:
            vis = compare_images(crop_img, _load_image(gt))
        except Exception:
            continue
        txt = text_similarity(crop_text, brand) if has_text else 0.0
        # CÓ text chữ trong logo -> KẾT HỢP visual + text (các brand Vin dùng chung chữ V đỏ,
        # visual gần như nhau; TEXT mới phân biệt vinfast/vinmec/vinsmartfuture). Không có text
        # -> chỉ visual như cũ.
        score = (0.5 * float(vis.score) + 0.5 * float(txt)) if has_text else float(vis.score)
        cand = {"brand": brand, "final_score": round(score, 4),
                "visual_score": round(float(vis.score), 4), "text_score": round(float(txt), 4),
                "matched": bool(score >= threshold), "gt": gt.name}
        if best is None or cand["final_score"] > best["final_score"]:
            best = cand
    return best
