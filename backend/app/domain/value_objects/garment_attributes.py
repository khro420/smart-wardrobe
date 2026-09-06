from dataclasses import dataclass, field
import math


# DeepFashion2 categories shared by the detector adapter and reviewed wardrobe data.
GARMENT_STRUCTURE = {
    "short_sleeve_top": ("top", 0), "long_sleeve_top": ("top", 1),
    "short_sleeve_outwear": ("outerwear", 2), "long_sleeve_outwear": ("outerwear", 2),
    "vest": ("top", 1), "sling": ("top", 0), "shorts": ("bottom", 0),
    "trousers": ("bottom", 0), "skirt": ("bottom", 0),
    "short_sleeve_dress": ("dress", 0), "long_sleeve_dress": ("dress", 0),
    "vest_dress": ("dress", 0), "sling_dress": ("dress", 0),
}


@dataclass(frozen=True)
class GarmentAttributes:
    values: dict[str, object] = field(default_factory=dict)

    def validate_embedding(self, expected_dimension: int) -> None:
        vector = self.values.get("embedding")
        if vector is None:
            return  # Explicitly unavailable until an embedding adapter is installed.
        if not isinstance(vector, list) or len(vector) != expected_dimension or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in vector
        ):
            raise ValueError("The garment embedding has an invalid dimension or non-finite value.")
