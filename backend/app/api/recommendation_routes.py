"""NLP chat and recommendation HTTP boundary from the report's application flow."""

from fastapi import APIRouter, Depends, Query, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from app.api.assistant_models import HomepageRecommendationCreate
from app.application.ports.homepage_runtime import homepage_service
from app.application.ports.assistant_runtime import assistant_service
from app.api.assistant_models import AssistantRecommendationCreate

from app.application.recommendation import recommendation_service as recommendations
from app.domain.value_objects.requests import RecommendationCreate, RecommendationSaveAsOutfit
from app.infrastructure.security import current_user_id
from app.application.wardrobe.profile_service import active_profile_id,profile_scope
from app.application.recommendation.wearer_identity import resolve_wearer
from app.domain.value_objects.recommendation_persistence import PersistenceConflict
from app.domain.value_objects.recommendation_refinement import RefinementAction


def _repository(service):
    if service is not None:return service.repository
    from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
    from app.infrastructure.persistence.postgresql_repository import DATABASE_PATH
    return SqliteRecommendationRepository(DATABASE_PATH)


def _category_call(operation,*args,**kwargs):
    from fastapi import HTTPException
    try:return operation(*args,**kwargs)
    except HTTPException as error:
        if isinstance(error.detail,dict) and error.detail.get('code','').startswith(('WearerCategory','WearerEligibility','WearerSubtype')):
            return {'status':error.detail['code'],'complete':False,'reason':error.detail['message']}
        raise


def _conflict():
    return JSONResponse(status_code=409,content={'status':'IdempotencyConflict','outcome':'IdempotencyConflict','complete':False})

router = APIRouter(prefix="/recommendations", tags=["NLP outfit recommendations"])
from app.development.mixed_wardrobe.feedback import router as explicit_feedback_router
router.include_router(explicit_feedback_router)


@router.get("/capabilities")
def capabilities(request: Request, user_id: str = Depends(current_user_id), homepage=Depends(homepage_service), assistant=Depends(assistant_service)):
    """Allow the new UI to avoid posting to the disabled legacy Assistant."""
    result = {"homepage_enabled":homepage is not None,"assistant_enabled":assistant is not None}
    from app.application.wardrobe.wearer_category_service import policy
    selected_policy=policy()
    subtype_enabled=selected_policy is not None and selected_policy['version']=='wearer-category-policy-2.0.0'
    result['wearer_category_policy']={'version':'wearer-category-capabilities-2.0.0' if subtype_enabled else 'wearer-category-capabilities-1.0.0','enabled':selected_policy is not None,'profile':'gender_category_subtype_v2' if subtype_enabled else 'gender_category_v1'}
    result['wearer_identity']={'version':'assistant-wearer-intent-1.0.0','request_field':'wearer_profile_id',
        'single_active_auto':True,'multi_active_explicit':True,'archived_history':True}
    attributes=getattr(assistant,'attribute_pipeline',None) if assistant is not None else None
    if attributes is not None and callable(getattr(attributes,'language_capabilities',None)):
        result['language_understanding']=attributes.language_capabilities()
    result['attributes']=attributes.capabilities() if attributes is not None else {
        'version':'attribute-request-capabilities-1.0.0','enabled':False,'request_version':'attribute-conditions-1.0.0',
        'grammar_version':None,'grammar_sha256':None,'policy_version':None,'policy_sha256':None,
        'fields':[],'roles':[],'quantifiers':[],'bounds':{},'blocked_sources':[]}
    from app.domain.value_objects.attribute_preferences import PROFILE as P2
    result['attribute_preferences']={'version':'attribute-preference-request-capabilities-1.0.0',
        'enabled':getattr(assistant,'preference_policy',None) is not None,'profile':P2,'default':'p1','explicit_selection_required':True}
    palette=getattr(assistant,'compatibility_policy',None) if assistant is not None else None
    result['palette_compatibility']=palette.capabilities() if palette is not None else {'version':'palette-compatibility-capabilities-1.0.0','enabled':False,'profile':'recorded_palette_compatibility_v1','default':'c1','explicit_selection_required':True}
    if assistant is not None:
        from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
        from app.application.recommendation.context_policy_registry import ContextPolicyRegistry
        if isinstance(assistant.interpreter,GeneralContextInterpreter):
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
    result['garment_continuation']={'version':'garment-only-continuation-capabilities-1.0.0','available':getattr(assistant,'garment_refinement_profile','disabled')=='garment_only_refinement_v1','profile':'garment_only_refinement_v1','max_results':10}
    from app.application.recommendation.local_preference_assistant import capability
    result['local_preferences']=capability(assistant)
    result['input_normalization']={'version':'normalized-input-capabilities-1.0.0','enabled':getattr(assistant,'input_normalization',None) is not None,
        'profile':'bounded_natural_input_v1','grammar_version':'conversational-normalized-grammar-1.8.0',
        'grammar_sha256':getattr(getattr(assistant,'input_normalization',None),'grammar',None),'scope':'non_contextual_P1_C1','default_enabled':False}
    result['compositional_input']={'version':'compositional-input-capabilities-1.0.0','enabled':getattr(assistant,'input_composition',None) is not None,
        'profile':'bounded_compositional_input_v1','grammar_version':'conversational-compositional-grammar-1.9.0',
        'grammar_sha256':getattr(getattr(assistant,'input_composition',None),'grammar',None),'scope':'non_contextual_P1_C1','default_enabled':False,'continuation':False}
    if result['local_preferences']['enabled'] and 'language_understanding' in result:
        result['language_understanding']={**result['language_understanding'],
            'soft_requests':'One positive upper/lower category or named-colour wish via the separate opt-in P1/C1 non-contextual profile; no added score weight.'}
    from app.development.main_fixture.gateway import capabilities as fixture_capabilities
    result['synthetic_fixture']=fixture_capabilities(user_id)
    from app.development.mixed_wardrobe.gateway import capabilities as mixed_capabilities
    result['mixed_wardrobe']=mixed_capabilities(user_id,request.client.host if request.client else None)
    if result['mixed_wardrobe']['enabled']:result['synthetic_fixture']['enabled']=False
    return result


@router.post("/homepage")
def homepage(body: HomepageRecommendationCreate, user_id: str = Depends(current_user_id), x_wardrobe_profile_id: str | None = Header(default=None), service=Depends(homepage_service)):
    try:
        prior=_repository(service).find_homepage_submission(user_id,body.submission_key,
            wearer_profile_id=body.wearer_profile_id,header_profile_id=x_wardrobe_profile_id)
    except PersistenceConflict:return _conflict()
    except Exception as error:
        from app.application.recommendation.failure_diagnostics import log_failure
        log_failure('homepage','lookup','PersistenceFailure',error)
        return JSONResponse(status_code=503,content={'status':'PersistenceFailure','outcome':'PersistenceFailure','complete':False})
    if prior is not None:
        from app.application.recommendation.homepage_recommendation_service import HomepageRecommendationService
        return JSONResponse(status_code=200,content=HomepageRecommendationService._success(prior,True,{}))
    if service is None:
        return JSONResponse(status_code=404, content={"status": "IntegrationDisabled", "complete": False})
    wearer=resolve_wearer(user_id,body.wearer_profile_id,x_wardrobe_profile_id)
    with profile_scope(wearer.profile_id):
        result = _category_call(service.recommend,user_id, body.submission_key,wearer=wearer)
    status = result["status"]
    code = 200
    if status == "Selected":
        code = 200 if result["replayed"] else 201
    elif status.startswith(("WearerCategory","WearerEligibility","WearerSubtype")):code=409
    elif status in ("IdempotencyConflict", "WardrobeChanged", "WardrobeCapacityExceeded"):
        code = 409
    elif status in ("InvalidInput", "PolicyUnavailable"):
        code = 422
    elif status in ("ProcessingFailure", "PersistenceFailure", "Interrupted"):
        code = 503
    return JSONResponse(status_code=code, content=result)


@router.get("")
def list_all(user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)) -> list[dict]:
    return recommendations.list_recommendations(user_id, profile_id)


@router.post("", status_code=201)
def create(body: AssistantRecommendationCreate, request: Request, user_id: str = Depends(current_user_id), x_wardrobe_profile_id: str | None = Header(default=None), service=Depends(assistant_service), pipeline: str | None = Query(default=None)):
    from app.development.main_fixture.gateway import PIPELINE,submit as fixture_submit,foreign_mode_receipt
    from app.development.main_fixture.store import FixtureError
    from app.development.mixed_wardrobe import gateway as mixed
    host=request.client.host if request.client else None
    mixed_parent=bool(body.refinement and body.refinement.kind=='alternative' and mixed.owns_parent(user_id,body.refinement.parent_recommendation_id))
    receipt_namespace=mixed.receipt_namespace(user_id,body.submission_key)
    mixed_receipt=receipt_namespace=='mixed'
    if pipeline in (None,'integrated') and receipt_namespace=='fixture':pipeline=PIPELINE
    if pipeline in (None,'integrated') and (mixed_parent or mixed_receipt or receipt_namespace is None and mixed.capabilities(user_id,host)['enabled'] and (body.refinement is None or body.refinement.kind=='initial')):
        if body.model_extra:return JSONResponse(status_code=422,content={'status':'InvalidInput','outcome':'InvalidInput','complete':False})
        try:
            value,code=mixed.submit(user_id,body,x_wardrobe_profile_id,host)
            return JSONResponse(status_code=code,content=value)
        except FixtureError as error:return JSONResponse(status_code=error.status,content={'status':error.code,'outcome':error.code,'complete':False})
        except HTTPException:raise
        except Exception as error:
            from app.development.main_fixture.core import UnsupportedFixtureRequest as OldUnsupported
            from app.development.mixed_wardrobe.core import UnsupportedFixtureRequest
            from app.domain.value_objects.attribute_conditions import AttributeRequestError
            if isinstance(error,(UnsupportedFixtureRequest,OldUnsupported)):return JSONResponse(status_code=422,content={'status':'UnsupportedMixedRequest','outcome':'UnsupportedMixedRequest','complete':False})
            if isinstance(error,AttributeRequestError):return JSONResponse(status_code=422,content={'status':error.status,'outcome':error.status,'context_reason':error.reason,'complete':False})
            from app.application.recommendation.failure_diagnostics import log_failure
            log_failure('assistant','persistence','PersistenceFailure',error)
            return JSONResponse(status_code=503,content={'status':'PersistenceFailure','outcome':'PersistenceFailure','complete':False})
    if pipeline==PIPELINE:
        if receipt_namespace!='fixture' and mixed.capabilities(user_id,host)['enabled']:
            return JSONResponse(status_code=409,content={'status':'MixedWardrobeRequiresRefresh','outcome':'MixedWardrobeRequiresRefresh','complete':False})
        if body.model_extra:return JSONResponse(status_code=422,content={'status':'InvalidInput','complete':False})
        try:
            result,code=fixture_submit(user_id,body,x_wardrobe_profile_id)
            return JSONResponse(status_code=code,content=result)
        except FixtureError as error:return JSONResponse(status_code=error.status,content={'status':error.code,'complete':False})
        except AttributeError:return JSONResponse(status_code=503,content={'status':'FixtureUnavailable','complete':False})
        except HTTPException:raise
        except Exception as error:
            from app.development.main_fixture.core import UnsupportedFixtureRequest
            if isinstance(error,UnsupportedFixtureRequest):return JSONResponse(status_code=422,content={'status':'UnsupportedFixtureRequest','complete':False})
            from app.domain.value_objects.attribute_conditions import AttributeRequestError
            if isinstance(error,AttributeRequestError):return JSONResponse(status_code=422,content={'status':error.status,'context_reason':error.reason,'complete':False})
            from app.application.recommendation.failure_diagnostics import log_failure
            log_failure('assistant','fixture','PersistenceFailure',error)
            return JSONResponse(status_code=503,content={'status':'PersistenceFailure','complete':False})
    if foreign_mode_receipt(user_id,body.submission_key):return _conflict()
    if pipeline not in (None,"integrated"):
        return JSONResponse(status_code=422,content={"status":"InvalidInput","outcome":"InvalidInput","complete":False})
    if body.model_extra:
        return JSONResponse(status_code=422,content={"status":"InvalidInput","outcome":"InvalidInput","complete":False})
    action=RefinementAction.parse(body.refinement.model_dump()) if body.refinement is not None else None
    from app.application.recommendation.local_preference_assistant import completed_receipt,has_soft_language,is_local_parent
    try:
        from app.application.recommendation.compositional_workflow_v1 import receipt as compositional_receipt,is_parent as compositional_parent
        composed=compositional_receipt(_repository(service),user_id,body,x_wardrobe_profile_id)
        if composed is not None:
            from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
            return _assistant_response(OutfitAssistantService._success(composed,True,{}))
        if action is not None and compositional_parent(_repository(service),user_id,action.parent_recommendation_id):
            return _assistant_response({'status':'RefinementUnavailable','complete':False,'context_reason':'compositional_continuation_unavailable'})
        from app.application.recommendation.normalized_workflow_v1 import receipt as normalized_receipt
        normalized=normalized_receipt(_repository(service),user_id,body,x_wardrobe_profile_id)
        if normalized is not None:
            from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
            return _assistant_response(OutfitAssistantService._success(normalized,True,{}))
        archived=completed_receipt(_repository(service),user_id,body,x_wardrobe_profile_id)
        if archived is not None:
            from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
            return _assistant_response(OutfitAssistantService._success(archived,True,{}))
        if action is not None and action.kind=='alternative' and is_local_parent(_repository(service),user_id,action.parent_recommendation_id):
            return _assistant_response({'status':'SoftContinuationUnavailable','complete':False})
    except PersistenceConflict:return _conflict()
    except Exception as error:
        from app.application.recommendation.failure_diagnostics import log_failure
        log_failure('assistant','local_receipt','PersistenceFailure',error)
        return _assistant_response({'status':'PersistenceFailure','complete':False})
    local=getattr(service,'local_preferences',None)
    normalization=getattr(service,'input_composition',None) or getattr(service,'input_normalization',None)
    if normalization is not None and action is None:
        # Existing receipts retain priority, even when this new opt-in is enabled.
        try:
            prior=_repository(service).find_assistant_submission(user_id,body.submission_key,body.request_text,
                wearer_profile_id=body.wearer_profile_id,header_profile_id=x_wardrobe_profile_id,attribute_conditions=body.attribute_conditions,
                preference_profile=body.preference_profile,compatibility_profile=body.compatibility_profile)
            if prior is not None:
                from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
                return _assistant_response(OutfitAssistantService._success(prior,True,{}))
            wearer=resolve_wearer(user_id,body.wearer_profile_id,x_wardrobe_profile_id)
            with profile_scope(wearer.profile_id):result=_category_call(normalization.recommend,user_id,body,wearer)
            if result is not None:return _assistant_response(result)
        except PersistenceConflict:return _conflict()
    if local is not None and has_soft_language(body.request_text):
        wearer=resolve_wearer(user_id,body.wearer_profile_id,x_wardrobe_profile_id)
        with profile_scope(wearer.profile_id):
            return _assistant_response(_category_call(local.recommend,user_id,body,wearer))
    try:
        prior=_repository(service).find_assistant_submission(user_id,body.submission_key,body.request_text,action,
            wearer_profile_id=body.wearer_profile_id,header_profile_id=x_wardrobe_profile_id,attribute_conditions=body.attribute_conditions,**({'preference_profile':body.preference_profile} if body.preference_profile is not None else {}),**({'compatibility_profile':body.compatibility_profile} if body.compatibility_profile is not None else {}))
    except PersistenceConflict:return _conflict()
    except Exception as error:
        from app.application.recommendation.failure_diagnostics import log_failure
        log_failure('assistant','lookup','PersistenceFailure',error)
        return JSONResponse(status_code=503,content={'status':'PersistenceFailure','outcome':'PersistenceFailure','complete':False})
    if prior is not None:
        from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
        result=OutfitAssistantService._success(prior,True,{})
    else:
        if service is None:
            return JSONResponse(status_code=404,content={"status":"IntegrationDisabled","outcome":"IntegrationDisabled","complete":False})
        if action is not None and action.kind=='alternative':
            try:_repository(service).require_owned_parent(user_id,action.parent_recommendation_id)
            except LookupError:return JSONResponse(status_code=404,content={'status':'RefinementNotFound','outcome':'RefinementNotFound','complete':False})
        wearer=resolve_wearer(user_id,body.wearer_profile_id,x_wardrobe_profile_id)
        with profile_scope(wearer.profile_id):
            result=_category_call(service.recommend,user_id,body.submission_key,body.request_text,
                body.refinement.model_dump() if body.refinement is not None else None,wearer=wearer,
                **({'attribute_conditions':body.attribute_conditions} if body.attribute_conditions is not None else {}),
                **({'preference_profile':body.preference_profile} if body.preference_profile is not None else {}),**({'compatibility_profile':body.compatibility_profile} if body.compatibility_profile is not None else {}))
    return _assistant_response(result)


def _assistant_response(result):
    status = result["status"]
    code = 200
    if status == "Selected":
        code = 200 if result["replayed"] else 201
    elif status in ("SoftProfileUnavailable","UnsupportedSoftPreference","AmbiguousSoftBinding","SoftContinuationUnavailable","InvalidInput","UnsupportedRequest","GarmentWordingClarification","PolicyUnavailable","InvalidPreferenceData","ProfileUnavailable","RefinementConflict","RefinementUnavailable","AttributeUnavailable","AttributeConflict","UnsupportedAttributeValue","EncodingLimitExceeded","PreferenceUnavailable","PreferenceInvalid","PreferenceCapacityExceeded","CompatibilityUnavailable","CompatibilityInvalid","CompatibilityCapacityExceeded"):
        code = 422
    elif status.startswith(("WearerCategory","WearerEligibility","WearerSubtype")):code=409
    elif status in ("IdempotencyConflict","WardrobeChanged","RefinementScopeChanged","WardrobeCapacityExceeded"):
        code = 409
    elif status=='RefinementNotFound':code=404
    elif status in ("ProcessingFailure","ProcessingError","PersistenceFailure","Interrupted","InvalidScoringInput"):
        code = 503
    content = {**result,"outcome":status}
    if status == "Selected":
        content["status"] = result["recommendation_status"]
    return JSONResponse(status_code=code,content=content)


@router.post("/{recommendation_id}/save-as-outfit", status_code=201)
def save_as_outfit(recommendation_id: str, body: RecommendationSaveAsOutfit, user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)) -> dict:
    return recommendations.save_as_outfit(recommendation_id, user_id, body.name, profile_id)


@router.get("/{recommendation_id}/saved-outfit")
def saved_outfit(recommendation_id: str, user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)) -> dict:
    return recommendations.saved_outfit_state(recommendation_id, user_id, profile_id)
