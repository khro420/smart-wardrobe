"""Closed opt-in pure-B1 policy. No context objective or new score producer."""
from pathlib import Path
import hashlib,json
from dataclasses import replace,asdict
from app.domain.value_objects.garment_only_refinement import PROFILE,GarmentRefinementPlan,GarmentRefinementDraft
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.domain.value_objects.recommendation_refinement import RefinementError
ENVIRONMENT_KEY='SMART_WARDROBE_GARMENT_ONLY_REFINEMENT_PROFILE'
RESOURCE=Path(__file__).with_name('config')/'garment_only_refinement.v1.json'
RESOURCE_SHA256='60bb2466fc5c5537ebc3126270c50e597240b79462e7f63d592254b90998ef92'

def load():
    raw=RESOURCE.read_bytes()
    if len(raw)>4096 or hashlib.sha256(raw).hexdigest()!=RESOURCE_SHA256:raise ValueError('Unapproved garment continuation policy.')
    return json.loads(raw)

def applies(request,intent):
    return type(request) is StructuredOutfitRequest and all(getattr(request,k) is None for k in ('occasion','style','colours','garment_categories','formality')) and intent is not None and intent.conditions.condition_count>0

def prepare(plan,action,user,wearer,text,request,intent,garments,rows,collection,selection,execution,evaluator,preference_capture,palette,eligibility):
    load()
    from app.application.recommendation.refinement_verifier import snapshot_digest,preference_digest,request_digest,scope_digest
    from app.domain.value_objects.attribute_selection_evidence import description_digest,subtype_digest,scope_digest as attribute_scope
    from app.domain.value_objects.attribute_preferences import digest
    from app.domain.value_objects.attribute_preference_evidence import preference_scope
    if wearer is None or not applies(request,intent):raise RefinementError('RefinementUnavailable','pure_B1_captured_wearer_required')
    exclusions=plan.exclusions if plan else action.excluded_categories if action else ()
    gh,ph,rh=snapshot_digest(garments),preference_digest(user,rows),request_digest(text,request,exclusions)
    dh=description_digest(collection)
    contracts={'version':load()['version'],'policy':RESOURCE_SHA256,'scoring':selection.hash,'execution':execution.provenance,'evaluator':asdict(evaluator.specification),
        'descriptions':dh,'intent':intent.sha256,'p2':digest(preference_capture.to_dict()) if preference_capture else None,
        'palette':palette.policy.hash if palette else None,'eligibility':digest(eligibility.eligibility.to_dict()) if eligibility else None}
    scope=scope_digest(rh,gh,ph,contracts)
    if plan is not None and plan.compatibility_scope_sha256!=scope:raise RefinementError('RefinementScopeChanged','ranking_scope_changed_start_fresh')
    base=plan or GarmentRefinementPlan(exclusions=exclusions,compatibility_scope_sha256=scope,wearer_profile_id=wearer.profile_id,attribute_intent=intent,description_collection_sha256=dh,attribute_scope_sha256=attribute_scope(user,wearer.profile_id,scope,intent,dh,subtype_digest(eligibility.account_subtypes) if eligibility and intent.to_dict()['version']=='assistant-attribute-intent-2.0.0' else None))
    if preference_capture:
        base=replace(base,preference_profile='attribute_preference_decision_v2',attribute_preference_sha256=digest(preference_capture.to_dict()),attribute_preference_scope_sha256=preference_scope(preference_capture,scope,gh,dh,rh))
    if palette:base=replace(base,compatibility_profile='recorded_palette_compatibility_v1',palette_collection_sha256=palette.collection_sha256)
    return base,GarmentRefinementDraft(base,action,gh,ph,rh),scope
