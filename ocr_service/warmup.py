# -*- coding: utf-8 -*-
"""Pre-load Paddle + Surya models so the FIRST real /ocr request is fast.

Run at build time (`RUN python warmup.py` in the Dockerfile) to bake models into
the image, or on container start when a persistent /models volume is mounted.
Downloads ~1.5 GB (Surya from HuggingFace) + Paddle models on first execution.
"""
import os
import sys
from pathlib import Path

# Pipeline nằm trong services/ (import phẳng) -> thêm vào path.
sys.path.insert(0, str(Path(__file__).resolve().parent / "services"))

os.environ.setdefault("PADDLE_DEVICE", "cpu")
os.environ.setdefault("TORCH_DEVICE", "cpu")
os.environ.setdefault("SURYA_QUANT", "int8")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("PADDLE_TEXT_DET", "PP-OCRv5_mobile_det")


def main() -> None:
    import numpy as np

    print("[warmup] loading Paddle PP-StructureV3 ...", flush=True)
    from paddle_common import get_engine

    eng = get_engine()
    # get_engine() only constructs; some sub-models lazy-load on first predict().
    eng.predict(np.ones((64, 64, 3), dtype=np.uint8) * 255)
    print("[warmup] Paddle ready.", flush=True)

    print("[warmup] loading Surya recognizer ...", flush=True)
    from surya_engine import SuryaEngine

    SuryaEngine(langs=["vi", "en"], profile="service", device="cpu")
    print("[warmup] Surya ready. Warmup done.", flush=True)


if __name__ == "__main__":
    main()
