"""Disjoint opt-in P1/C1 workflow and proof. No legacy proof is reinterpreted."""
from dataclasses import dataclass,asdict
from fractions import Fraction
from types import SimpleNamespace
import json,uuid
from app.domain.value_objects.attribute_conditions import encode,decode,digest,exact,AttributeRequestError
from app.application.nlp.compositional_request_v1 import CompositionalIntent,base_parse
from app.domain.value_objects.request_local_selection import LocalSelectionProof,MAX_PROOF
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.domain.value_objects.intended_wearer import IntendedWearer
from app.domain.value_objects.recommendation_persistence import PersistenceConflict,WardrobeChanged
from app.application.recommendation.request_local_soft_workflow import InternalLocalPreferenceWorkflow,resource_identities
from app.application.recommendation.request_local_selection_verifier import restore_sources,IndependentStructural
from app.application.recommendation.request_local_selection_engine import public_scorers,public_score,LocalSelectionUnavailable,FrozenQuery
from app.application.recommendation.request_local_bounded_ranking import CompletedLedger
from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.application.recommendation.decision_score_codec import score_to_json,score_from_json
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot

KEY='compositional_selection'
VERSION='compositional-selection-proof-1.0.0'
INPUTS_VERSION='compositional-selection-inputs-1.0.0'
COMMON=('owner_id','wearer','attribute_policy','sources','preferences','source_revisions','eligibility','resources')

def resources(mode):
    from app.domain.value_objects.request_local_selection import POLICY
    value=resource_identities()
    return {**value,'ranking':'compositional-p1-c1-1.0.0','optional_policy':dict(POLICY) if mode=='soft' else None}

@dataclass(frozen=True)
class CompositionalProof:
    payload:bytes
    def __post_init__(self):
        v=decode(self.payload,MAX_PROOF);exact(v,('version','mode','intent','evaluation','revision'))
        if v['version']!=VERSION or v['mode'] not in ('ordinary','soft') or v['revision']!=digest({**v,'revision':''}):raise ValueError('Invalid compositional proof.')
        data=CompositionalIntent(encode(v['intent'])).to_dict()
        if (data['optional'] is not None)!=(v['mode']=='soft') or 'context' in data['request']:raise ValueError('Compositional mode/context mismatch.')
        exact(v['evaluation'],('version',*COMMON,'decision'))
        if v['evaluation']['version']!=INPUTS_VERSION:raise ValueError('Unknown compositional evaluation.')
        if type(v['evaluation']['preferences']) is not list or len(v['evaluation']['preferences'])>100:raise ValueError('Unbounded compositional preference scope.')
    def to_dict(self):return decode(self.payload,MAX_PROOF)
    def inputs(self):
        from app.domain.value_objects.request_local_source_codec import unpack_sources
        v=self.to_dict()['evaluation']
        return {**{k:v[k] for k in COMMON},'sources':unpack_sources(v['sources'])}

def verify(proof,owner,profile,*,text=None,score=None,items=None):
    from app.application.recommendation.compositional_selection_v1 import select
    if type(proof) is not CompositionalProof:raise ValueError('Typed compositional proof required.')
    v=proof.to_dict();intent=CompositionalIntent(encode(v['intent']));source=proof.inputs();wearer=IntendedWearer(**source['wearer'])
    if wearer.account_id!=owner or wearer.profile_id!=profile or source['owner_id']!=owner or text is not None and text!=intent.raw:raise ValueError('Compositional ownership/raw-text mismatch.')
    if source['resources']!=resources(v['mode']):raise ValueError('Unregistered compositional resources/budgets.')
    policy=AttributeEvidencePolicy(encode(source['attribute_policy']));rows=restore_sources(source)
    if policy.snapshot()!=AttributeEvidencePolicy.load().snapshot():raise ValueError('Compositional qualification policy binding mismatch.')
    revisions=source['source_revisions'];exact(revisions,('profile','details','preferences'));p=revisions['profile'];d=revisions['details']
    if p['id']!=profile or p['user_id']!=owner or p['status']!='active' or p['name']!=wearer.name_at_request or d['profile_id']!=profile or d['revision']!=source['eligibility']['details_revision'] or d['version']!='wearer-profile-details-1.0.0' or d['gender_identity'].strip().casefold()!=source['eligibility']['gender_key']:raise ValueError('Compositional profile mismatch.')
    preferences=tuple(PreferenceSnapshot(**p) for p in source['preferences'])
    expected=[PreferenceSnapshot(p['id'],owner,p['preference_type'],p['preference_value_json'],None if p['weight'] is None else str(p['weight']),p['source'],bool(p['is_active'])) for p in revisions['preferences']]
    if encode([asdict(p) for p in expected])!=encode(source['preferences']) or any(p['user_id']!=owner or p['profile_id']!=profile or p['is_active']!=1 for p in revisions['preferences']):raise ValueError('Compositional preference revision mismatch.')
    candidate,actual,decision=select(owner,intent,rows,preferences,'reference',wearer_scope=profile,independent=True,policy=policy)
    if decision!=v['evaluation']['decision']:raise ValueError('Independent compositional winner/complete ledger mismatch.')
    if score is not None and score_to_json(score)!=score_to_json(actual):raise ValueError('Compositional stored score mismatch.')
    if items is not None:
        wanted=[(m.garment.garment_id,m.role,m.item_order,m.garment.name,m.garment.category,m.garment.preferred_media_id) for m in candidate.members]
        if wanted!=[(m['garment_id'],m['garment_role'],m['item_order'],m['name'],m['category'],m['preferred_media_id']) for m in items]:raise ValueError('Compositional immutable item mismatch.')
    return candidate,actual


def fingerprint(proof):
    source=proof.inputs()
    return digest({'version':9,'owner_id':source['owner_id'],'profile_id':source['wearer']['profile_id'],'intent':proof.to_dict()['intent'],'mode':proof.to_dict()['mode'],'policy':'compositional_p1_c1_v1'})

def is_parent(repository,owner,identifier):
    conn=repository._connect()
    try:
        row=conn.execute('SELECT m.provenance_json FROM recommendation_metadata m JOIN recommendations r ON r.id=m.recommendation_id WHERE r.id=? AND r.user_id=?',(identifier,owner)).fetchone()
        return row is not None and KEY in json.loads(row['provenance_json'])
    finally:conn.close()

def receipt(repository,owner,body,header):
    if not body.submission_key:return None
    conn=repository._connect()
    try:
        conn.execute('BEGIN')
        if not conn.execute("SELECT 1 FROM users WHERE id=? AND account_status='active'",(owner,)).fetchone():raise ValueError('Active compositional owner required.')
        row=conn.execute("SELECT s.fingerprint,r.id,r.profile_id,m.provenance_json FROM recommendation_submissions s JOIN recommendations r ON r.id=s.recommendation_id AND r.user_id=s.user_id JOIN recommendation_metadata m ON m.recommendation_id=r.id WHERE s.user_id=? AND s.operation='assistant' AND s.submission_key=?",(owner,body.submission_key)).fetchone()
        if not row:return None
        saved=json.loads(row['provenance_json']).get(KEY)
        if saved is None:return None
        proof=CompositionalProof(encode(saved));intent=CompositionalIntent(encode(saved['intent']))
        if body.request_text!=intent.raw or any(p is not None and p!=row['profile_id'] for p in (body.wearer_profile_id,header)) or any(getattr(body,k) is not None for k in ('refinement','attribute_conditions','preference_profile','compatibility_profile')) or row['fingerprint']!=fingerprint(proof):raise PersistenceConflict('Compositional receipt raw/mode/wearer conflict.')
        return repository._read(conn,owner,row['id'],account_history=True)
    finally:conn.rollback();conn.close()

def read_record(record,identity_items,receipt_fingerprint):
    if set(record['provenance'])!={KEY}:raise ValueError('Compositional proof must be present in its closed namespace.')
    proof=CompositionalProof(encode(record['provenance'][KEY]));source=proof.inputs()
    wrapped=record['score_metadata'];exact(wrapped,('version','exact_score','proof_sha256'))
    if wrapped['version']!='compositional-score-metadata-1.0.0' or wrapped['proof_sha256']!=proof.to_dict()['revision'] or receipt_fingerprint!=fingerprint(proof):raise ValueError('Compositional score/proof/receipt binding mismatch.')
    record={**record,'score_metadata':wrapped['exact_score']}
    score=score_from_json(json.dumps(record['score_metadata']))
    for name,component in zip(('request_match_score','compatibility_score','preference_score'),(score.request_match,score.compatibility,score.preference)):
        if record[name]!=(None if component.summary.value is None else float(component.summary.value)):raise ValueError('Compositional stored scalar contradicts exact score.')
    if record['total_score']!=float(score.total):raise ValueError('Compositional stored total contradicts exact score.')
    verify(proof,record['user_id'],record['profile_id'],text=record['request_text'],score=score,items=identity_items)
    return {**record,'intended_wearer':IntendedWearer(**source['wearer']).evidence(),'wearer_intent_state':'captured'}

def display(record):
    from app.application.recommendation.scoring_display import display_for_record
    from app.domain.value_objects.request_local_selection import POLICY
    proof=CompositionalProof(encode(record['provenance'][KEY]));value=proof.to_dict();intent=value['intent']
    verify(proof,record['user_id'],record['profile_id'],text=record['request_text'],score=score_from_json(json.dumps(record['score_metadata'])))
    if value['mode']=='soft':
        inner={'version':'request-local-preference-display-1.0.0','kind':'RequestLocalPreference','profile':POLICY['version'],
            'grammar_version':intent['grammar_version'],'mandatory_request':intent['request'],'hard_intent':intent['hard_intent'],
            'optional_intent':intent['optional'],'decision':value['evaluation']['decision'],'budgets':dict(POLICY),
            'continuation_available':False,'continuation_reason':'soft_continuation_not_implemented'}
    else:inner=asdict(display_for_record({**record,'provenance':{'scoring_profile':record['score_metadata']['profile_name']}}))
    return {**record,'scoring_display':inner,'input_normalization':{'version':'compositional-input-display-1.0.0',
        'grammar_version':intent['grammar_version'],'normalized_text':intent['normalization']['normalized_text'],
        'hard_conditions':intent['hard_intent']['conditions'] if intent['hard_intent'] else None,
        'original_hard_spans':intent['original_hard_spans'],'original_optional_spans':intent['original_optional_spans']}}

class CompositionalWorkflow:
    def __init__(self,repository,engine):
        from app.application.nlp.compositional_request_v1 import identity
        self.grammar=identity();self.repository,self.engine=repository,engine
        from app.domain.value_objects.request_local_source_codec import VERSION as codec
        self.capture_workflow=InternalLocalPreferenceWorkflow(source_codec=codec)

    def prepare(self,owner,profile_id,intent):
        from app.infrastructure.persistence.postgresql_repository import utcnow
        from app.application.wardrobe.profile_service import require_active_profile
        from app.domain.value_objects.request_local_source_codec import VERSION as codec,pack_sources
        from app.application.recommendation.compositional_selection_v1 import select
        if type(intent) is not CompositionalIntent:raise ValueError('Typed compositional intent required.')
        conn=self.repository._connect()
        try:
            conn.execute('BEGIN');profile=require_active_profile(conn,owner,profile_id);wearer=IntendedWearer(owner,profile_id,profile['name'],'explicit',utcnow())
            scope,sources,preferences=self.capture_workflow.capture(conn,owner,wearer,source_codec=codec)
            revisions=self.capture_workflow.source_revisions(conn,owner,wearer)
        finally:conn.rollback();conn.close()
        data=intent.to_dict();mode='soft' if data['optional'] else 'ordinary'
        _,_,decision=select(owner,intent,scope.usable_descriptions,preferences,self.engine,wearer_scope=profile_id)
        evaluation={'version':INPUTS_VERSION,'owner_id':owner,'wearer':asdict(wearer),'attribute_policy':AttributeEvidencePolicy.load().snapshot(),
            'sources':pack_sources(sources),'preferences':[asdict(p) for p in preferences],'source_revisions':revisions,'eligibility':scope.eligibility.to_dict(),'resources':resources(mode),'decision':decision}
        value={'version':VERSION,'mode':mode,'intent':data,'evaluation':evaluation,'revision':''};value['revision']=digest(value)
        proof=CompositionalProof(encode(value));verify(proof,owner,profile_id,text=intent.raw)
        return proof

    def persist(self,owner,profile_id,intent,key,proof):
        from app.infrastructure.persistence.postgresql_repository import utcnow
        from app.application.wardrobe.profile_service import require_active_profile
        from app.domain.value_objects.request_local_source_codec import VERSION as codec
        if type(intent) is not CompositionalIntent or type(proof) is not CompositionalProof:raise ValueError('Typed compositional intent/proof required.')
        if not key:raise AttributeRequestError('InvalidInput','submission_key_required')
        source=proof.inputs();wearer=IntendedWearer(**source['wearer']);conn=self.repository._connect()
        try:
            conn.execute('BEGIN IMMEDIATE')
            if not conn.execute("SELECT 1 FROM users WHERE id=? AND account_status='active'",(owner,)).fetchone():raise ValueError('Active compositional owner required.')
            prior=conn.execute("SELECT fingerprint,recommendation_id FROM recommendation_submissions WHERE user_id=? AND operation='assistant' AND submission_key=?",(owner,key)).fetchone()
            if prior:
                if prior['fingerprint']!=fingerprint(proof):raise PersistenceConflict('Compositional submission conflict.')
                return self.repository._read(conn,owner,prior['recommendation_id'],account_history=True),True
            require_active_profile(conn,owner,profile_id)
            if source['owner_id']!=owner or wearer.profile_id!=profile_id or proof.to_dict()['intent']!=intent.to_dict():raise ValueError('Compositional writer identity mismatch.')
            self.repository.checkpoint('compositional_before_revalidation',conn)
            scope,sources,preferences=self.capture_workflow.capture(conn,owner,wearer,source_codec=codec)
            if encode(sources)!=encode(source['sources']) or encode([asdict(p) for p in preferences])!=encode(source['preferences']) or scope.eligibility.to_dict()!=source['eligibility'] or source['source_revisions']!=self.capture_workflow.source_revisions(conn,owner,wearer) or source['resources']!=resources(proof.to_dict()['mode']) or source['attribute_policy']!=AttributeEvidencePolicy.load().snapshot():raise WardrobeChanged('Compositional complete source/settings scope changed.')
            # Fresh independent raw->compositional interpretation and complete winner
            # reconstruction run while locked; no first-pass result is trusted.
            candidate,score=verify(CompositionalProof(proof.payload),owner,profile_id,text=intent.raw)
            self.repository.checkpoint('compositional_revalidated',conn)
            identifier,chat,now=str(uuid.uuid4()),str(uuid.uuid4()),utcnow()
            conn.execute("INSERT INTO nlp_chats(id,user_id,profile_id,request_text,interpreted_intent,extracted_entities_json,status,created_at,completed_at) VALUES(?,?,?,?,?,?,'completed',?,?)",(chat,owner,profile_id,intent.raw,'outfit_recommendation',json.dumps(intent.to_dict()['request']),now,now));self.repository.checkpoint('chat',conn)
            values=[float(c.summary.value) if c.summary.value is not None else None for c in (score.request_match,score.compatibility,score.preference)]+[float(score.total)]
            conn.execute("INSERT INTO recommendations(id,user_id,profile_id,chat_id,recommendation_type,status,created_at,expires_at,request_match_score,compatibility_score,preference_score,total_score) VALUES(?,?,?,?,'assistant','available',?,NULL,?,?,?,?)",(identifier,owner,profile_id,chat,now,*values));self.repository.checkpoint('recommendation',conn)
            for m in candidate.members:
                conn.execute('INSERT INTO recommendation_items VALUES(?,?,?,?,?)',(identifier,m.garment.garment_id,m.role,m.item_order,now));self.repository.checkpoint('item',conn)
                conn.execute('INSERT INTO recommendation_item_snapshots VALUES(?,?,?)',(identifier,m.garment.garment_id,json.dumps({'name':m.garment.name,'category':m.garment.category,'preferred_media_id':m.garment.preferred_media_id})));self.repository.checkpoint('snapshot',conn)
            wire_score={'version':'compositional-score-metadata-1.0.0','exact_score':json.loads(score_to_json(score)),'proof_sha256':proof.to_dict()['revision']}
            conn.execute('INSERT INTO recommendation_metadata VALUES(?,?,?)',(identifier,json.dumps({KEY:proof.to_dict()}),json.dumps(wire_score)));self.repository.checkpoint('metadata',conn)
            conn.execute('INSERT INTO recommendation_submissions VALUES(?,?,?,?,?)',(owner,'assistant',key,fingerprint(proof),identifier));self.repository.checkpoint('submission',conn)
            result=self.repository._read(conn,owner,identifier,eligible={r.garment_id for r in scope.usable_rows},account_history=True)
            self.repository.checkpoint('before_commit',conn);conn.commit()
            return result,False
        except BaseException:conn.rollback();raise
        finally:conn.close()

    def recommend(self,owner,body,wearer):
        from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
        try:
            if body.refinement is not None:return {'status':'RefinementUnavailable','complete':False}
            if any(getattr(body,k) is not None for k in ('attribute_conditions','preference_profile','compatibility_profile')):raise AttributeRequestError('UnsupportedRequest','compositional_profile_scope_unavailable')
            intent=CompositionalIntent.capture(body.request_text)
            if 'context' in intent.to_dict()['request']:
                context=intent.to_dict()['request']['context']
                situations=context.get('situation',{}).get('values',[])
                if any('interview' in x or 'wedding' in x for x in situations) and context.get('role',{}).get('state')=='Unspecified':
                    raise AttributeRequestError('UnsupportedRequest','compositional_context_role_required')
                # Previously supported raw contexts retain their original path.
                # Repaired/new contextual clauses require a separate proof.
                def meaning(v):
                    if isinstance(v,dict):return {k:meaning(x) for k,x in v.items() if k not in ('original_text','spans')}
                    if isinstance(v,list):return [meaning(x) for x in v]
                    return v
                try:old=base_parse(body.request_text)
                except AttributeRequestError:raise AttributeRequestError('UnsupportedRequest','compositional_context_contract_unavailable')
                old_hard=old['hard']['conditions'] if old['hard'] else None
                new_hard=intent.to_dict()['hard_intent']
                if meaning(old['request'])!=meaning(intent.to_dict()['request']) or old_hard!=(new_hard['conditions'] if new_hard else None):raise AttributeRequestError('UnsupportedRequest','compositional_context_contract_unavailable')
                return None
            proof=self.prepare(owner,wearer.profile_id,intent)
            saved,replayed=self.persist(owner,wearer.profile_id,intent,body.submission_key,proof)
            return OutfitAssistantService._success(saved,replayed,{})
        except LocalSelectionUnavailable as error:
            optional=intent.to_dict()['optional']
            resolution=optional['resolution']['state'] if optional else None
            result={'status':error.status,'complete':True,'mandatory':asdict(error.completion)}
            if optional:result['optional_resolution']=resolution
            if error.status=='InsufficientEvidence':
                result['context_reason']='hard_evidence_unknown_conflicting_preference' if resolution=='ContradictedByHard' else 'required_garment_description_unknown'
            return result
        except AttributeRequestError as error:return {'status':error.status,'complete':False,'context_reason':error.reason}
        except PersistenceConflict:return {'status':'IdempotencyConflict','complete':False}
        except WardrobeChanged:return {'status':'WardrobeChanged','complete':False}
        except __import__('fastapi').HTTPException:raise
        except Exception as error:
            from app.application.recommendation.failure_diagnostics import log_failure
            log_failure('assistant','compositional_workflow','PersistenceFailure',error)
            return {'status':'PersistenceFailure','complete':False}
