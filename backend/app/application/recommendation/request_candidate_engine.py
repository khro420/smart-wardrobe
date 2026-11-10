"""Phase 3B-1 wrapper; completed Phase 3A contracts remain unchanged."""
from app.application.recommendation.recommendation_engine import RecommendationEngine
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.recommendation.request_candidate_session import RequestCandidateSession
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.domain.value_objects.request_candidate_evaluation import RequestGenerationResult


class RequestCandidateEngine:
    def __init__(self, query=None, structural_engine=None, evaluator_factory=None, optimized=True, *, evaluator_specification=None, attribute_context=None, attribute_verifier=None):
        if query is None and structural_engine is None:
            raise ValueError("Inject the Phase 1 query or Phase 3A engine.")
        self.structural_engine = structural_engine or RecommendationEngine(query)
        if evaluator_specification is not None:
            from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
            if type(evaluator_specification) is not EvaluatorSpecification or evaluator_factory is not None:
                raise ValueError("Unapproved or conflicting evaluator specification.")
            evaluator_specification.construct()  # Validate before acquiring garments.
            evaluator_factory = evaluator_specification.construct
        self.evaluator_factory = evaluator_factory or (lambda: RequestConstraintEvaluator(optimized=optimized))
        if (attribute_context is None)!=(attribute_verifier is None):raise ValueError('Both attribute admission and independent verification are required.')
        self.attribute_context,self.attribute_verifier=attribute_context,attribute_verifier
        self.attribute_seen=()
        self.attribute_counter_guard=None

    def generate_candidates(self,user_id,request):
        if not isinstance(request,StructuredOutfitRequest):
            return RequestCandidateSession(None,request,None,RequestGenerationResult("PolicyUnavailable",reason="structured_request_required"))
        try:
            evaluator = self.evaluator_factory()  # Fresh classification cache per session.
            if not evaluator.supports(request):
                return RequestCandidateSession(None,request,evaluator,RequestGenerationResult("PolicyUnavailable",reason="request_policy_unavailable"))
            structural = self.structural_engine.generate_homepage_candidates(user_id)
            result = structural.result
            if result.status in ("ProcessingFailure","Interrupted","PolicyUnavailable","WardrobeCapacityExceeded"):
                return RequestCandidateSession(structural,request,evaluator,RequestGenerationResult(result.status,reason=result.reason))
            return RequestCandidateSession(structural,request,evaluator,attribute_context=self.attribute_context,attribute_verifier=self.attribute_verifier,attribute_seen=self.attribute_seen,attribute_counter_guard=self.attribute_counter_guard)
        except Exception:
            return RequestCandidateSession(None,request,None,RequestGenerationResult("ProcessingFailure",reason="request_evaluation_setup_failed"))
