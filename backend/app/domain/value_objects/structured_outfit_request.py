"""The five approved request fields; no garment identifiers or bindings."""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class GarmentCategoryConstraint:
    kind: Literal["category", "group"]
    value: str

    def __post_init__(self):
        if self.kind not in ("category", "group") or not isinstance(self.value, str) or not self.value:
            raise ValueError("Invalid garment category constraint.")


@dataclass(frozen=True)
class StructuredOutfitRequest:
    intent: str = "outfit_recommendation"
    occasion: str | None = None
    style: str | None = None
    colours: tuple[str, ...] | None = None
    garment_categories: tuple[GarmentCategoryConstraint, ...] | None = None
    formality: str | None = None

    def __post_init__(self):
        if self.intent != "outfit_recommendation":
            raise ValueError("Only outfit recommendation intent is supported.")
        for name in ("occasion", "style", "formality"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value):
                raise ValueError(f"Invalid {name}.")
        for name, item_type in (("colours", str), ("garment_categories", GarmentCategoryConstraint)):
            value = getattr(self, name)
            if value is not None:
                if not isinstance(value, (list, tuple)) or not value or any(not isinstance(item, item_type) for item in value):
                    raise ValueError(f"Invalid {name}.")
                object.__setattr__(self, name, tuple(dict.fromkeys(value)))

    def to_dict(self) -> dict:
        return {"intent": self.intent, "occasion": self.occasion, "style": self.style,
                "colours": list(self.colours) if self.colours is not None else None,
                "garment_categories": [{"kind": item.kind, "value": item.value} for item in self.garment_categories] if self.garment_categories is not None else None,
                "formality": self.formality}
