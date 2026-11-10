"""Version-dispatched C2 archives; old proof validators retain their meaning."""
from app.domain.value_objects.palette_compatibility import PROFILE,PROFILES,DECISION,WEIGHTS,PaletteCompatibilityComponent
from app.application.recommendation.palette_compatibility_policy import RESOURCE_SHA256

def base_relative(data):
    base=dict(data)
    base.update(version=base.pop('base_version'),explanation_version=base.pop('base_explanation_version'),actual_profile=base.pop('base_actual_profile'))
    base.pop('compatibility_profile');base.pop('compatibility_policy_sha256')
    return base

def validate_relative(data,score,candidate=None,request=None):
    from app.application.recommendation.palette_compatibility_selection import legacy_score
    from app.application.recommendation.context_relevance_verifier import validate_evidence
    if (type(data) is not dict or data.get('version')!='context-relevance-evidence-3.0.0'
        or data.get('explanation_version')!='context-relevance-explanation-3.0.0'
        or data.get('compatibility_profile')!=PROFILE or data.get('compatibility_policy_sha256')!=RESOURCE_SHA256
        or data.get('actual_profile')!=score.profile_name or score.profile_name not in PROFILES.values()
        or score.policy_version!=DECISION or score.weights!=WEIGHTS or type(score.compatibility) is not PaletteCompatibilityComponent):
        raise ValueError('Invalid C2 relative proof/score identity.')
    base=dict(data)
    version=base.pop('base_version');explanation=base.pop('base_explanation_version');actual=base.pop('base_actual_profile')
    base.pop('compatibility_profile');base.pop('compatibility_policy_sha256')
    proxy=legacy_score(score)
    if version not in ('context-relevance-evidence-1.0.0','context-relevance-evidence-1.1.0','context-relevance-evidence-1.2.0','context-relevance-evidence-1.3.0','context-relevance-evidence-2.0.0') or actual!=proxy.profile_name:
        raise ValueError('Invalid C2 archived base dispatch.')
    base.update(version=version,explanation_version=explanation,actual_profile=actual)
    validate_evidence(base,proxy,candidate,request)
    return data

def validate_archive(value,score,user,wearer,*,items=None,request_text=None,request=None):
    from app.application.recommendation.palette_compatibility_policy import PalettePolicy,encode,digest
    from app.application.recommendation.palette_compatibility_codec import exact,score_data
    from app.application.recommendation.palette_compatibility_preparation import PreparedPaletteCompatibility
    from app.application.recommendation.palette_compatibility_scorer import public_component
    from app.application.recommendation.attribute_preference_codec import restore_snapshot
    from app.domain.value_objects.garment_description_evidence import GarmentDescriptionEvidence
    from app.shared_contracts.confirmed_garment_description import ConfirmedGarmentDescription
    from app.domain.value_objects.outfit_candidate import OutfitCandidate,CandidateMember
    from app.domain.value_objects.palette_compatibility import EVIDENCE
    from app.application.recommendation.refinement_verifier import request_digest
    from app.domain.value_objects.context_relevance import require_digest
    from app.domain.value_objects.recommendation_refinement import canonical_uuid,canonical_categories
    exact(value,('contract','policy_snapshot','account_id','wearer_id','collection_sha256','strict_snapshot_sha256','original_text','request','excluded_categories','request_sha256','selected','score_sha256','revision'))
    if len(encode(value))>131072:raise ValueError('Oversized C2 selected archive.')
    original=dict(value);revision=original.pop('revision')
    if digest(original)!=revision or value['contract']!=EVIDENCE or value['account_id']!=user or value['wearer_id']!=wearer:raise ValueError('C2 archive revision/account/wearer mismatch.')
    canonical_uuid(wearer)
    for key in ('collection_sha256','strict_snapshot_sha256','request_sha256','score_sha256','revision'):require_digest(value[key])
    if type(value['original_text']) is not str or not 1<=len(value['original_text'])<=500:raise ValueError('C2 original text required.')
    if request_text is not None and request_text!=value['original_text'] or request is not None and request!=value['request']:raise ValueError('C2 stored request mismatch.')
    exclusions=canonical_categories(value['excluded_categories'])
    if request_digest(value['original_text'],value['request'],exclusions)!=value['request_sha256'] or digest(score_data(score))!=value['score_sha256']:raise ValueError('C2 score/request archive binding mismatch.')
    if type(value['selected']) is not list or not 1<=len(value['selected'])<=3:raise ValueError('C2 selected members missing/oversize.')
    pool=[];members=[]
    for position,row in enumerate(value['selected'],1):
        exact(row,('role','snapshot_sha256','snapshot','description'));require_digest(row['snapshot_sha256'])
        garment=restore_snapshot(row['snapshot'])
        if garment.user_id!=user:raise ValueError('Foreign C2 archived source.')
        pool.append(ConfirmedGarmentDescription(garment,GarmentDescriptionEvidence.from_dict(row['description'])))
        members.append(CandidateMember(garment,row['role'],position))
    candidate=OutfitCandidate(tuple(members));policy=PalettePolicy.restore(value['policy_snapshot'])
    prepared=PreparedPaletteCompatibility(user,pool,policy,archived=True)
    key=tuple((m.role,m.garment.garment_id) for m in candidate.members)
    if public_component(prepared.facts,key,policy)!=score.compatibility:raise ValueError('C2 source intervals and contribution do not reconstruct exactly.')
    if items is not None:
        actual={v['garment_id']:v for v in items}
        if set(actual)!={g.snapshot.garment_id for g in pool}:raise ValueError('C2 selected historical identities disagree.')
        for g in pool:
            if (actual[g.snapshot.garment_id].get('name'),actual[g.snapshot.garment_id].get('category'))!=(g.snapshot.name,g.snapshot.category):raise ValueError('C2 selected historical display disagrees.')
    return value

def validate_refinement(data,relative,score,identifier,text,payload,candidate=None,*,user_id=None,wearer_profile_id=None):
    from app.application.recommendation.refinement_verifier import validate_refinement as old_validate
    from app.application.recommendation.palette_compatibility_selection import legacy_score
    from app.domain.value_objects.context_relevance import require_digest
    if data.get('version')!='recommendation-refinement-evidence-3.0.0' or data.get('compatibility_profile')!=PROFILE or data.get('request_fingerprint_version')!=6:raise ValueError('Invalid C2 refinement identity.')
    require_digest(data['palette_collection_sha256'])
    validate_relative(relative,score,candidate)
    old=dict(data)
    old.update(version=old.pop('base_version'),request_fingerprint_version=old.pop('base_request_fingerprint_version'))
    old.pop('compatibility_profile');old.pop('palette_collection_sha256')
    if old['version'] not in ('recommendation-refinement-evidence-1.1.0','recommendation-refinement-evidence-1.2.0','recommendation-refinement-evidence-2.0.0'):raise ValueError('Invalid C2 base refinement version.')
    return old_validate(old,base_relative(relative),legacy_score(score),identifier,text,payload,candidate,user_id=user_id,wearer_profile_id=wearer_profile_id)

def read_chain(conn,user,parent_id):
    """Same bounded existing indexes; C2 records have their own size/version gate."""
    from app.infrastructure.persistence.refinement_lineage_query import SELECT_RECORD
    from app.domain.value_objects.recommendation_refinement import canonical_uuid,step_key
    from app.application.recommendation.palette_compatibility_policy import decode
    from app.application.recommendation.palette_compatibility_codec import bounded_provenance
    def record(identifier):
        canonical_uuid(identifier);row=conn.execute(SELECT_RECORD,(user,identifier)).fetchone()
        if row is None:raise LookupError('Recommendation not found.')
        row=dict(row);p=decode(row['provenance_json'],1048576);bounded_provenance(p)
        if len(row['score_json'].encode())>262144 or len(row['extracted_entities_json'].encode())>65536:raise ValueError('Oversized C2 lineage record.')
        if p.get('refinement',{}).get('version')!='recommendation-refinement-evidence-3.0.0':raise ValueError('C2 lineage supplement required.')
        return row
    parent=record(parent_id);proof=decode(parent['provenance_json'],1048576)['refinement'];root=record(proof['root_id'])
    keys=tuple(step_key(root['id'],n) for n in range(1,10))
    rows=conn.execute("SELECT submission_key,recommendation_id FROM recommendation_submissions WHERE user_id=? AND operation='assistant' AND submission_key IN (?,?,?,?,?,?,?,?,?)",(user,*keys)).fetchall()
    by_key={row['submission_key']:dict(record(row['recommendation_id']),submission_key=row['submission_key']) for row in rows}
    return parent,(root,*(by_key[k] for k in keys if k in by_key))

def validate_chain(user,records):
    from app.application.recommendation.palette_compatibility_policy import decode,digest
    from app.application.recommendation.decision_score_codec import score_from_json
    from app.application.recommendation.attribute_preference_verifier import validate as preference_validate,conditions_from
    from app.application.recommendation.attribute_selection_verifier import validate_selection
    from app.domain.value_objects.intended_wearer import validate_wearer_evidence
    from app.domain.value_objects.recommendation_refinement import step_key
    if not records or len(records)>10:raise ValueError('Missing/oversized C2 lineage.')
    seen=[];root=None;previous=None;last_score=None
    for ordinal,row in enumerate(records):
        if row['user_id']!=user:raise LookupError('Recommendation not found.')
        p=decode(row['provenance_json'],1048576);proof=p['refinement'];relative=p['context_relevance'];payload=decode(row['extracted_entities_json'],65536)
        score=score_from_json(row['score_json'])
        validate_wearer_evidence(p.get('intended_wearer'),user,row.get('profile_id'))
        archive=validate_archive(p['palette_compatibility'],score,user,row.get('profile_id'),request_text=row['request_text'],request=payload)
        signature=validate_refinement(proof,relative,score,row['id'],row['request_text'],payload,user_id=user,wearer_profile_id=row.get('profile_id'))
        if proof['palette_collection_sha256']!=archive['collection_sha256']:raise ValueError('C2 lineage source digest mismatch.')
        if 'attribute_intent_sha256' in proof:
            saved=validate_selection(p.get('attribute_selection'),user,row.get('profile_id'),proof['compatibility_scope_sha256']).to_dict()
            if (proof['description_collection_sha256'],proof['attribute_scope_sha256'],relative['attribute_scope_sha256'])!=(saved['description_collection_sha256'],saved['attribute_scope_sha256'],saved['attribute_scope_sha256']):raise ValueError('C2/B1 lineage source mismatch.')
            from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
            if proof['attribute_intent_sha256']!=AttributeIntent.from_dict(saved['intent']).sha256:raise ValueError('C2/B1 intent mismatch.')
        elif 'attribute_selection' in p:raise ValueError('Missing C2/B1 lineage binding.')
        if 'preference_profile' in proof:
            saved=p['attribute_preference'];preference_validate(saved,score,user,row.get('profile_id'),conditions=conditions_from(p),request_text=row['request_text'],exclusions=proof['excluded_categories'])
            from app.domain.value_objects.attribute_preferences import digest as p2_digest
            if (proof['attribute_preference_sha256'],proof['attribute_preference_scope_sha256'],relative['preference_snapshot_sha256'],relative['preference_ledger_sha256'])!=(p2_digest(saved['snapshot']),saved['scope']['preference_scope_sha256'],saved['snapshot']['revision'],p2_digest(saved['ledger'])):raise ValueError('C2/P2 lineage binding mismatch.')
        elif 'attribute_preference' in p:raise ValueError('Missing C2/P2 lineage binding.')
        if proof['ordinal']!=ordinal or proof['parent_id']!=(previous['id'] if previous else None) or proof['seen_sha256']!=__import__('app.domain.value_objects.recommendation_refinement',fromlist=['digest']).digest(tuple(seen)) or signature in seen:raise ValueError('Invalid C2 Seen/chain sequence.')
        blocker=relative['strongest_unresolved']
        if blocker and tuple(tuple(v) for v in blocker['key'] if v[0]!='outerwear') in seen:raise ValueError('C2 blocker is already seen.')
        if root is None:root=proof
        else:
            keys=('root_id','root_R','root_total','excluded_categories','compatibility_scope_sha256','garment_snapshot_sha256','preference_snapshot_sha256','request_sha256','policy_sha256','wearer_profile_id','compatibility_profile','palette_collection_sha256','attribute_intent_sha256','description_collection_sha256','attribute_scope_sha256','preference_profile','attribute_preference_sha256','attribute_preference_scope_sha256')
            if any(proof.get(k)!=root.get(k) for k in keys) or row.get('submission_key')!=step_key(root['root_id'],ordinal) or score.total>last_score.total:raise ValueError('Changed C2 lineage scope or increased alternative total.')
        seen.append(signature);previous=row;last_score=score
    return tuple(seen)

def continuation(user,parent,records,text,key,wearer=None,*,attribute_conditions=None,preference_profile=None,compatibility_profile=None):
    from app.application.recommendation.palette_compatibility_policy import decode
    from app.domain.value_objects.recommendation_refinement import RefinementError,RefinementPlan,step_key
    from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
    from app.domain.value_objects.attribute_conditions import AttributeConditions
    from app.domain.value_objects.context_relevance import read_ratio
    from app.application.recommendation.refinement_verifier import rebuild_request
    if compatibility_profile!=PROFILE:raise RefinementError('IdempotencyConflict','compatibility_profile_mismatch_start_fresh')
    seen=validate_chain(user,records);root=decode(records[0]['provenance_json'],1048576);proof=decode(parent['provenance_json'],1048576)['refinement']
    if wearer is None or wearer.account_id!=user or any(v.get('profile_id')!=wearer.profile_id for v in records):raise RefinementError('IdempotencyConflict','wearer_mismatch')
    if ('attribute_preference' in root)!=(preference_profile is not None) or preference_profile not in (None,'attribute_preference_decision_v2'):raise RefinementError('IdempotencyConflict','preference_profile_mismatch_start_fresh')
    source=root.get('attribute_selection');intent=AttributeIntent.from_dict(source['intent']) if source else None
    typed=AttributeConditions.from_dict(attribute_conditions).to_dict() if attribute_conditions is not None else None
    if typed!=(intent.to_dict()['typed_input'] if intent else None) or text!=records[0]['request_text']:raise RefinementError('IdempotencyConflict','original_attribute_intent_and_text_required')
    ordinal=proof['ordinal']
    if ordinal>=len(records) or records[ordinal]['id']!=parent['id']:raise ValueError('C2 parent not in chain.')
    if ordinal==9:raise RefinementError('RefinementLimitReached','ten_result_limit')
    if key!=step_key(proof['root_id'],ordinal+1):raise RefinementError('RefinementUnavailable','canonical_step_key_required')
    plan=RefinementPlan(tuple(proof['excluded_categories']),proof['root_id'],parent['id'],ordinal+1,read_ratio(proof['root_R']),read_ratio(proof['root_total']),seen[:ordinal+1],proof['compatibility_scope_sha256'],wearer.profile_id,
        intent,source['description_collection_sha256'] if source else None,source['attribute_scope_sha256'] if source else None,preference_profile,proof.get('attribute_preference_sha256'),proof.get('attribute_preference_scope_sha256'),PROFILE,proof['palette_collection_sha256'])
    return plan,rebuild_request(decode(records[0]['extracted_entities_json'],65536))
