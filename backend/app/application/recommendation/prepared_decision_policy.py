"""Session-local exact arithmetic reuse; original decision validators still run.

Only normalized numeric atoms are cached, never candidates, decisions, owners or
raw diagnostics. Each application constructs the original validated value type.
"""
from dataclasses import dataclass
from fractions import Fraction as F
from functools import lru_cache
from types import MappingProxyType
from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
from app.domain.value_objects.compatibility_decision import CompatibilityDecision, DecisionCompatibilityComponent

PAIRS = MappingProxyType({"top_bottom":1,"top_bottom_outerwear":3,"dress":0,"dress_outerwear":1})
ARITHMETIC_CAPACITY = 256


@dataclass(frozen=True)
class ArithmeticFacts:
    total: int
    known: int
    known_sum: F
    lower: F
    upper: F
    midpoint: F
    basis: str


def arithmetic(atoms):
    values=tuple(F(n,d) for pair in atoms if pair is not None for n,d in (pair,))
    M,known,K=len(atoms),len(values),sum(values,F(0))
    if not M: raise ValueError("Non-empty atomic values required.")
    L,U=K/M,(K+M-known)/M
    basis="Computed" if known==M else "FullyConventional" if not known else "PartiallyConventional"
    return ArithmeticFacts(M,known,K,L,U,(L+U)/2,basis)


@dataclass(frozen=True,init=False)
class PreparedDecisionPolicy:
    _policy: CompatibilityDecisionPolicy
    weights: tuple[F,...]
    name: str
    version: str
    hash: str
    _arithmetic: object

    def __init__(self,policy,capacity=ARITHMETIC_CAPACITY):
        if not isinstance(policy,CompatibilityDecisionPolicy):
            raise ValueError("Validated original decision policy required.")
        if type(capacity) is not int or not 0<=capacity<=ARITHMETIC_CAPACITY:
            raise ValueError("Invalid arithmetic capacity.")
        object.__setattr__(self,"_policy",policy)
        object.__setattr__(self,"weights",policy.weights)
        for name in ("name","version","hash"):
            object.__setattr__(self,name,getattr(policy,name))
        object.__setattr__(self,"_arithmetic",lru_cache(maxsize=capacity,typed=True)(arithmetic))

    @property
    def cache_info(self):
        return self._arithmetic.cache_info()

    def apply(self,raw,structure):
        pairs=PAIRS[structure]
        if not pairs:
            return self._policy.apply(raw,structure)
        atoms=tuple(x for x in raw.details if x.name.startswith(("colour:","style:")))
        if len(atoms)!=2*pairs:
            raise ValueError("Complete original rule evidence required.")
        # Integer numerator/denominator keys avoid repeatedly hashing Fractions.
        # ScoreEvidence already enforces exact numeric types; the original
        # CompatibilityDecision below independently rechecks all evidence/sums.
        key=tuple(None if x.value is None else (x.value.numerator,x.value.denominator) for x in atoms)
        facts=self._arithmetic(key)
        decision=CompatibilityDecision(raw,structure,facts.basis,facts.midpoint,facts.lower,facts.upper,
                                       facts.total,facts.known,facts.known_sum,pairs,self.version,self.hash)
        return DecisionCompatibilityComponent(raw.summary,raw.details,decision=decision)
