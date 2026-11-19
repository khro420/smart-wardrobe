"""Exposed stabilization regressions; external fresh reserve stays separate."""
import copy,uuid
import pytest
from app.development.mixed_wardrobe import semantic_structured as current,core,context_selection,gateway
from app.domain.value_objects.attribute_conditions import AttributeRequestError
from tests.test_semantic_structured import (projection,fixture_rows,enable,mixed,bank,composition_boundary,category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,post)

@pytest.mark.parametrize('raw',[
 'We are going shopping to buy a few gifts. I need black trousers.',
 "We're going shopping to purchase a few books. I need black trousers.",
 'We are shopping to buy a present. I need black trousers.',
 'We are going to buy shoes; I need black trousers.',
 "We're off to the mall to purchase a few books; I need black trousers.",
])
def test_auxiliary_actor_and_nested_shopping_purpose_keep_mandatory_lower(raw):
 d=current.document(raw,current.propose(raw));p=projection(d)
 assert p['context']=='everyday.shopping' and p['optional'] is None
 assert p['hard']==[{'role':'lower','quantifier':'exists','predicates':[
  {'attribute':'category','operator':'in','values':['trousers']},
  {'attribute':'primary_colour','operator':'in','values':['black']}]}]
 actions=d['semantic_proposal']['analysis']['requested_actions']['actions']
 assert actions and all(a['actor']=='user' and a['kind']=='user_shopping_activity' for a in actions)
 text=d['normalization']['normalized_text']
 assert all(text[x:y]=='we' for a in actions for x,y in a['actor_spans'])

@pytest.mark.parametrize('raw',[
 'Can you buy black trousers for me?',
 'We asked you to buy books; recommend an outfit.',
 'We are going shopping; buy black trousers for us.',
 'We are not going shopping to buy books; suggest an outfit.',
 'They are going shopping to buy books; suggest an outfit.',
 'We are going shopping to steal jeans; suggest an outfit.',
])
def test_participants_never_license_assistant_foreign_or_unresolved_actions(raw):
 with pytest.raises(AttributeRequestError):current.document(raw,current.propose(raw))

@pytest.mark.parametrize('raw',[
 "I'd like either a grey or black shirt.",
 'I would like either a black or grey shirt.',
 "I'd like a grey or black shirt.",
 "I'd like either a grey shirt or a black shirt.",
])
def test_polite_modal_desire_is_one_hard_same_member_or_with_original_spans(raw):
 d=current.document(raw,current.propose(raw));p=projection(d)
 assert p['context']=='none' and p['optional'] is None
 assert p['hard']==[{'role':'upper','quantifier':'exists','predicates':[
  {'attribute':'category','operator':'in','values':['long_sleeve_top','short_sleeve_top']},
  {'attribute':'primary_colour','operator':'in','values':['black','grey']}]}]
 assert d['normalization']['original_text']==raw
 for s in d['original_hard_spans']:assert raw[s['start']:s['end']]==s['text']
 assert any(u.get('request_command',{}).get('binding')=='positive_modal_desire_object_v1' for u in d['semantic_proposal']['analysis']['units'])

@pytest.mark.parametrize('raw',[
 "I'd like either a grey shirt or black trousers.",
 'I would like black trousers or a white skirt.',
 "I'd like either a cotton shirt or a wool shirt.",
 'I like either a black or grey shirt.',
 "I wouldn't like a black shirt.",
 "I'd like no shorts.",
 "My friend said I'd like a black shirt.",
 'I would like a waterproof shirt.',
])
def test_modal_desire_does_not_license_unsupported_or_ambiguous_meanings(raw):
 # Material OR is already representable for a single member; unlike the
 # other cases it remains a supported exact set-valued material predicate.
 if raw=="I'd like either a cotton shirt or a wool shirt.":
  p=projection(current.document(raw,current.propose(raw)))
  assert p['hard'][0]['predicates']==[
   {'attribute':'category','operator':'in','values':['long_sleeve_top','short_sleeve_top']},
   {'attribute':'material','operator':'contains_any','values':['cotton','wool']}]
 else:
  with pytest.raises(AttributeRequestError):current.document(raw,current.propose(raw))

@pytest.mark.parametrize('missing',[False,True])
def test_polite_or_and_shopping_requirements_have_three_engine_exact_agreement(monkeypatch,missing):
 monkeypatch.setattr(core,'rows_from_catalog',lambda *_:fixture_rows(missing=(0,'material') if missing else None))
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 raw='We are going shopping to buy gifts. I would like a cotton shirt.'
 d=current.document(raw,current.propose(raw));interpret=lambda _:copy.deepcopy(d)
 a=context_selection.select(scope,raw,'wearer',_interpret=interpret)
 assert a==context_selection.select(scope,raw,'wearer','compact_exhaustive',_interpret=interpret)==context_selection.select(scope,raw,'wearer',independent=True,_interpret=interpret)
 assert a['status']==('InsufficientEvidence' if missing else 'Selected')
 material=next(p for g in d['hard_intent']['conditions']['groups'] for p in g['conditions'] if p['attribute']=='material')
 assert material['operator']=='contains_any' and material['values']==['cotton']

def test_stabilized_proposals_remain_independently_bound():
 raw="I'd like either a grey or black shirt.";p=current.propose(raw)
 unit=next(u for u in p['analysis']['units'] if 'request_command' in u)
 unit['request_command']['actor_span']=[0,0]
 with pytest.raises(AttributeRequestError):current.document(raw,p)

def test_authenticated_new_grammar_original_text_history_and_receipts(mixed,monkeypatch):
 client,_,pid,_,_,_=mixed;enable(monkeypatch)
 caps=client.get('/api/v1/recommendations/capabilities');assert caps.status_code==200
 assert caps.json()['mixed_wardrobe']['grammar_version']=='hybrid-semantic-intent-1.3.0'
 raw='We are going shopping to buy a few gifts. I need black trousers.'
 key=uuid.uuid4().hex;r=post(client,pid,raw,key);assert r.status_code==201,r.text;answer=r.json()
 assert answer['request_text']==raw and post(client,pid,raw,key).json()['id']==answer['id']
 assert post(client,pid,'I need jeans.',key).status_code==409
 store=gateway.open_store(enabled=True)
 with store.connection() as c:
  row=c.execute('select * from phase2nd_mixed_proofs where id=?',(answer['id'],)).fetchone()
  assert store.verify_record(c,row,store.catalog['owner_id'])==answer['provenance'][gateway.KEY]
 monkeypatch.setattr(current,'propose',lambda *_:(_ for _ in ()).throw(AssertionError('History reran model')))
 assert client.get('/api/v1/chats/'+answer['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200
