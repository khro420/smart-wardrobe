"""Explicitly injected extension; the Phase 3B-1 default remains unchanged."""
from dataclasses import replace
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.recommendation.suitability_policy import SuitabilityPolicy
from app.application.recommendation.suitability_evidence_mapper import SuitabilityEvidenceParser
from app.application.recommendation.occasion_evaluator import OccasionEvaluator
from app.application.recommendation.formality_evaluator import FormalityEvaluator
from app.domain.value_objects.request_candidate_evaluation import RequestEvaluation


class SuitabilityRequestEvaluator:
    def __init__(self,policy=None,minimum_evaluator=None,parser=None):
        self.policy = policy or SuitabilityPolicy.load()
        self.minimum = minimum_evaluator or RequestConstraintEvaluator()
        self.parser = parser or SuitabilityEvidenceParser(self.policy)
        if self.parser.policy != self.policy:
            raise ValueError("Suitability parser and policy differ.")
        # Existing session cache metric retains its colour/style meaning.
        self.mapper = self.minimum.mapper
        self.occasion = OccasionEvaluator(self.parser)
        self.formality = FormalityEvaluator(self.parser)

    def supports(self,request):
        return ((request.occasion is None or request.occasion in self.policy.enabled_occasions)
                and (request.formality is None or request.formality in self.policy.enabled_formality)
                and self.minimum.supports(replace(request,occasion=None,formality=None)))

    def evaluate(self,candidate,request):
        if not self.supports(request):
            raise ValueError("Request requires an unavailable suitability policy.")
        minimum = self.minimum.evaluate(candidate,replace(request,occasion=None,formality=None))
        conditions = list(minimum.conditions)
        if request.occasion is not None:
            conditions.append(self.occasion.evaluate(candidate,request.occasion))
        if request.formality is not None:
            conditions.append(self.formality.evaluate(candidate,request.formality))
        return RequestEvaluation(tuple(conditions))
