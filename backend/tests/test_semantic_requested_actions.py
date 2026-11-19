"""Exposed action/occasion regressions, never the external validation reserve."""
import copy,uuid
import pytest
from app.development.mixed_wardrobe import semantic_structured as current,core,context_selection,gateway
from app.domain.value_objects.attribute_conditions import AttributeRequestError
from tests.test_semantic_structured import (projection,fixture_rows,enable,mixed,bank,composition_boundary,category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,post)

@pytest.mark.parametrize('raw',[
 "I'm going shopping for clothes.",
 'What should I wear to go shopping?',
 "I'm heading to the mall to buy some shoes.",
])
def test_task_shopping_occasions_have_no_purchase_target_hard_conditions(raw):
 d=current.document(raw,current.propose(raw))
 assert d['request']['context']['situation']['values']==['everyday.shopping']
 assert d['hard_intent'] is None and d['optional'] is None
 assert d['semantic_proposal']['analysis']['requested_actions']['actions']

@pytest.mark.parametrize('raw',[
 'Please buy a striped shirt for me.','Can you order jeans online?',
 'I want you to buy jeans.','Recommend an outfit and purchase black trousers.',
 'Recommend jeans to buy.',"I'm told to buy shoes; recommend an outfit.",
 'If I buy a shirt, recommend an outfit.','I need an outfit provided that I purchase jeans.',
 'Please recommend an outfit for "buying jeans".',
 'Please shop for me.',"Don't buy me shorts.",
 "I don't buy shoes; recommend an outfit.",
 "I'm buying jeans and I want to wear them.",
])
def test_unsupported_requested_actions_reported_quotes_conditionals_and_references_refuse(raw):
 with pytest.raises(AttributeRequestError):current.document(raw,current.propose(raw))

@pytest.mark.parametrize('raw',[
 "Don't buy me anything; just recommend an outfit.",
 'Do not purchase a blue shirt. Recommend an outfit.',
 "Don't order anything; what outfit should I wear?",
])
def test_negated_assistant_purchase_does_not_prohibit_clothes(raw):
 d=current.document(raw,current.propose(raw));assert 'context' not in d['request']
 assert d['hard_intent'] is None and d['optional'] is None
 a=d['semantic_proposal']['analysis']['requested_actions']['actions']
 assert len(a)==1 and a[0]['kind']=='excluded_assistant_action'
 assert d['normalization']['original_text']==raw

@pytest.mark.parametrize('raw',[
 "I'm going to buy cotton trousers; I need a black shirt.",
 'Recommend an outfit for buying a cotton top; I need a black shirt.',
])
def test_purchase_targets_do_not_become_wardrobe_constraints(raw):
 d=current.document(raw,current.propose(raw));groups=d['hard_intent']['conditions']['groups']
 assert len(groups)==1 and groups[0]['role']=='upper'
 assert sorted((c['attribute'],c['values']) for c in groups[0]['conditions'])==[('category',['long_sleeve_top','short_sleeve_top']),('primary_colour',['black'])]
 assert d['request']['context']['situation']['values']==['everyday.shopping']
 a=d['semantic_proposal']['analysis']['requested_actions']['actions'][0]
 assert a['kind']=='user_shopping_activity' and a['targets']
 for s in d['original_hard_spans']:assert raw[s['start']:s['end']]==s['text']

@pytest.mark.parametrize('raw,attributes',[
 ('I need jeans for shopping.',{'category','material'}),
 ('Suggest blue trousers for shopping.',{'category','primary_colour'}),
])
def test_existing_garment_requirement_for_activity_is_preserved(raw,attributes):
 d=current.document(raw,current.propose(raw));assert d['request']['context']['situation']['values']==['everyday.shopping']
 assert {c['attribute'] for g in d['hard_intent']['conditions']['groups'] for c in g['conditions']}==attributes

@pytest.mark.parametrize('raw',[
 'Can you suggest clothes for buying books?',
 'Please recommend clothing for purchasing a coat.',
 'I need an outfit for a shopping trip.',
 'Shopping trip.',
])
def test_generic_advice_and_registered_nominal_activity_remain_supported(raw):
 d=current.document(raw,current.propose(raw))
 assert d['request']['context']['situation']['values']==['everyday.shopping'] and d['hard_intent'] is None

@pytest.mark.parametrize('missing',[False,True])
def test_purchase_context_keeps_exact_scores_and_strict_unknown(monkeypatch,missing):
 raw="I'm going to buy a jacket; I need a cotton shirt.";d=current.document(raw,current.propose(raw))
 rows=fixture_rows(missing=(0,'material') if missing else None);monkeypatch.setattr(core,'rows_from_catalog',lambda *_:rows)
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 interpret=lambda _:copy.deepcopy(d)
 a=context_selection.select(scope,raw,'wearer',_interpret=interpret);b=context_selection.select(scope,raw,'wearer','compact_exhaustive',_interpret=interpret);c=context_selection.select(scope,raw,'wearer',independent=True,_interpret=interpret)
 assert a==b==c and a['status']==('InsufficientEvidence' if missing else 'Selected')
 if not missing:
  ref="I'm going shopping; I need a cotton shirt.";control=current.document(ref,current.propose(ref))
  oracle=context_selection.select(scope,ref,'wearer',independent=True,_interpret=lambda _:control)
  for field in ('selected','mandatory','baseline','candidate_scores_sha256','optional'):assert a.get(field)==oracle.get(field)

def test_action_proof_source_tampering_refused():
 raw="Don't buy a blue shirt; recommend an outfit.";p=current.propose(raw)
 p['analysis']['requested_actions']['actions'][0]['kind']='user_shopping_activity'
 with pytest.raises(AttributeRequestError):current.document(raw,p)

def test_purchase_purpose_is_not_erased_as_a_product():
 raw="I'm buying shoes for a wedding. What should I wear?"
 with pytest.raises(AttributeRequestError):current.document(raw,current.propose(raw))

def test_excluded_purchase_purpose_is_not_an_outfit_occasion():
 raw="Don't buy a shirt for a wedding; just recommend an outfit."
 d=current.document(raw,current.propose(raw));assert 'context' not in d['request'] and d['hard_intent'] is None
 a=d['semantic_proposal']['analysis']['requested_actions']['actions'][0]
 assert a['targets'][0]['text']=='a shirt'
 assert a['oblique_arguments'][0]['text']=='a wedding'

def test_authenticated_activity_and_excluded_action_history(mixed,monkeypatch):
 client,_,pid,_,_,_=mixed;enable(monkeypatch)
 for raw in ("I'm going shopping for clothes.","Don't buy me anything; just recommend an outfit."):
  key=uuid.uuid4().hex;r=post(client,pid,raw,key);assert r.status_code==201,r.text;answer=r.json()
  assert answer['request_text']==raw
  assert post(client,pid,raw,key).json()['id']==answer['id']
  assert post(client,pid,'I need jeans.',key).status_code==409
  with monkeypatch.context() as m:
   m.setattr(current,'propose',lambda *_:(_ for _ in ()).throw(AssertionError('History reclassified action')))
   h=client.get('/api/v1/chats/'+answer['chat_id'],headers={'X-Wardrobe-Profile-Id':pid});assert h.status_code==200
  s=gateway.open_store(enabled=True)
  with s.connection() as c:
   row=c.execute('select * from phase2nd_mixed_proofs where id=?',(answer['id'],)).fetchone()
   assert s.verify_record(c,row,s.catalog['owner_id'])==answer['provenance'][gateway.KEY]

@pytest.mark.parametrize('raw,role,attributes',[
 ("I'm off to the mall to purchase a few books. I need a white top.",'upper',{'primary_colour'}),
 ("We're off to the shops to buy some gifts. I need black trousers.",'lower',{'category','primary_colour'}),
 ("I'm off to the mall to purchase a blue shirt. I need black trousers.",'lower',{'category','primary_colour'}),
 ("I'm off to the mall to buy a present; I need jeans.",'lower',{'category','material'}),
])
def test_self_departure_and_purchase_purpose_keep_independent_garment_requirements(raw,role,attributes):
 d=current.document(raw,current.propose(raw))
 assert d['request']['context']['situation']['values']==['everyday.shopping']
 groups=d['hard_intent']['conditions']['groups']
 assert len(groups)==1 and groups[0]['role']==role
 assert {c['attribute'] for c in groups[0]['conditions']}==attributes
 assert any(c['reason']=='shopping_departure_carrier' for c in d['semantic_proposal']['analysis']['requested_actions']['coverage'])
 if role=='lower':
  assert all(c['values']!=['blue'] for c in groups[0]['conditions'])
 assert d['normalization']['original_text']==raw

@pytest.mark.parametrize('raw',[
 "I'm off duty; buy a white shirt for me.",
 "You're off to the mall to buy books; recommend an outfit.",
 "I'm off to the mall to steal a shirt; recommend an outfit.",
 "I'm not off to the mall to buy books; recommend an outfit.",
 "I'm off to the mall to buy books if it rains; recommend an outfit.",
 'Please buy white shirts; I need black trousers.',
 'Tell me to buy books at the mall.',
 'My friend is off to the mall to buy books; suggest an outfit.',
])
def test_departure_is_not_permission_for_foreign_negated_or_unsupported_actions(raw):
 with pytest.raises(AttributeRequestError):current.document(raw,current.propose(raw))

def test_departure_source_coverage_is_independently_reconstructed():
 raw="I'm off to the mall to buy books; I need jeans."
 proposal=current.propose(raw)
 coverage=proposal['analysis']['requested_actions']['coverage']
 carrier=next(c for c in coverage if c['reason']=='shopping_departure_carrier')
 assert proposal['analysis']['normalization']['normalized_text'][carrier['start']:carrier['end']]=='off'
 carrier['end']+=3
 with pytest.raises(AttributeRequestError):current.document(raw,proposal)

@pytest.mark.parametrize('missing',[False,True])
def test_departure_purchase_scores_and_unknown_match_the_existing_context(monkeypatch,missing):
 raw="I'm off to the mall to buy books; I need a cotton shirt."
 d=current.document(raw,current.propose(raw))
 monkeypatch.setattr(core,'rows_from_catalog',lambda *_:fixture_rows(missing=(0,'material') if missing else None))
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 options={'_interpret':lambda _:copy.deepcopy(d)}
 a=context_selection.select(scope,raw,'wearer',**options)
 assert a==context_selection.select(scope,raw,'wearer','compact_exhaustive',**options)==context_selection.select(scope,raw,'wearer',independent=True,**options)
 assert a['status']==('InsufficientEvidence' if missing else 'Selected')
 control=current.document('I am going shopping; I need a cotton shirt.',current.propose('I am going shopping; I need a cotton shirt.'))
 expected=context_selection.select(scope,raw,'wearer',independent=True,_interpret=lambda _:control)
 for key in ('selected','mandatory','baseline','candidate_scores_sha256','optional'):assert a.get(key)==expected.get(key)

def test_authenticated_departure_preserves_frozen_history_and_receipts(mixed,monkeypatch):
 client,_,pid,_,_,_=mixed;enable(monkeypatch)
 raw="I'm off to the mall to purchase a few books."
 key=uuid.uuid4().hex;r=post(client,pid,raw,key);assert r.status_code==201,r.text
 answer=r.json();assert answer['request_text']==raw
 assert post(client,pid,raw,key).json()['id']==answer['id']
 assert post(client,pid,'Please buy books for me.',key).status_code==409
 store=gateway.open_store(enabled=True)
 with store.connection() as c:
  row=c.execute('select * from phase2nd_mixed_proofs where id=?',(answer['id'],)).fetchone()
  assert store.verify_record(c,row,store.catalog['owner_id'])==answer['provenance'][gateway.KEY]
 monkeypatch.setattr(current,'propose',lambda *_:(_ for _ in ()).throw(AssertionError('History reran the model')))
 assert client.get('/api/v1/chats/'+answer['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200
