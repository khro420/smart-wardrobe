"""Explicit versioned decision adapter; raw Unknown never becomes Available.

The base ComponentScore contract and all existing callers remain unchanged.
Only this named subtype substitutes an explicitly recorded decision contribution.
"""
from dataclasses import dataclass, field
from fractions import Fraction as F
from app.domain.value_objects.recommendation_score import ComponentScore


@dataclass(frozen=True)
class CompatibilityDecision:
    raw: ComponentScore
    structure: str
    basis: str
    value: F
    lower: F | None
    upper: F | None
    atomic_count: int
    known_count: int
    known_sum: F
    pair_count: int
    policy_version: str
    policy_hash: str

    def __post_init__(self):
        structures = {"top_bottom": 1, "top_bottom_outerwear": 3,
                      "dress": 0, "dress_outerwear": 1}
        if not isinstance(self.raw, ComponentScore) or self.structure not in structures:
            raise ValueError("Invalid raw compatibility or structure.")
        if (self.policy_version != "compatibility-decision-1.0.0"
                or not isinstance(self.policy_hash, str) or len(self.policy_hash) != 64
                or any(c not in "0123456789abcdef" for c in self.policy_hash)):
            raise ValueError("Missing decision policy identity.")
        for v in (self.value, self.known_sum):
            if type(v) is not F:
                raise ValueError("Exact decision arithmetic required.")
        if any(type(v) is not int or v < 0 for v in
               (self.atomic_count, self.known_count, self.pair_count)):
            raise ValueError("Invalid decision counts.")
        if self.pair_count != structures[self.structure]:
            raise ValueError("Decision structure/pair mismatch.")
        atoms = tuple(x for x in self.raw.details if x.name.startswith(("colour:", "style:")))
        known = tuple(x.value for x in atoms if x.value is not None)
        if (self.atomic_count != len(atoms) or self.atomic_count != 2*self.pair_count
                or self.known_count != len(known) or self.known_sum != sum(known, F(0))):
            raise ValueError("Decision coverage does not match actual atomic evidence.")
        if not self.pair_count:
            if (self.basis != "NoPairReference" or self.value != F(1, 2)
                    or self.lower is not None or self.upper is not None
                    or self.raw.summary.state != "NotApplicable" or self.raw.summary.value is not None
                    or (self.raw.summary.observed, self.raw.summary.possible) != (0, 0)
                    or tuple(x.name for x in self.raw.details) != ("colour_coordination", "style_consistency")
                    or any(x.state != "NotApplicable" or x.value is not None or x.observed or x.possible for x in self.raw.details)):
                raise ValueError("Explicit no-pair convention required.")
            return
        m = self.atomic_count-self.known_count
        lower = self.known_sum/self.atomic_count
        upper = (self.known_sum+m)/self.atomic_count
        basis = "Computed" if not m else "FullyConventional" if not self.known_count else "PartiallyConventional"
        if (type(self.lower) is not F or type(self.upper) is not F
                or (self.lower, self.upper, self.value, self.basis) != (lower, upper, (lower+upper)/2, basis)):
            raise ValueError("Invalid exact bounds/midpoint/basis.")
        if (self.raw.summary.observed, self.raw.summary.possible) != (self.known_count, self.atomic_count):
            raise ValueError("Raw coverage mismatch.")
        if m:
            if self.raw.summary.value is not None or self.raw.summary.state != "Unknown":
                raise ValueError("Unresolved raw evidence must remain Unknown.")
        elif self.raw.summary.state != "Available" or self.raw.summary.value != lower:
            raise ValueError("Complete decision must equal measured compatibility.")


@dataclass(frozen=True, kw_only=True)
class DecisionCompatibilityComponent(ComponentScore):
    decision: CompatibilityDecision
    adapter_version: str = field(default="compatibility-decision-component-1.0.0", init=False)

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.decision, CompatibilityDecision):
            raise ValueError("Explicit immutable decision required.")
        if (self.summary, self.details) != (self.decision.raw.summary, self.decision.raw.details):
            raise ValueError("Adapter must preserve actual raw evidence.")

    @property
    def contribution(self):
        return self.decision.value
