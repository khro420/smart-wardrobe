"""Full archived-scope reconstruction, separate enumeration and promotion logic.

Never calls first_selection, bounded_rank, the compact audit, NLP or a database.
Version one is pinned to the existing P1/C1 public arithmetic and B0/B1 policies.
"""
from dataclasses import asdict
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace
from types import MappingProxyType
import hashlib,json
from app.domain.value_objects.attribute_conditions import encode,digest,exact
from app.domain.value_objects.request_local_preference import RequestLocalPreferenceIntent
from app.domain.value_objects.request_local_selection import LocalSelectionProof,SETTINGS,POLICY
from app.domain.value_objects.intended_wearer import IntendedWearer
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
from app.shared_contracts.confirmed_garment_description import ConfirmedGarmentDescription
from app.domain.value_objects.garment_description_evidence import GarmentDescriptionEvidence
from app.domain.value_objects.contextual_garment_evidence import ContextualGarmentEvidence
from app.domain.value_objects.general_context_evidence import AppearanceEvidence
from app.domain.value_objects.saved_attribute_evidence import SavedAttributeEvidence
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
from app.domain.value_objects.outfit_candidate import OutfitCandidate,CandidateMember
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier,_possibility
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.recommendation.request_candidate_session import RequestCandidateSession
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
from app.application.recommendation.request_local_bounded_ranking import PrimaryRecord,CompletedLedger,PromotionComparison,BoundedDecision
from app.application.recommendation.request_local_preference_evidence import OptionalEvaluation
from app.application.recommendation.request_local_selection_engine import public_scorers,public_score,decision_document
from app.application.recommendation.refinement_verifier import snapshot_digest
from app.domain.value_objects.attribute_selection_evidence import description_digest
from app.application.recommendation.decision_score_codec import score_to_json

def restore_snapshot(v):
    v=dict(v);c=dict(v['contextual_suitability']);c['reviewed_styles']=tuple(c['reviewed_styles']);c['wedding_decisions']=tuple(c['wedding_decisions'])
    a=dict(v['appearance_evidence']);a['features']=tuple(tuple(x) for x in a['features'])
    v.update(contextual_suitability=ContextualGarmentEvidence(**c),appearance_evidence=AppearanceEvidence(**a),saved_attribute_evidence=SavedAttributeEvidence(**v['saved_attribute_evidence']))
    return ConfirmedGarmentSnapshot(**v)

def restore_sources(proof):
    rows=tuple(ConfirmedGarmentDescription(restore_snapshot(s['snapshot']),GarmentDescriptionEvidence.from_dict(s['description'])) for s in proof['sources'])
    if len({r.snapshot.garment_id for r in rows})!=len(rows) or any(r.snapshot.user_id!=proof['owner_id'] or r.snapshot.status!='available' for r in rows):raise ValueError('Invalid complete archived account scope.')
    from app.domain.value_objects.wearer_category_eligibility import validate_evidence
    from app.application.wardrobe.wearer_category_service import effective_category,decision
    eligibility=proof['eligibility'];validate_evidence(eligibility,proof['owner_id'],proof['wearer']['profile_id'])
    if len(rows)!=eligibility['account_count']:raise ValueError('Incomplete archived account collection.')
    original=digest({'snapshots':snapshot_digest(r.snapshot for r in rows),'descriptions':description_digest(rows),
        'raw_category_sources':digest([s['category_source'] for s in sorted(proof['sources'],key=lambda s:s['snapshot']['garment_id'])])})
    expected=digest({'original':original,'subtype_sources':eligibility['subtype_sources']}) if eligibility['version']=='wearer-category-eligibility-evidence-2.0.0' else original
    if expected!=eligibility['account_source_sha256']:raise ValueError('Archived complete account source binding mismatch.')
    permitted=[]
    for row,source in zip(rows,proof['sources']):
        exact(source,('snapshot','description','category_source','links','media','media_sha256'))
        exact(source['category_source'],('id','category','attributes_json','additional_attributes','preferred_media_id','updated_at'))
        exact(source['links'],('processing_item_id','job_id','review_status','crop_media_id','preferred_media_id','item_created_at','owner_id','job_status','source_media_id','job_updated_at','job_completed_at'))
        exact(source['media'],('id','user_id','media_type','storage_key','content_type','size_bytes','status','created_at'))
        if source['category_source']['id']!=row.snapshot.garment_id:raise ValueError('Foreign category source.')
        state=decision(effective_category(source['category_source']),eligibility['gender_key'],eligibility['policy'])
        if eligibility['version']=='wearer-category-eligibility-evidence-2.0.0':
            state=eligibility['subtype_decisions'][row.snapshot.garment_id]
        if state=='Permit':permitted.append(row.snapshot.garment_id)
        links=source['links'];media=source['media']
        if links['owner_id']!=proof['owner_id'] or links['job_status']!='completed' or links['review_status']!='confirmed' or media['user_id']!=proof['owner_id'] or media['status']!='available' or media['id']!=row.snapshot.preferred_media_id or len(source['media_sha256'])!=64:raise ValueError('Unqualified archived source links.')
    if sorted(permitted)!=eligibility['usable_ids']:raise ValueError('Incorrect archived wearer filtering.')
    return tuple(r for r in rows if r.snapshot.garment_id in permitted)

class IndependentStructural:
    def __init__(self,rows):
        role={'top':'upper','bottom':'lower','dress':'one_piece','outerwear':'outerwear'}
        slots={name:[] for name in role.values()}
        from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
        for row in rows:
            g=row.snapshot
            if g.category not in GARMENT_STRUCTURE or (g.structural_role,g.layering_index)!=GARMENT_STRUCTURE[g.category]:continue
            if not g.garment_id.strip() or not g.preferred_media_id.strip():continue
            slots[role[g.structural_role]].append(g)
        for bucket in slots.values():bucket.sort(key=lambda g:g.garment_id)
        def candidates():
            for roles in [('upper','lower'),('upper','lower','outerwear'),('one_piece',),('one_piece','outerwear')]:
                for members in product(*(slots[r] for r in roles)):
                    yield OutfitCandidate(tuple(CandidateMember(g,r,i) for i,(r,g) in enumerate(zip(roles,members),1)))
        self.iterator=candidates();self.result=SimpleNamespace(complete=True,status='CandidatesAvailable')
    def __iter__(self):return self
    def __next__(self):return next(self.iterator)
    def close(self):pass

class _IndependentOptionalFacts:
    """Fresh per reconstruction; never borrows the first evaluator's cache."""
    def __init__(self,intent,rows,policy,scope):
        if len(rows)>100:raise ValueError('Unbounded independent optional facts.')
        self.intent,self.rows,self.policy,self.scope=intent,rows,policy,scope
        self.sources=MappingProxyType(dict(rows));self.optional=intent.to_dict()['optional']
        self.classifier=policy.primary_classifier();self.members={}

    def member(self,m):
        row=self.sources[m.garment.garment_id]
        if self.rows.get(m.garment.garment_id) is not row or row.snapshot!=m.garment:raise ValueError('Changed independently captured member.')
        key=(m.role,m.garment.garment_id)
        if key not in self.members:
            document=row.description.to_dict();bounds=[];ledger=[]
            for p in self.optional['predicates']:
                field=p['attribute'];record=document['fields'][field];fact=self.policy.fact(m.garment,document,field,'in',self.classifier)
                unresolved=record['state'] in ('Stale','Conflicting','Malformed','Unsure')
                possible=frozenset((True,False)) if unresolved else _possibility(fact,field,'in',p['values'])
                state='Pass' if possible=={True} else 'Fail' if possible=={False} else 'Unknown';bounds.append(possible)
                reason='unresolved_B0_record' if unresolved else 'matched_recorded_value' if state=='Pass' else 'known_mismatch' if state=='Fail' else {'Stale':'stale_description','Malformed':'malformed_description','Conflicting':'conflicting_description','Unsure':'unknown_material','Inapplicable':'inapplicable_role','Absent':'missing_description','Missing':'missing_description'}.get(fact.state,'incomplete_recorded_set' if fact.state in ('Known','KnownEmpty') and fact.applicability=='applicable' else 'unqualified_source')
                ledger.append(encode({'garment_id':m.garment.garment_id,'role':m.role,'predicate':p,'verdict':state,'fact_state':fact.state,'source':fact.source,'fact_values':list(fact.values),'record_state':record['state'],'reason':reason}))
            self.members[key]=((all(b=={True} for b in bounds),all(True in b for b in bounds)),tuple(ledger))
        return self.members[key]

def independent_optional(candidate,intent,rows,policy,scope,*,prepared=None):
    facts=prepared if prepared is not None else _IndependentOptionalFacts(intent,rows,policy,scope)
    if type(facts) is not _IndependentOptionalFacts or facts.intent is not intent or facts.rows is not rows or facts.policy is not policy or facts.scope!=scope:raise ValueError('Foreign independent optional preparation.')
    states=[];ledger=[]
    for m in candidate.members:
        if m.role!=facts.optional['role']:continue
        state,records=facts.member(m);states.append(state);ledger.extend(records)
    yes=any(x[0] for x in states);maybe=any(x[1] for x in states)
    if not states:ledger.append(encode({'reason':'preferred_role_absent','role':facts.optional['role']}))
    return OptionalEvaluation(candidate.key,scope,'Satisfied' if yes else 'Unverifiable' if maybe else 'Unsatisfied',int(yes),F(int(yes)),F(int(maybe)),tuple(ledger))

def reconstruct(proof):
    v=proof.expanded_dict();intent=RequestLocalPreferenceIntent(encode(v['intent']));owner=v['owner_id'];wearer=IntendedWearer(**v['wearer'])
    from app.application.recommendation.request_local_soft_workflow import resource_identities
    if v['resources']!=resource_identities():raise ValueError('Unregistered archived scoring resources.')
    policy=AttributeEvidencePolicy(encode(v['attribute_policy']))
    if policy.sha256!=v['intent']['qualification_policy_sha256']:raise ValueError('Unregistered qualification policy binding.')
    collection=restore_sources(v);by_id={r.snapshot.garment_id:r for r in collection}
    revisions=v['source_revisions'];exact(revisions,('profile','details','preferences'));profile=revisions['profile'];details=revisions['details']
    exact(profile,('id','user_id','name','is_default','status','created_at','updated_at'))
    exact(details,('profile_id','version','gender_identity','revision','updated_at'))
    if profile['id']!=wearer.profile_id or profile['user_id']!=owner or profile['status']!='active' or profile['name']!=wearer.name_at_request or details['profile_id']!=wearer.profile_id or details['revision']!=v['eligibility']['details_revision'] or details['version']!='wearer-profile-details-1.0.0' or details['gender_identity'].strip().casefold()!=v['eligibility']['gender_key']:raise ValueError('Wrong archived wearer revisions.')
    preferences=[]
    for p in revisions['preferences']:
        exact(p,('id','user_id','profile_id','preference_type','preference_value_json','weight','source','is_active','created_at','updated_at'))
        if p['user_id']!=owner or p['profile_id']!=wearer.profile_id or type(p['is_active']) is not int or p['is_active']!=1:raise ValueError('Foreign archived preference revision.')
        preferences.append(PreferenceSnapshot(p['id'],owner,p['preference_type'],p['preference_value_json'],None if p['weight'] is None else str(p['weight']),p['source'],bool(p['is_active'])))
    if encode([asdict(p) for p in preferences])!=encode(v['preferences']):raise ValueError('Archived preference revisions disagree with scoring inputs.')
    scope=digest({'contract':'isolated-local-source-scope-1.0.0','account':owner,'wearer_scope':wearer.profile_id,'intent':intent.revision,'snapshots':snapshot_digest(r.snapshot for r in collection),'descriptions':description_digest(collection),'policy':policy.sha256})
    request=StructuredOutfitRequest(**v['intent']['mandatory_request']);hard=IndependentAttributeVerifier.prepare(intent.hard.conditions,collection,policy) if intent.hard else None
    stream=RequestCandidateSession(IndependentStructural(collection),request,RequestConstraintEvaluator());gate=ScoringEligibilityGate(stream,owner,request)
    from app.application.recommendation.request_local_score_encoding import LocalScoreEncoding
    encoding=LocalScoreEncoding()
    scorers=public_scorers(owner,tuple(PreferenceSnapshot(**r) for r in v['preferences']));points=[];candidate_map={};score_map={};failed=unknown=0
    try:
        for item in stream:
            state=hard.decision(item.candidate.key) if hard else 'Pass'
            if state=='Fail':failed+=1;continue
            if state=='Unknown':unknown+=1;continue
            verified=gate.verify(item);score=public_score(verified,scorers);key=item.candidate.key
            row=PrimaryRecord(key,score.request_match.contribution,score.compatibility.contribution,score.preference.contribution,score.total,scope,encoding.encode(score).encode())
            points.append(row);candidate_map[key]=item.candidate;score_map[key]=score
        if not stream.result.complete:raise ValueError('Independent mandatory scope incomplete.')
        completion=CompletedLedger(stream.result.examined,len(points),failed,unknown,True)
    finally:stream.close()
    if not points:raise ValueError('No independently admitted candidate.')
    baseline=min(points,key=lambda p:p.original_key);comparisons=[];eligible=[]
    optional_facts=_IndependentOptionalFacts(intent,by_id,policy,scope)
    resolution=optional_facts.optional['resolution']['state']
    for point in points:
        optional=independent_optional(candidate_map[point.key],intent,by_id,policy,scope,prepared=optional_facts);reasons=[]
        if resolution!='Active':reasons.append('inactive_optional_intent')
        elif not optional.support:reasons.append('no_qualified_match')
        if point.t+F(1,50)<baseline.t:reasons.append('T_loss_above_budget')
        if point.c+F(1,10)<baseline.c:reasons.append('C_loss_above_budget')
        if point.p+F(1,10)<baseline.p:reasons.append('P_loss_above_budget')
        if point.r<baseline.r:reasons.append('R_would_decrease')
        if not reasons:eligible.append(point)
        comparisons.append(PromotionComparison(point,optional,tuple(reasons)))
    selected=min(eligible,key=lambda p:p.original_key) if eligible else baseline
    commitment=hashlib.sha256(b''.join(sorted(p.identity() for p in points))).hexdigest()
    result=BoundedDecision(baseline,selected,completion,tuple(sorted(comparisons,key=lambda p:p.primary.key)),commitment)
    return result,candidate_map[selected.key],score_map[selected.key]

def verify(proof,owner,profile_id,*,candidate=None,score=None,items=None,text=None):
    if type(proof) is not LocalSelectionProof:raise ValueError('Typed complete local proof required.')
    v=proof.expanded_dict()
    if v['owner_id']!=owner or v['wearer']['profile_id']!=profile_id or text is not None and v['intent']['original_text']!=text:raise ValueError('Wrong archived local request ownership/text.')
    decision,expected,actual=reconstruct(proof)
    if decision_document(decision)!=v['decision']:raise ValueError('Independent complete-scope local decision mismatch.')
    if candidate is not None and candidate!=expected or score is not None and score_to_json(score)!=score_to_json(actual):raise ValueError('Local selected candidate/score mismatch.')
    if items is not None:
        wanted=[(m.garment.garment_id,m.role,m.item_order,m.garment.name,m.garment.category,m.garment.preferred_media_id) for m in expected.members]
        observed=[(m['garment_id'],m['garment_role'],m['item_order'],m['name'],m['category'],m['preferred_media_id']) for m in items]
        if wanted!=observed:raise ValueError('Local historical selected items mismatch.')
    return decision,expected,actual


_LOCAL_SEAL=object()

class _VerifiedLocalRecord(dict):
    """In-process result only. JSON/copy-to-dict carries no verification seal."""
    __slots__=('_binding',)
    def __init__(self,record,*,_seal=None):
        if _seal is not _LOCAL_SEAL:raise ValueError('Internal verified local record required.')
        super().__init__(record);object.__setattr__(self,'_binding',encode(dict(record)))
    def __setattr__(self,name,value):raise TypeError('Immutable local verification binding.')
    def __delattr__(self,name):raise TypeError('Immutable local verification binding.')

def _is_verified_record(record):
    if type(record) is not _VerifiedLocalRecord:return False
    if encode(dict(record))!=record._binding:raise ValueError('Verified local response was modified.')
    return True

class _LockedLocalVerification:
    __slots__=('connection','proof','candidate','score','owner','profile_id')
    def __init__(self,conn,command,candidate,score,*,_seal=None):
        if _seal is not _LOCAL_SEAL or not conn.in_transaction:raise ValueError('Locked independent verification required.')
        for name,value in (('connection',conn),('proof',command.local_preference.proof),('candidate',candidate),('score',score),('owner',command.user_id),('profile_id',command.wearer.profile_id)):
            object.__setattr__(self,name,value)
    def __setattr__(self,name,value):raise TypeError('Immutable locked local verification.')
    def __delattr__(self,name):raise TypeError('Immutable locked local verification.')

    def read_back(self,conn,record,items):
        if conn is not self.connection or not conn.in_transaction:raise ValueError('Foreign/ended local verification transaction.')
        if record['user_id']!=self.owner or record['profile_id']!=self.profile_id or record['request_text']!=self.proof.to_dict()['intent']['original_text']:
            raise ValueError('Local verified read-back ownership/text mismatch.')
        if encode(record['provenance']['request_local_preference'])!=encode(self.proof.to_dict()):raise ValueError('Local read-back proof differs from locked verification.')
        from app.application.recommendation.decision_score_codec import score_from_json
        if score_to_json(score_from_json(json.dumps(record['score_metadata'])))!=score_to_json(self.score):raise ValueError('Local read-back score differs from locked verification.')
        wanted=[(m.garment.garment_id,m.role,m.item_order,m.garment.name,m.garment.category,m.garment.preferred_media_id) for m in self.candidate.members]
        observed=[(m['garment_id'],m['garment_role'],m['item_order'],m['name'],m['category'],m['preferred_media_id']) for m in items]
        if wanted!=observed:raise ValueError('Local read-back items differ from locked verification.')
        return _VerifiedLocalRecord(record,_seal=_LOCAL_SEAL)

def _verify_locked(conn,command):
    if not conn.in_transaction:raise ValueError('Local verification requires the writer transaction.')
    _,candidate,score=verify(command.local_preference.proof,command.user_id,command.wearer.profile_id,candidate=command.candidate,score=command.score,text=command.request_text)
    return _LockedLocalVerification(conn,command,candidate,score,_seal=_LOCAL_SEAL)
