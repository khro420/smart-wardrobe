"""Independent canonical meanings; authentic disposable persistence, no live POST."""
from pathlib import Path
import copy
import json
import uuid
import pytest
from tests.test_mixed_context_development import (mixed, bank, composition_boundary, category_api, language_api, palette_api, p2_api, attribute_api, refinement_api, expanded_api, relative_api, automatic_api, everyday_api, release, lifecycle, post)
from app.development.mixed_wardrobe import context_language as language, context_intent as previous, context_selection as selection, gateway, core
from app.development.mixed_wardrobe.context_contract import ENV as CONTEXT_ENV, PROFILE as CONTEXT_PROFILE, VERSION as PREVIOUS_VERSION
from app.development.mixed_wardrobe.context_language_contract import ENV, PROFILE, VERSION
from app.development.mixed_wardrobe.store import FixtureError
from app.domain.value_objects.attribute_conditions import AttributeRequestError
from app.application.recommendation.attribute_preference_codec import restore_request
from app.application.recommendation.general_context_evaluator import EvaluatorSpecification

BANK = json.loads((Path(__file__).with_name('fixtures')/'phase2p_context_requests.v1.json').read_text())['cases']


def meaning(d):
    request, optional = d['request'], d['optional']
    groups = []
    for g in d['hard_intent']['conditions']['groups'] if d['hard_intent'] else []:
        groups.append({'role':g['role'],'quantifier':g['quantifier'],'conditions':sorted([{k:v for k,v in c.items() if k!='id'} for c in g['conditions']],key=lambda x:json.dumps(x,sort_keys=True))})
    plan = EvaluatorSpecification.current('context_18_v1').construct().plan(restore_request(request))
    return {'request':{k:v for k,v in request.items() if k!='context'},
            'slots':{k:{'state':v['state'],'values':v['values']} for k,v in request['context'].items() if isinstance(v,dict) and 'state' in v},
            'hard_groups':sorted(groups,key=lambda x:json.dumps(x,sort_keys=True)),
            'optional':None if optional is None else {'role':optional['role'],'quantifier':optional['quantifier'],'predicates':[{k:v for k,v in c.items() if k!='id'} for c in optional['predicates']],'resolution':optional['resolution']['state']},
            'policy_binding':plan.binding.identifier,'predicate':plan.predicate.identifier,'secondary':[p.binding.identifier for _,p in plan.secondary]}


@pytest.mark.parametrize('case', BANK, ids=[c['id'] for c in BANK])
def test_independently_authored_request_meanings_and_raw_spans(case):
    if case['expected']=='Refused':
        with pytest.raises(AttributeRequestError):
            language.document(case['raw'])
        return
    d = language.document(case['raw'])
    assert language.contextual(case['raw'])
    assert d['request']['context']['situation']['values'] == [case['situation']]
    assert meaning(d) == meaning(previous.document(case['canonical']))
    assert d['normalization']['original_text'] == case['raw']
    m = d['normalization']
    assert len(m['character_map'])==len(m['normalized_text'])
    assert all(0<=a<=b<=len(case['raw']) for a,b in m['character_map'])
    for span in d['original_hard_spans']+d['original_optional_spans']+d['original_context_spans']:
        assert case['raw'][span['start']:span['end']] == span['text']
    for t in m['transformations']:
        if 'raw_start' in t:
            assert case['raw'][t['raw_start']:t['raw_end']] == t['raw_text']
    if case['group']=='phase2o':
        # Exact old semantic interpretation, not just a generated response.
        assert d['request'] == previous.document(case['raw'])['request']


REPRESENTATIVES = []
for case in BANK:
    if case['expected']=='Supported' and (case['group'] not in ('paraphrase','phase2o') or case['situation'] not in {c['situation'] for c in REPRESENTATIVES}):
        REPRESENTATIVES.append(case)


@pytest.mark.parametrize('case', REPRESENTATIVES, ids=[c['id'] for c in REPRESENTATIVES])
def test_exact_candidate_scores_winners_and_three_engines(case, monkeypatch):
    from tests.test_context_relevance_ranking import rows
    from app.development.main_fixture.core import FixtureRow
    frozen = tuple(FixtureRow(g, {'category':g.category,'primary_colour':g.primary_colour,'style':list(g.style_tags),'pattern':'plain','material':['cotton']}) for g in rows())
    monkeypatch.setattr(core,'rows_from_catalog',lambda *_:frozen)
    v = {'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
    before = selection.select(v,case['canonical'],'wearer',independent=True)
    a = selection.select(v,case['raw'],'wearer',_interpret=language.document)
    b = selection.select(v,case['raw'],'wearer','compact_exhaustive',_interpret=language.document)
    c = selection.select(v,case['raw'],'wearer',independent=True,_interpret=language.document)
    assert a==b==c
    for key in ('status','mandatory','candidate_scores_sha256','baseline','selected','eligible_promotion_count','optional','explanation'):
        assert a.get(key)==before.get(key)
    assert json.loads(core.encoded(a))==a


def test_registered_source_map_and_rule_tampering_refused(monkeypatch,tmp_path):
    path=tmp_path/'rules.json';path.write_bytes(language.RESOURCE.read_bytes()+b' ')
    monkeypatch.setattr(language,'RESOURCE',path)
    with pytest.raises(ValueError,match='Unregistered semantic'):
        language.document("I'm running shopping errands.")


def test_authenticated_versions_history_and_continuation_keep_parent_contract(mixed,monkeypatch):
    client,_,pid,_,_,_=mixed
    monkeypatch.setenv(CONTEXT_ENV,CONTEXT_PROFILE);monkeypatch.delenv(ENV,raising=False)
    old_raw="I'm going shopping, I need a purple top and denim trousers."
    old=post(client,pid,old_raw);assert old.status_code==201,old.text
    oldp=old.json()['provenance']['phase2nd_mixed_selection'];assert oldp['version']==PREVIOUS_VERSION
    monkeypatch.setenv(ENV,PROFILE)
    cap=client.get('/api/v1/recommendations/capabilities').json()
    assert cap['mixed_wardrobe']['contextual']['language_expansion']['enabled']
    # Upgrade must not reinterpret a v2 parent's existing action as v3.
    action=old.json()['development_continuation']['next_action']
    old_child=post(client,pid,old_raw,action['submission_key'],refinement=action['refinement'])
    assert old_child.status_code==201,old_child.text
    assert old_child.json()['provenance']['phase2nd_mixed_selection']['version']==PREVIOUS_VERSION
    raw='IM RUNNING SHOPPING ERRANDS, I NEED A PURPLE TOP AND DENIM TROUSERS.'
    s=gateway.open_store(enabled=True)
    with s.connection() as conn:v=s.capture(conn,s.catalog['owner_id'],pid)
    expected=selection.select(v,old_raw,pid,independent=True)
    result=post(client,pid,raw);assert result.status_code==201,result.text
    r=result.json();p=r['provenance']['phase2nd_mixed_selection'];assert p['version']==VERSION and p['raw']==raw
    assert p['decision']['selected']==expected['selected'] and p['decision']['candidate_scores_sha256']==expected['candidate_scores_sha256']
    assert post(client,pid,raw,p['receipt']).json()['id']==r['id']
    assert post(client,pid,old_raw,p['receipt']).status_code==409
    action=r['development_continuation']['next_action'];assert action
    child=post(client,pid,raw,action['submission_key'],refinement=action['refinement']);assert child.status_code==201,child.text
    cp=child.json()['provenance']['phase2nd_mixed_selection'];assert cp['version']==VERSION and cp['ordinal']==1 and cp['seen']==[s.base(p['decision'])]
    history=client.get('/api/v1/chats/'+child.json()['chat_id'],headers={'X-Wardrobe-Profile-Id':pid})
    assert history.status_code==200 and history.json()['request_text']==raw and history.json()['recommendation']['provenance']['phase2nd_mixed_selection']==cp
    assert post(client,pid,raw,action['submission_key'],refinement=action['refinement']).json()['id']==child.json()['id']
    monkeypatch.delenv(ENV,raising=False)
    assert client.get('/api/v1/chats/'+r['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).json()['recommendation']['development_continuation']['next_action'] is None
    assert client.get('/api/v1/chats/'+old.json()['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).json()['recommendation']['development_continuation']['next_action']


def test_semantic_optional_atomic_rollback_and_resigned_map_tamper(mixed,monkeypatch):
    client,_,pid,_,_,_=mixed
    monkeypatch.setenv(CONTEXT_ENV,CONTEXT_PROFILE);monkeypatch.setenv(ENV,PROFILE)
    s=gateway.open_store(enabled=True)
    def counts():
        with s.connection() as c:return tuple(c.execute('select count(*) from '+t).fetchone()[0] for t in ('recommendations','nlp_chats','recommendation_submissions'))
    raw="I'm running shopping errands, I need a purple top, preferably wearing blue trousers."
    before=counts();mirror=gateway.mirror
    def fault(c,*args):mirror(c,*args);raise RuntimeError('Injected semantic mirror rollback')
    with monkeypatch.context() as m:
        m.setattr(gateway,'mirror',fault);assert post(client,pid,raw).status_code==503
    assert counts()==before
    answer=post(client,pid,raw);assert answer.status_code==201,answer.text
    r=answer.json();p=r['provenance']['phase2nd_mixed_selection'];assert p['decision']['intent']['optional'] and r['development_continuation']['next_action'] is None
    changed=copy.deepcopy(p);changed['decision']['intent']['normalization']['character_map'][0]=[0,len(raw)]
    with s.connection() as c:c.execute('update phase2nd_mixed_proofs set proof_json=?,proof_sha256=?,signature=? where id=?',(core.encoded(changed).decode(),core.digest(changed),s.sign(changed),r['id']))
    with s.connection() as c:
        with pytest.raises(FixtureError,match='IndependentFixtureHistoryMismatch'):
            s.verify_record(c,c.execute('select * from phase2nd_mixed_proofs where id=?',(r['id'],)).fetchone(),s.catalog['owner_id'])
