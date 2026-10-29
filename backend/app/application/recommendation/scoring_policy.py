"""Explicit, exact-weight profiles; no per-candidate reweighting or default."""
from dataclasses import dataclass
from fractions import Fraction
import json
from pathlib import Path
from app.application.recommendation.preference_normalizer import precise_weight

DEFAULT_SCORING_POLICY = Path(__file__).with_name("config") / "scoring_policy.v1.json"


@dataclass(frozen=True)
class ScoringProfile:
    name: str
    version: str
    weights: tuple[Fraction, ...]
    compatibility: str

    def __post_init__(self):
        if not isinstance(self.name,str) or not self.name or not isinstance(self.version,str) or not self.version or self.compatibility not in ("disabled","shared_style_jaccard"):
            raise ValueError("Invalid scoring profile metadata.")
        if not isinstance(self.weights,(list,tuple)) or len(self.weights) != 3 or any(not isinstance(x,Fraction) or not 0 <= x <= 1 for x in self.weights) or sum(self.weights) != 1:
            raise ValueError("Three finite nonnegative exact weights must sum to one.")
        if self.compatibility == "disabled" and self.weights[1] != 0:
            raise ValueError("Unavailable compatibility must have zero weight.")
        object.__setattr__(self,"weights",tuple(self.weights))

    @classmethod
    def load(cls,name,path=DEFAULT_SCORING_POLICY):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw,dict) or raw.get("version") != "phase4a-1.0.0" or raw.get("default_activation") is not False:
            raise ValueError("Invalid scoring policy version/activation.")
        try:
            item = raw["profiles"][name]
            if item["compatibility"] == "shared_style_jaccard" and item.get("reject_unpaired_candidates") is not True:
                raise ValueError("Experimental profile must reject unpaired sessions.")
            return cls(name,raw["version"],tuple(precise_weight(x) for x in item["weights"]),item["compatibility"])
        except (KeyError,TypeError) as exc:
            raise ValueError("Unknown or malformed scoring profile.") from exc
