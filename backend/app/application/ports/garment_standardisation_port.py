from dataclasses import dataclass
from typing import Protocol
from app.domain.value_objects.standardisation_result import StandardisationResult


@dataclass(frozen=True)
class GarmentStandardisationInput:
    """Evidence supplied to VTOFF without replacing its segmentation fallback."""

    source_media_id: str
    crop_media_id: str
    mask_media_id: str | None
    category: str
    segmentation_confidence: float = 1.0


class GarmentStandardisationPort(Protocol):
    def standardise(self, item: GarmentStandardisationInput, user_id: str) -> StandardisationResult: ...
