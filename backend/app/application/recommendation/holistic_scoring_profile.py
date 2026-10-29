"""Separate profile type: Phase 4A configuration/contracts stay untouched."""
from dataclasses import dataclass
from fractions import Fraction
import json
from pathlib import Path
from app.application.recommendation.preference_normalizer import precise_weight

DEFAULT_HOLISTIC_PROFILES = Path(__file__).with_name("config") / "scoring_policy.v2.json"


@dataclass(frozen=True)
class HolisticScoringProfile:
    name: str
    version: str
    weights: tuple[Fraction, ...]
    compatibility: str = "reviewed_holistic"

    def __post_init__(self):
        if not isinstance(self.name,str) or not self.name or self.version != "phase4ba-1.0.0" or self.compatibility != "reviewed_holistic" or not isinstance(self.weights,(list,tuple)) or len(self.weights) != 3 or any(not isinstance(x,Fraction) or not 0 <= x <= 1 for x in self.weights) or sum(self.weights) != 1:
            raise ValueError("Invalid holistic experimental profile.")
        object.__setattr__(self,"weights",tuple(self.weights))

    @classmethod
    def load(cls,name,path=DEFAULT_HOLISTIC_PROFILES):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw,dict) or raw.get("default_activation") is not False or raw.get("compatibility") != "reviewed_holistic":
            raise ValueError("Invalid holistic profile configuration.")
        try:
            return cls(name,raw["version"],tuple(precise_weight(x) for x in raw["profiles"][name]))
        except (KeyError,TypeError) as exc:
            raise ValueError("Unknown or malformed holistic profile.") from exc
