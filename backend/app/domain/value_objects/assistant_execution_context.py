"""Immutable metadata, never a candidate-stream completion certificate."""
from dataclasses import dataclass
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest


@dataclass(frozen=True)
class AssistantExecutionContext:
    user_id: str
    request: StructuredOutfitRequest
    evaluator: str
    suitability_policy: str | None
    structure_policy: str
    context_bundle: str | None = None

    def __post_init__(self):
        if self.context_bundle is not None:
            from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
            bundle_id=getattr(getattr(self.request,'context',None),'bundle_id','legacy_8_v1')
            if self.context_bundle != EvaluatorSpecification.current(bundle_id).registry_sha256 or self.evaluator != "GeneralContextEvaluator":
                raise ValueError("Invalid contextual execution bundle.")
        if (not isinstance(self.request,StructuredOutfitRequest)
                or any(not isinstance(v,str) or not v for v in (self.user_id,self.evaluator,self.structure_policy))
                or self.suitability_policy is not None and (not isinstance(self.suitability_policy,str) or not self.suitability_policy)):
            raise ValueError('Invalid Assistant execution metadata.')

    def validate_winner(self,user_id,request,ranked):
        if (self.user_id!=user_id or self.request!=request or not ranked.complete
                or ranked.status!='Selected' or ranked.winner is None or ranked.scored_count<1
                or ranked.winner.verified.user_id!=user_id or ranked.winner.verified.request!=request):
            raise ValueError('Assistant winner/context mismatch.')
