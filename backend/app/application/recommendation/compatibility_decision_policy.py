"""Approved isolated experimental conventions, never discovered by live services."""
from dataclasses import dataclass
from fractions import Fraction as F
import json
from pathlib import Path
from app.application.recommendation.rule_based_compatibility_policy import load_json, digest
from app.domain.value_objects.recommendation_score import ComponentScore, ScoreEvidence
from app.domain.value_objects.compatibility_decision import CompatibilityDecision, DecisionCompatibilityComponent

CONFIG = Path(__file__).with_name("config") / "compatibility_decision.v1.json"
EXPECTED = {"version": "compatibility-decision-1.0.0", "default_activation": False,
            "atomic_rules": ["colour", "style"], "missing_rule_bounds": ["0", "1"],
            "decision": "interval_midpoint", "no_pair_reference": "1/2",
            "weights": ["3/5", "1/5", "1/5"], "profile": "experimental_compatibility_decision_v1"}


@dataclass(frozen=True)
class CompatibilityDecisionPolicy:
    version: str
    hash: str

    def __post_init__(self):
        if self.version != EXPECTED["version"] or self.hash != digest(EXPECTED):
            raise ValueError("Unapproved compatibility decision policy.")

    @property
    def name(self):
        return EXPECTED["profile"]

    @property
    def weights(self):
        return (F(3, 5), F(1, 5), F(1, 5))

    @classmethod
    def load(cls, path=CONFIG):
        raw = load_json(path)
        if json.dumps(raw, sort_keys=True) != json.dumps(EXPECTED, sort_keys=True):
            raise ValueError("Invalid or activated decision configuration.")
        return cls(raw["version"], digest(raw))

    def apply(self, raw, structure):
        pairs = {"top_bottom": 1, "top_bottom_outerwear": 3, "dress": 0, "dress_outerwear": 1}[structure]
        if not pairs:
            if raw.summary.value is not None or raw.summary.observed or raw.summary.possible:
                raise ValueError("No-pair conversion requires actual zero relationships.")
            # The original scorer remains untouched. This version explicitly records
            # that its zero pair relationships are NA, not an observed dress rating.
            raw = ComponentScore(ScoreEvidence("compatibility", None, "NotApplicable",
                                 reasons=raw.summary.reasons), raw.details)
            decision = CompatibilityDecision(raw, structure, "NoPairReference", F(1, 2),
                                             None, None, 0, 0, F(0), 0, self.version, self.hash)
        else:
            atoms = tuple(x for x in raw.details if x.name.startswith(("colour:", "style:")))
            values = tuple(x.value for x in atoms if x.value is not None)
            M, known, K = len(atoms), len(values), sum(values, F(0))
            if M != pairs*2:
                raise ValueError("Complete original rule evidence required.")
            L, U = K/M, (K+M-known)/M
            basis = "Computed" if known == M else "FullyConventional" if not known else "PartiallyConventional"
            decision = CompatibilityDecision(raw, structure, basis, (L+U)/2, L, U,
                                             M, known, K, pairs, self.version, self.hash)
        return DecisionCompatibilityComponent(raw.summary, raw.details, decision=decision)
