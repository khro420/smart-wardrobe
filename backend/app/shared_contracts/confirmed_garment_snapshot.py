"""Immutable current wardrobe data; no inferred recommendation conditions."""
from dataclasses import dataclass
import math
from app.domain.value_objects.contextual_garment_evidence import ContextualGarmentEvidence
from app.domain.value_objects.general_context_evidence import AppearanceEvidence
from app.domain.value_objects.saved_attribute_evidence import SavedAttributeEvidence


@dataclass(frozen=True)
class GarmentPaletteEntry:
    hex_value: str
    coverage: float | None = None

    def __post_init__(self):
        if not isinstance(self.hex_value, str) or not self.hex_value.strip():
            raise ValueError("Palette colour must be nonblank text.")
        if self.coverage is not None and (
            isinstance(self.coverage, bool) or not isinstance(self.coverage, (int, float))
            or not math.isfinite(self.coverage) or not 0 <= self.coverage <= 1
        ):
            raise ValueError("Palette coverage must be a finite number between zero and one.")


@dataclass(frozen=True)
class ConfirmedGarmentSnapshot:
    garment_id: str
    user_id: str
    status: str
    category: str
    name: str
    preferred_media_id: str
    is_favourite: bool
    updated_at: str
    structural_role: str | None = None
    layering_index: int | None = None
    primary_colour: str | None = None
    secondary_colour: str | None = None
    colour_palette: tuple[GarmentPaletteEntry, ...] | None = None
    style_tags: tuple[str, ...] | None = None
    pattern: str | None = None
    fit: str | tuple[str | None, ...] | None = None
    material: str | tuple[str | None, ...] | None = None
    colour_temperature: str | None = None
    is_dominant: bool | None = None
    custom_tags: tuple[str, ...] | None = None
    invalid_attributes: tuple[str, ...] = ()
    contextual_suitability: ContextualGarmentEvidence = ContextualGarmentEvidence()
    appearance_evidence: AppearanceEvidence = AppearanceEvidence()
    saved_attribute_evidence: SavedAttributeEvidence = SavedAttributeEvidence()

    def __post_init__(self):
        if type(self.saved_attribute_evidence) is not SavedAttributeEvidence:
            raise ValueError('Saved attribute evidence must be immutable.')
        if type(self.appearance_evidence) is not AppearanceEvidence:
            raise ValueError('Appearance observations must be immutable.')
        if not isinstance(self.contextual_suitability, ContextualGarmentEvidence):
            raise ValueError('Contextual evidence must be immutable.')
        # Type hints alone do not freeze caller-owned lists or dictionaries.
        for name in ("garment_id", "user_id", "status", "category", "name", "preferred_media_id", "updated_at"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"{name} must be text.")
        for name in ("structural_role", "primary_colour", "secondary_colour", "pattern", "colour_temperature"):
            if getattr(self, name) is not None and not isinstance(getattr(self, name), str):
                raise ValueError(f"{name} must be text or None.")
        if not isinstance(self.is_favourite, bool) or (self.is_dominant is not None and not isinstance(self.is_dominant, bool)):
            raise ValueError("Favourite and dominance values must be booleans.")
        if self.layering_index is not None and (isinstance(self.layering_index, bool) or not isinstance(self.layering_index, int)):
            raise ValueError("Layering index must be an integer or None.")
        for name in ("style_tags", "custom_tags", "invalid_attributes", "fit", "material"):
            value = getattr(self, name)
            if value is None and name != "invalid_attributes":
                continue
            if name in ("fit", "material") and isinstance(value, str):
                continue
            if not isinstance(value, (list, tuple)) or any(
                not isinstance(item, str) and not (name in ("fit", "material") and item is None)
                for item in value
            ):
                raise ValueError(f"{name} contains an invalid collection value.")
            object.__setattr__(self, name, tuple(value))
        if self.colour_palette is not None:
            if not isinstance(self.colour_palette, (list, tuple)):
                raise ValueError("Palette must be a list or tuple.")
            entries = tuple(GarmentPaletteEntry(**entry) if isinstance(entry, dict) else entry for entry in self.colour_palette)
            if any(not isinstance(entry, GarmentPaletteEntry) for entry in entries):
                raise ValueError("Palette must contain immutable palette entries.")
            object.__setattr__(self, "colour_palette", entries)
