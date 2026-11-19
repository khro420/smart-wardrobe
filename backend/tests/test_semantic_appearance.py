"""Appearance-goal regressions; fresh validation remains outside this module."""
import copy,uuid
from dataclasses import replace
import pytest
from app.development.mixed_wardrobe import semantic_appearance as current,semantic_unified as historical,core,context_selection,gateway
from app.development.mixed_wardrobe.semantic_appearance_contract import PROFILE
from app.domain.value_objects.attribute_conditions import AttributeRequestError
from tests.test_semantic_unified import (projection,fixture_rows,rows_with,enable as previous_enable,mixed,bank,composition_boundary,category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,post)

def enable(monkeypatch):
 previous_enable(monkeypatch);monkeypatch.setenv('SMART_WARDROBE_DEVELOPMENT_SEMANTIC_PROFILE',PROFILE)

def interpret(raw):return current.document(raw,current.propose(raw))

@pytest.mark.parametrize('raw,context,style',[
 ('im going for dating and i want to look sporty','social.date','sporty'),
 ('I want to look sporty.','none','sporty'),
 ("I'd like to look casual.",'none','casual'),
 ('I need to look classic.','none','classic'),
 ('I want to look sporty for shopping.','everyday.shopping','sporty'),
 ('I am going dating and I want to look smart casual.','social.date','smart casual'),
])
def test_owned_goal_and_existing_context_are_complete_mandatory_meanings(raw,context,style):
 d=interpret(raw);p=projection(d)
 assert p['context']==context and p['optional'] is None
 assert p['hard']==[{'role':'all_selected','quantifier':'all_present','predicates':[{'attribute':'style','operator':'contains_any','values':[style]}]}]
 assert d['normalization']['original_text']==raw
 for s in d['original_hard_spans']:assert raw[s['start']:s['end']]==s['text']
 assert any(u['kind']=='appearance_goal' and u['binding']=='own_positive_appearance_goal-1.0.0' for u in d['semantic_proposal']['analysis']['units'])

@pytest.mark.parametrize('raw',[
 'My friend wants to look sporty; recommend an outfit.',
 'I want you to look sporty.',
 "I'd prefer to look sporty.",
 "I don't want to look sporty.",
 'I want to look for sporty clothes.',
 'I want to look at a sporty outfit.',
 'I want to look sportier than yesterday.',
 'I want to look sporty or formal.',
 'I look sporty.',
 'I wanted to look sporty.',
 'Please buy a sporty outfit for me.',
 'I want to look sporty for you to buy clothes.',
 'Recommend an outfit for you to order jeans.',
])
def test_ambiguous_reported_optional_negative_and_purchase_meanings_refuse(raw):
 with pytest.raises(AttributeRequestError):interpret(raw)

@pytest.mark.parametrize('raw',[
 'I want a sporty outfit.',
 "I'd like a short-sleeved top.",
 "I'm studying at the library and I'd prefer black trousers.",
 "I'm going on a date and I want a sporty outfit.",
])
def test_previous_supported_meanings_are_exactly_equivalent(raw):
 assert projection(interpret(raw))==projection(historical.document(raw,historical.propose(raw)))
 assert historical.identity()=='f53bef4649a293652936482c16535f93ac98458b9743c46e93a46780044bfbff'

@pytest.mark.parametrize('missing',[False,True])
def test_neutral_goal_has_exact_three_engine_scores_and_strict_unknown(monkeypatch,missing):
 monkeypatch.setattr(core,'rows_from_catalog',lambda *_:rows_with('sporty',missing))
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 raw='I want to look sporty.';d=interpret(raw);opts={'_interpret':lambda _:copy.deepcopy(d)}
 a=core.select(scope,raw,'wearer',**opts)
 assert a==core.select(scope,raw,'wearer','compact_exhaustive',**opts)==core.select(scope,raw,'wearer',independent=True,**opts)
 assert a['status']==('InsufficientEvidence' if missing else 'Selected')
 control=historical.document('I want a sporty outfit.',historical.propose('I want a sporty outfit.'))
 b=core.select(scope,raw,'wearer',independent=True,_interpret=lambda _:control)
 for name in ('selected','mandatory','candidate_scores_sha256','baseline'):assert a.get(name)==b.get(name)

def test_qualified_sporty_pair_is_not_invented_as_date_suitability(monkeypatch):
 rows=[]
 for row in fixture_rows(upper_category='short_sleeve_top',lower_category='shorts'):
  attrs=copy.deepcopy(row.declaration);attrs['style']=['sporty']
  rows.append(core.FixtureRow(replace(row.snapshot,style_tags=('sporty',)),attrs))
 monkeypatch.setattr(core,'rows_from_catalog',lambda *_:tuple(rows))
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 raw='im going for dating and i want to look sporty';d=interpret(raw);opts={'_interpret':lambda _:copy.deepcopy(d)}
 a=context_selection.select(scope,raw,'wearer',**opts)
 assert a==context_selection.select(scope,raw,'wearer','compact_exhaustive',**opts)==context_selection.select(scope,raw,'wearer',independent=True,**opts)
 assert a['status']=='InsufficientEvidence' and a['mandatory']['passed']==0
 neutral=interpret('I want to look sporty.')
 assert core.select(scope,'I want to look sporty.','wearer',independent=True,_interpret=lambda _:neutral)['status']=='Selected'

def test_controller_and_source_coverage_tampering_refused():
 raw='I want to look sporty.';p=current.propose(raw)
 u=next(u for u in p['analysis']['units'] if u['kind']=='appearance_goal');u['actor_span']=[0,0]
 with pytest.raises(AttributeRequestError):current.document(raw,p)

def test_old_new_authenticated_persistence_history_receipts_and_rollback(mixed,monkeypatch):
 client,_,pid,_,_,_=mixed;previous_enable(monkeypatch)
 old=post(client,pid,"I'd like something casual.");assert old.status_code==201,old.text;old=old.json()
 enable(monkeypatch)
 caps=client.get('/api/v1/recommendations/capabilities');assert caps.status_code==200
 assert caps.json()['mixed_wardrobe']['grammar_version']=='hybrid-semantic-intent-1.4.1'
 raw='I want to look casual.';key=uuid.uuid4().hex;r=post(client,pid,raw,key);assert r.status_code==201,r.text;new=r.json()
 assert new['request_text']==raw and post(client,pid,raw,key).json()['id']==new['id']
 assert post(client,pid,'I need jeans.',key).status_code==409
 store=gateway.open_store(enabled=True)
 with store.connection() as c:
  for a in (old,new):
   row=c.execute('select * from phase2nd_mixed_proofs where id=?',(a['id'],)).fetchone()
   assert store.verify_record(c,row,store.catalog['owner_id'])==a['provenance'][gateway.KEY]
 with monkeypatch.context() as m:
  m.setattr(current,'propose',lambda *_:(_ for _ in ()).throw(AssertionError('History reran inference')))
  for a in (old,new):assert client.get('/api/v1/chats/'+a['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200
 action=new['development_continuation']['next_action'];assert action
 child=post(client,pid,raw,action['submission_key'],refinement=action['refinement']);assert child.status_code==201,child.text
 assert post(client,pid,raw,action['submission_key'],refinement=action['refinement']).json()['id']==child.json()['id']
 def counts():
  with store.connection() as c:return tuple(c.execute('select count(*) from '+t).fetchone()[0] for t in ('recommendations','nlp_chats','recommendation_submissions'))
 before=counts();mirror=gateway.mirror
 def fail(*args):mirror(*args);raise RuntimeError('injected rollback')
 with monkeypatch.context() as m:
  m.setattr(gateway,'mirror',fail);assert post(client,pid,'I need to look casual.').status_code==503
 assert counts()==before
