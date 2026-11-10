"""Validate a complete stored garment chain and restore its original intent."""
import json
from app.domain.value_objects.garment_only_refinement import KEY,GarmentRefinementPlan,step_key
from app.domain.value_objects.recommendation_refinement import RefinementError,digest
from app.domain.value_objects.context_relevance import read_ratio
from app.application.recommendation.garment_only_refinement_verifier import validate

def projection(row):return {**row,'provenance':json.loads(row['provenance_json']),'score_metadata':json.loads(row['score_json'])}
def validate_chain(user,records):
    from app.application.recommendation.decision_score_codec import score_from_json
    if not records or len(records)>10:raise ValueError('Missing/oversized garment chain.')
    seen=[];previous=None;root=None;previous_score=None
    for index,row in enumerate(records):
        if row['user_id']!=user:raise LookupError('Recommendation not found.')
        record=projection(row);proof=record['provenance'][KEY];signature=validate(record)
        if proof['ordinal']!=index or proof['parent_id']!=previous or signature in seen or proof['seen_sha256']!=digest(tuple(seen)):raise ValueError('Noncontiguous or repeated garment chain.')
        if root is None:
            root=proof
            if read_ratio(proof['root_total'])!=score_from_json(row['score_json']).total:raise ValueError('Root total mismatch.')
        else:
            for key in ('root_id','root_R','root_total','profile_id','user_id','excluded_categories','compatibility_scope_sha256','garment_snapshot_sha256','preference_snapshot_sha256','request_sha256','policy_sha256','attribute_intent_sha256','description_collection_sha256','attribute_scope_sha256','preference_profile','attribute_preference_sha256','attribute_preference_scope_sha256','compatibility_profile','palette_collection_sha256'):
                if proof[key]!=root[key]:raise ValueError('Changed garment lineage scope.')
            if row.get('submission_key')!=step_key(root['root_id'],index):raise ValueError('Noncanonical garment receipt.')
        score=score_from_json(row['score_json'])
        if previous_score is not None and score.total>previous_score.total:raise ValueError('Alternative total increased.')
        from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
        intent=AttributeIntent.from_dict(record['provenance']['attribute_selection']['intent'])
        plan=GarmentRefinementPlan(tuple(proof['excluded_categories']),proof['root_id'] if index else None,proof['parent_id'],index,read_ratio(proof['root_R']) if index else None,read_ratio(proof['root_total']) if index else None,tuple(seen),proof['compatibility_scope_sha256'],proof['profile_id'],intent,proof['description_collection_sha256'],proof['attribute_scope_sha256'],proof['preference_profile'],proof['attribute_preference_sha256'],proof['attribute_preference_scope_sha256'],proof['compatibility_profile'],proof['palette_collection_sha256'])
        if plan.selection_scope_sha256!=proof['selection_scope_sha256']:raise ValueError('Changed exact garment selection scope.')
        seen.append(signature);previous=row['id'];previous_score=score
    return tuple(seen)

def continuation(user,parent,records,text,key,wearer=None,attribute_conditions=None,preference_profile=None,compatibility_profile=None):
    from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
    from app.domain.value_objects.attribute_conditions import AttributeConditions
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
    if not records:raise RefinementError('RefinementUnavailable','old_garment_roots_not_promoted')
    if wearer is None or wearer.account_id!=user or any(r['profile_id']!=wearer.profile_id for r in records):raise RefinementError('IdempotencyConflict','wearer_mismatch')
    seen=validate_chain(user,records);root=projection(records[0]);proof=projection(parent)['provenance'][KEY];source=root['provenance']['attribute_selection']
    if any(proof[k]!=v for k,v in (('preference_profile',preference_profile),('compatibility_profile',compatibility_profile))):raise RefinementError('IdempotencyConflict','captured_modes_required')
    intent=AttributeIntent.from_dict(source['intent']);typed=AttributeConditions.from_dict(attribute_conditions).to_dict() if attribute_conditions is not None else None
    if typed!=intent.to_dict()['typed_input'] or text!=records[0]['request_text']:raise RefinementError('IdempotencyConflict','original_text_and_conditions_required')
    index=proof['ordinal']
    if index>=len(records) or records[index]['id']!=parent['id']:raise ValueError('Parent not in garment lineage.')
    if index==9:raise RefinementError('RefinementLimitReached','ten_result_limit')
    if key!=step_key(proof['root_id'],index+1):raise RefinementError('RefinementUnavailable','canonical_step_key_required')
    plan=GarmentRefinementPlan(tuple(proof['excluded_categories']),proof['root_id'],parent['id'],index+1,read_ratio(proof['root_R']),read_ratio(proof['root_total']),seen[:index+1],proof['compatibility_scope_sha256'],wearer.profile_id,intent,proof['description_collection_sha256'],proof['attribute_scope_sha256'],preference_profile,proof['attribute_preference_sha256'],proof['attribute_preference_scope_sha256'],compatibility_profile,proof['palette_collection_sha256'])
    return plan,StructuredOutfitRequest(**json.loads(records[0]['extracted_entities_json']))
