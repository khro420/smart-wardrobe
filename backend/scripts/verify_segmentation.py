"""Real-weight smoke check, not held-out mAP. Run from backend with Python.

Uses three existing validation samples without training or changing weights.
"""
from io import BytesIO
import json
from pathlib import Path
import sys
import time

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from PIL import Image
import cv2
import numpy as np
import torch
from app.infrastructure.ai.garment_segmentation_adapter import get_garment_adapter, YoloGarmentAdapter
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE


def main():
    output = BACKEND.parent / "storage/verification/segmentation"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    adapter = get_garment_adapter()
    assert isinstance(adapter, YoloGarmentAdapter), "Real segmentation weights are required for this check."
    assert list(adapter.pipeline.detector.model.names.values()) == list(GARMENT_STRUCTURE)
    report = {"kind": "real-weight smoke check, not an accuracy benchmark", "model": adapter.model_metadata,
              "torch": torch.__version__, "opencv": cv2.__version__, "numpy": np.__version__,
              "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
              "load_seconds": round(time.perf_counter() - started, 3), "samples": []}
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    for name in ("000001", "000002", "000003"):
        source = BACKEND / f"datasets/deepfashion2_yolo_seg/images/validation/{name}.jpg"
        with Image.open(source) as image:
            width, height = image.size
        start = time.perf_counter()
        detections = adapter.analyse(source)
        entry = {"sample": name, "width": width, "height": height,
                 "seconds": round(time.perf_counter() - start, 3), "candidates": []}
        for i, detection in enumerate(detections):
            assert detection.category in GARMENT_STRUCTURE
            assert 0.25 <= detection.confidence <= 1
            x1, y1, x2, y2 = detection.bounding_box
            assert 0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height
            mask = Image.open(BytesIO(detection.mask_png))
            crop = Image.open(BytesIO(detection.crop_png))
            assert mask.size == (width, height) and mask.getbbox() is not None
            mask_box = mask.getbbox()
            assert crop.size == (mask_box[2] - mask_box[0], mask_box[3] - mask_box[1]) and crop.mode == "RGBA"
            assert crop.getchannel("A").getbbox() is not None
            assert detection.attributes["fit"] is None and detection.attributes["material"] is None
            (output / f"{name}-{i}-crop.png").write_bytes(detection.crop_png)
            (output / f"{name}-{i}-mask.png").write_bytes(detection.mask_png)
            entry["candidates"].append({"category": detection.category, "confidence": round(detection.confidence, 4),
                                        "bounding_box": detection.bounding_box})
        report["samples"].append(entry)
    assert any(len(entry["candidates"]) >= 2 for entry in report["samples"])
    report["inference_device"] = str(adapter.pipeline.detector.model.predictor.device)
    report["peak_cuda_allocated_mb"] = round(torch.cuda.max_memory_allocated() / 1024 ** 2, 2) if torch.cuda.is_available() else None
    (output / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
