"""Versioned user-approved Phase 3A compositions; not report-prescribed enums."""
from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType


@dataclass(frozen=True)
class StructuralPolicy:
    version: str
    role_map: object
    compositions: tuple[tuple[str, ...], ...]

    def __post_init__(self):
        expected = {"top":"upper", "bottom":"lower", "dress":"one_piece", "outerwear":"outerwear"}
        compositions = tuple(tuple(value) for value in self.compositions)
        if self.version != "1.0.0" or dict(self.role_map) != expected or compositions != (("upper","lower"),("upper","lower","outerwear"),("one_piece",),("one_piece","outerwear")):
            raise ValueError("Unapproved structural policy.")
        object.__setattr__(self, "role_map", MappingProxyType(dict(self.role_map)))
        object.__setattr__(self, "compositions", compositions)

    @classmethod
    def load(cls):
        raw = json.loads((Path(__file__).with_name("config") / "structure.v1.json").read_text(encoding="utf-8"))
        expected = {"top":"upper", "bottom":"lower", "dress":"one_piece", "outerwear":"outerwear"}
        compositions = tuple(tuple(value) for value in raw["compositions"])
        if raw["version"] != "1.0.0" or raw["role_map"] != expected or compositions != (("upper","lower"),("upper","lower","outerwear"),("one_piece",),("one_piece","outerwear")):
            raise ValueError("Structural policy differs from the approved Phase 3A rules.")
        return cls(raw["version"], MappingProxyType(dict(raw["role_map"])), compositions)
