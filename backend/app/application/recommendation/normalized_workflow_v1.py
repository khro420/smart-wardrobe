"""Disjoint opt-in P1/C1 workflow and proof. No legacy proof is reinterpreted."""
from dataclasses import dataclass,asdict
from fractions import Fraction
from types import SimpleNamespace
import json,uuid
from app.domain.value_objects.attribute_conditions import encode,decode,digest,exact,AttributeRequestError
from app.application.nlp.normalized_request_v1 import NormalizedIntent,base_parse
from app.domain.value_objects.request_local_selection import LocalSelectionProof,MAX_PROOF
from app.domain.value_objects.request_local_preference import RequestLocalPreferenceIntent
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

KEY='normalized_selection'
VERSION='normalized-selection-proof-1.0.0'
INPUTS_VERSION='normalized-ordinary-inputs-1.0.0'
COMMON=('owner_id','wearer','attribute_policy','sources','preferences','source_revisions','eligibility','resources')

def resources(mode):
    value=resource_identities()
    return {**value,'ranking':'normalized-original-p1-c1-1.0.0'} if mode=='ordinary' else value

@dataclass(frozen=True)
class NormalizedProof:
    payload:bytes
    def __post_init__(self):
        v=decode(self.payload,MAX_PROOF);exact(v,('version','mode','intent','evaluation','revision'))
        if v['version']!=VERSION or v['mode'] not in ('ordinary','soft') or v['revision']!=digest({**v,'revision':''}):raise ValueError('Invalid normalized proof envelope.')
        intent=NormalizedIntent(encode(v['intent'])).to_dict()
        if (intent['local_intent'] is not None)!=(v['mode']=='soft'):raise ValueError('Normalized hard/soft mode mismatch.')
        if 'context' in intent['request']:raise ValueError('Context needs a separate normalized selection contract.')
        if v['mode']=='soft':
            inner=LocalSelectionProof(encode(v['evaluation']))
            if inner.to_dict()['intent']!=intent['local_intent']:raise ValueError('Normalized soft interpretation differs from inner proof.')
        else:
            exact(v['evaluation'],('version',*COMMON,'decision'))
            if v['evaluation']['version']!=INPUTS_VERSION:raise ValueError('Unknown normalized ordinary inputs.')
    def to_dict(self):return decode(self.payload,MAX_PROOF)
    def inputs(self):
        v=self.to_dict()
        if v['mode']=='soft':return {k:LocalSelectionProof(encode(v['evaluation'])).expanded_dict()[k] for k in COMMON}
        from app.domain.value_objects.request_local_source_codec import unpack_sources
        return {**{k:v['evaluation'][k] for k in COMMON},'sources':unpack_sources(v['evaluation']['sources'])}

def choose(points):
    # Existing scalar tie order: T, R, C, P descending, ordered UUID key ascending.
    return min(points,key=lambda item:(-item[1].total,-item[1].request_match.contribution,-item[1].compatibility.contribution,-item[1].preference.contribution,item[0].key))

def ordinary_first(owner,intent,rows,preferences,engine):
    from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
    from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions
    from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
    from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
    request=StructuredOutfitRequest(**intent['request']);policy=AttributeEvidencePolicy.load()
    hard=AttributeIntent.from_dict(intent['hard_intent']) if intent['hard_intent'] else None
    prepared=PreparedAttributeConditions.prepare(hard.conditions,rows,policy) if hard else None
    independent=IndependentAttributeVerifier.prepare(hard.conditions,rows,policy) if hard else None
    query=FrozenQuery(owner,[r.snapshot for r in rows]);scores={}
    if engine=='compact_exhaustive':
        from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
        from app.infrastructure.persistence.recommendation_repository_adapter import encode as legacy_encode
        audit=[];outcome=CompactExhaustiveScorer(query,SimpleNamespace(get_active_preferences=lambda who:preferences),attribute_context=prepared,attribute_verifier=independent,audit=audit.append).rank(owner,request)
        if not outcome.complete:raise ValueError('Incomplete normalized compact scope.')
        scores={tuple(tuple(k) for k in r['key']):score_from_json(legacy_encode(r['score'])) for r in audit if r['verified']}
    elif engine!='reference':raise ValueError('Unknown normalized execution engine.')
    stream=RequestCandidateEngine(query,attribute_context=prepared,attribute_verifier=independent).generate_candidates(owner,request)
    points=[];scorers=public_scorers(owner,preferences)
    try:
        gate=ScoringEligibilityGate(stream,owner,request)
        for item in stream:
            verified=gate.verify(item);score=public_score(verified,scorers) if engine=='reference' else scores.pop(verified.candidate.key)
            points.append((verified.candidate,score))
        r=stream.result;completion=CompletedLedger(r.examined,r.passed,r.failed,r.unknown,r.complete)
        if scores or not r.complete:raise ValueError('Normalized admission/score set mismatch.')
    finally:stream.close()
    if not points:raise LocalSelectionUnavailable(completion)
    candidate,score=choose(points)
    return candidate,score,{'selected_key':[list(k) for k in candidate.key],'score':json.loads(score_to_json(score)),'mandatory':asdict(completion)}

def verify(proof,owner,profile,*,text=None,score=None,items=None):
    from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
    from app.application.recommendation.request_candidate_session import RequestCandidateSession
    from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
    from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
    v=proof.to_dict();intent=NormalizedIntent(encode(v['intent']));source=proof.inputs();wearer=IntendedWearer(**source['wearer'])
    if wearer.account_id!=owner or wearer.profile_id!=profile or source['owner_id']!=owner or text is not None and text!=intent.raw:raise ValueError('Normalized request ownership/raw-text mismatch.')
    if v['mode']=='soft':
        from app.application.recommendation.request_local_selection_verifier import verify as old_verify
        _,candidate,actual=old_verify(LocalSelectionProof(encode(v['evaluation'])),owner,profile,text=intent.normalized,items=items,score=score)
    else:
        if source['resources']!=resources('ordinary'):raise ValueError('Unregistered normalized scoring resources.')
        policy=AttributeEvidencePolicy(encode(source['attribute_policy']));rows=restore_sources(source)
        revisions=source['source_revisions'];p=revisions['profile'];d=revisions['details']
        if p['id']!=profile or p['user_id']!=owner or p['status']!='active' or p['name']!=wearer.name_at_request or d['profile_id']!=profile or d['revision']!=source['eligibility']['details_revision'] or d['version']!='wearer-profile-details-1.0.0' or d['gender_identity'].strip().casefold()!=source['eligibility']['gender_key']:raise ValueError('Normalized source profile mismatch.')
        preferences=tuple(PreferenceSnapshot(**p) for p in source['preferences'])
        expected=[PreferenceSnapshot(p['id'],owner,p['preference_type'],p['preference_value_json'],None if p['weight'] is None else str(p['weight']),p['source'],bool(p['is_active'])) for p in revisions['preferences']]
        if encode([asdict(p) for p in expected])!=encode(source['preferences']) or any(p['user_id']!=owner or p['profile_id']!=profile or p['is_active']!=1 for p in revisions['preferences']):raise ValueError('Normalized preference revisions mismatch.')
        data=intent.to_dict();request=StructuredOutfitRequest(**data['request']);hard=AttributeIntent.from_dict(data['hard_intent']) if data['hard_intent'] else None
        facts=IndependentAttributeVerifier.prepare(hard.conditions,rows,policy) if hard else None
        session=RequestCandidateSession(IndependentStructural(rows),request,RequestConstraintEvaluator());points=[];failed=unknown=0;scorers=public_scorers(owner,preferences)
        try:
            gate=ScoringEligibilityGate(session,owner,request)
            for item in session:
                state=facts.decision(item.candidate.key) if facts else 'Pass'
                if state=='Fail':failed+=1;continue
                if state=='Unknown':unknown+=1;continue
                verified=gate.verify(item);points.append((verified.candidate,public_score(verified,scorers)))
            r=session.result
            completion=CompletedLedger(r.examined,len(points),r.failed+failed,r.unknown+unknown,r.complete)
        finally:session.close()
        if not points or not completion.complete:raise ValueError('No complete independently admitted normalized winner.')
        # Independent explicit scalar comparison rather than the first selector.
        candidate,actual=points[0]
        for c,s in points[1:]:
            a=(s.total,s.request_match.contribution,s.compatibility.contribution,s.preference.contribution)
            b=(actual.total,actual.request_match.contribution,actual.compatibility.contribution,actual.preference.contribution)
            if a>b or a==b and c.key<candidate.key:candidate,actual=c,s
        expected={'selected_key':[list(k) for k in candidate.key],'score':json.loads(score_to_json(actual)),'mandatory':asdict(completion)}
        if expected!=v['evaluation']['decision']:raise ValueError('Normalized independent winner/admission ledger mismatch.')
    if score is not None and score_to_json(score)!=score_to_json(actual):raise ValueError('Normalized stored score mismatch.')
    if items is not None:
        wanted=[(m.garment.garment_id,m.role,m.item_order,m.garment.name,m.garment.category,m.garment.preferred_media_id) for m in candidate.members]
        if wanted!=[(m['garment_id'],m['garment_role'],m['item_order'],m['name'],m['category'],m['preferred_media_id']) for m in items]:raise ValueError('Normalized immutable item mismatch.')
    return candidate,actual

def fingerprint(proof):
    source=proof.inputs()
    return digest({'version':8,'owner_id':source['owner_id'],'profile_id':source['wearer']['profile_id'],'intent':proof.to_dict()['intent'],'mode':proof.to_dict()['mode'],'policy':'normalized_p1_c1_v1'})

def receipt(repository,owner,body,header):
    if not body.submission_key:return None
    conn=repository._connect()
    try:
        conn.execute('BEGIN')
        if not conn.execute("SELECT 1 FROM users WHERE id=? AND account_status='active'",(owner,)).fetchone():raise ValueError('Active normalized owner required.')
        row=conn.execute("SELECT s.fingerprint,r.id,r.profile_id,m.provenance_json FROM recommendation_submissions s JOIN recommendations r ON r.id=s.recommendation_id AND r.user_id=s.user_id JOIN recommendation_metadata m ON m.recommendation_id=r.id WHERE s.user_id=? AND s.operation='assistant' AND s.submission_key=?",(owner,body.submission_key)).fetchone()
        if not row:return None
        saved=json.loads(row['provenance_json']).get(KEY)
        if saved is None:return None
        proof=NormalizedProof(encode(saved));intent=NormalizedIntent(encode(saved['intent']))
        if body.request_text!=intent.raw or any(p is not None and p!=row['profile_id'] for p in (body.wearer_profile_id,header)) or any(getattr(body,k) is not None for k in ('refinement','attribute_conditions','preference_profile','compatibility_profile')) or row['fingerprint']!=fingerprint(proof):raise PersistenceConflict('Normalized receipt raw/mode/wearer conflict.')
        return repository._read(conn,owner,row['id'],account_history=True)
    finally:conn.rollback();conn.close()

def read_record(record,identity_items,receipt_fingerprint):
    if set(record['provenance'])!={KEY}:raise ValueError('Normalized proof must be present in its closed namespace.')
    proof=NormalizedProof(encode(record['provenance'][KEY]));source=proof.inputs()
    wrapped=record['score_metadata'];exact(wrapped,('version','exact_score','proof_sha256'))
    if wrapped['version']!='normalized-score-metadata-1.0.0' or wrapped['proof_sha256']!=proof.to_dict()['revision'] or receipt_fingerprint!=fingerprint(proof):raise ValueError('Normalized score/proof/receipt binding mismatch.')
    record={**record,'score_metadata':wrapped['exact_score']}
    score=score_from_json(json.dumps(record['score_metadata']))
    for name,component in zip(('request_match_score','compatibility_score','preference_score'),(score.request_match,score.compatibility,score.preference)):
        if record[name]!=(None if component.summary.value is None else float(component.summary.value)):raise ValueError('Normalized stored scalar contradicts exact score.')
    if record['total_score']!=float(score.total):raise ValueError('Normalized stored total contradicts exact score.')
    verify(proof,record['user_id'],record['profile_id'],text=record['request_text'],score=score,items=identity_items)
    return {**record,'intended_wearer':IntendedWearer(**source['wearer']).evidence(),'wearer_intent_state':'captured'}

def display(record):
    from app.application.recommendation.scoring_display import local_preference_display,display_for_record
    proof=NormalizedProof(encode(record['provenance'][KEY]));value=proof.to_dict();intent=value['intent']
    verify(proof,record['user_id'],record['profile_id'],text=record['request_text'],score=score_from_json(json.dumps(record['score_metadata'])))
    if value['mode']=='soft':
        inner=local_preference_display({**record,'request_text':intent['normalization']['normalized_text'],'provenance':{'request_local_preference':value['evaluation']}})['scoring_display']
    else:inner=asdict(display_for_record({**record,'provenance':{'scoring_profile':record['score_metadata']['profile_name']}}))
    return {**record,'scoring_display':inner,'input_normalization':{'version':'normalized-input-display-1.0.0',
        'grammar_version':intent['grammar_version'],'normalized_text':intent['normalization']['normalized_text'],
        'hard_conditions':intent['hard_intent']['conditions'] if intent['hard_intent'] else None,
        'original_hard_spans':intent['original_hard_spans'],'original_optional_spans':intent['original_optional_spans']}}

class NormalizedWorkflow:
    def __init__(self,repository,engine):
        from app.application.nlp.normalized_request_v1 import identity
        self.grammar=identity();self.repository,self.engine=repository,engine
        from app.domain.value_objects.request_local_source_codec import VERSION as codec
        self.capture_workflow=InternalLocalPreferenceWorkflow(source_codec=codec)

    def prepare(self,owner,profile_id,intent):
        if type(intent) is not NormalizedIntent:raise ValueError('Typed normalized intent required.')
        data=intent.to_dict()
        if data['local_intent']:
            command=self.capture_workflow.prepare(self.repository,owner,profile_id,RequestLocalPreferenceIntent(encode(data['local_intent'])),'normalized-internal-preparation',engine=self.engine)
            mode='soft';evaluation=command.local_preference.proof.to_dict()
        else:
            from app.infrastructure.persistence.postgresql_repository import utcnow
            from app.application.wardrobe.profile_service import require_active_profile
            from app.domain.value_objects.request_local_source_codec import VERSION as codec,pack_sources
            conn=self.repository._connect()
            try:
                conn.execute('BEGIN');profile=require_active_profile(conn,owner,profile_id);wearer=IntendedWearer(owner,profile_id,profile['name'],'explicit',utcnow())
                scope,sources,preferences=self.capture_workflow.capture(conn,owner,wearer,source_codec=codec)
                revisions=self.capture_workflow.source_revisions(conn,owner,wearer)
            finally:conn.rollback();conn.close()
            _,_,decision=ordinary_first(owner,data,scope.usable_descriptions,preferences,self.engine)
            mode='ordinary';evaluation={'version':INPUTS_VERSION,'owner_id':owner,'wearer':asdict(wearer),'attribute_policy':AttributeEvidencePolicy.load().snapshot(),
                'sources':pack_sources(sources),'preferences':[asdict(p) for p in preferences],'source_revisions':revisions,'eligibility':scope.eligibility.to_dict(),'resources':resources('ordinary'),'decision':decision}
        value={'version':VERSION,'mode':mode,'intent':data,'evaluation':evaluation,'revision':''};value['revision']=digest(value)
        proof=NormalizedProof(encode(value));verify(proof,owner,profile_id,text=intent.raw)
        return proof

    def persist(self,owner,profile_id,intent,key,proof):
        from app.infrastructure.persistence.postgresql_repository import utcnow
        from app.application.wardrobe.profile_service import require_active_profile
        from app.domain.value_objects.request_local_source_codec import VERSION as codec
        if type(intent) is not NormalizedIntent or type(proof) is not NormalizedProof:raise ValueError('Typed normalized intent/proof required.')
        if not key:raise AttributeRequestError('InvalidInput','submission_key_required')
        source=proof.inputs();wearer=IntendedWearer(**source['wearer']);conn=self.repository._connect()
        try:
            conn.execute('BEGIN IMMEDIATE')
            if not conn.execute("SELECT 1 FROM users WHERE id=? AND account_status='active'",(owner,)).fetchone():raise ValueError('Active normalized owner required.')
            prior=conn.execute("SELECT fingerprint,recommendation_id FROM recommendation_submissions WHERE user_id=? AND operation='assistant' AND submission_key=?",(owner,key)).fetchone()
            if prior:
                if prior['fingerprint']!=fingerprint(proof):raise PersistenceConflict('Normalized submission conflict.')
                return self.repository._read(conn,owner,prior['recommendation_id'],account_history=True),True
            require_active_profile(conn,owner,profile_id)
            if source['owner_id']!=owner or wearer.profile_id!=profile_id or proof.to_dict()['intent']!=intent.to_dict():raise ValueError('Normalized writer identity mismatch.')
            self.repository.checkpoint('normalized_before_revalidation',conn)
            scope,sources,preferences=self.capture_workflow.capture(conn,owner,wearer,source_codec=codec)
            if encode(sources)!=encode(source['sources']) or encode([asdict(p) for p in preferences])!=encode(source['preferences']) or scope.eligibility.to_dict()!=source['eligibility'] or source['source_revisions']!=self.capture_workflow.source_revisions(conn,owner,wearer) or source['resources']!=resources(proof.to_dict()['mode']) or source['attribute_policy']!=AttributeEvidencePolicy.load().snapshot():raise WardrobeChanged('Normalized complete source/settings scope changed.')
            # Fresh independent raw->normalized interpretation and complete winner
            # reconstruction run while locked; no first-pass result is trusted.
            candidate,score=verify(NormalizedProof(proof.payload),owner,profile_id,text=intent.raw)
            self.repository.checkpoint('normalized_revalidated',conn)
            identifier,chat,now=str(uuid.uuid4()),str(uuid.uuid4()),utcnow()
            conn.execute("INSERT INTO nlp_chats(id,user_id,profile_id,request_text,interpreted_intent,extracted_entities_json,status,created_at,completed_at) VALUES(?,?,?,?,?,?,'completed',?,?)",(chat,owner,profile_id,intent.raw,'outfit_recommendation',json.dumps(intent.to_dict()['request']),now,now));self.repository.checkpoint('chat',conn)
            values=[float(c.summary.value) if c.summary.value is not None else None for c in (score.request_match,score.compatibility,score.preference)]+[float(score.total)]
            conn.execute("INSERT INTO recommendations(id,user_id,profile_id,chat_id,recommendation_type,status,created_at,expires_at,request_match_score,compatibility_score,preference_score,total_score) VALUES(?,?,?,?,'assistant','available',?,NULL,?,?,?,?)",(identifier,owner,profile_id,chat,now,*values));self.repository.checkpoint('recommendation',conn)
            for m in candidate.members:
                conn.execute('INSERT INTO recommendation_items VALUES(?,?,?,?,?)',(identifier,m.garment.garment_id,m.role,m.item_order,now));self.repository.checkpoint('item',conn)
                conn.execute('INSERT INTO recommendation_item_snapshots VALUES(?,?,?)',(identifier,m.garment.garment_id,json.dumps({'name':m.garment.name,'category':m.garment.category,'preferred_media_id':m.garment.preferred_media_id})));self.repository.checkpoint('snapshot',conn)
            wire_score={'version':'normalized-score-metadata-1.0.0','exact_score':json.loads(score_to_json(score)),'proof_sha256':proof.to_dict()['revision']}
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
            if any(getattr(body,k) is not None for k in ('attribute_conditions','preference_profile','compatibility_profile')):raise AttributeRequestError('UnsupportedRequest','normalized_profile_scope_unavailable')
            intent=NormalizedIntent.capture(body.request_text)
            if 'context' in intent.to_dict()['request']:
                # Canonical contexts already accepted by the original grammar
                # remain on that path, with their original ranking/proofs.
                def meaning(v):
                    if isinstance(v,dict):return {k:meaning(x) for k,x in v.items() if k not in ('original_text','spans')}
                    if isinstance(v,list):return [meaning(x) for x in v]
                    return v
                try:old=base_parse(body.request_text)
                except AttributeRequestError:raise AttributeRequestError('UnsupportedRequest','normalized_context_scope_unavailable')
                old_hard=old['hard']['conditions'] if old['hard'] else None
                new_hard=intent.to_dict()['hard_intent']
                if meaning(old['request'])!=meaning(intent.to_dict()['request']) or old_hard!=(new_hard['conditions'] if new_hard else None):raise AttributeRequestError('UnsupportedRequest','normalized_context_scope_unavailable')
                return None
            proof=self.prepare(owner,wearer.profile_id,intent)
            saved,replayed=self.persist(owner,wearer.profile_id,intent,body.submission_key,proof)
            return OutfitAssistantService._success(saved,replayed,{})
        except LocalSelectionUnavailable as error:return {'status':error.status,'complete':True,'mandatory':asdict(error.completion),'context_reason':'required_garment_description_unknown' if error.status=='InsufficientEvidence' else None}
        except AttributeRequestError as error:return {'status':error.status,'complete':False,'context_reason':error.reason}
        except PersistenceConflict:return {'status':'IdempotencyConflict','complete':False}
        except WardrobeChanged:return {'status':'WardrobeChanged','complete':False}
        except __import__('fastapi').HTTPException:raise
        except Exception as error:
            from app.application.recommendation.failure_diagnostics import log_failure
            log_failure('assistant','normalized_workflow','PersistenceFailure',error)
            return {'status':'PersistenceFailure','complete':False}
