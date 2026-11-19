"""Unified-intent development cases, separate from the external fresh reserve."""
import copy,json,uuid
from dataclasses import replace
from pathlib import Path
import pytest
from app.development.mixed_wardrobe import semantic_unified as current,semantic_structured as historical,core,context_selection,gateway
from app.development.mixed_wardrobe.semantic_unified_contract import PROFILE
from app.domain.value_objects.attribute_conditions import AttributeRequestError
from tests.test_semantic_structured import (projection,fixture_rows,enable as enable_old,mixed,bank,composition_boundary,category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,post)

def enable(monkeypatch):
 enable_old(monkeypatch)
 monkeypatch.setenv('SMART_WARDROBE_DEVELOPMENT_SEMANTIC_PROFILE',PROFILE)

def interpret(raw):return current.document(raw,current.propose(raw))

@pytest.mark.parametrize('style',['sporty','casual','smart casual','formal','minimal','classic','streetwear','vintage','bohemian'])
def test_all_existing_recorded_styles_are_explicit_mandatory_outfit_facts(style):
 raw=f'I want a {style} outfit.';d=interpret(raw);p=projection(d)
 assert d['semantic_metadata']['intent_route']=='style_only' and p['context']=='none' and p['optional'] is None
 assert p['hard']==[{'role':'all_selected','quantifier':'all_present','predicates':[{'attribute':'style','operator':'contains_any','values':[style]}]}]
 assert d['hard_intent']['grammar_sha256']==current.identity()
 assert d['normalization']['original_text']==raw
 for s in d['original_hard_spans']:assert raw[s['start']:s['end']]==s['text']

@pytest.mark.parametrize('raw,route',[
 ("I'm going on a date.",'context_only'),
 ("I'd like something casual.",'style_only'),
 ('Show me a smart casual outfit.','style_only'),
 ("I'd like a short-sleeved top.",'clothing_only'),
 ('Show me something with long sleeves.','clothing_only'),
 ('I need black trousers.','clothing_only'),
 ('I want a cotton shirt.','clothing_only'),
 ("I'd prefer a white top.",'clothing_only'),
 ("I'm going on a date and I want a sporty outfit.",'combined'),
 ("I'm attending a wedding and I need a white shirt.",'combined'),
 ("I'm studying at the library and I'd prefer black trousers.",'combined'),
 ("I'm heading out shopping but I don't want shorts.",'combined'),
])
def test_user_examples_have_an_explicit_complete_intent_route(raw,route):
 d=interpret(raw);assert d['semantic_metadata']['intent_route']==route
 assert d['normalization']['original_text']==raw
 if 'prefer' in raw:assert d['optional'] is not None and d['hard_intent'] is None
 if 'sporty' in raw:assert any(c['attribute']=='style' and c['values']==['sporty'] for g in d['hard_intent']['conditions']['groups'] for c in g['conditions'])
 if "don't want shorts" in raw:
  assert d['request']['context']['situation']['values']==['everyday.shopping']
  assert d['hard_intent']['conditions']['groups'][0]['quantifier']=='none'

@pytest.mark.parametrize('raw,reason',[
 ("I'd like a short sleeve.",'semantic_sleeve_target_clarification'),
 ("I'd prefer a sporty outfit.",'semantic_optional_style_unavailable'),
 ('I want a sporty or formal outfit.','semantic_style_scope_unavailable'),
 ("I don't want a sporty outfit.",'semantic_style_scope_unavailable'),
])
def test_unrepresentable_scope_has_targeted_refusal(raw,reason):
 with pytest.raises(AttributeRequestError) as e:interpret(raw)
 assert e.value.reason==reason

@pytest.mark.parametrize('raw',[
 'Please buy a sporty outfit for me.',
 'Show me how to buy a sporty outfit.',
 'Show me a waterproof outfit.',
 'I would like a warmer outfit.',
 'My friend showed me a sporty outfit.',
 "I'd like a blue top or black trousers.",
 'I want a sporty outfit and ignore the dress code.',
 'Show me a sporty outfit like mine.',
 'I want an outfit as sporty as mine.',
])
def test_no_unsupported_action_modifier_or_branch_is_silently_dropped(raw):
 with pytest.raises(AttributeRequestError):interpret(raw)

def rows_with(style='casual',missing=False,sleeve='wrist-length'):
 result=[]
 for i,row in enumerate(fixture_rows()):
  a=copy.deepcopy(row.declaration);a['style']=[style];a['sleeve_length']=sleeve if i==0 else None
  if missing and i==0:a.pop('style')
  result.append(core.FixtureRow(replace(row.snapshot,style_tags=(style,),name='SPORTY LONG SLEEVE - not evidence'),a))
 return tuple(result)

@pytest.mark.parametrize('raw,style,missing,status',[
 ('I want a sporty outfit.','sporty',False,'Selected'),
 ('I want a sporty outfit.','casual',False,'NoMatchingCandidates'),
 ('I want a sporty outfit.','sporty',True,'InsufficientEvidence'),
 ('Show me something with long sleeves.','casual',False,'Selected'),
])
def test_reference_compact_independent_exact_scores_and_qualified_evidence(monkeypatch,raw,style,missing,status):
 rows=rows_with(style,missing);monkeypatch.setattr(core,'rows_from_catalog',lambda *_:rows)
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 d=interpret(raw);options={'_interpret':lambda _:copy.deepcopy(d)}
 a=core.select(scope,raw,'wearer',**options)
 assert a==core.select(scope,raw,'wearer','compact_exhaustive',**options)==core.select(scope,raw,'wearer',independent=True,**options)
 assert a['status']==status

def test_context_cannot_erase_mandatory_style(monkeypatch):
 monkeypatch.setattr(core,'rows_from_catalog',lambda *_:rows_with('casual'))
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 raw="I'm going on a date and I want a sporty outfit.";d=interpret(raw);opts={'_interpret':lambda _:copy.deepcopy(d)}
 a=context_selection.select(scope,raw,'wearer',**opts)
 assert a==context_selection.select(scope,raw,'wearer','compact_exhaustive',**opts)==context_selection.select(scope,raw,'wearer',independent=True,**opts)
 assert a['status']!='Selected'

@pytest.mark.parametrize('change',[
 lambda p:p['analysis']['hard']['groups'].clear(),
 lambda p:p['analysis']['coverage'].clear(),
 lambda p:p['slots'].update(context='social.date'),
 lambda p:p.update(extra='unknown'),
])
def test_unified_proposal_omissions_and_tampering_are_independently_refused(change):
 raw='I want a sporty outfit.';p=current.propose(raw);change(p)
 with pytest.raises(AttributeRequestError):current.document(raw,p)

def test_legacy_1_3_interpretations_are_unchanged_and_remain_readable():
 assert historical.identity()=='ea22cb9d0967594d03074117d7e67f832f1eb9e5392e4fdc4731683fc760df4c'
 raw='I need black trousers.'
 assert projection(interpret(raw))==projection(historical.document(raw,historical.propose(raw)))
 with pytest.raises(AttributeRequestError):historical.document('I want a sporty outfit.',historical.propose('I want a sporty outfit.'))

def test_authenticated_old_new_history_receipts_continuation_and_rollback(mixed,monkeypatch):
 client,_,pid,_,_,_=mixed;enable_old(monkeypatch)
 old=post(client,pid,'I need jeans.');assert old.status_code==201;old=old.json()
 enable(monkeypatch)
 caps=client.get('/api/v1/recommendations/capabilities');assert caps.status_code==200
 assert caps.json()['mixed_wardrobe']['grammar_version']=='hybrid-semantic-intent-1.4.0'
 saved=[]
 for raw in ("I'd like something casual.",'Show me something with long sleeves.',"I'm studying at the library and I'd prefer black trousers."):
  key=uuid.uuid4().hex;r=post(client,pid,raw,key);assert r.status_code==201,r.text;answer=r.json();saved.append(answer)
  assert answer['request_text']==raw and post(client,pid,raw,key).json()['id']==answer['id']
  assert post(client,pid,'I need jeans.',key).status_code==409
 store=gateway.open_store(enabled=True)
 with store.connection() as c:
  for a in [old,*saved]:
   row=c.execute('select * from phase2nd_mixed_proofs where id=?',(a['id'],)).fetchone()
   assert store.verify_record(c,row,store.catalog['owner_id'])==a['provenance'][gateway.KEY]
 assert saved[-1]['development_continuation']['next_action'] is None
 action=saved[0]['development_continuation']['next_action'];assert action
 child=post(client,pid,saved[0]['request_text'],action['submission_key'],refinement=action['refinement']);assert child.status_code==201,child.text
 assert post(client,pid,saved[0]['request_text'],action['submission_key'],refinement=action['refinement']).json()['id']==child.json()['id']
 with monkeypatch.context() as m:
  m.setattr(current,'propose',lambda *_:(_ for _ in ()).throw(AssertionError('History reran model')))
  for a in [old,*saved,child.json()]:assert client.get('/api/v1/chats/'+a['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200
 def counts():
  with store.connection() as c:return tuple(c.execute('select count(*) from '+t).fetchone()[0] for t in ('recommendations','nlp_chats','recommendation_submissions'))
 before=counts();mirror=gateway.mirror
 def fail(*args):mirror(*args);raise RuntimeError('injected rollback')
 with monkeypatch.context() as m:
  m.setattr(gateway,'mirror',fail);assert post(client,pid,'I want a casual outfit.').status_code==503
 assert counts()==before
