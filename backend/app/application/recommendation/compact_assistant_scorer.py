"""Production DI bridge into the existing service; no persistence or API fork."""
from app.application.recommendation.general_context_evaluator import GeneralContextEvaluator, evaluator_selector
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.application.recommendation.structural_policy import StructuralPolicy
from app.domain.value_objects.assistant_execution_context import AssistantExecutionContext
from app.domain.value_objects.general_context_request import GeneralContextRequest


def execution_context(session,engine,user_id,request):
    if session is None or session.request!=request or session.evaluator is None:
        raise ValueError('Missing actual evaluator metadata.')
    return AssistantExecutionContext(user_id,request,type(session.evaluator).__name__,
        getattr(getattr(session.evaluator,'policy',None),'version',None),
        engine.structural_engine.generator.policy.version,
        session.evaluator.specification.registry_sha256 if type(session.evaluator) is GeneralContextEvaluator and (isinstance(request,GeneralContextRequest) or session.evaluator.specification.bundle_id=='legacy_8_v1') else None)


class CompactAssistantScorer:
    implementation='compact-exhaustive-1.0.0'

    def __init__(self,captured_engine,preferences,profile,*,kernel_factory=CompactExhaustiveScorer,context_ranking=False):
        self.engine,self.preferences,self.profile=captured_engine.engine,preferences,profile
        self.kernel_factory=kernel_factory
        self.kernel=None
        self.prepared_context=None
        self.context_ranking=context_ranking
        if context_ranking:self.implementation='compact-context-relevance-1.0.0'

    def rank(self,user_id,request,profile_name=None,refinement_plan=None):
        if profile_name is not None and profile_name!=self.profile:
            raise ValueError('Execution/scoring selection mismatch.')
        self.prepared_context=None
        selected_evaluator=self.engine.evaluator_factory()
        if isinstance(request,GeneralContextRequest) and getattr(selected_evaluator.specification,'bundle_id','legacy_8_v1')!=request.context.bundle_id:
            raise ValueError('Interpreter/evaluator bundle mismatch.')
        if self.engine.structural_engine.generator.policy!=StructuralPolicy.load():
            raise ValueError('Compact engine requires the approved structural policy.')
        self.kernel=self.kernel_factory(self.engine.structural_engine.retrieval.query,self.preferences,self.profile,
            evaluator_type=evaluator_selector(selected_evaluator),**({'context_ranking':True} if self.context_ranking else {}))
        if refinement_plan is not None:self.implementation='compact-refinement-1.0.0'
        result=self.kernel.rank(user_id,request,refinement_plan=refinement_plan) if refinement_plan is not None else self.kernel.rank(user_id,request)
        if result.status=='Selected':
            # Metadata only. Do NOT copy the reconstruction session into the
            # captured engine or fabricate its RequestGenerationResult.
            self.prepared_context=execution_context(self.kernel.public_session,self.engine,user_id,request)
            self.prepared_context.validate_winner(user_id,request,result)
        return result
