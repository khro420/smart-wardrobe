"""Qualified facts, never garment labels, satisfy the two reported requests."""
import copy,json,uuid
from dataclasses import replace
import pytest
from app.development.mixed_wardrobe import core,context_selection,gateway,semantic_model,semantic_frames,semantic_constraints as current
from app.development.mixed_wardrobe.semantic_constraint_contract import VERSION,GRAMMAR
from app.development.mixed_wardrobe.store import Store
from app.development.main_fixture.store import FixtureError
from app.domain.value_objects.attribute_conditions import AttributeRequestError
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from tests.test_semantic_frames import (proposal,condition,enable,mixed,bank,composition_boundary,category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,post)

JEANS="I need jeans and I'd prefer a black top."
COTTON="I'm studying in the library tomorrow, and I need a cotton shirt."

@pytest.fixture(scope='module')
def interpretations():return {raw:current.document(raw,semantic_model.propose(raw)) for raw in (JEANS,COTTON)}

def predicates(data):return [(g['role'],g['quantifier'],c['attribute'],c['operator'],c['values']) for g in data['hard_intent']['conditions']['groups'] for c in g['conditions']]

def test_exact_real_model_hard_and_optional_meanings(interpretations):
 jeans=interpretations[JEANS];cotton=interpretations[COTTON]
 assert predicates(jeans)==[('lower','exists','category','in',['trousers']),('lower','exists','material','contains_any',['denim'])]
 assert jeans['optional']['role']=='upper' and jeans['optional']['resolution']['state']=='Active'
 assert [(c['attribute'],c['values']) for c in jeans['optional']['predicates']]==[('primary_colour',['black'])]
 assert predicates(cotton)==[('upper','exists','material','contains_any',['cotton']),('upper','exists','category','in',['long_sleeve_top','short_sleeve_top'])]
 assert cotton['optional'] is None
 assert cotton['request']['context']['situation']['values']==['academic.library_study']
 assert cotton['request']['context']['temporal']['values']==['tomorrow']
 for raw,data in interpretations.items():
  assert data['normalization']['original_text']==raw and data['grammar_version']==GRAMMAR
  for s in data['original_hard_spans']:assert raw[s['start']:s['end']]==s['text']

def fixture_rows(upper_category='long_sleeve_top',upper_material=('cotton',),lower_category='trousers',lower_material=('denim',),missing=None):
 from tests.test_context_relevance_ranking import rows
 result=[]
 for g,category,material in ((rows()[0],upper_category,upper_material),(rows()[3],lower_category,lower_material)):
  g=replace(g,category=category,structural_role=GARMENT_STRUCTURE[category][0],layering_index=GARMENT_STRUCTURE[category][1],material=material,
            name='COTTON SHIRT - name is not evidence' if len(result)==0 else 'JEANS - name is not evidence')
  a={'category':category,'material':list(material) if material is not None else None,'primary_colour':'black' if len(result)==0 else 'blue','style':['casual'],'pattern':'plain'}
  if missing and missing[0]==len(result):a.pop(missing[1])
  result.append(core.FixtureRow(g,a))
 return tuple(result)

@pytest.mark.parametrize('raw,kwargs,status',[
 (JEANS,{},'Selected'),(JEANS,{'lower_material':('cotton',)},'NoMatchingCandidates'),
 (JEANS,{'lower_material':None},'InsufficientEvidence'),(JEANS,{'missing':(1,'material')},'InsufficientEvidence'),
 (JEANS,{'lower_category':'shorts'},'NoMatchingCandidates'),
 (COTTON,{},'Selected'),(COTTON,{'upper_category':'short_sleeve_top'},'Selected'),
 (COTTON,{'upper_category':'vest'},'NoMatchingCandidates'),(COTTON,{'upper_category':'sling'},'NoMatchingCandidates'),
 (COTTON,{'upper_material':('denim',),'lower_material':('cotton',)},'NoMatchingCandidates'),
 (COTTON,{'upper_material':None},'InsufficientEvidence'),(COTTON,{'missing':(0,'material')},'InsufficientEvidence'),
 (COTTON,{'missing':(0,'category')},'InsufficientEvidence'),
])
def test_misleading_names_missing_facts_and_three_engine_agreement(interpretations,monkeypatch,raw,kwargs,status):
 rows=fixture_rows(**kwargs);monkeypatch.setattr(core,'rows_from_catalog',lambda *_:rows)
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 fn=core.select if raw==JEANS else context_selection.select
 interpret=lambda _:copy.deepcopy(interpretations[raw])
 a=fn(scope,raw,'wearer',_interpret=interpret);b=fn(scope,raw,'wearer','compact_exhaustive',_interpret=interpret);c=fn(scope,raw,'wearer',independent=True,_interpret=interpret)
 assert a==b==c and a['status']==status
 if status=='Selected':assert a['selected']['key']==[['upper',rows[0].snapshot.garment_id],['lower',rows[1].snapshot.garment_id]]

@pytest.mark.parametrize('raw,quote,kind,category,expected',[
 ('I need a black or white shirt.','a black or white shirt','hard','vest','Fail'),
 ('I need a black or white shirt.','a black or white shirt','hard','long_sleeve_top','Pass'),
 ("I don't want a cotton shirt.",'a cotton shirt','exclude','vest','Pass'),
 ("I don't want a cotton shirt.",'a cotton shirt','exclude','long_sleeve_top','Fail'),
])
def test_category_is_in_the_same_or_negative_group(raw,quote,kind,category,expected):
 d=current.document(raw,proposal(raw,conditions=[condition(quote,kind)]));rows=fixture_rows(upper_category=category)
 byid={r.snapshot.garment_id:r for r in rows};key=(('upper',rows[0].snapshot.garment_id),('lower',rows[1].snapshot.garment_id))
 groups=d['hard_intent']['conditions']['groups'];assert len(groups)==1
 assert core.first_hard(key,groups,byid,'test')==core.independent_hard(key,groups,byid,'test')==expected

def test_frozen_predecessor_is_not_silently_redefined():
 p=proposal('I need a cotton shirt.',conditions=[condition('a cotton shirt')])
 before=semantic_frames.document(p['source_text'],p);after=current.document(p['source_text'],p)
 assert not any(c['attribute']=='category' for g in before['hard_intent']['conditions']['groups'] for c in g['conditions'])
 assert before['grammar_sha256']==semantic_frames.identity() and after['grammar_sha256']==current.identity()
 assert before['grammar_sha256']!=after['grammar_sha256']
 with pytest.raises(AttributeRequestError):current.document('I need jeans.',proposal('I need jeans.',conditions=[]))

@pytest.mark.parametrize('raw,conditions',[
 ('I need grey trousers, not a grey shirt.',[condition('grey trousers'),condition('a grey shirt','exclude')]),
])
def test_plain_shirt_and_multi_role_scope_keep_existing_predicates(raw,conditions):
 p=proposal(raw,conditions=conditions);old=semantic_frames.document(raw,p);new=current.document(raw,p)
 groups=new['hard_intent']['conditions']['groups']
 before=old['hard_intent']['conditions']['groups'] if old['hard_intent'] else []
 for a,b in zip(before,groups):
  assert (a['id'],a['role'],a['quantifier'])==(b['id'],b['role'],b['quantifier'])
  assert b['conditions'][:len(a['conditions'])]==a['conditions']
 upper=next(g for g in groups if g['role']=='upper')
 assert upper['conditions'][-1]['values']==list(current.SHIRT_CATEGORIES)
 if before:assert groups[0]==before[0] and upper['quantifier']=='none'

def test_untyped_shirt_keeps_the_existing_explicit_refusal():
 raw='I need a shirt.';p=proposal(raw,conditions=[condition('a shirt')])
 for document in (semantic_frames.document,current.document):
  with pytest.raises(AttributeRequestError,match='language_unsupported_requirement'):document(raw,p)

def test_authenticated_independent_write_history_tamper_receipts_and_old_reader(mixed,monkeypatch):
 from app.development.mixed_wardrobe.semantic_constraint_contract import GRAMMAR as CURRENT_GRAMMAR
 client,_,pid,_,_,_=mixed;enable(monkeypatch)
 from app.development.mixed_wardrobe.semantic_frame_contract import VERSION as OLD
 with monkeypatch.context() as m:
  m.setattr(Store,'interpretation_version',lambda *_:OLD)
  old=post(client,pid,COTTON);assert old.status_code==201,old.text;old=old.json()
 s=gateway.open_store(enabled=True)
 for raw in (JEANS,COTTON):
  key=uuid.uuid4().hex;response=post(client,pid,raw,key);assert response.status_code==201,response.text
  answer=response.json();p=answer['provenance'][gateway.KEY]
  assert p['version']=='mixed-personalized-semantic-frames-1.1.0' and p['decision']['intent']['grammar_version']==CURRENT_GRAMMAR
  assert post(client,pid,raw,key).json()['id']==answer['id']
  assert post(client,pid,'Recommend an outfit.',key).status_code==409
  with s.connection() as c:
   record=c.execute('select * from phase2nd_mixed_proofs where id=?',(answer['id'],)).fetchone()
   assert s.verify_record(c,record,s.catalog['owner_id'])==p
   assert p['decision']['selected']['score']['weights']==[{'numerator':3,'denominator':5},{'numerator':1,'denominator':5},{'numerator':1,'denominator':5}]
   if raw==COTTON:
    bad=copy.deepcopy(p);groups=bad['decision']['intent']['hard_intent']['conditions']['groups'];groups[0]['conditions']=[c for c in groups[0]['conditions'] if c['attribute']!='category']
    row={**dict(record),'proof_json':core.encoded(bad).decode(),'proof_sha256':core.digest(bad),'signature':s.sign(bad)}
    with pytest.raises(FixtureError,match='IndependentFixtureHistoryMismatch'):s.verify_record(c,row,s.catalog['owner_id'])
  with monkeypatch.context() as m:
   m.setattr(semantic_model,'propose',lambda *_:(_ for _ in ()).throw(AssertionError('History reclassified input')))
   history=client.get('/api/v1/chats/'+answer['chat_id'],headers={'X-Wardrobe-Profile-Id':pid})
   assert history.status_code==200 and history.json()['recommendation']['provenance'][gateway.KEY]==p
 assert client.get('/api/v1/chats/'+old['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200
 def counts():
  with s.connection() as c:return tuple(c.execute('select count(*) from '+t).fetchone()[0] for t in ('recommendations','nlp_chats','recommendation_submissions'))
 before=counts()
 def changed():
  with s.connection() as c:c.execute('update phase2nd_instance set catalog_sha256=?',('0'*64,))
 with pytest.raises(FixtureError,match='ChangedFixtureAuthority'):
  s.recommend(s.catalog['owner_id'],pid,COTTON,uuid.uuid4().hex,before_lock=changed)
 assert counts()==before
