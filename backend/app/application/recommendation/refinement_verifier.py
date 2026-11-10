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
WEARER_EVIDENCE_VERSION='recommendation-refinement-evidence-1.1.0'
ATTRIBUTE_EVIDENCE_VERSION='recommendation-refinement-evidence-1.2.0'
FIELDS={'version','policy_version','policy_sha256','root_id','parent_id','ordinal',
    'request_fingerprint_version','canonical_action','excluded_categories','compatibility_scope_sha256',
    'selection_scope_sha256','garment_snapshot_sha256','preference_snapshot_sha256','request_sha256',
    'root_R','root_total','base_signature_sha256','seen_count','seen_sha256','mode','total_vs_root'}


def bounded_provenance(value, *, draft=False):
    if type(value) is dict and 'palette_compatibility' in value:
        from app.application.recommendation.palette_compatibility_codec import bounded_provenance as bounded_c2
        return bounded_c2(value)
    if type(value) is dict and 'attribute_preference' in value:
        from app.application.recommendation.attribute_preference_codec import bounded_provenance as bounded_p2
        return bounded_p2(value)
    if type(value) is dict and 'attribute_selection' in value:
        from app.domain.value_objects.attribute_selection_evidence import bounded_provenance as bounded_attribute
        return bounded_attribute(value)
    if type(value) is dict and type(value.get('refinement')) is dict and value['refinement'].get('version')==ATTRIBUTE_EVIDENCE_VERSION:
        raise ValueError('Attribute refinement requires its immutable selection sidecar.')
    text=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
    refinement=value.get('refinement') if type(value) is dict else None
    limit=327680 if draft or type(refinement) is dict and refinement.get('version') in (EVIDENCE_VERSION,WEARER_EVIDENCE_VERSION) else 262144
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


def finalize_supplement(plan,identifier,action,score,relative,garment_hash,preference_hash,request_hash,wearer=None):
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
    if wearer is not None:
        from app.application.recommendation.wearer_identity import wearer_scope
        if plan.wearer_profile_id!=wearer.profile_id:raise ValueError('Draft wearer mismatch.')
        data.update(version=WEARER_EVIDENCE_VERSION,request_fingerprint_version=3,
            wearer_profile_id=wearer.profile_id,wearer_scope_sha256=wearer_scope(wearer.account_id,wearer.profile_id,plan.compatibility_scope_sha256))
    if plan.attribute_intent is not None:
        if wearer is None:raise ValueError('Attribute refinement requires captured wearer.')
        data.update(version=ATTRIBUTE_EVIDENCE_VERSION,request_fingerprint_version=4,
            attribute_intent_sha256=plan.attribute_intent.sha256,description_collection_sha256=plan.description_collection_sha256,
            attribute_scope_sha256=plan.attribute_scope_sha256)
    data['selection_scope_sha256']=selection_digest(plan.compatibility_scope_sha256,root,plan.parent_id,
        plan.ordinal,plan.mode,data['root_R'],data['seen_sha256'],len(plan.seen))
    if plan.preference_profile is not None:
        from app.domain.value_objects.recommendation_refinement import preference_selection_digest
        data.update(version='recommendation-refinement-evidence-2.0.0',request_fingerprint_version=5,
            preference_profile=plan.preference_profile,attribute_preference_sha256=plan.attribute_preference_sha256,
            attribute_preference_scope_sha256=plan.attribute_preference_scope_sha256)
        data['selection_scope_sha256']=preference_selection_digest(data['selection_scope_sha256'],plan.preference_profile,plan.attribute_preference_sha256,plan.attribute_preference_scope_sha256)
    if plan.compatibility_profile is not None:
        data.update(base_version=data['version'],base_request_fingerprint_version=data['request_fingerprint_version'],
            version='recommendation-refinement-evidence-3.0.0',request_fingerprint_version=6,
            compatibility_profile=plan.compatibility_profile,palette_collection_sha256=plan.palette_collection_sha256)
    relative['selection_scope_sha256']=data['selection_scope_sha256']
    return data


def validate_refinement(data,relative,score,identifier,request_text,request_payload,candidate=None,*,user_id=None,wearer_profile_id=None):
    if type(data) is dict and data.get('version')=='recommendation-refinement-evidence-3.0.0':
        from app.application.recommendation.palette_compatibility_verifier import validate_refinement as validate_c2
        return validate_c2(data,relative,score,identifier,request_text,request_payload,candidate,user_id=user_id,wearer_profile_id=wearer_profile_id)
    if type(data) is dict and data.get('version')=='recommendation-refinement-evidence-2.0.0':
        from app.domain.value_objects.recommendation_refinement import preference_selection_digest
        from app.domain.value_objects.attribute_preferences import PROFILE
        extra={'preference_profile','attribute_preference_sha256','attribute_preference_scope_sha256'}
        attribute='attribute_intent_sha256' in data
        expected=FIELDS|{'wearer_profile_id','wearer_scope_sha256'}|extra
        if attribute:expected|={'attribute_intent_sha256','description_collection_sha256','attribute_scope_sha256'}
        if set(data)!=expected or data['preference_profile']!=PROFILE or data['request_fingerprint_version']!=5 or relative.get('version')!='context-relevance-evidence-2.0.0':raise ValueError('Invalid P2 refinement schema/version.')
        for key in ('attribute_preference_sha256','attribute_preference_scope_sha256'):require_digest(data[key])
        base=selection_digest(data['compatibility_scope_sha256'],data['root_id'],data['parent_id'],data['ordinal'],data['mode'],data['root_R'],data['seen_sha256'],data['seen_count'])
        if data['selection_scope_sha256']!=preference_selection_digest(base,PROFILE,data['attribute_preference_sha256'],data['attribute_preference_scope_sha256']) or relative['selection_scope_sha256']!=data['selection_scope_sha256']:
            raise ValueError('P2 refinement selection scope mismatch.')
        old={k:v for k,v in data.items() if k not in extra};old.update(version=ATTRIBUTE_EVIDENCE_VERSION if attribute else WEARER_EVIDENCE_VERSION,request_fingerprint_version=4 if attribute else 3,selection_scope_sha256=base)
        ranking={**relative,'version':'context-relevance-evidence-1.3.0' if attribute else 'context-relevance-evidence-1.2.0','selection_scope_sha256':base}
        return validate_refinement(old,ranking,score,identifier,request_text,request_payload,candidate,user_id=user_id,wearer_profile_id=wearer_profile_id)
    attribute=type(data) is dict and data.get('version')==ATTRIBUTE_EVIDENCE_VERSION
    new=type(data) is dict and data.get('version') in (WEARER_EVIDENCE_VERSION,ATTRIBUTE_EVIDENCE_VERSION)
    fields=FIELDS|{'wearer_profile_id','wearer_scope_sha256'} if new else FIELDS
    if attribute:fields=fields|{'attribute_intent_sha256','description_collection_sha256','attribute_scope_sha256'}
    if type(data) is not dict or set(data)!=fields or data['version'] not in (EVIDENCE_VERSION,WEARER_EVIDENCE_VERSION,ATTRIBUTE_EVIDENCE_VERSION):
        raise ValueError('Exact archived refinement schema required.')
    if len(json.dumps(data,separators=(',',':'),ensure_ascii=True).encode())>(36864 if attribute else 32768):
        raise RelativeEncodingLimit('Refinement supplement exceeds 32 KiB.')
    if (data['policy_version'],data['policy_sha256'])!=ARCHIVED_POLICY:
        raise ValueError('Unsupported archived refinement policy.')
    for key in fields:
        if key.endswith('_sha256'):require_digest(data[key])
    if new:
        from app.application.recommendation.wearer_identity import wearer_scope
        canonical_uuid(data['wearer_profile_id'])
        if user_id is None or wearer_profile_id!=data['wearer_profile_id'] or data['wearer_scope_sha256']!=wearer_scope(user_id,wearer_profile_id,data['compatibility_scope_sha256']):
            raise ValueError('Archived wearer scope mismatch.')
    if attribute and (relative.get('version')!='context-relevance-evidence-1.3.0' or relative.get('attribute_scope_sha256')!=data['attribute_scope_sha256']):
        raise ValueError('Attribute refinement/ranking scope mismatch.')
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
    if type(data['request_fingerprint_version']) is not int or data['request_fingerprint_version']!=(4 if attribute else 3 if new else 2 if action is not None else 1) or ordinal and action is None:
        raise ValueError('Fingerprint contract mismatch.')
    floor,total=read_ratio(data['root_R']),read_ratio(data['root_total'])
    if not 0<=floor<=1 or not 0<=total<=1 or score.request_match.contribution<floor or score.total>total:
        raise ValueError('Original floor or total violated.')
    if not ordinal and (floor!=score.request_match.contribution or total!=score.total):
        raise ValueError('Root score mismatch.')
    if data['total_vs_root']!=('same' if score.total==total else 'lower'):
        raise ValueError('False total comparison.')
    if relative['version']!=('context-relevance-evidence-1.3.0' if attribute else 'context-relevance-evidence-1.2.0') or relative['selection_mode']!='best_evidenced_with_coverage_v1':
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
