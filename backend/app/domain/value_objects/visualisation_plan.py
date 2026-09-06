"""Immutable, model-independent input snapshot for one visualisation."""
from dataclasses import asdict, dataclass
from typing import Literal

CATEGORY_MODES = {
    "short_sleeve_top": "upper", "long_sleeve_top": "upper", "vest": "upper", "sling": "upper",
    "shorts": "lower", "trousers": "lower", "skirt": "lower",
    "short_sleeve_dress": "overall", "long_sleeve_dress": "overall",
    "vest_dress": "overall", "sling_dress": "overall",
}
CAPTURE_GUIDANCE = (
    "Use a clear photograph of one person facing the camera, with the relevant "
    "body region visible and no severe occlusion."
)


@dataclass(frozen=True)
class VTONConfiguration:
    width: int = 768
    height: int = 1024
    steps: int = 50
    guidance: float = 2.5
    seed: int = 42
    precision: str = "bf16"
    preprocessing_version: str = "catvton-crop-pad-automask-v1"

    def __post_init__(self):
        if (self.width, self.height) != (768, 1024) or self.precision != "bf16":
            raise ValueError("Only the documented 768x1024 BF16 profile is supported.")
        if not 1 <= self.steps <= 100 or not 0 <= self.guidance <= 10 or not 0 <= self.seed < 2**32:
            raise ValueError("Invalid generation configuration.")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class VisualisationGarment:
    garment_id: str
    source_media_id: str
    category: str
    role: str
    item_order: int


@dataclass(frozen=True)
class VisualisationPlan:
    source_type: Literal["outfit", "recommendation"]
    source_id: str
    person_image_id: str
    person_media_id: str
    garments: tuple[VisualisationGarment, ...]
    configuration: VTONConfiguration

    @property
    def mode(self) -> str:
        if len(self.garments) != 1:
            raise ValueError(
                "Select an outfit containing exactly one garment. "
                "Multi-garment try-on is not supported."
            )
        try:
            return CATEGORY_MODES[self.garments[0].category]
        except KeyError:
            raise ValueError(
                "This garment category is not supported for try-on. "
                "Choose a top, bottom or dress; outerwear is not supported."
            ) from None
