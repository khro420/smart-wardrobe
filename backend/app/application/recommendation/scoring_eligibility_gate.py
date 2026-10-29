"""Bind one fresh request session to its context, independently recheck rules.

Internal dependency injection is trusted. The gate cannot certify a malicious
replacement of the Phase 1 query; confirmation remains that contract's job.
"""
from app.application.recommendation.general_context_evaluator import GeneralContextEvaluator, construct_evaluator, evaluator_selector
from uuid import uuid4
from app.application.recommendation.request_candidate_session import RequestCandidateSession
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.contextual_suitability_evaluator import ContextualSuitabilityEvaluator
from app.domain.value_objects.request_candidate_evaluation import EvaluatedCandidate
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.domain.value_objects.scored_candidate import VerifiedScoringInput,_GATE_SEAL


class InvalidScoringInput(ValueError):
    pass


class ScoringEligibilityGate:
    def __init__(self,session,user_id,request):
        if not isinstance(session,RequestCandidateSession) or not isinstance(request,StructuredOutfitRequest) or session.request != request or not isinstance(user_id,str) or not user_id.strip():
            raise InvalidScoringInput("Invalid request/session context.")
        if session.result.examined or session.result.status == "Running" or session.result.status == "MatchingCandidates":
            raise InvalidScoringInput("Scoring requires a fresh unconsumed session.")
        evaluator_type = type(session.evaluator)
        if evaluator_type not in (RequestConstraintEvaluator,SuitabilityRequestEvaluator,ContextualSuitabilityEvaluator,GeneralContextEvaluator):
            raise InvalidScoringInput("Unapproved evaluator policy.")
        # Fresh approved verifier prevents injected evidence from enabling hex
        # approximations or supplying an empty evaluation for a different request.
        try:self.verifier = construct_evaluator(evaluator_selector(session.evaluator))
        except (ValueError,TypeError,AttributeError) as error:raise InvalidScoringInput('Invalid evaluator bundle.') from error
        if not self.verifier.supports(request):
            raise InvalidScoringInput("Mandatory request policy unavailable.")
        self.session,self.user_id,self.request = session,user_id,request
        self.context_id = uuid4().hex

    def verify(self,item):
        if self.session.request != self.request or not isinstance(item,EvaluatedCandidate) or item.evaluation.state != "Pass":
            raise InvalidScoringInput("Only request-evaluated passing candidates may be scored.")
        if any(member.garment.user_id != self.user_id for member in item.candidate.members):
            raise InvalidScoringInput("Foreign candidate.")
        checked = self.verifier.evaluate(item.candidate,self.request)
        if checked.state != "Pass" or checked != item.evaluation:
            raise InvalidScoringInput("Mandatory coverage/evidence mismatch.")
        return VerifiedScoringInput(item,self.request,self.user_id,self.context_id,_GATE_SEAL)
