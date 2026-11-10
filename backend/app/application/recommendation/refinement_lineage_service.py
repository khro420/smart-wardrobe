"""Authoritative bounded stored chain validation, independent of live wardrobe data."""
import json
from app.domain.value_objects.recommendation_refinement import RefinementPlan,RefinementError,digest,step_key
from app.domain.value_objects.context_relevance import read_ratio
from app.application.recommendation.refinement_verifier import validate_refinement,rebuild_request


def validate_chain(user,records):
    from app.application.recommendation.decision_score_codec import score_from_json
    from app.application.recommendation.context_relevance_verifier import validate_evidence
    if not records or len(records)>10:raise ValueError('Missing or oversized stored lineage.')
    new_binding=any(json.loads(record['provenance_json'])['refinement']['version'] in ('recommendation-refinement-evidence-1.1.0','recommendation-refinement-evidence-1.2.0','recommendation-refinement-evidence-2.0.0') for record in records)
    if new_binding and (any(record.get('profile_id') is None for record in records) or len({record.get('profile_id') for record in records})!=1):
        raise ValueError('Inconsistent stored wearer lineage.')
    seen=[];root=None;previous=None
    for ordinal,record in enumerate(records):
        if record['user_id']!=user:raise LookupError('Recommendation not found.')
        provenance=json.loads(record['provenance_json']);proof=provenance['refinement'];relative=provenance['context_relevance']
        score=score_from_json(record['score_json']);payload=json.loads(record['extracted_entities_json'])
        validate_evidence(relative,score)
        signature=validate_refinement(proof,relative,score,record['id'],record['request_text'],payload,user_id=user,wearer_profile_id=record.get('profile_id'))
        if proof['version'] in ('recommendation-refinement-evidence-1.1.0','recommendation-refinement-evidence-1.2.0','recommendation-refinement-evidence-2.0.0'):
            from app.domain.value_objects.intended_wearer import validate_wearer_evidence
            validate_wearer_evidence(provenance.get('intended_wearer'),user,record.get('profile_id'))
        if 'attribute_intent_sha256' in proof:
            from app.application.recommendation.attribute_selection_verifier import validate_selection
            from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
            evidence=validate_selection(provenance.get('attribute_selection'),user,record.get('profile_id'),proof['compatibility_scope_sha256'])
            attr=evidence.to_dict();intent=AttributeIntent.from_dict(attr['intent'])
            if (proof['attribute_intent_sha256']!=intent.sha256 or proof['description_collection_sha256']!=attr['description_collection_sha256']
                or proof['attribute_scope_sha256']!=attr['attribute_scope_sha256'] or relative['attribute_selection_sha256']!=evidence.sha256
                or record['request_text']!=intent.to_dict()['original_text']):raise ValueError('Stored attribute lineage binding mismatch.')
        elif 'attribute_selection' in provenance:raise ValueError('Legacy refinement cannot adopt new attribute intent.')
        if proof['version']=='recommendation-refinement-evidence-2.0.0':
            from app.application.recommendation.attribute_preference_verifier import validate as validate_preference,conditions_from
            from app.domain.value_objects.attribute_preferences import digest as p2_digest
            saved=provenance.get('attribute_preference')
            validate_preference(saved,score,user,record.get('profile_id'),conditions=conditions_from(provenance),request_text=record['request_text'],exclusions=proof['excluded_categories'])
            if proof['attribute_preference_sha256']!=p2_digest(saved['snapshot']) or proof['attribute_preference_scope_sha256']!=saved['scope']['preference_scope_sha256'] or relative['preference_snapshot_sha256']!=saved['snapshot']['revision'] or relative['preference_ledger_sha256']!=p2_digest(saved['ledger']):
                raise ValueError('P2 lineage input/score scope mismatch.')
        elif 'attribute_preference' in provenance:raise ValueError('Legacy lineage cannot adopt P2.')
        if proof['ordinal']!=ordinal or proof['parent_id']!=(previous['id'] if previous else None):raise ValueError('Noncontiguous stored lineage.')
        if proof['seen_sha256']!=digest(tuple(seen)) or signature in seen:raise ValueError('Repeated base or false seen evidence.')
        blocker=relative['strongest_unresolved']
        if blocker is not None and tuple(tuple(pair) for pair in blocker['key'] if pair[0]!='outerwear') in seen:
            raise ValueError('Remaining blocker cannot be an already selected base.')
        if root is None:root=proof
        else:
            for key in ('root_id','root_R','root_total','excluded_categories','compatibility_scope_sha256','garment_snapshot_sha256','preference_snapshot_sha256','request_sha256','policy_sha256'):
                if proof[key]!=root[key]:raise ValueError('Inconsistent stored lineage scope.')
            if ('attribute_intent_sha256' in proof)!=('attribute_intent_sha256' in root):
                raise ValueError('Mixed attribute lineage versions.')
            if 'attribute_intent_sha256' in proof:
                for key in ('attribute_intent_sha256','description_collection_sha256','attribute_scope_sha256'):
                    if proof[key]!=root[key]:raise ValueError('Changed attribute intent or sources in lineage.')
            if (proof['version']=='recommendation-refinement-evidence-2.0.0')!=(root['version']=='recommendation-refinement-evidence-2.0.0'):
                raise ValueError('Mixed P1/P2 lineage versions.')
            if proof['version']=='recommendation-refinement-evidence-2.0.0':
                for key in ('preference_profile','attribute_preference_sha256','attribute_preference_scope_sha256'):
                    if proof[key]!=root[key]:raise ValueError('Changed P2 snapshot in lineage.')
            if record.get('submission_key')!=step_key(root['root_id'],ordinal):raise ValueError('Noncanonical stored step receipt.')
            previous_score=score_from_json(previous['score_json'])
            if score.total>previous_score.total:raise ValueError('Alternative total increased under unchanged scope.')
        seen.append(signature);previous=record
    return tuple(seen)


def continuation(user,parent,records,request_text,submission_key,wearer=None,attribute_conditions=None,preference_profile=None):
    if not records:raise RefinementError('RefinementUnavailable','relative_ordinary_required')
    if wearer is not None:
        if wearer.account_id!=user:raise LookupError('Recommendation not found.')
        if any(record.get('profile_id') is None for record in records):
            raise RefinementError('RefinementUnavailable','legacy_wearer_unrecorded')
        if any(record.get('profile_id')!=wearer.profile_id for record in records) or parent.get('profile_id')!=wearer.profile_id:
            raise RefinementError('IdempotencyConflict','wearer_mismatch')
    root_preference=json.loads(records[0]['provenance_json']).get('attribute_preference')
    if (root_preference is not None)!=(preference_profile is not None) or preference_profile is not None and preference_profile!='attribute_preference_decision_v2':
        raise RefinementError('IdempotencyConflict','preference_profile_mismatch_start_fresh')
    seen=validate_chain(user,records)
    proof=json.loads(parent['provenance_json'])['refinement']
    source=json.loads(records[0]['provenance_json']).get('attribute_selection')
    intent=None
    if source is not None:
        from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
        from app.domain.value_objects.attribute_conditions import AttributeConditions
        intent=AttributeIntent.from_dict(source['intent'])
        actual=AttributeConditions.from_dict(attribute_conditions).to_dict() if attribute_conditions is not None else None
        if actual!=intent.to_dict()['typed_input']:raise RefinementError('IdempotencyConflict','original_attribute_intent_required')
    elif attribute_conditions is not None:raise RefinementError('IdempotencyConflict','new_attributes_require_new_root')
    index=proof['ordinal']
    if index>=len(records) or records[index]['id']!=parent['id']:raise ValueError('Parent not in stored lineage.')
    if request_text!=records[0]['request_text']:raise RefinementError('IdempotencyConflict','original_text_required')
    if index==9:raise RefinementError('RefinementLimitReached','ten_result_limit')
    if submission_key!=step_key(proof['root_id'],index+1):raise RefinementError('RefinementUnavailable','canonical_step_key_required')
    plan=RefinementPlan(tuple(proof['excluded_categories']),proof['root_id'],parent['id'],index+1,
        read_ratio(proof['root_R']),read_ratio(proof['root_total']),seen[:index+1],proof['compatibility_scope_sha256'],wearer.profile_id if wearer else None,
        intent,source['description_collection_sha256'] if source else None,source['attribute_scope_sha256'] if source else None,preference_profile,
        proof.get('attribute_preference_sha256'),proof.get('attribute_preference_scope_sha256'))
    return plan,rebuild_request(json.loads(records[0]['extracted_entities_json']))
