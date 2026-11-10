"""Trusted application persistence input; not an external recommendation API."""
from dataclasses import dataclass
from app.domain.value_objects.intended_wearer import IntendedWearer
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
    wearer: IntendedWearer | None = None
    captured_garment_sha256: str | None = None
    captured_preference_sha256: str | None = None
    attribute: object | None = None
    preference: object | None = None
    compatibility: object | None = None
    eligibility: object | None = None

    def __post_init__(self):
        from app.domain.value_objects.wearer_category_eligibility import EligibilityWriteDraft
        if self.eligibility is not None and (type(self.eligibility) is not EligibilityWriteDraft or self.wearer is None):raise ValueError('Captured owned wearer eligibility draft required.')
        from app.domain.value_objects.palette_compatibility import PaletteWriteDraft,PROFILES
        c2=self.score is not None and self.score.profile_name in PROFILES.values()
        if (self.compatibility is not None)!=c2:raise ValueError('C2 score requires exactly its immutable palette draft.')
        if c2 and (type(self.compatibility) is not PaletteWriteDraft or self.operation!='assistant' or self.wearer is None or self.captured_garment_sha256 is None):raise ValueError('C2 requires captured owned Assistant scope.')
        if self.preference is not None:
            from app.domain.value_objects.attribute_preference_evidence import AttributePreferenceWriteDraft
            from app.domain.value_objects.attribute_preferences import PROFILE
            if type(self.preference) is not AttributePreferenceWriteDraft or self.operation!='assistant' or self.wearer is None or self.captured_garment_sha256 is None or self.score.profile_name not in (PROFILE,PROFILES[True,False],PROFILES[True,True]):
                raise ValueError('P2 requires an immutable captured owned Assistant scope.')
        elif self.score is not None and self.score.profile_name=='attribute_preference_decision_v2':
            raise ValueError('P2 score requires its immutable preference draft.')
        if c2 and (self.preference is not None)!=(self.score.profile_name in (PROFILES[True,False],PROFILES[True,True])):raise ValueError('C2 preference mode/archive mismatch.')
        if self.attribute is not None:
            from app.domain.value_objects.attribute_selection_evidence import AttributeWriteDraft
            if type(self.attribute) is not AttributeWriteDraft or self.operation!='assistant' or self.wearer is None or self.captured_garment_sha256 is None:
                raise ValueError('New attribute writes require immutable captured owned scope.')
            intent=self.attribute.evidence.to_dict()['intent']
            if intent['original_text']!=self.request_text:raise ValueError('Attribute intent text mismatch.')
        if self.wearer is not None and (type(self.wearer) is not IntendedWearer or self.wearer.account_id!=self.user_id):
            raise ValueError("Captured owned wearer required.")
        if (self.captured_garment_sha256 is None)!=(self.captured_preference_sha256 is None):
            raise ValueError('Both captured Assistant scopes are required.')
        if self.captured_garment_sha256 is not None:
            from app.domain.value_objects.context_relevance import require_digest
            require_digest(self.captured_garment_sha256);require_digest(self.captured_preference_sha256)
        from app.domain.value_objects.garment_only_refinement import GarmentRefinementDraft
        if self.refinement is not None and (type(self.refinement) not in (RefinementDraft,GarmentRefinementDraft) or self.operation!='assistant'):
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
