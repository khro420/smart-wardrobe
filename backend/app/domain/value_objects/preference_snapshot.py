"""Immutable read-only preference projections and normalized scoring inputs."""
from dataclasses import dataclass
from fractions import Fraction
from app.domain.value_objects.structured_outfit_request import GarmentCategoryConstraint


@dataclass(frozen=True)
class PreferenceSnapshot:
    preference_id: str
    user_id: str
    preference_type: str
    value_json: str
    weight: str | None = None
    source: str | None = None
    is_active: bool = True

    def __post_init__(self):
        if any(not isinstance(x,str) for x in (self.preference_id,self.user_id,self.preference_type,self.value_json)) or not self.preference_id or not self.user_id:
            raise ValueError("Invalid preference identity or JSON representation.")
        if (self.weight is not None and not isinstance(self.weight,str)) or (self.source is not None and not isinstance(self.source,str)) or not isinstance(self.is_active,bool):
            raise ValueError("Invalid preference metadata.")


@dataclass(frozen=True)
class NormalizedPreference:
    preference_id: str
    preference_type: str
    values: tuple[str | GarmentCategoryConstraint, ...]
    importance: Fraction

    def __post_init__(self):
        if self.preference_type not in ("colours","styles","garment_categories","formality") or not isinstance(self.preference_id,str):
            raise ValueError("Invalid normalized preference type.")
        if not isinstance(self.values,(list,tuple)) or not self.values or any(not isinstance(x,GarmentCategoryConstraint if self.preference_type == "garment_categories" else str) for x in self.values):
            raise ValueError("Invalid preference values.")
        if not isinstance(self.importance,Fraction) or not 0 < self.importance <= 1:
            raise ValueError("Invalid preference importance.")
        object.__setattr__(self,"values",tuple(dict.fromkeys(self.values)))


@dataclass(frozen=True)
class NormalizedPreferenceSet:
    user_id: str
    preferences: tuple[NormalizedPreference, ...] = ()
    diagnostics: tuple[tuple[str,str], ...] = ()

    def __post_init__(self):
        if not isinstance(self.user_id,str) or not self.user_id.strip() or not isinstance(self.preferences,(tuple,list)) or any(not isinstance(x,NormalizedPreference) for x in self.preferences):
            raise ValueError("Invalid normalized preference set.")
        if len({x.preference_type for x in self.preferences}) != len(self.preferences):
            raise ValueError("Duplicate normalized preference types.")
        if not isinstance(self.diagnostics,(list,tuple)) or any(not isinstance(x,(tuple,list)) or len(x) != 2 or any(not isinstance(y,str) for y in x) for x in self.diagnostics):
            raise ValueError("Invalid preference diagnostics.")
        object.__setattr__(self,"preferences",tuple(self.preferences))
        object.__setattr__(self,"diagnostics",tuple(tuple(x) for x in self.diagnostics))
