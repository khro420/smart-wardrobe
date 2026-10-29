"""Concrete bindings used only by the FastAPI composition root."""
from app.application.ports.workflow_runtime import WorkflowRuntime, configure_workflow
from app.infrastructure.ai.garment_segmentation_adapter import get_garment_adapter
from app.infrastructure.ai.attribute_embedding_adapter import get_attribute_adapter
from app.infrastructure.ai.vtoff_adapter import get_standardisation_adapter
from app.infrastructure.media import protected_media_store
from app.infrastructure.persistence import postgresql_repository
from app.application.wardrobe.wardrobe_service import WardrobeWriter
from app.application.ports.visualisation_repository import (
    VisualisationRuntime,
    configure_visualisation,
)
from app.domain.value_objects.visualisation_plan import VTONConfiguration
from app.infrastructure.ai.gpu_runtime import gpu_inference_slot
from app.infrastructure.ai.vton_adapter import get_vton_adapter
from app.infrastructure.ai.vton_preprocessing import validate_generated_output
from app.infrastructure.config import (
    VTON_GUIDANCE_SCALE, VTON_HEIGHT, VTON_INFERENCE_STEPS,
    VTON_QUEUE_LIMIT, VTON_SEED, VTON_WIDTH,
)


class LocalWorkflowRepository:
    connection = staticmethod(postgresql_repository.connection)
    utcnow = staticmethod(postgresql_repository.utcnow)


class ProtectedMediaAdapter:
    path_for_owner = staticmethod(protected_media_store.media_path_for_owner)
    store_bytes = staticmethod(protected_media_store.store_media_bytes)
    store_image = staticmethod(protected_media_store.store_image)


def configure_local_workflow():
    import os
    from app.application.recommendation.assistant_execution_selection import AssistantExecutionSelection, ENVIRONMENT_KEY as EXECUTION_KEY, DEFAULT_ENGINE
    from app.application.recommendation.assistant_scoring_selection import AssistantScoringSelection, ENVIRONMENT_KEY as SCORING_KEY, DEFERRED
    # Reject invalid server settings at startup, including disabled integration.
    execution = AssistantExecutionSelection(os.getenv(EXECUTION_KEY,DEFAULT_ENGINE))
    scoring = AssistantScoringSelection(os.getenv(SCORING_KEY,DEFERRED))
    from app.application.recommendation.contextual_selection import contextual_selection
    contextual = contextual_selection()
    context_ranking=os.getenv('SMART_WARDROBE_ASSISTANT_CONTEXT_RANKING_PROFILE','disabled')
    refinement=os.getenv('SMART_WARDROBE_ASSISTANT_REFINEMENT_PROFILE','disabled')
    if refinement!='disabled':
        from app.application.recommendation.refinement_policy import RefinementPolicy
        if (refinement!='optional_refinement_v1' or context_ranking!='context_relevance_decision_v1'
            or os.getenv('SMART_WARDROBE_ASSISTANT_CONTEXT_BUNDLE','legacy_8_v1')!='context_18_v1'
            or os.getenv('SMART_WARDROBE_ASSISTANT_ENABLED','false').lower()!='true'):
            raise ValueError('Invalid optional refinement configuration.')
        RefinementPolicy.load()
    if context_ranking!='disabled':
        from app.application.recommendation.context_relevance_policy import ContextRelevancePolicy,PROFILE
        from app.application.recommendation.assistant_scoring_selection import DECISION
        if (context_ranking!=PROFILE or scoring.profile!=DECISION
                or os.getenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE')!='general_context_v1'
                or os.getenv('SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED','false').lower()!='true'):
            raise ValueError('Invalid context ranking/profile combination.')
        ContextRelevancePolicy.load(bundle_id=os.getenv('SMART_WARDROBE_ASSISTANT_CONTEXT_BUNDLE','legacy_8_v1'))
    from app.application.ports.chat_history_runtime import configure_chat_history_service
    from app.application.chat_history.chat_history_service import ChatHistoryService
    from app.infrastructure.persistence.chat_history_query_adapter import SqliteChatHistoryQuery
    configure_chat_history_service(ChatHistoryService(SqliteChatHistoryQuery()))
    import os
    from app.application.ports.homepage_runtime import configure_homepage_service
    from app.application.recommendation.homepage_recommendation_service import HomepageRecommendationService
    from app.application.recommendation.recommendation_engine import RecommendationEngine
    from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
    from app.application.ports.recommendation_runtime import configure_recommendation_query
    from app.infrastructure.persistence.confirmed_garment_query_adapter import get_confirmed_garment_query
    configure_recommendation_query(get_confirmed_garment_query())
    from app.application.ports.recommendation_runtime import configure_transaction_garment_query
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    configure_transaction_garment_query(SqliteConfirmedGarmentQuery)
    configure_homepage_service(
        HomepageRecommendationService(RecommendationEngine(get_confirmed_garment_query()), SqliteRecommendationRepository())
        if os.getenv("SMART_WARDROBE_HOMEPAGE_ENABLED", "false").lower() == "true" else None
    )
    from app.application.ports.assistant_runtime import configure_assistant_service
    configure_assistant_service(None)
    if os.getenv("SMART_WARDROBE_ASSISTANT_ENABLED","false").lower() == "true":
        from app.application.nlp.nlp_interpreter import NLPInterpreter
        from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
        from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
        from app.application.recommendation.assistant_scoring_selection import ENVIRONMENT_KEY, DEFERRED
        from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
        from app.infrastructure.persistence.active_preference_query_adapter import SqliteActivePreferenceQuery
        evaluator = SuitabilityRequestEvaluator if os.getenv("SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED","false").lower() == "true" else None
        interpreter = NLPInterpreter()
        if contextual is not None:
            # Both opt-in profiles supply paired interpretation and fresh evaluator construction.
            interpreter, evaluator = contextual
        configure_assistant_service(OutfitAssistantService(interpreter,RequestCandidateEngine(get_confirmed_garment_query(),evaluator_factory=evaluator),SqliteActivePreferenceQuery(),SqliteRecommendationRepository(),scoring_profile=scoring.profile,execution_engine=execution.engine,context_ranking_profile=context_ranking,refinement_profile=refinement))
    configure_workflow(WorkflowRuntime(
        database=LocalWorkflowRepository(), media=ProtectedMediaAdapter(),
        segmentation=get_garment_adapter, standardisation=get_standardisation_adapter,
        attributes=get_attribute_adapter, confirmed_writer=WardrobeWriter(),
    ))
    configure_visualisation(VisualisationRuntime(
        repository=LocalWorkflowRepository(),
        media=ProtectedMediaAdapter(),
        adapter=get_vton_adapter,
        gpu_slot=gpu_inference_slot,
        configuration=lambda: VTONConfiguration(
            width=VTON_WIDTH, height=VTON_HEIGHT,
            steps=VTON_INFERENCE_STEPS, guidance=VTON_GUIDANCE_SCALE,
            seed=VTON_SEED,
        ),
        validate_output=validate_generated_output,
        queue_limit=VTON_QUEUE_LIMIT,
    ))
