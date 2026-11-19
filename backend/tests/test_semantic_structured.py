"""Exposed development cases; never describe these as unseen evaluation."""
from pathlib import Path
import copy,json,uuid
import pytest
from app.development.mixed_wardrobe import semantic_structured as current,semantic_model,core,context_selection,gateway
from app.development.mixed_wardrobe.semantic_structured_contract import VERSION,PROFILE,GRAMMAR
from app.development.mixed_wardrobe.semantic_frame_contract import ENV
from app.development.mixed_wardrobe.store import Store,FixtureError
from app.domain.value_objects.attribute_conditions import AttributeRequestError
from tests.test_semantic_frames import (enable as enable_previous,mixed,bank,composition_boundary,category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,post)
from tests.test_semantic_constraint_verification import fixture_rows,JEANS,COTTON

BANK=json.loads((Path(__file__).with_name('fixtures')/'semantic_typed_development.v1.json').read_text())

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'))
def preds(cs):return sorted([{'attribute':c['attribute'],'operator':c['operator'],'values':sorted(c['values'],key=canonical)} for c in cs],key=canonical)
def groups(gs):return sorted([{'role':g['role'],'quantifier':g['quantifier'],'predicates':preds(g.get('conditions',g.get('predicates',[])))} for g in gs],key=canonical)
def projection(d):
 c=d['request'].get('context',{});value=lambda n:c.get(n,{}).get('values',[])
 scalar=lambda n:(value(n) or [None])[0];context=scalar('situation') or 'none';optional=d['optional'];hard=d['hard_intent']
 return {'context':context,'role':scalar('role'),'venue':scalar('venue') or BANK['intrinsic_venues'].get(context),
 'companions':sorted(value('companions')),'temporal':sorted(value('temporal')),'facets':sorted(value('facets')),
 'dress_code':(scalar('dress_code') or '').replace('_',' ') or None,'formality':(scalar('formality') or '').replace('_',' ') or None,
 'interview_default_inferred':bool(d.get('interview_default',{}).get('inferred')),
 'hard':groups(hard['conditions']['groups']) if hard else [],
 'optional':None if optional is None else {'role':optional['role'],'quantifier':optional['quantifier'],'predicates':preds(optional['predicates']),'resolution':optional['resolution']['state']},
 'secondary_required':d['semantic_metadata']['secondary']}
def target(v):
 v=copy.deepcopy(v);v['hard']=groups(v['hard'])
 if v['optional']:v['optional']['predicates']=preds(v['optional']['predicates'])
 for name in ('companions','temporal','facets','secondary_required'):v[name]=sorted(v[name])
 if v['venue']=='campus':v['venue']='university'
 return v

@pytest.mark.parametrize('case',BANK['cases'],ids=lambda c:c['id'])
def test_exposed_structured_development_bank(case):
 if case['decision']=='refuse':
  with pytest.raises(AttributeRequestError):current.document(case['text'],current.propose(case['text']))
  return
 d=current.document(case['text'],current.propose(case['text']))
 assert projection(d)==target(case['expected'])
 assert d['normalization']['original_text']==case['text']
 for name in ('original_hard_spans','original_optional_spans','original_context_spans'):
  for s in d[name]:assert case['text'][s['start']:s['end']]==s['text']

@pytest.mark.parametrize('raw',[
 "I'd prefer a black top and blue trousers.","I don't want shorts and blue trousers.",
 'I need a blue shirt or black trousers.','I need jeans or a skirt.',
 'I need a cotton or striped shirt.','I need blue trousers if it rains.',
 'I need a warmer cotton shirt.','I need a cotton shirt without a collar.',
 "I'm attending a wedding with colleagues.","I'm getting married tomorrow.",
 "My friend is being interviewed for a job.",
 "My brother is having a job interview as the candidate.",
 "I need clothes for my friend's job interview as the candidate.",
 "I'm shopping unless I have a job interview as the candidate.",
 "I'd prefer a blue top, but any colour is fine.",
 'I need either blue or black trousers, preferably red or green.',
 'I need a blue shirt and a waterproof jacket.',
 'I need a professional outfit for the office.',
 'Please suggest an outfit for watching.',
])
def test_unrepresented_requirements_and_cross_clause_polarity_refuse(raw):
 with pytest.raises(AttributeRequestError):current.document(raw,current.propose(raw))

@pytest.mark.parametrize('raw',[
 'I need a shirt that is not blue.',
 'I need a not blue shirt.',
 'I need black trousers for a white or red wedding.',
 'I need a blue shirt for a black or white presentation at university as the presenter.',
])
def test_descriptor_and_negative_scope_cannot_cross_event_or_relative_clause(raw):
 with pytest.raises(AttributeRequestError):current.document(raw,current.propose(raw))

@pytest.mark.parametrize('raw',[
 'I have a birthday party and dinner. Suggest an outfit.',
 'I have a dinner and a date. Choose clothes.',
])
def test_compound_facets_cannot_merge_independent_event_heads(raw):
 with pytest.raises(AttributeRequestError):current.document(raw,current.propose(raw))

@pytest.mark.parametrize('raw',[
 'Please recommend clothes at the library.',
 'I need a black top with my family at a restaurant.',
 'I need a blue top as the guest.',
])
def test_context_slots_cannot_be_discarded_when_activity_is_unresolved(raw):
 with pytest.raises(AttributeRequestError):current.document(raw,current.propose(raw))

@pytest.mark.parametrize('raw,context,facet',[
 ("I'm going to a birthday dinner.",'social.meal','celebration:birthday'),
 ("I'm having dinner for my birthday.",'social.meal','celebration:birthday'),
 ("I'm going on a dinner date.",'social.date','meal:dinner'),
 ('I have a date for dinner tonight.','social.date','meal:dinner'),
])
def test_compound_facets_require_a_shared_nominal_event(raw,context,facet):
 d=current.document(raw,current.propose(raw));frame=d['request']['context']
 assert frame['situation']['values']==[context] and frame['facets']['values']==[facet]

def test_direct_compiler_never_reparses_generated_english(monkeypatch):
 from app.application.nlp.compositional_request_v1 import CompositionalIntent
 from app.application.nlp import normalized_request_v1
 def forbidden(*_):raise AssertionError('legacy English reparse')
 monkeypatch.setattr(CompositionalIntent,'capture',forbidden);monkeypatch.setattr(normalized_request_v1,'base_parse',forbidden)
 for raw in ('I need either a blue or a white shirt.',"I need trousers preferably black.","Please choose clothes for studying at a library today."):
  assert current.document(raw,current.propose(raw))['grammar_version']==GRAMMAR

def test_grey_gray_and_negation_are_exact_role_equivalents():
 texts=('I need grey trousers, not a grey shirt.','I need gray trousers, not a gray shirt.')
 data=[current.document(t,current.propose(t)) for t in texts]
 assert data[0]['hard_intent']['conditions']==data[1]['hard_intent']['conditions']
 assert [g['role'] for g in data[0]['hard_intent']['conditions']['groups']]==['lower','upper']
 assert [g['quantifier'] for g in data[0]['hard_intent']['conditions']['groups']]==['exists','none']

def test_ordinary_category_keeps_earned_request_match_and_exact_scores(monkeypatch):
 from app.development.mixed_wardrobe import semantic_constraints
 raw='I want a top.';old=semantic_constraints.document(raw,semantic_model.propose(raw));new=current.document(raw,current.propose(raw))
 assert new['request']==old['request'] and new['hard_intent'] is old['hard_intent'] is None
 assert new['request']['garment_categories']==[{'kind':'group','value':'top'}]
 rows=fixture_rows();monkeypatch.setattr(core,'rows_from_catalog',lambda *_:rows)
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 a=core.select(scope,raw,'wearer',_interpret=lambda _:new)
 b=core.select(scope,raw,'wearer','compact_exhaustive',_interpret=lambda _:new)
 c=core.select(scope,raw,'wearer',independent=True,_interpret=lambda _:new)
 oracle=core.select(scope,raw,'wearer',independent=True,_interpret=lambda _:old)
 assert a==b==c and a['status']=='Selected'
 for name in ('selected','mandatory','baseline','candidate_scores_sha256'):assert a.get(name)==oracle.get(name)

@pytest.mark.parametrize('raw',['Suggest a casual outfit.','I want a formal outfit.','I need a smart casual outfit.'])
def test_neutral_style_keeps_b1_qualification_and_exact_scores(raw,monkeypatch):
 from app.development.mixed_wardrobe import semantic_constraints
 old=semantic_constraints.document(raw,semantic_model.propose(raw));new=current.document(raw,current.propose(raw))
 assert new['request']==old['request']
 assert groups(new['hard_intent']['conditions']['groups'])==groups(old['hard_intent']['conditions']['groups'])
 rows=fixture_rows();monkeypatch.setattr(core,'rows_from_catalog',lambda *_:rows)
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 a=core.select(scope,raw,'wearer',_interpret=lambda _:new);b=core.select(scope,raw,'wearer','compact_exhaustive',_interpret=lambda _:new);c=core.select(scope,raw,'wearer',independent=True,_interpret=lambda _:new)
 oracle=core.select(scope,raw,'wearer',independent=True,_interpret=lambda _:old)
 assert a==b==c and a['status']==oracle['status']
 for name in ('selected','mandatory','baseline','candidate_scores_sha256'):assert a.get(name)==oracle.get(name)

@pytest.mark.parametrize('mutate',[
 lambda p:p.update(extra=True),lambda p:p.update(source_text='changed'),
 lambda p:p['analysis']['hard']['groups'].clear(),lambda p:p['analysis']['coverage'].clear(),
 lambda p:p['slots'].update(context='everyday.shopping'),lambda p:p['selection'].update(grounded_candidates=['everyday.shopping']),
 lambda p:p['identity'].update(compiler_sha256='0'*64),
])
def test_source_graph_and_model_contract_tampering(mutate):
 raw='I need a cotton shirt.';p=current.propose(raw);mutate(p)
 with pytest.raises(AttributeRequestError):current.document(raw,p)

@pytest.mark.parametrize('raw',[JEANS,COTTON])
@pytest.mark.parametrize('missing',[False,True])
def test_same_member_unknown_and_exact_three_engine_scores(raw,missing,monkeypatch):
 rows=fixture_rows(missing=(1 if raw==JEANS else 0,'material') if missing else None)
 monkeypatch.setattr(core,'rows_from_catalog',lambda *_:rows)
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 d=current.document(raw,current.propose(raw));fn=core.select if raw==JEANS else context_selection.select;interpret=lambda _:copy.deepcopy(d)
 a=fn(scope,raw,'wearer',_interpret=interpret);b=fn(scope,raw,'wearer','compact_exhaustive',_interpret=interpret);c=fn(scope,raw,'wearer',independent=True,_interpret=interpret)
 assert a==b==c and a['status']==('InsufficientEvidence' if missing else 'Selected')
 if not missing:
  from app.development.mixed_wardrobe import semantic_constraints
  old=semantic_constraints.document(raw,semantic_model.propose(raw))
  oracle=fn(scope,raw,'wearer',independent=True,_interpret=lambda _:old)
  for name in ('selected','mandatory','baseline','candidate_scores_sha256','optional'):assert a.get(name)==oracle.get(name)

@pytest.mark.parametrize('raw,kwargs',[
 (JEANS,{'lower_material':('cotton',)}),
 (COTTON,{'upper_category':'vest'}),
 (COTTON,{'upper_material':('denim',),'lower_material':('cotton',)}),
])
def test_misleading_names_cannot_substitute_for_wrong_qualified_facts(raw,kwargs,monkeypatch):
 rows=fixture_rows(**kwargs);monkeypatch.setattr(core,'rows_from_catalog',lambda *_:rows)
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 data=current.document(raw,current.propose(raw));fn=core.select if raw==JEANS else context_selection.select;interpret=lambda _:copy.deepcopy(data)
 decisions=[fn(scope,raw,'wearer',**kw,_interpret=interpret) for kw in ({},{'engine':'compact_exhaustive'},{'independent':True})]
 assert decisions[0]==decisions[1]==decisions[2] and decisions[0]['status']=='NoMatchingCandidates'

@pytest.mark.parametrize('colours,expected',[('black or white','Pass'),('white or red','Fail')])
def test_colour_or_is_same_member_and_independently_admitted(colours,expected):
 raw='I need either a '+colours+' shirt.';data=current.document(raw,current.propose(raw));rows=fixture_rows()
 by_id={r.snapshot.garment_id:r for r in rows};key=(('upper',rows[0].snapshot.garment_id),('lower',rows[1].snapshot.garment_id))
 groups_=data['hard_intent']['conditions']['groups']
 assert core.first_hard(key,groups_,by_id,'scope')==core.independent_hard(key,groups_,by_id,'scope')==expected

def enable(monkeypatch):
 enable_previous(monkeypatch);monkeypatch.setenv(ENV,PROFILE)

def test_authenticated_locked_persistence_receipts_history_and_continuation(mixed,monkeypatch):
 client,_,pid,_,_,_=mixed;enable_previous(monkeypatch)
 old=post(client,pid,'I need jeans.');assert old.status_code==201,old.text;old=old.json()
 enable(monkeypatch)
 assert gateway.open_store(enabled=True).interpretation_version('I need jeans.')==VERSION
 assert client.get('/api/v1/recommendations/capabilities').json()['mixed_wardrobe']['grammar_version']==GRAMMAR
 saved=[]
 for raw in ('I need jeans.',"I need trousers preferably black.","Please choose clothes for studying at a library today."):
  key=uuid.uuid4().hex;r=post(client,pid,raw,key);assert r.status_code==201,r.text;answer=r.json();saved.append(answer)
  p=answer['provenance'][gateway.KEY];assert p['version']=='mixed-personalized-semantic-frames-1.3.0'
  assert p['decision']['intent']['normalization']['original_text']==raw
  assert post(client,pid,raw,key).json()['id']==answer['id']
  assert post(client,pid,'I need a white top.',key).status_code==409
 root=saved[0];action=root['development_continuation']['next_action'];assert action
 child=post(client,pid,root['request_text'],action['submission_key'],refinement=action['refinement']);assert child.status_code==201,child.text;saved.append(child.json())
 assert saved[1]['development_continuation']['next_action'] is None
 store=gateway.open_store(enabled=True)
 for answer in saved:
  proof=answer['provenance'][gateway.KEY]
  assert store.action(answer['id'],{**proof,'ordinal':9}) is None
  with store.connection() as c:
   record=c.execute('select * from phase2nd_mixed_proofs where id=?',(answer['id'],)).fetchone()
   assert store.verify_record(c,record,store.catalog['owner_id'])==proof
   bad=copy.deepcopy(proof);bad['semantic_proposal']['analysis']['coverage'].clear()
   changed={**dict(record),'proof_json':core.encoded(bad).decode(),'proof_sha256':core.digest(bad),'signature':store.sign(bad)}
   with pytest.raises((AttributeRequestError,FixtureError,ValueError)):store.verify_record(c,changed,store.catalog['owner_id'])
 with monkeypatch.context() as m:
  m.setattr(current,'propose',lambda *_:(_ for _ in ()).throw(AssertionError('history reran classifier')))
  for answer in [old,*saved]:assert client.get('/api/v1/chats/'+answer['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200
 assert client.get('/api/v1/chats/'+saved[0]['chat_id'],headers={'X-Wardrobe-Profile-Id':str(uuid.uuid4())}).status_code==404
 def counts():
  with store.connection() as c:return tuple(c.execute('select count(*) from '+t).fetchone()[0] for t in ('recommendations','nlp_chats','recommendation_submissions'))
 before=counts();real=current.propose;calls=[]
 def disagree(raw):
  p=real(raw);calls.append(1)
  if len(calls)==2:p['analysis']['coverage'].clear()
  return p
 with monkeypatch.context() as m:
  m.setattr(current,'propose',disagree)
  with pytest.raises(FixtureError,match='SemanticInterpretationChanged'):store.recommend(store.catalog['owner_id'],pid,'I need jeans.',uuid.uuid4().hex)
 assert len(calls)==2 and counts()==before
 mirror=gateway.mirror
 def fail(*args):mirror(*args);raise RuntimeError('injected rollback')
 with monkeypatch.context() as m:
  m.setattr(gateway,'mirror',fail);assert post(client,pid,'I need jeans.').status_code==503
 assert counts()==before

def test_default_remains_1_1_and_missing_models_refuse(mixed,monkeypatch):
 from app.development.mixed_wardrobe.semantic_constraint_contract import VERSION as OLD
 client,_,pid,_,_,_=mixed;enable_previous(monkeypatch)
 assert gateway.open_store(enabled=True).interpretation_version('I need jeans.')==OLD
 enable(monkeypatch)
 def missing(*_):raise semantic_model.ModelUnavailable('missing models')
 monkeypatch.setattr(semantic_model,'ready',missing)
 r=post(client,pid,'I need jeans.');assert r.status_code==503
