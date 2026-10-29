"""Authoritative bounded stored chain validation, independent of live wardrobe data."""
import json
from app.domain.value_objects.recommendation_refinement import RefinementPlan,RefinementError,digest,step_key
from app.domain.value_objects.context_relevance import read_ratio
from app.application.recommendation.refinement_verifier import validate_refinement,rebuild_request


def validate_chain(user,records):
    from app.application.recommendation.decision_score_codec import score_from_json
    from app.application.recommendation.context_relevance_verifier import validate_evidence
    if not records or len(records)>10:raise ValueError('Missing or oversized stored lineage.')
    seen=[];root=None;previous=None
    for ordinal,record in enumerate(records):
        if record['user_id']!=user:raise LookupError('Recommendation not found.')
        provenance=json.loads(record['provenance_json']);proof=provenance['refinement'];relative=provenance['context_relevance']
        score=score_from_json(record['score_json']);payload=json.loads(record['extracted_entities_json'])
        validate_evidence(relative,score)
        signature=validate_refinement(proof,relative,score,record['id'],record['request_text'],payload)
        if proof['ordinal']!=ordinal or proof['parent_id']!=(previous['id'] if previous else None):raise ValueError('Noncontiguous stored lineage.')
        if proof['seen_sha256']!=digest(tuple(seen)) or signature in seen:raise ValueError('Repeated base or false seen evidence.')
        blocker=relative['strongest_unresolved']
        if blocker is not None and tuple(tuple(pair) for pair in blocker['key'] if pair[0]!='outerwear') in seen:
            raise ValueError('Remaining blocker cannot be an already selected base.')
        if root is None:root=proof
        else:
            for key in ('root_id','root_R','root_total','excluded_categories','compatibility_scope_sha256','garment_snapshot_sha256','preference_snapshot_sha256','request_sha256','policy_sha256'):
                if proof[key]!=root[key]:raise ValueError('Inconsistent stored lineage scope.')
            if record.get('submission_key')!=step_key(root['root_id'],ordinal):raise ValueError('Noncanonical stored step receipt.')
            previous_score=score_from_json(previous['score_json'])
            if score.total>previous_score.total:raise ValueError('Alternative total increased under unchanged scope.')
        seen.append(signature);previous=record
    return tuple(seen)


def continuation(user,parent,records,request_text,submission_key):
    if not records:raise RefinementError('RefinementUnavailable','relative_ordinary_required')
    seen=validate_chain(user,records)
    proof=json.loads(parent['provenance_json'])['refinement']
    index=proof['ordinal']
    if index>=len(records) or records[index]['id']!=parent['id']:raise ValueError('Parent not in stored lineage.')
    if request_text!=records[0]['request_text']:raise RefinementError('IdempotencyConflict','original_text_required')
    if index==9:raise RefinementError('RefinementLimitReached','ten_result_limit')
    if submission_key!=step_key(proof['root_id'],index+1):raise RefinementError('RefinementUnavailable','canonical_step_key_required')
    plan=RefinementPlan(tuple(proof['excluded_categories']),proof['root_id'],parent['id'],index+1,
        read_ratio(proof['root_R']),read_ratio(proof['root_total']),seen[:index+1],proof['compatibility_scope_sha256'])
    return plan,rebuild_request(json.loads(records[0]['extracted_entities_json']))
