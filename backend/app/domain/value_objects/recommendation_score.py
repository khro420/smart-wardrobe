"""Immutable exact scores with unknown/NA distinct from numerical contribution."""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class ScoreEvidence:
    name: str
    value: Fraction | None
    state: str
    observed: int = 0
    possible: int = 0
    reasons: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.name,str) or self.state not in ("Available","Partial","Unknown","NotApplicable","Unavailable","NoPreferences","NoSupportedPreferences"):
            raise ValueError("Invalid scoring evidence metadata.")
        if self.value is not None and (not isinstance(self.value,Fraction) or not 0 <= self.value <= 1):
            raise ValueError("Score must be an exact fraction in 0–1.")
        if (self.state in ("Available","Partial")) != (self.value is not None):
            raise ValueError("Only supported numerical evidence carries a score.")
        if any(isinstance(x,bool) or not isinstance(x,int) or x < 0 for x in (self.observed,self.possible)) or self.observed > self.possible:
            raise ValueError("Invalid evidence coverage counts.")
        if not isinstance(self.reasons,(list,tuple)) or any(not isinstance(x,str) for x in self.reasons):
            raise ValueError("Invalid evidence reasons.")
        object.__setattr__(self,"reasons",tuple(self.reasons))


@dataclass(frozen=True)
class ComponentScore:
    summary: ScoreEvidence
    details: tuple[ScoreEvidence, ...] = ()

    def __post_init__(self):
        if not isinstance(self.summary,ScoreEvidence) or not isinstance(self.details,(list,tuple)) or any(not isinstance(x,ScoreEvidence) for x in self.details):
            raise ValueError("Invalid component evidence.")
        object.__setattr__(self,"details",tuple(self.details))

    @property
    def contribution(self):
        return self.summary.value if self.summary.value is not None else Fraction(0)


@dataclass(frozen=True)
class RecommendationScore:
    request_match: ComponentScore
    compatibility: ComponentScore
    preference: ComponentScore
    total: Fraction
    profile_name: str
    policy_version: str
    weights: tuple[Fraction, ...]

    def __post_init__(self):
        components = (self.request_match,self.compatibility,self.preference)
        if any(not isinstance(x,ComponentScore) for x in components) or not isinstance(self.total,Fraction) or not 0 <= self.total <= 1:
            raise ValueError("Invalid recommendation scores.")
        if not isinstance(self.weights,(list,tuple)) or len(self.weights) != 3 or any(not isinstance(w,Fraction) or not 0 <= w <= 1 for w in self.weights) or sum(self.weights) != 1:
            raise ValueError("Invalid score weights.")
        if self.total != sum(w*c.contribution for w,c in zip(self.weights,components)):
            raise ValueError("Total does not match component calculation.")
        if not isinstance(self.profile_name,str) or not self.profile_name or not isinstance(self.policy_version,str) or not self.policy_version:
            raise ValueError("Missing score provenance.")
        object.__setattr__(self,"weights",tuple(self.weights))
