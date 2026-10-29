"""Trusted application persistence input; not an external recommendation API."""
from dataclasses import dataclass
import json
from app.domain.value_objects.outfit_candidate import OutfitCandidate
from app.domain.value_objects.recommendation_score import RecommendationScore
from app.domain.value_objects.recommendation_refinement import RefinementDraft


@dataclass(frozen=True)
class RecommendationWrite:
    user_id: str
    operation: str
    submission_key: str
    request_json: str
    candidate: OutfitCandidate
    provenance_json: str
    request_text: str | None = None
    score: RecommendationScore | None = None
    refinement: RefinementDraft | None = None

    def __post_init__(self):
        if self.refinement is not None and (type(self.refinement) is not RefinementDraft or self.operation!='assistant'):
            raise ValueError('Refinement requires a typed Assistant draft.')
        for value in (self.user_id, self.submission_key):
            if not isinstance(value, str) or not value.strip() or len(value) > 200:
                raise ValueError("Invalid submission identity.")
        if self.operation not in ("homepage", "assistant"):
            raise ValueError("Invalid operation.")
        for name in ("request_json", "provenance_json"):
            value = json.loads(getattr(self, name), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
            if not isinstance(value, dict) or (name == "provenance_json" and not value):
                raise ValueError("Expected object and nonempty policy provenance.")
            object.__setattr__(self, name, json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False))
        if not isinstance(self.candidate, OutfitCandidate) or any(m.garment.user_id != self.user_id for m in self.candidate.members):
            raise ValueError("Invalid candidate ownership.")
        if self.operation == "homepage" and (self.request_text is not None or self.score is not None):
            raise ValueError("Homepage cannot contain chat or scores.")
        if self.operation == "assistant" and (not isinstance(self.request_text, str) or not self.request_text.strip() or len(self.request_text) > 500 or not isinstance(self.score, RecommendationScore)):
            raise ValueError("Assistant requires original request and actual scores.")
        if self.score is not None:
            provenance=json.loads(self.provenance_json)
            if self.score.profile_name=='context_relevance_decision_v1' and 'context_relevance' not in provenance:
                raise ValueError('Relative score requires ranking proof.')
            if 'context_relevance' in provenance:
                from app.domain.value_objects.context_relevance import bounded_json
                bounded_json(provenance['context_relevance'])


class PersistenceConflict(ValueError):
    """Same scoped key was used for another request."""


class WardrobeChanged(ValueError):
    """Selected evidence no longer equals the current strict snapshot."""
