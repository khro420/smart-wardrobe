"""Closed archived proof validation, independent of current parser/feature flags."""
from fractions import Fraction
import json
from app.domain.value_objects.garment_only_refinement import KEY,VERSION,step_key
from app.domain.value_objects.recommendation_refinement import digest,canonical_uuid,canonical_categories
from app.domain.value_objects.context_relevance import ratio,read_ratio,require_digest
FIELDS={'version','policy_sha256','root_id','parent_id','ordinal','root_R','root_total','selected_base','seen_sha256','mode','excluded_categories','compatibility_scope_sha256','selection_scope_sha256','garment_snapshot_sha256','preference_snapshot_sha256','request_sha256','bindings_sha256','score_sha256','profile_id','user_id','attribute_intent_sha256','description_collection_sha256','attribute_scope_sha256','preference_profile','attribute_preference_sha256','attribute_preference_scope_sha256','compatibility_profile','palette_collection_sha256'}
FIELDS=FIELDS|{'structured_request'}
BINDINGS=('attribute_selection','attribute_base_scope_sha256','attribute_preference','palette_compatibility','intended_wearer','wearer_category_eligibility','garment_wording')

def bindings(provenance):return digest({k:provenance.get(k) for k in BINDINGS})
def score_digest(score):
    from app.application.recommendation.decision_score_codec import score_to_json
    return digest(json.loads(score_to_json(score)))

def finalize(draft,identifier,score,candidate,provenance,user,profile):
    from app.application.recommendation.refinement_selector import base_signature
    from app.application.recommendation.garment_only_refinement_policy import RESOURCE_SHA256
    p=draft.plan
    proof={'version':VERSION,'policy_sha256':RESOURCE_SHA256,'root_id':p.root_id or identifier,'parent_id':p.parent_id,'ordinal':p.ordinal,'root_R':ratio(p.root_R if p.ordinal else Fraction(0)),
        'root_total':ratio(p.root_total if p.ordinal else score.total),'selected_base':[list(pair) for pair in base_signature(candidate)],'seen_sha256':digest(p.seen),'mode':p.mode,'excluded_categories':list(p.exclusions),
        'compatibility_scope_sha256':p.compatibility_scope_sha256,'selection_scope_sha256':p.selection_scope_sha256,'garment_snapshot_sha256':draft.garment_snapshot_sha256,'preference_snapshot_sha256':draft.preference_snapshot_sha256,'request_sha256':draft.request_sha256,
        'bindings_sha256':bindings(provenance),'score_sha256':score_digest(score),'profile_id':profile,'user_id':user}
    for name in ('attribute_intent_sha256','description_collection_sha256','attribute_scope_sha256','preference_profile','attribute_preference_sha256','attribute_preference_scope_sha256','compatibility_profile','palette_collection_sha256'):
        proof[name]=p.attribute_intent.sha256 if name=='attribute_intent_sha256' else getattr(p,name)
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
    proof['structured_request']=StructuredOutfitRequest().to_dict()
    return proof

def validate(record):
    from app.application.recommendation.decision_score_codec import score_from_json
    from app.application.recommendation.attribute_selection_verifier import validate_selection
    from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
    from app.domain.value_objects.intended_wearer import validate_wearer_evidence
    from app.application.recommendation.garment_only_refinement_policy import RESOURCE_SHA256
    p=record['provenance'];proof=p[KEY];user=record['user_id'];profile=record['profile_id']
    if type(proof) is not dict or set(proof)!=FIELDS or proof['version']!=VERSION or proof['policy_sha256']!=RESOURCE_SHA256:raise ValueError('Unknown garment lineage proof.')
    if len(json.dumps(proof).encode())>8192:raise ValueError('Oversized garment proof.')
    for name in ('root_id','profile_id'):canonical_uuid(proof[name])
    if type(proof['user_id']) is not str or not proof['user_id'].strip() or len(proof['user_id'])>200:raise ValueError('Invalid owned account identity.')
    if proof['parent_id'] is not None:canonical_uuid(proof['parent_id'])
    if proof['user_id']!=user or proof['profile_id']!=profile:raise ValueError('Garment proof ownership mismatch.')
    index=proof['ordinal']
    if type(index) is not int or not 0<=index<=9 or bool(index)!=(proof['parent_id'] is not None) or not index and proof['root_id']!=record['id']:raise ValueError('Invalid garment chain identity.')
    if tuple(proof['excluded_categories'])!=canonical_categories(proof['excluded_categories']):raise ValueError('Noncanonical exclusions.')
    for name in ('compatibility_scope_sha256','selection_scope_sha256','garment_snapshot_sha256','preference_snapshot_sha256','request_sha256','bindings_sha256','score_sha256','seen_sha256'):require_digest(proof[name])
    score=score_from_json(json.dumps(record['score_metadata']))
    if score.weights!=(Fraction(3,5),Fraction(1,5),Fraction(1,5)) or score.request_match.summary.state!='NotApplicable' or score.request_match.summary.value is not None or score.request_match.contribution!=0 or read_ratio(proof['root_R'])!=0:raise ValueError('Garment continuation changed R/math.')
    if proof['score_sha256']!=score_digest(score) or proof['bindings_sha256']!=bindings(p):raise ValueError('Stored garment evidence/score changed.')
    if proof['mode']!='garment_contribution_floor_base_distinct_v1' or 'refinement' in p or 'context_relevance' in p:raise ValueError('Mixed context/garment lineage.')
    evidence=validate_selection(p['attribute_selection'],user,profile,p['attribute_base_scope_sha256'],record.get('items')).to_dict()
    intent=AttributeIntent.from_dict(evidence['intent'])
    if intent.to_dict()['original_text']!=record['request_text'] or proof['attribute_intent_sha256']!=intent.sha256 or proof['attribute_scope_sha256']!=evidence['attribute_scope_sha256'] or proof['description_collection_sha256']!=evidence['description_collection_sha256'] or p['attribute_base_scope_sha256']!=proof['compatibility_scope_sha256']:raise ValueError('Garment intent/scope mismatch.')
    validate_wearer_evidence(p.get('intended_wearer'),user,profile)
    if 'wearer_category_eligibility' in p:
        from app.domain.value_objects.wearer_category_eligibility import validate_evidence
        validate_evidence(p['wearer_category_eligibility'],user,profile,record.get('items') or ())
    if 'garment_wording' in p:
        from app.application.nlp.garment_wording_guidance import validate as validate_wording
        validate_wording(p['garment_wording'],record['request_text'],intent)
    request=json.loads(record['extracted_entities_json']) if 'extracted_entities_json' in record else p.get('palette_compatibility',{}).get('request') or p.get('attribute_preference',{}).get('ledger',{}).get('request') or proof['structured_request']
    if request!=proof['structured_request']:raise ValueError('Changed captured structured request.')
    if request is not None and (set(request)!=set(('intent','occasion','style','colours','garment_categories','formality')) or request['intent']!='outfit_recommendation' or any(request[k] is not None for k in ('occasion','style','colours','garment_categories','formality'))):raise ValueError('Garment continuation requires a pure request.')
    if request is not None:
        from app.application.recommendation.refinement_verifier import request_digest
        if request_digest(record['request_text'],request,proof['excluded_categories'])!=proof['request_sha256']:raise ValueError('Changed garment request.')
    signature=tuple(tuple(pair) for pair in proof['selected_base'])
    if tuple(pair[0] for pair in signature) not in (('upper','lower'),('one_piece',)) or any(len(pair)!=2 or type(pair[1]) is not str for pair in signature):raise ValueError('Invalid selected base.')
    if record.get('items') is not None:
        actual=tuple((m['garment_role'],m['garment_id']) for m in record['items'] if m['garment_role']!='outerwear')
        if actual!=signature or any(m['category'] in proof['excluded_categories'] for m in record['items']):raise ValueError('Stored selected members changed.')
    for key,mode in (('attribute_preference','preference_profile'),('palette_compatibility','compatibility_profile')):
        if (key in p)!=(proof[mode] is not None):raise ValueError('Garment captured mode changed.')
    if 'attribute_preference' in p:
        from app.application.recommendation.attribute_preference_verifier import validate as validate_p2
        validate_p2(p['attribute_preference'],score,user,profile,conditions=intent.conditions,items=record.get('items'),request_text=record['request_text'],exclusions=proof['excluded_categories'])
        if digest(p['attribute_preference']['snapshot'])!=proof['attribute_preference_sha256'] or p['attribute_preference']['scope']['preference_scope_sha256']!=proof['attribute_preference_scope_sha256']:raise ValueError('P2 capture changed.')
    if 'palette_compatibility' in p:
        from app.application.recommendation.palette_compatibility_verifier import validate_archive
        validate_archive(p['palette_compatibility'],score,user,profile,items=record.get('items'),request_text=record['request_text'])
        if p['palette_compatibility']['collection_sha256']!=proof['palette_collection_sha256']:raise ValueError('C2 source capture changed.')
    return signature

def descriptor(record):
    validate(record);p=record['provenance'][KEY];index=p['ordinal']
    action={'submission_key':step_key(p['root_id'],index+1),'refinement':{'version':'assistant-refinement-request-1.0.0','kind':'alternative','parent_recommendation_id':record['id']}} if index<9 else None
    if action is not None:
        for key in ('preference_profile','compatibility_profile'):
            if p[key] is not None:action[key]=p[key]
    return {'version':'garment-only-continuation-display-1.0.0','root_id':p['root_id'],'parent_id':p['parent_id'],'ordinal':index,'excluded_categories':p['excluded_categories'],'root_R':p['root_R'],'root_total':p['root_total'],'limit_reached':index==9,'next_action':action,'mode':p['mode']}
