"""NLP chat and recommendation HTTP boundary from the report's application flow."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from app.api.homepage_models import HomepageRecommendationCreate
from app.application.ports.homepage_runtime import homepage_service
from app.application.ports.assistant_runtime import assistant_service
from app.api.assistant_models import AssistantRecommendationCreate

from app.application.recommendation import recommendation_service as recommendations
from app.domain.value_objects.requests import RecommendationCreate, RecommendationSaveAsOutfit
from app.infrastructure.security import current_user_id

router = APIRouter(prefix="/recommendations", tags=["NLP outfit recommendations"])


@router.get("/capabilities")
def capabilities(user_id: str = Depends(current_user_id), homepage=Depends(homepage_service), assistant=Depends(assistant_service)):
    """Allow the new UI to avoid posting to the disabled legacy Assistant."""
    result = {"homepage_enabled":homepage is not None,"assistant_enabled":assistant is not None}
    if assistant is not None:
        from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
        from app.application.recommendation.context_policy_registry import ContextPolicyRegistry
        if type(assistant.interpreter) is GeneralContextInterpreter:
            result["context_support"] = ContextPolicyRegistry.load(bundle_id=assistant.interpreter.bundle_id).capabilities()
        if getattr(assistant,'context_ranking_profile','disabled')!='disabled':
            from app.application.recommendation.context_relevance_policy import ContextRelevancePolicy,PROFILE,POLICY_VERSION,CATALOGUE_VERSION
            policy=ContextRelevancePolicy.load(bundle_id=getattr(assistant.interpreter,'bundle_id','legacy_8_v1'))
            result['context_ranking']=dict(version='context-ranking-capabilities-1.0.0',profile=PROFILE,
                policy_version=policy.policy_version,catalogue_version=policy.catalogue_version,
                policy_sha256=policy.policy_sha256,catalogue_sha256=policy.catalogue_sha256,
                objectives=[dict(situation=e.objective.situation,target=e.objective.target,authority=e.objective.authority) for e in policy.entries],
                source_quality='provisional_recorded_labels',independent_appropriateness_validation='OPEN')
            if policy.bundle_id!='legacy_8_v1':result['context_ranking'].update(version='context-ranking-capabilities-1.1.0',bundle_id=policy.bundle_id)
        if getattr(assistant,'refinement_profile','disabled')=='optional_refinement_v1':
            from app.application.recommendation.refinement_policy import RefinementPolicy
            from app.domain.value_objects.recommendation_refinement import CATEGORIES,SHORTCUTS
            refinement=RefinementPolicy.load()
            result['refinement']=dict(version='recommendation-refinement-capabilities-1.0.0',available=True,
                profile='optional_refinement_v1',ordinary_situations=list(refinement.ordinary_situations),
                categories=list(CATEGORIES),shortcuts={k:list(v) for k,v in SHORTCUTS},max_results=10,typed_input_only=True)
    return result


@router.post("/homepage")
def homepage(body: HomepageRecommendationCreate, user_id: str = Depends(current_user_id), service=Depends(homepage_service)):
    if service is None:
        return JSONResponse(status_code=404, content={"status": "IntegrationDisabled", "complete": False})
    result = service.recommend(user_id, body.submission_key)
    status = result["status"]
    code = 200
    if status == "Selected":
        code = 200 if result["replayed"] else 201
    elif status in ("IdempotencyConflict", "WardrobeChanged"):
        code = 409
    elif status in ("InvalidInput", "PolicyUnavailable"):
        code = 422
    elif status in ("ProcessingFailure", "PersistenceFailure", "Interrupted"):
        code = 503
    return JSONResponse(status_code=code, content=result)


@router.get("")
def list_all(user_id: str = Depends(current_user_id)) -> list[dict]:
    return recommendations.list_recommendations(user_id)


@router.post("", status_code=201)
def create(body: AssistantRecommendationCreate, user_id: str = Depends(current_user_id), service=Depends(assistant_service), pipeline: str | None = Query(default=None)):
    if pipeline not in (None,"integrated"):
        return JSONResponse(status_code=422,content={"status":"InvalidInput","outcome":"InvalidInput","complete":False})
    if service is None:
        return JSONResponse(status_code=404,content={"status":"IntegrationDisabled","outcome":"IntegrationDisabled","complete":False})
    if body.model_extra:
        return JSONResponse(status_code=422,content={"status":"InvalidInput","outcome":"InvalidInput","complete":False})
    result = (service.recommend(user_id,body.submission_key,body.request_text,body.refinement.model_dump())
        if body.refinement is not None else service.recommend(user_id,body.submission_key,body.request_text))
    status = result["status"]
    code = 200
    if status == "Selected":
        code = 200 if result["replayed"] else 201
    elif status in ("InvalidInput","UnsupportedRequest","PolicyUnavailable","InvalidPreferenceData","ProfileUnavailable","RefinementConflict","RefinementUnavailable"):
        code = 422
    elif status in ("IdempotencyConflict","WardrobeChanged","RefinementScopeChanged"):
        code = 409
    elif status=='RefinementNotFound':code=404
    elif status in ("ProcessingFailure","ProcessingError","PersistenceFailure","Interrupted","InvalidScoringInput"):
        code = 503
    content = {**result,"outcome":status}
    if status == "Selected":
        content["status"] = result["recommendation_status"]
    return JSONResponse(status_code=code,content=content)


@router.post("/{recommendation_id}/save-as-outfit", status_code=201)
def save_as_outfit(recommendation_id: str, body: RecommendationSaveAsOutfit, user_id: str = Depends(current_user_id)) -> dict:
    return recommendations.save_as_outfit(recommendation_id, user_id, body.name)


@router.get("/{recommendation_id}/saved-outfit")
def saved_outfit(recommendation_id: str, user_id: str = Depends(current_user_id)) -> dict:
    return recommendations.saved_outfit_state(recommendation_id, user_id)
