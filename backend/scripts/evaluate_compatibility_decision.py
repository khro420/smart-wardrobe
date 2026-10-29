"""Fixed synthetic demonstrations only; no reviewed fashion judgments or accuracy."""
import argparse
from dataclasses import asdict
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
from app.application.recommendation.cached_rule_based_compatibility_scorer import CachedRuleBasedCompatibilityScorer
from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
from app.application.recommendation.decision_recommendation_scorer import DecisionRecommendationScorer
from app.application.recommendation.decision_score_codec import score_to_json, score_from_json


class Query:
    def __init__(self, rows): self.rows = tuple(rows)
    def get_confirmed_available_garments(self, user_id): return self.rows


class Preferences:
    def __init__(self, rows=()): self.rows = rows
    def get_active_preferences(self, user_id): return self.rows


def garment(identifier, category, colour="blue", styles=("classic",)):
    role, index = GARMENT_STRUCTURE[category]
    return ConfirmedGarmentSnapshot(identifier, "synthetic-owner", "available", category,
                                    "SYNTHETIC "+identifier, "synthetic-media", False, "synthetic-v1",
                                    structural_role=role, layering_index=index, primary_colour=colour, style_tags=styles)


def examples():
    top, high, low, dress, outer = (garment("top", "vest"), garment("bottom", "trousers"),
                                  garment("bottom", "trousers", "red", ("sporty",)),
                                  garment("dress", "vest_dress"), garment("outer", "long_sleeve_outwear", "white"))
    cases = [
        ("single_dress", [dress], StructuredOutfitRequest(), []),
        ("measured_high_beats_dress", [top, high, dress], StructuredOutfitRequest(), []),
        ("dress_beats_measured_zero", [top, low, dress], StructuredOutfitRequest(), []),
        ("dress_outerwear", [dress, outer], StructuredOutfitRequest(), []),
        ("top_bottom_outerwear", [top, low, outer], StructuredOutfitRequest(), []),
        ("annotation_before", [top, low], StructuredOutfitRequest(), []),
        ("annotation_removed", [garment("top", "vest", styles=None), low], StructuredOutfitRequest(), []),
        ("partial_colour", [garment("top", "vest", None), high], StructuredOutfitRequest(), []),
        ("partial_style", [garment("top", "vest", styles=None), high], StructuredOutfitRequest(), []),
        ("entirely_unknown", [garment("top", "vest", None, None), garment("bottom", "trousers", None, None)], StructuredOutfitRequest(), []),
        ("narrow_heuristic_colour_zero", [top, garment("bottom", "trousers", "red")], StructuredOutfitRequest(), []),
        ("changed_request_preferences", [top, low], StructuredOutfitRequest(style="classic"),
         [PreferenceSnapshot("synthetic-pref", "synthetic-owner", "styles", '{"values":["classic"]}')]),
    ]
    output = []
    for name, rows, request, prefs in cases:
        engine = RequestCandidateEngine(Query(rows))
        outcome, cache = DecisionRecommendationScorer(engine, Preferences(prefs)).rank_with_cache_info("synthetic-owner", request)
        if outcome.status != "Selected" or not outcome.complete:
            raise RuntimeError("Synthetic example did not complete: "+name)
        score = outcome.winner.score
        encoded = score_to_json(score)
        if score_from_json(encoded) != score:
            raise RuntimeError("Exact replay failed.")
        # Tiny explanatory fixtures only, never the large-workload pipeline.
        session = engine.generate_candidates("synthetic-owner", request)
        gate = ScoringEligibilityGate(session, "synthetic-owner", request)
        scorer, policy = CachedRuleBasedCompatibilityScorer(), CompatibilityDecisionPolicy.load()
        candidates = []
        for item in session:
            v = gate.verify(item)
            from app.domain.value_objects.compatibility_signature import STRUCTURES
            structure = next(k for k, roles in STRUCTURES.items() if roles == tuple(m.role for m in v.candidate.members))
            c = policy.apply(scorer.score(v), structure)
            candidates.append({"key": v.candidate.key, "compatibility": asdict(c)})
        output.append({"name": name, "synthetic": True, "status": outcome.status,
                       "winner": outcome.winner.verified.candidate.key, "score": json.loads(encoded),
                       "diagnostics": outcome.diagnostics, "cache": asdict(cache), "candidates": candidates})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[2]
    target = args.output.resolve()
    if target.exists() or not target.is_relative_to(repository/"storage"):
        parser.error("New output within repository storage required.")
    values = examples()
    result = {"version": "1.0.0", "synthetic": True, "independent_review": False,
              "fashion_quality_accuracy": None, "examples": values,
              "script_hash": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, default=lambda x: {"numerator": x.numerator, "denominator": x.denominator} if isinstance(x, F) else None)
    print("Completed synthetic examples:", target)


if __name__ == "__main__": main()
