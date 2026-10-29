"""Scoring wrappers preserve completed immutable outfit contracts."""
from dataclasses import dataclass,field
from app.domain.value_objects.request_candidate_evaluation import EvaluatedCandidate
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.domain.value_objects.recommendation_score import RecommendationScore

# Internal proof of gate construction, not authentication or a cryptographic token.
_GATE_SEAL = object()


@dataclass(frozen=True)
class VerifiedScoringInput:
    evaluated: EvaluatedCandidate
    request: StructuredOutfitRequest
    user_id: str
    context_id: str
    _seal: object = field(default=None,repr=False,compare=False)

    def __post_init__(self):
        if self._seal is not _GATE_SEAL or not isinstance(self.evaluated,EvaluatedCandidate) or not isinstance(self.request,StructuredOutfitRequest):
            raise ValueError("Request/session eligibility gate required.")
        if not isinstance(self.user_id,str) or not self.user_id or any(x.garment.user_id != self.user_id for x in self.evaluated.candidate.members):
            raise ValueError("Scoring ownership mismatch.")
        if not isinstance(self.context_id,str) or not self.context_id:
            raise ValueError("Missing scoring context identity.")

    @property
    def candidate(self):
        return self.evaluated.candidate


@dataclass(frozen=True)
class ScoredCandidate:
    verified: VerifiedScoringInput
    score: RecommendationScore

    def __post_init__(self):
        if not isinstance(self.verified,VerifiedScoringInput) or not isinstance(self.score,RecommendationScore):
            raise ValueError("Invalid scored candidate.")
