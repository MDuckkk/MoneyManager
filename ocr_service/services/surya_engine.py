"""Surya OCR engine wrapper."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, NamedTuple

from metadata import EngineMetadata, package_version
from ocr_contract import OCRLine, OCRResult, text_from_lines


class SuryaFactories(NamedTuple):
    load_foundation_predictor: Callable[..., Any]
    load_detection_predictor: Callable[..., Any]
    load_recognition_predictor: Callable[..., Any]
    ocr_task_name: str


def get_surya_factories() -> SuryaFactories:
    """Import Surya predictors lazily so the package remains optional."""
    try:
        from surya.common.surya.schema import TaskNames
        from surya.detection import DetectionPredictor
        from surya.foundation import FoundationPredictor
        from surya.recognition import RecognitionPredictor
    except ImportError as exc:
        raise ImportError(
            "SuryaEngine requires the 'surya-ocr' package. "
            "Install it to use the real Surya backend."
        ) from exc

    return SuryaFactories(
        FoundationPredictor,
        DetectionPredictor,
        RecognitionPredictor,
        TaskNames.ocr_with_boxes,
    )


class SuryaEngine:
    """Run Surya OCR and normalize extracted text."""

    def __init__(
        self,
        langs: list[str] | None = None,
        profile: str = "benchmark",
        device: str = "unknown",
        **run_ocr_kwargs: Any,
    ):
        self.langs = langs or ["vi", "en"]
        self.profile = profile
        self.device = device
        self.run_ocr_kwargs = run_ocr_kwargs
        factories = get_surya_factories()
        foundation_predictor = factories.load_foundation_predictor()
        _materialize_surya_rotary_state(getattr(foundation_predictor, "model", None))
        self.det_predictor = factories.load_detection_predictor()
        self.rec_predictor = factories.load_recognition_predictor(foundation_predictor)
        self.ocr_task_name = factories.ocr_task_name

    def metadata(self) -> EngineMetadata:
        return EngineMetadata(
            name="surya",
            package="surya-ocr",
            package_version=package_version("surya-ocr"),
            model=str(self.ocr_task_name),
            device=self.device,
            profile=self.profile,
        )

    def extract(self, image: Any) -> dict[str, Any]:
        """Return normalized OCR text from Surya output."""
        ocr_kwargs = {"math_mode": False, **self.run_ocr_kwargs}
        result = self.rec_predictor(
            [image],
            task_names=[self.ocr_task_name],
            det_predictor=self.det_predictor,
            highres_images=[image],
            **ocr_kwargs,
        )
        lines = _extract_ocr_lines(result)
        metadata = self.metadata()
        ocr_result = OCRResult(
            text=text_from_lines(lines),
            lines=lines,
            blocks=[],
            raw=result,
            engine=metadata.name,
            engine_version=metadata.package_version,
            model=metadata.model,
            confidence_source="ocr_score",
            metadata=metadata.to_dict(),
        )

        return ocr_result.to_dict()


def _extract_ocr_lines(result: Any) -> list[OCRLine]:
    if not result:
        return []

    pages = result if isinstance(result, list) else [result]
    ocr_lines: list[OCRLine] = []
    for page_index, page in enumerate(pages):
        for line in _page_lines(page):
            text = _line_text(line)
            if not text:
                continue
            ocr_lines.append(
                OCRLine(
                    text=text,
                    bbox=_line_bbox(line),
                    polygon=_line_polygon(line),
                    confidence=_line_confidence(line),
                    page_index=page_index,
                )
            )
    return ocr_lines


def _materialize_surya_rotary_state(model: Any) -> None:
    if model is None:
        return

    rotary_emb = getattr(getattr(model, "decoder", None), "rotary_emb", None)
    if rotary_emb is not None:
        original_inv_freq = getattr(rotary_emb, "original_inv_freq", None)
        inv_freq = getattr(rotary_emb, "inv_freq", None)
        if (
            original_inv_freq is not None
            and inv_freq is not None
            and getattr(getattr(original_inv_freq, "device", None), "type", None) == "meta"
        ):
            rotary_emb.original_inv_freq = inv_freq.detach().clone()

    vision_encoder = getattr(model, "vision_encoder", None)
    vision_rotary_emb = getattr(vision_encoder, "rotary_pos_emb", None)
    vision_inv_freq = getattr(vision_rotary_emb, "inv_freq", None)
    if getattr(getattr(vision_inv_freq, "device", None), "type", None) != "meta":
        return

    import torch

    config = vision_encoder.config
    head_dim = config.hidden_size // config.num_heads
    rotary_dim = head_dim // 2
    theta = getattr(config, "rope_theta", 10000.0)
    vision_rotary_emb.inv_freq = 1.0 / (
        theta ** (torch.arange(0, rotary_dim, 2, dtype=torch.float) / rotary_dim)
    )


def _page_lines(page: Any) -> list[Any]:
    if isinstance(page, dict):
        return page.get("text_lines") or page.get("lines") or []

    return getattr(page, "text_lines", None) or getattr(page, "lines", None) or []


def _line_text(line: Any) -> str | None:
    if isinstance(line, dict):
        return line.get("text")

    return getattr(line, "text", None)


def _line_bbox(line: Any) -> list[float] | None:
    value = line.get("bbox") if isinstance(line, dict) else getattr(line, "bbox", None)
    if value is None:
        return None
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [float(item) for item in value]


def _line_polygon(line: Any) -> list[list[float]] | None:
    value = line.get("polygon") if isinstance(line, dict) else getattr(line, "polygon", None)
    if value is None:
        value = line.get("poly") if isinstance(line, dict) else getattr(line, "poly", None)
    if value is None:
        return None
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [[float(coordinate) for coordinate in point] for point in value]


def _line_confidence(line: Any) -> float | None:
    value = line.get("confidence") if isinstance(line, dict) else getattr(line, "confidence", None)
    if value is None:
        value = line.get("score") if isinstance(line, dict) else getattr(line, "score", None)
    return None if value is None else float(value)
