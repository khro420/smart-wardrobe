from dataclasses import dataclass


@dataclass(frozen=True)
class DetectedGarment:
    """Model-independent candidate transferred from segmentation to review."""
    category: str
    confidence: float
    attributes: dict[str, object]
    bounding_box: tuple[float, float, float, float] | None = None
    mask_png: bytes | None = None
    crop_png: bytes | None = None
