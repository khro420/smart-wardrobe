"""Untrusted slots, old/new engines and authenticated disposable persistence."""
import copy,hashlib,json,uuid
import pytest
from app.development.mixed_wardrobe import semantic_frames as f,semantic_model as model,context_selection,context_language,core,gateway
from app.development.mixed_wardrobe.semantic_frame_contract import ENV,PROFILE,VERSION
from app.domain.value_objects.attribute_conditions import AttributeRequestError
from tests.test_mixed_context_development import (mixed,bank,composition_boundary,category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,post)

def proposal(raw,context='none',conditions=(),**extra):
 from app.application.nlp.compositional_input_v1 import normalize
 slots=dict(context=context,context_quote=raw if context!='none' else '',role='unspecified',role_quote='',dress_code='unspecified',dress_quote='',formality='unspecified',formality_quote='',context_conditions=[],secondary=[],conditions=list(conditions),uncertain=False,unsupported=[])
 slots.update(extra)
 return {'version':'local-semantic-proposal-1.0.0','source_text':raw,'source_sha256':hashlib.sha256(raw.encode()).hexdigest(),'identity':model.identity(),'input_normalization':normalize(raw),'slots':slots}

def condition(q,kind='hard'):return {'quote':q,'kind':kind}

def test_possession_not_companionship_or_invented_dress_code():
 raw="I'm going to a friend's wedding.";d=f.document(raw,proposal(raw,'ceremony.wedding'))
 c=d['request']['context'];assert c['situation']['values']==['ceremony.wedding']
 assert c['companions']['state']=='Unspecified' and c['dress_code']['state']=='Unspecified'
 assert d['normalization']['original_text']==raw and d['semantic_proposal']['source_text']==raw
 for x in d['original_context_spans']:assert raw[x['start']:x['end']]==x['text']

@pytest.mark.parametrize('mutate',[
 lambda p:p.update(source_text='different'),lambda p:p['identity'].update(nli_revision='unregistered'),
 lambda p:p.update(unknown=True),lambda p:p['slots'].update(unknown=True),lambda p:p['slots'].update(context=['ceremony.wedding']),
 lambda p:p['slots'].update(role=[]),lambda p:p['slots'].update(uncertain='no'),lambda p:p['slots'].update(uncertain=True),
 lambda p:p['slots'].update(unsupported=['weather']),lambda p:p['slots'].update(dress_code='casual',dress_quote='casual'),
 lambda p:p['slots'].update(role='candidate',role_quote='candidate'),lambda p:p['slots'].update(context='social.meal')])
def test_invalid_uncertain_hallucinated_and_unknown_output_refused(mutate):
 raw="I'm going to a friend's wedding.";p=proposal(raw,'ceremony.wedding');mutate(p)
 with pytest.raises(AttributeRequestError):f.document(raw,p)

@pytest.mark.parametrize('raw,conditions',[
 ('I need blue trousers.',[]),('I need black trousers.',[condition('trousers')]),
 ("I'd prefer blue trousers.",[condition('blue trousers')]),
 ("I don't want shorts.",[condition('shorts')]),
 ('I need trousers.',[condition('trousers','exclude')]),
 ('I need magical cotton trousers.',[condition('cotton trousers')]),
 ('I need a cotton shirt.',[condition('a cotton shirt','optional')]),
 ('I need black or white trousers.',[condition('white trousers')])])
def test_omissions_and_hard_soft_negative_changes_refused(raw,conditions):
 with pytest.raises(AttributeRequestError):f.document(raw,proposal(raw,conditions=conditions))

def test_exact_role_binding_or_negation_optional_and_original_spans():
 raw='I need a black or white top, no shorts, preferably blue trousers.'
 p=proposal(raw,conditions=[condition('a black or white top'),condition('no shorts','exclude'),condition('blue trousers','optional')])
 d=f.document(raw,p);groups=d['hard_intent']['conditions']['groups']
 assert any(c['values']==['black','white'] for g in groups for c in g['conditions'])
 assert any(g['quantifier']=='none' for g in groups)
 assert d['optional']['role']=='lower' and d['optional']['resolution']['state']=='Active'
 for x in d['original_hard_spans']+d['original_optional_spans']:assert raw[x['start']:x['end']]==x['text']

@pytest.mark.parametrize('raw', ['I need a cotton shirt.','I need black trousers.'])
def test_neutral_reference_compact_and_independent_identical(raw,monkeypatch):
 from tests.test_context_relevance_ranking import rows
 from app.development.main_fixture.core import FixtureRow
 frozen=tuple(FixtureRow(g,{'category':g.category,'primary_colour':g.primary_colour,'style':list(g.style_tags),'material':['cotton']}) for g in rows())
 monkeypatch.setattr(core,'rows_from_catalog',lambda *_:frozen)
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 phrase=raw[len('I need '):-1];p=proposal(raw,conditions=[condition(phrase)])
 expected=core.select(scope,raw,'wearer',independent=True)
 interpret=lambda text:f.document(text,p)
 a=core.select(scope,raw,'wearer',_interpret=interpret);b=core.select(scope,raw,'wearer','compact_exhaustive',_interpret=interpret);c=core.select(scope,raw,'wearer',independent=True,_interpret=interpret)
 assert a==b==c
 for field in ('status','mandatory','selected','candidate_scores_sha256','optional'):assert a.get(field)==expected.get(field)

def test_contextual_three_engines_equal_existing_policy(monkeypatch):
 from tests.test_context_relevance_ranking import rows
 from app.development.main_fixture.core import FixtureRow
 frozen=tuple(FixtureRow(g,{'category':g.category,'primary_colour':g.primary_colour,'style':list(g.style_tags)}) for g in rows())
 monkeypatch.setattr(core,'rows_from_catalog',lambda *_:frozen)
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 raw="I'm going to a friend's wedding.";p=proposal(raw,'ceremony.wedding');interpret=lambda text:f.document(text,p)
 expected=context_selection.select(scope,"I'm attending a wedding.",'wearer',independent=True)
 a=context_selection.select(scope,raw,'wearer',_interpret=interpret);b=context_selection.select(scope,raw,'wearer','compact_exhaustive',_interpret=interpret);c=context_selection.select(scope,raw,'wearer',independent=True,_interpret=interpret)
 assert a==b==c
 for field in ('status','mandatory','selected','candidate_scores_sha256'):assert a.get(field)==expected.get(field)

def enable(monkeypatch):
 from app.development.mixed_wardrobe import context_contract,context_language_contract,interview_default_contract,fashion_contract,personalization
 for mod in (context_contract,context_language_contract,interview_default_contract,fashion_contract,personalization):monkeypatch.setenv(mod.ENV,mod.PROFILE)
 monkeypatch.setenv(ENV,PROFILE)

def test_real_models_authenticated_write_history_receipts_continuation_feedback_and_rollback(mixed,monkeypatch):
 client,_,pid,_,_,_=mixed
 # Preserve an old root before the additive interpreter is enabled.
 old=post(client,pid,'I need jeans.');assert old.status_code==201,old.text;old=old.json()
 enable(monkeypatch)
 caps=client.get('/api/v1/recommendations/capabilities').json()['mixed_wardrobe']
 from app.development.mixed_wardrobe.semantic_constraint_contract import GRAMMAR as CURRENT_GRAMMAR
 assert caps['contextual']['semantic_interpreter']['ready'] and caps['grammar_version']==CURRENT_GRAMMAR
 key=uuid.uuid4().hex;raw="I'm going to a friend's wedding."
 wedding=post(client,pid,raw,key);assert wedding.status_code==201,wedding.text;w=wedding.json()
 assert w['request_text']==raw and w['mixed_wardrobe_display']['decision']['intent']['semantic_metadata']['primary']=='ceremony.wedding'
 assert post(client,pid,raw,key).json()['id']==w['id']
 assert post(client,pid,'I need jeans.',key).status_code==409
 root=post(client,pid,'I need jeans.');assert root.status_code==201,root.text;r=root.json()
 for _ in range(2):
  action=r['development_continuation']['next_action'];assert action
  result=post(client,pid,r['request_text'],action['submission_key'],refinement=action['refinement']);assert result.status_code==201,result.text;r=result.json()
  assert post(client,pid,r['request_text'],action['submission_key'],refinement=action['refinement']).json()['id']==r['id']
 s=gateway.open_store(enabled=True)
 proof=r['provenance']['phase2nd_mixed_selection'];assert proof['semantic_proposal']['source_text']==r['request_text']
 assert s.action(r['id'],{**proof,'ordinal':9}) is None
 assert client.get('/api/v1/chats/'+w['chat_id'],headers={'X-Wardrobe-Profile-Id':str(uuid.uuid4())}).status_code==404
 for vote in ('like','dislike','clear'):
  assert client.put('/api/v1/recommendations/'+w['id']+'/feedback',headers={'X-Wardrobe-Profile-Id':pid},json={'wearer_profile_id':pid,'verdict':vote}).status_code==200
 def counts():
  with s.connection() as c:return tuple(c.execute('select count(*) from '+t).fetchone()[0] for t in ('recommendations','nlp_chats','recommendation_submissions'))
 before=counts();mirror=gateway.mirror
 def fail(*args):mirror(*args);raise RuntimeError('injected atomic rollback')
 with monkeypatch.context() as m:
  m.setattr(gateway,'mirror',fail);assert post(client,pid,'I want a cotton shirt.').status_code==503
 assert counts()==before
 with s.connection() as c:
  row=c.execute('select * from phase2nd_mixed_proofs where id=?',(w['id'],)).fetchone();p=json.loads(row['proof_json']);p['semantic_proposal']['slots']['context']='social.meal'
  altered={**dict(row),'proof_json':core.encoded(p).decode(),'proof_sha256':core.digest(p),'signature':s.sign(p)}
  with pytest.raises((ValueError,AttributeRequestError)):s.verify_record(c,altered,p['catalog']['fixture']['owner_id'])
 # History rechecks dependency bindings without re-proposing/classifying context.
 monkeypatch.delenv(ENV)
 with monkeypatch.context() as m:
  m.setattr(model,'propose',lambda *_:(_ for _ in ()).throw(AssertionError('history re-inferred')))
  for result in (old,w,r):assert client.get('/api/v1/chats/'+result['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200

def test_model_unavailable_never_falls_back(mixed,monkeypatch):
 client,_,pid,_,_,_=mixed;enable(monkeypatch)
 def fail(*_):raise model.ModelUnavailable('missing model')
 monkeypatch.setattr(model,'propose',fail)
 response=post(client,pid,'I need jeans.');assert response.status_code==503
 assert response.json()['status']=='SemanticInterpreterUnavailable'

def test_companions_and_own_roles_are_not_erased_by_the_model():
 for raw in ("I'm attending a wedding with colleagues.","I'm getting married this weekend.","I'm attending my own wedding."):
  p=model.propose(raw)
  with pytest.raises(AttributeRequestError):f.document(raw,p)

def test_missing_context_observation_is_refused():
 raw="I'm meeting friends for dinner."
 p=model.propose(raw);assert p['slots']['context_conditions']
 p['slots']['context_conditions']=[]
 with pytest.raises(AttributeRequestError,match='semantic_source_grounding'):f.document(raw,p)

def test_ontology_is_exactly_the_approved_eighteen_contexts():
 from app.application.recommendation.context_bundle import ContextBundle
 assert len(model.CONTEXTS)==18 and set(model.CONTEXTS)==set(ContextBundle.load('context_18_v1').record['scopes'])

def test_missing_prerequisite_never_selects_the_old_interpreter(mixed,monkeypatch):
 from app.development.mixed_wardrobe.interview_default_contract import ENV as DEFAULT_ENV
 client,_,pid,_,_,_=mixed;enable(monkeypatch);monkeypatch.setenv(DEFAULT_ENV,'disabled')
 r=post(client,pid,'I need jeans.');assert r.status_code==422 and r.json()['status']=='SemanticProfileUnavailable'

@pytest.mark.parametrize('raw,context,role',[
 ("I'm giving a presentation at university tomorrow.",'academic.presentation','presenter'),
 ("I am being interviewed for a job.",'professional.job_interview','candidate'),
 ("I'm meeting friends for dinner tonight.",'social.meal','unspecified'),
])
def test_real_model_actor_and_context_slots(raw,context,role):
 d=f.document(raw,model.propose(raw))
 assert d['semantic_metadata']['primary']==context
 assert d['semantic_metadata']['role']==role
 assert d['normalization']['original_text']==raw
 if context=='social.meal':assert d['request']['context']['companions']['values']==['friends']
 if context=='professional.job_interview':assert d['interview_default']['inferred']

@pytest.mark.parametrize('raw',[
 "I don't prefer black trousers.","I'd prefer not to wear black trousers.",
 "I don't need black trousers.",
])
def test_negated_preference_or_necessity_cannot_become_a_hard_exclusion(raw):
 with pytest.raises(AttributeRequestError,match='semantic_polarity_mismatch'):
  f.document(raw,proposal(raw,conditions=[condition('black trousers','exclude')]))

def test_positive_necessity_can_require_an_exclusion():
 raw='I need no shorts.'
 d=f.document(raw,proposal(raw,conditions=[condition('no shorts','exclude')]))
 groups=d['hard_intent']['conditions']['groups']
 assert len(groups)==1 and groups[0]['quantifier']=='none'
 assert groups[0]['conditions'][0]['values']==['shorts']
