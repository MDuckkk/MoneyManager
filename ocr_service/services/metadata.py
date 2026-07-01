"""Engine version and runtime metadata helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib import metadata
from typing import Any


@dataclass(frozen=True)
class EngineMetadata:
    name: str
    package: str
    package_version: str
    model: str | None = None
    device: str = "unknown"
    profile: str = "benchmark"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def package_version(package_name: str) -> str:
    try:
        return metadata.version(package_name)
    except Exception:
        return "unknown"
