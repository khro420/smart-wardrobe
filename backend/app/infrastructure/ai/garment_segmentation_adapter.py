"""Stable boundary around replaceable garment-analysis implementations."""

from pathlib import Path
from functools import lru_cache
from threading import Lock
import hashlib
import os
from app.application.ports.garment_segmentation_port import GarmentSegmentationPort
from app.domain.value_objects.detected_garment import DetectedGarment
from app.infrastructure.ai.gpu_runtime import gpu_inference_slot


class DevelopmentGarmentAdapter:
    """Runnable local adapter when trained model weights are unavailable.

    It intentionally makes one clearly review-required candidate. It is not
    represented as a trained segmentation result and is replaced by YOLO below.
    """
    def analyse(self, image_path: Path) -> list[DetectedGarment]:
        return [DetectedGarment(
            category="Unclassified garment",
            confidence=0.0,
            attributes={
                "source": "development fallback",
                "requires_review": True,
                "fit": None,
                "style": None,
                "material": None,
                "pattern": None,
                "colour_palette": [],
            },
        )]


class YoloGarmentAdapter:
    def __init__(self, model_path: Path):
        from app.infrastructure.ai.cv.pipeline import GarmentPipeline
        import ultralytics
        self.pipeline = GarmentPipeline(str(model_path))
        self._inference_lock = Lock()
        self.model_metadata = {"weights": model_path.name, "sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
                               "ultralytics_version": ultralytics.__version__, "confidence_threshold": 0.25,
                               "source_space_masks": True, "canonical_size": 512}

    def analyse(self, image_path: Path) -> list[DetectedGarment]:
        with gpu_inference_slot(), self._inference_lock:
            output = self.pipeline.process(str(image_path), save_dir=None, include_media=True)
        if "error" in output:
            raise RuntimeError(output["error"])
        return [DetectedGarment(
            category=result["detection"]["class_name"],
            confidence=result["detection"]["confidence"],
            attributes={**result["attributes"], **result["color"], **result["manual"],
                        "primary_colour": result["color"].get("primary_color"),
                        "source": "YOLO segmentation", "model": self.model_metadata, "requires_review": True},
            bounding_box=tuple(result["detection"]["bounding_box"]),
            crop_png=result["crop_png"],
            mask_png=result["mask_png"],
        ) for result in output["results"]]


@lru_cache(maxsize=1)
def _load_yolo(model_path: Path, modified_at: int) -> YoloGarmentAdapter:
    return YoloGarmentAdapter(model_path)


def get_garment_adapter() -> GarmentSegmentationPort:
    model_path = Path(__file__).resolve().parents[3] / "models" / "cv" / "best.pt"
    if os.getenv("SMART_WARDROBE_AI_MODE", "production").lower() == "development":
        return DevelopmentGarmentAdapter()
    return _load_yolo(model_path, model_path.stat().st_mtime_ns) if model_path.exists() else DevelopmentGarmentAdapter()
