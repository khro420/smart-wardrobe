"""Archived refinement identity, scope and selected-fact verification."""
from dataclasses import asdict
import json
from app.domain.value_objects.context_relevance import read_ratio, ratio, require_digest, RelativeEncodingLimit
from app.domain.value_objects.recommendation_refinement import (
    RefinementAction, canonical_categories, canonical_uuid, digest, selection_digest,
)

ARCHIVED_POLICY=('recommendation-refinement-policy-1.0.0',
    'f347c29e22fdd9cd8947e2b70322118d26a0d47c0380c64ab0faf65f1d26f0e4')
EVIDENCE_VERSION='recommendation-refinement-evidence-1.0.0'
FIELDS={'version','policy_version','policy_sha256','root_id','parent_id','ordinal',
    'request_fingerprint_version','canonical_action','excluded_categories','compatibility_scope_sha256',
    'selection_scope_sha256','garment_snapshot_sha256','preference_snapshot_sha256','request_sha256',
    'root_R','root_total','base_signature_sha256','seen_count','seen_sha256','mode','total_vs_root'}


def bounded_provenance(value, *, draft=False):
    text=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
    refinement=value.get('refinement') if type(value) is dict else None
    limit=327680 if draft or type(refinement) is dict and refinement.get('version')==EVIDENCE_VERSION else 262144
    if len(text.encode())>limit:raise RelativeEncodingLimit('Provenance encoding exceeds its versioned bound.')
    return text


def snapshot_digest(garments):
    return digest([asdict(g) for g in sorted(garments,key=lambda g:g.garment_id)])


def preference_digest(user,rows):
    from app.application.recommendation.preference_normalizer import PreferenceNormalizer
    normalized=PreferenceNormalizer().normalize(user,rows)
    def exact(value):
        from fractions import Fraction
        if isinstance(value,Fraction):return ratio(value)
        if isinstance(value,dict):return {k:exact(v) for k,v in value.items()}
        if isinstance(value,(tuple,list)):return [exact(v) for v in value]
        return value
    return digest({'raw':[asdict(row) for row in rows],'normalized':exact(asdict(normalized))})


def request_digest(text,request,exclusions):
    return digest({'text':text,'request':request.to_dict() if hasattr(request,'to_dict') else request,
                   'excluded_categories':list(exclusions)})


def scope_digest(request_hash,garments_hash,preferences_hash,contracts):
    return digest(dict(version='recommendation-refinement-scope-1.0.0',request_sha256=request_hash,
        garment_snapshot_sha256=garments_hash,preference_snapshot_sha256=preferences_hash,contracts=contracts))


def stored_signature(relative):
    signature=tuple((m['role'],m['garment_id']) for m in relative['selected_members'] if m['role']!='outerwear')
    if tuple(x[0] for x in signature) not in (('one_piece',),('upper','lower')):
        raise ValueError('Invalid stored base structure.')
    return signature


def finalize_supplement(plan,identifier,action,score,relative,garment_hash,preference_hash,request_hash):
    """Writer assigns a root identity; the ranking draft itself is never persisted."""
    root=plan.root_id if plan.ordinal else identifier
    floor=plan.root_R if plan.ordinal else score.request_match.contribution
    total=plan.root_total if plan.ordinal else score.total
    data=dict(version=EVIDENCE_VERSION,policy_version=ARCHIVED_POLICY[0],policy_sha256=ARCHIVED_POLICY[1],
        root_id=root,parent_id=plan.parent_id,ordinal=plan.ordinal,
        request_fingerprint_version=2 if action else 1,canonical_action=action.to_dict() if action else None,
        excluded_categories=list(plan.exclusions),compatibility_scope_sha256=plan.compatibility_scope_sha256,
        garment_snapshot_sha256=garment_hash,preference_snapshot_sha256=preference_hash,request_sha256=request_hash,
        root_R=ratio(floor),root_total=ratio(total),base_signature_sha256=digest(stored_signature(relative)),
        seen_count=len(plan.seen),seen_sha256=digest(plan.seen),mode=plan.mode,
        total_vs_root='same' if score.total==total else 'lower')
    data['selection_scope_sha256']=selection_digest(plan.compatibility_scope_sha256,root,plan.parent_id,
        plan.ordinal,plan.mode,data['root_R'],data['seen_sha256'],len(plan.seen))
    relative['selection_scope_sha256']=data['selection_scope_sha256']
    return data


def validate_refinement(data,relative,score,identifier,request_text,request_payload,candidate=None):
    if type(data) is not dict or set(data)!=FIELDS or data['version']!=EVIDENCE_VERSION:
        raise ValueError('Exact archived refinement schema required.')
    if len(json.dumps(data,separators=(',',':'),ensure_ascii=True).encode())>32768:
        raise RelativeEncodingLimit('Refinement supplement exceeds 32 KiB.')
    if (data['policy_version'],data['policy_sha256'])!=ARCHIVED_POLICY:
        raise ValueError('Unsupported archived refinement policy.')
    for key in FIELDS:
        if key.endswith('_sha256'):require_digest(data[key])
    canonical_uuid(identifier);canonical_uuid(data['root_id'])
    ordinal=data['ordinal']
    if type(ordinal) is not int or not 0<=ordinal<=9 or type(data['seen_count']) is not int or data['seen_count']!=ordinal:
        raise ValueError('Invalid bounded sequence position.')
    if ordinal:
        canonical_uuid(data['parent_id'])
        if identifier in (data['root_id'],data['parent_id']):raise ValueError('Cyclic refinement identity.')
    elif data['parent_id'] is not None or data['root_id']!=identifier or data['seen_sha256']!=digest(()):
        raise ValueError('Invalid root identity.')
    expected_mode='same_R_floor_base_distinct_v1' if ordinal else 'initial_permitted_optimum_v1'
    if data['mode']!=expected_mode:raise ValueError('Invalid selection mode.')
    exclusions=canonical_categories(data['excluded_categories'])
    if list(exclusions)!=data['excluded_categories']:raise ValueError('Noncanonical stored exclusions.')
    action=data['canonical_action']
    if action is not None:
        parsed=RefinementAction.parse(action)
        if parsed.to_dict()!=action or parsed.kind!=('alternative' if ordinal else 'initial'):
            raise ValueError('Invalid stored action.')
        if ordinal and parsed.parent_recommendation_id!=data['parent_id'] or not ordinal and parsed.excluded_categories!=exclusions:
            raise ValueError('Action/lineage mismatch.')
    if type(data['request_fingerprint_version']) is not int or data['request_fingerprint_version']!=(2 if action is not None else 1) or ordinal and action is None:
        raise ValueError('Fingerprint contract mismatch.')
    floor,total=read_ratio(data['root_R']),read_ratio(data['root_total'])
    if not 0<=floor<=1 or not 0<=total<=1 or score.request_match.contribution<floor or score.total>total:
        raise ValueError('Original floor or total violated.')
    if not ordinal and (floor!=score.request_match.contribution or total!=score.total):
        raise ValueError('Root score mismatch.')
    if data['total_vs_root']!=('same' if score.total==total else 'lower'):
        raise ValueError('False total comparison.')
    if relative['version']!='context-relevance-evidence-1.2.0' or relative['selection_mode']!='best_evidenced_with_coverage_v1':
        raise ValueError('A refinement cannot use legacy request match as its floor.')
    blocker=relative['strongest_unresolved']
    if ordinal and blocker is not None and read_ratio(blocker['R_high'])<floor:
        raise ValueError('Remaining blocker cannot be below the original floor.')
    expected=selection_digest(data['compatibility_scope_sha256'],data['root_id'],data['parent_id'],ordinal,
        data['mode'],data['root_R'],data['seen_sha256'],data['seen_count'])
    if data['selection_scope_sha256']!=expected or relative['selection_scope_sha256']!=expected:
        raise ValueError('Selection scope binding mismatch.')
    if request_digest(request_text,request_payload,exclusions)!=data['request_sha256']:
        raise ValueError('Original request identity mismatch.')
    signature=stored_signature(relative)
    if digest(signature)!=data['base_signature_sha256']:raise ValueError('Base identity mismatch.')
    if candidate is not None:
        from app.application.recommendation.refinement_selector import check_selected_exclusions,base_signature
        check_selected_exclusions(candidate,exclusions)
        if base_signature(candidate)!=signature:raise ValueError('Selected base mismatch.')
    if not ordinal and any(relative['coverage'][k] for k in ('already_seen','below_floor_points','unresolved_below_floor')):
        raise ValueError('Root has no prior selection floor or seen bases.')
    return signature


def rebuild_request(payload):
    """Decode a stored frame, without invoking current interpretation."""
    from app.domain.value_objects.general_context_request import GeneralContext,ContextSlot,SourceSpan,GeneralContextRequest
    from app.domain.value_objects.structured_outfit_request import GarmentCategoryConstraint
    values=dict(payload);frame=dict(values.pop('context'))
    for key,value in tuple(frame.items()):
        if isinstance(value,dict):
            if set(value)!={'state','values','spans'}:raise ValueError('Invalid archived frame slot.')
            frame[key]=ContextSlot(value['state'],tuple(value['values']),tuple(SourceSpan(**s) for s in value['spans']))
    values['garment_categories']=tuple(GarmentCategoryConstraint(**c) for c in values['garment_categories']) if values['garment_categories'] else None
    rebuilt=GeneralContextRequest(**values,context=GeneralContext(**frame))
    if digest(rebuilt.to_dict())!=digest(payload):raise ValueError('Archived request schema mismatch.')
    return rebuilt
