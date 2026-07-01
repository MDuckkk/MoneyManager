"""Normalized OCR output contract used by local extraction."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class OCRLine:
    text: str
    bbox: list[float] | None
    confidence: float | None
    page_index: int
    polygon: list[list[float]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OCRResult:
    text: str
    lines: list[OCRLine]
    blocks: list[dict[str, Any]]
    raw: Any
    engine: str
    engine_version: str
    model: str | None
    confidence_source: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text or text_from_lines(self.lines),
            "lines": [line.to_dict() for line in self.lines],
            "blocks": self.blocks,
            "raw": self.raw,
            "engine": self.engine,
            "engine_version": self.engine_version,
            "model": self.model,
            "confidence_source": self.confidence_source,
            "metadata": self.metadata,
        }


def text_from_lines(lines: list[OCRLine]) -> str:
    return "\n".join(line.text for line in lines if line.text.strip())
