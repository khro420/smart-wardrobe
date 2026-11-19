"""Development regressions only; the sealed 2U-A reserve is external."""
import copy,json,uuid
import pytest
from app.development.mixed_wardrobe import semantic_structured as current,core,gateway
from app.development.mixed_wardrobe.store import Store,FixtureError
from app.domain.value_objects.attribute_conditions import AttributeRequestError
from tests.test_semantic_structured import (projection,fixture_rows,enable,mixed,bank,composition_boundary,category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,post)

KNOWN="Don't include shorts; I need trousers, preferably blue."

@pytest.mark.parametrize('raw',[
 KNOWN,
 'Do not include any shorts. I need trousers preferably blue.',
 "Please don't include shorts. I need trousers, preferably blue.",
 "Could you not include shorts? I need trousers, preferably blue.",
])
def test_validated_negative_command_equivalence_and_complete_spans(raw):
 data=current.document(raw,current.propose(raw))
 reference="I don't want shorts; I need trousers, preferably blue."
 assert projection(data)==projection(current.document(reference,current.propose(reference)))
 assert data['normalization']['original_text']==raw
 units=[u for u in data['semantic_proposal']['analysis']['units'] if u.get('negative_command')]
 assert len(units)==1 and units[0]['negative_command']['lemma']=='include'
 assert units[0]['negative_command']['group_id']=='g01'
 assert data['hard_intent']['conditions']['groups'][0]['quantifier']=='none'
 assert data['optional']['role']=='lower' and data['optional']['resolution']['state']=='Active'
 for key in ('original_hard_spans','original_optional_spans'):
  for s in data[key]:assert raw[s['start']:s['end']]==s['text']

@pytest.mark.parametrize('raw,reference',[
 ("Don't include a blue shirt.","I don't want a blue shirt."),
 ('Do not include anything red.',"I don't want anything red."),
 ("Don't include jeans.","I don't want jeans."),
 ("Don't suggest shorts.","I don't want shorts."),
])
def test_command_preserves_same_member_global_and_jeans_semantics(raw,reference):
 a=current.document(raw,current.propose(raw));b=current.document(reference,current.propose(reference))
 assert projection(a)==projection(b)

@pytest.mark.parametrize('raw',[
 "Don't bleach shorts; I need trousers.",
 "Don't destroy a blue top.",
 "I can't include shorts.",
 "You don't include shorts.",
 "I was told not to include shorts.",
 "I don't need shorts.",
 "Don't include shorts unless I am indoors.",
 "Don't include a top that's not black.",
 "Don't include shorts, preferably blue.",
 "Don't include a striped top and a blue shirt.",
 "I don't think you should include shorts.",
])
def test_unknown_actions_noncommands_nested_negation_and_unbound_optional_refuse(raw):
 with pytest.raises(AttributeRequestError):current.document(raw,current.propose(raw))

@pytest.mark.parametrize('missing',[False,True])
def test_strict_unknown_and_three_engine_agreement(monkeypatch,missing):
 data=current.document(KNOWN,current.propose(KNOWN));rows=fixture_rows(missing=(1,'category') if missing else None)
 monkeypatch.setattr(core,'rows_from_catalog',lambda *_:rows)
 scope={'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
 interpret=lambda _:copy.deepcopy(data)
 a=core.select(scope,KNOWN,'wearer',_interpret=interpret);b=core.select(scope,KNOWN,'wearer','compact_exhaustive',_interpret=interpret);c=core.select(scope,KNOWN,'wearer',independent=True,_interpret=interpret)
 assert a==b==c and a['status']==('InsufficientEvidence' if missing else 'Selected')
 if not missing:
  reference="I don't want shorts; I need trousers, preferably blue."
  control=current.document(reference,current.propose(reference))
  oracle=core.select(scope,reference,'wearer',independent=True,_interpret=lambda _:control)
  for name in ('selected','mandatory','baseline','candidate_scores_sha256','optional'):assert a.get(name)==oracle.get(name)

@pytest.mark.parametrize('mutation',[
 lambda p:p['analysis']['units'][0]['negative_command'].update(lemma='bleach'),
 lambda p:p['analysis']['units'][0]['negative_command'].update(group_id='g02'),
 lambda p:p['analysis']['coverage'].clear(),
])
def test_negative_command_binding_is_independently_reconstructed(mutation):
 p=current.propose(KNOWN);mutation(p)
 with pytest.raises(AttributeRequestError):current.document(KNOWN,p)

def test_authenticated_negative_write_history_receipts_and_locked_revalidation(mixed,monkeypatch):
 client,_,pid,_,_,_=mixed;enable(monkeypatch);key=uuid.uuid4().hex
 r=post(client,pid,KNOWN,key);assert r.status_code==201,r.text;answer=r.json()
 proof=answer['provenance'][gateway.KEY];assert answer['request_text']==KNOWN
 assert proof['decision']['intent']['optional']['role']=='lower'
 assert post(client,pid,KNOWN,key).json()['id']==answer['id']
 assert post(client,pid,'I need a blue top.',key).status_code==409
 assert answer['development_continuation']['next_action'] is None
 store=gateway.open_store(enabled=True)
 with store.connection() as c:
  row=c.execute('select * from phase2nd_mixed_proofs where id=?',(answer['id'],)).fetchone()
  assert store.verify_record(c,row,store.catalog['owner_id'])==proof
  bad=copy.deepcopy(proof);bad['semantic_proposal']['analysis']['units'][0]['negative_command']['group_id']='g02'
  row={**dict(row),'proof_json':core.encoded(bad).decode(),'proof_sha256':core.digest(bad),'signature':store.sign(bad)}
  with pytest.raises(AttributeRequestError):store.verify_record(c,row,store.catalog['owner_id'])
 with monkeypatch.context() as m:
  m.setattr(current,'propose',lambda *_:(_ for _ in ()).throw(AssertionError('History reclassified input')))
  assert client.get('/api/v1/chats/'+answer['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200
 def counts():
  with store.connection() as c:return tuple(c.execute('select count(*) from '+t).fetchone()[0] for t in ('recommendations','nlp_chats','recommendation_submissions'))
 before=counts();real=current.propose;calls=[]
 def changed(raw):
  p=real(raw);calls.append(1)
  if len(calls)==2:p['analysis']['units'][0]['negative_command']['group_id']='g02'
  return p
 with monkeypatch.context() as m:
  m.setattr(current,'propose',changed)
  with pytest.raises(FixtureError,match='SemanticInterpretationChanged'):store.recommend(store.catalog['owner_id'],pid,KNOWN,uuid.uuid4().hex)
 assert len(calls)==2 and counts()==before
