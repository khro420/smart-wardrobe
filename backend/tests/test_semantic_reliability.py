"""Scope projection, strict facts and additive proof compatibility; no live data."""
from pathlib import Path
import copy,json,uuid
import pytest
from app.development.mixed_wardrobe import semantic_reliability as current,semantic_model,semantic_constraints as previous,core,gateway
from app.development.mixed_wardrobe.store import Store,FixtureError
from app.domain.value_objects.attribute_conditions import AttributeRequestError
from tests.test_semantic_frames import (enable as enable_previous,mixed,bank,composition_boundary,category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,post)
from tests.test_semantic_constraint_verification import fixture_rows

CASES=json.loads((Path(__file__).with_name('fixtures')/'semantic_scope_regressions.v1.json').read_text())['cases']
CONTEXT_CASES=json.loads((Path(__file__).with_name('fixtures')/'semantic_scope_regressions.v1.json').read_text())['context_cases']

def enable(monkeypatch):
 from app.development.mixed_wardrobe.semantic_frame_contract import ENV
 from app.development.mixed_wardrobe.semantic_reliability_contract import PROFILE
 enable_previous(monkeypatch);monkeypatch.setenv(ENV,PROFILE)

@pytest.mark.parametrize('case',CONTEXT_CASES,ids=lambda c:c['id'])
def test_context_modifiers_are_not_erased_before_nli(case):
 p=current.propose(case['text']);record=p['context_projection']
 assert all(word in record['focus'] for word in case['required_focus_terms'])
 assert p['slots']['context']==case['expected_context']
 d=current.document(case['text'],p)
 assert d['request']['context']['situation']['values']==[case['expected_context']]
 broken=copy.deepcopy(p);broken['context_projection']['focus']='different source'
 with pytest.raises(AttributeRequestError):current.document(case['text'],broken)

@pytest.mark.parametrize('case',CASES,ids=lambda c:c['id'])
def test_discovery_cases_are_regressions_not_held_out(case):
 p=current.propose(case['text'])
 assert p['base_slots']!=p['slots'] and p['scope_changes']
 assert p['slots']['conditions']==[{'quote':case['hard_quote'],'kind':'hard'},{'quote':'preferably black','kind':'optional'}]
 if case.get('known_downstream_refusal'):
  with pytest.raises(AttributeRequestError,match=case['known_downstream_refusal']):current.document(case['text'],p)
 else:
  d=current.document(case['text'],p)
  assert d['optional']['resolution']['state']==case['expected_resolution']
  assert d['optional']['role']=='lower'
  assert {c['attribute'] for g in d['hard_intent']['conditions']['groups'] for c in g['conditions']}=={'category','primary_colour'}

@pytest.mark.parametrize('raw,role,state',[
 ('I need a cotton top, preferably blue.','upper','Active'),
 ('I need red trousers, preferably blue.','lower','ContradictedByHard'),
 ('I need grey trousers, preferably grey.','lower','EntailedByHard'),
])
def test_new_regression_variants_are_exact_not_phrase_exceptions(raw,role,state):
 d=current.document(raw,current.propose(raw))
 assert d['optional']['role']==role and d['optional']['resolution']['state']==state
 assert d['normalization']['original_text']==raw
 for name in ('original_hard_spans','original_optional_spans'):
  for s in d[name]:assert raw[s['start']:s['end']]==s['text']

@pytest.mark.parametrize('raw',[
 "I don't want shorts, preferably black.",
 'I need trousers, preferably black or blue.',
 'I need trousers, preferably cotton.',
 'I need trousers, preferably very black.',
 "I'd prefer a blue top and trousers, preferably black.",
 'I need trousers, preferably black and a waterproof shirt.',
])
def test_no_invented_anchor_optional_or_material_or_discarded_requirements(raw):
 p=current.propose(raw)
 assert not p['scope_changes']
 with pytest.raises(AttributeRequestError):current.document(raw,p)

@pytest.mark.parametrize('mutation',[
 lambda p:p.update(extra=True),lambda p:p['identity'].update(scope_projection='unknown'),
 lambda p:p['slots']['conditions'].pop(),lambda p:p.update(scope_changes=[]),
 lambda p:p.update(source_text='different'),lambda p:p['base_slots']['conditions'].clear(),
])
def test_untrusted_scope_and_source_tampering_refused(mutation):
 raw='I need trousers, preferably black.';p=current.propose(raw);mutation(p)
 with pytest.raises(AttributeRequestError):current.document(raw,p)

@pytest.mark.parametrize('unknown',[False,True])
def test_three_engines_and_unchanged_qualification(monkeypatch,unknown):
 raw='I need trousers, preferably black.';p=current.propose(raw);d=current.document(raw,p)
 rows=fixture_rows(missing=(1,'category') if unknown else None)
 monkeypatch.setattr(core,'rows_from_catalog',lambda *_:rows)
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 interpret=lambda _:copy.deepcopy(d)
 a=core.select(scope,raw,'wearer',_interpret=interpret);b=core.select(scope,raw,'wearer','compact_exhaustive',_interpret=interpret);c=core.select(scope,raw,'wearer',independent=True,_interpret=interpret)
 assert a==b==c and a['status']==('InsufficientEvidence' if unknown else 'Selected')
 if not unknown:
  from app.application.nlp.compositional_request_v1 import CompositionalIntent
  oracle=core.select(scope,raw,'wearer',independent=True,_interpret=lambda _:CompositionalIntent.capture(raw).to_dict())
  for k in ('selected','mandatory','baseline','candidate_scores_sha256','optional'):assert a[k]==oracle[k]

def test_authenticated_new_and_frozen_proofs_and_locked_reextraction(mixed,monkeypatch):
 client,_,pid,_,_,_=mixed;enable(monkeypatch)
 from app.development.mixed_wardrobe.semantic_constraint_contract import VERSION as OLD
 with monkeypatch.context() as m:
  m.setattr(Store,'interpretation_version',lambda *_:OLD)
  old=post(client,pid,'I need a cotton shirt.');assert old.status_code==201,old.text;old=old.json()
 raw='I need trousers, preferably black.';key=uuid.uuid4().hex
 response=post(client,pid,raw,key);assert response.status_code==201,response.text;answer=response.json()
 p=answer['provenance'][gateway.KEY]
 assert p['version']=='mixed-personalized-semantic-frames-1.2.0'
 assert p['semantic_proposal']['scope_changes'] and p['decision']['intent']['optional']['role']=='lower'
 assert post(client,pid,raw,key).json()['id']==answer['id']
 assert post(client,pid,'I need jeans.',key).status_code==409
 assert answer['development_continuation']['next_action'] is None
 with monkeypatch.context() as m:
  m.setattr(current,'propose',lambda *_:(_ for _ in ()).throw(AssertionError('History reran extraction')))
  for r in (old,answer):assert client.get('/api/v1/chats/'+r['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200
 s=gateway.open_store(enabled=True)
 def counts():
  with s.connection() as c:return tuple(c.execute('select count(*) from '+t).fetchone()[0] for t in ('recommendations','nlp_chats','recommendation_submissions'))
 before=counts();real=current.propose;calls=[]
 def disagree(raw):
  value=real(raw);calls.append(1)
  if len(calls)==2:value['scope_changes'].append({'untrusted':'write-lock disagreement'})
  return value
 with monkeypatch.context() as m:
  m.setattr(current,'propose',disagree)
  with pytest.raises(FixtureError,match='SemanticInterpretationChanged'):
   s.recommend(s.catalog['owner_id'],pid,raw,uuid.uuid4().hex)
 assert len(calls)==2 and counts()==before

def test_candidate_is_opt_in_and_does_not_replace_verified_default(mixed,monkeypatch):
 from app.development.mixed_wardrobe.semantic_frame_contract import ENV,PROFILE as OLD_PROFILE
 from app.development.mixed_wardrobe.semantic_constraint_contract import VERSION as OLD_VERSION
 from app.development.mixed_wardrobe.semantic_reliability_contract import VERSION,GRAMMAR
 client,_,_,_,_,_=mixed;enable(monkeypatch)
 assert gateway.open_store(enabled=True).interpretation_version('I need jeans.')==VERSION
 assert client.get('/api/v1/recommendations/capabilities').json()['mixed_wardrobe']['grammar_version']==GRAMMAR
 monkeypatch.setenv(ENV,OLD_PROFILE)
 assert gateway.open_store(enabled=True).interpretation_version('I need jeans.')==OLD_VERSION
