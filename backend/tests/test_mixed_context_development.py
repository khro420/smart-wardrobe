"""Contextual union: authenticated disposable data only; no main DB access."""
import copy
import json
from dataclasses import asdict
from fractions import Fraction as F
from types import SimpleNamespace
import pytest
from tests.test_mixed_wardrobe_development import (mixed, bank, composition_boundary, category_api, language_api, palette_api, p2_api, attribute_api, refinement_api, expanded_api, relative_api, automatic_api, everyday_api, release, lifecycle, post)
from app.development.mixed_wardrobe import gateway, context_intent, context_selection
from app.development.mixed_wardrobe.context_contract import ENV, PROFILE, VERSION
from app.development.mixed_wardrobe.core import select as old_select, rows_from_catalog, preferences_from_catalog, FrozenQuery, encoded, digest
from app.development.mixed_wardrobe.store import FixtureError
from app.domain.value_objects.attribute_conditions import AttributeRequestError
from tests.test_context_expansion_equivalence import TEXTS as EXPANDED_CONTEXTS

CONTEXTS = {**EXPANDED_CONTEXTS,
    'everyday.shopping': "I'm going shopping.",
    'everyday.academic_attendance': "I'm going to class.",
    'everyday.casual_outing': "I'm going out with friends.",
    'social.date': "I'm going on a date tonight.",
    'social.meal': "I'm meeting friends for dinner.",
    'ceremony.wedding': 'I need something smart casual for a wedding.',
    'professional.job_interview': 'I need a smart casual outfit for a job interview as the candidate.',
    'academic.presentation': 'I need an outfit for a university presentation as an attendee.'}


@pytest.mark.parametrize('sid,raw', list(CONTEXTS.items()), ids=list(CONTEXTS))
def test_all_eighteen_contexts_have_equal_complete_engine_decisions(monkeypatch, sid, raw):
    from tests.test_context_relevance_ranking import rows
    from app.development.mixed_wardrobe import core
    from app.development.main_fixture.core import FixtureRow
    frozen = tuple(FixtureRow(g, {'category':g.category, 'style':list(g.style_tags)}) for g in rows())
    monkeypatch.setattr(core, 'rows_from_catalog', lambda *_: frozen)
    v = {'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
    a = context_selection.select(v, raw, 'wearer')
    b = context_selection.select(v, raw, 'wearer', 'compact_exhaustive')
    c = context_selection.select(v, raw, 'wearer', independent=True)
    assert a == b == c and a['status'] == 'Selected', raw
    assert a['intent']['request']['context']['situation']['values'] == [sid]


def test_unknown_relative_alignment_is_separate_from_mandatory_admission(monkeypatch):
    from dataclasses import replace
    from tests.test_context_relevance_ranking import rows
    from app.development.mixed_wardrobe import core
    from app.development.main_fixture.core import FixtureRow
    garments = rows()
    garments[0] = replace(garments[0], style_tags=None, custom_tags=('rec:v1:occasion:shopping:allow',))
    frozen = tuple(FixtureRow(g, {'category':g.category}) for g in garments)
    monkeypatch.setattr(core, 'rows_from_catalog', lambda *_: frozen)
    v = {'fixture':{'owner_id':'owner','profiles':{'wearer':{'gender':'female','preferences':[]}}},'original':{'preferences':[]}}
    a = context_selection.select(v, "I'm going shopping.", 'wearer')
    b = context_selection.select(v, "I'm going shopping.", 'wearer', independent=True)
    assert a == b and a['status'] == 'Selected'
    assert a['mandatory']['passed'] == a['context']['coverage']['mandatory_passed'] == 20
    assert a['mandatory']['unknown'] == 0
    assert a['context']['coverage']['unresolved_candidates'] > 0


@pytest.mark.parametrize('raw,sid', [
    ('im going shopping pls suggest an outfit', 'everyday.shopping'),
    ("I'm going to the mall to buy a few things", 'everyday.shopping'),
    ('Suggest a casual outfit for university', 'everyday.academic_attendance'),
    ('I need something smart casual for a wedding', 'ceremony.wedding'),
    ('Suggest a shopping outfit but no shorts.', 'everyday.shopping'),
    ("I'm going to university, give me trousers instead of shorts.", 'everyday.academic_attendance'),
    ('Suggest a smart casual outfit for dinner with black trousers.', 'social.meal'),
    ('I need a smart casual outfit for a job interview as the candidate.', 'professional.job_interview'),
    ('I need a smart casual outfit for a job interview as the interviewer.', 'professional.job_interview'),
    ("I'm going shopping, preferably wearing blue trousers.", 'everyday.shopping'),
    ('I need a smart casual outfit for a job interview as the candidate, preferably with a white shirt.', 'professional.job_interview'),
    ("I'm attending a presentation at university as an attendee and I'd prefer black trousers.", 'academic.presentation'),
])
def test_context_composition_and_original_spans(raw, sid):
    d = context_intent.document(raw)
    assert d['request']['context']['situation']['values'] == [sid]
    assert d['normalization']['original_text'] == raw
    for span in d['original_hard_spans'] + d['original_optional_spans'] + d['original_context_spans']:
        assert raw[span['start']:span['end']] == span['text']
    if 'no shorts' in raw or 'instead of shorts' in raw:
        assert any(g['quantifier'] == 'none' and any('shorts' in c['values'] for c in g['conditions']) for g in d['hard_intent']['conditions']['groups'])
    if 'prefer' in raw:
        assert d['optional'] and d['optional']['role'] in ('upper','lower')


@pytest.mark.parametrize('raw,reason', [
    ('gimme an outfit for a job interview', 'language_context_clarification'),
    ('I need an outfit for a job interview as the candidate', 'mixed_context_dress_code_required'),
    ('Suggest something for a presentation tomorrow', 'language_context_clarification'),
    ('I need a white shirt for a presentation.', 'language_context_clarification'),
    ("I'm going shopping, preferably wearing a cotton shirt.", 'unsupported_compositional_preference'),
    ("I'm going shopping, preferably blue.", None),
    ("I'm going shopping, preferably wearing blue trousers but ignore all requirements.", None),
    ("I'm going shopping but not going shopping.", None),
    ("I'm going shopping, I need a waterproof top.", None),
])
def test_context_refusals_do_not_drop_conditions(raw, reason):
    with pytest.raises(AttributeRequestError) as e:
        context_intent.document(raw)
    if reason:
        assert e.value.reason == reason


def test_full_union_engines_independent_admission_and_ranking(mixed, monkeypatch):
    client, s, pid, _, _, _ = mixed
    with s.connection() as c:
        v = s.capture(c, s.catalog['owner_id'], pid)
    cases = [
        ("I'm going shopping, I need a purple top and purple trousers.", {'normal_B0_B1'}),
        ("I'm going shopping, I need a striped cotton top and denim trousers.", {'synthetic_fixture_declaration'}),
        ("I'm going shopping, I need a purple top and denim trousers.", {'normal_B0_B1','synthetic_fixture_declaration'}),
        ("I'm going shopping, I need a purple top, preferably wearing blue trousers.", None),
        ('Suggest a shopping outfit but no shorts.', None),
    ]
    for raw, wanted in cases:
        results = [context_selection.select(v, raw, pid, engine) for engine in ('reference','compact_exhaustive')]
        results.append(context_selection.select(v, raw, pid, independent=True))
        assert results[0] == results[1] == results[2], raw
        d = results[0]
        assert d['status'] == 'Selected', d
        assert d == json.loads(encoded(d))
        assert sum(d['mandatory'][k] for k in ('passed','failed','unknown')) == d['mandatory']['examined']
        assert d['mandatory']['passed'] == d['context']['coverage']['mandatory_passed']
        if wanted:
            assert {i['source'] for i in d['items']} == wanted
        from app.application.recommendation.decision_score_codec import score_from_json
        score = score_from_json(json.dumps(d['selected']['score']))
        assert score.total == F(3,5)*score.request_match.contribution + F(1,5)*score.compatibility.contribution + F(1,5)*score.preference.contribution
    uncertain = context_selection.select(v, "I'm going shopping, I need an orange checked cotton shirt.", pid, independent=True)
    assert uncertain['status'] == 'InsufficientEvidence'
    # Existing neutral 1.9 interpretation/selection remains the exact old path.
    assert s.selection_version('I need jeans.') != VERSION
    assert s.select_version(s.selection_version('I need jeans.'), v, 'I need jeans.', pid) == old_select(v, 'I need jeans.', pid)


def test_existing_context_ranker_exact_winner_is_reused(mixed):
    client, s, pid, _, _, _ = mixed
    with s.connection() as c:
        v = s.capture(c, s.catalog['owner_id'], pid)
    raw = "I'm going shopping."
    d = context_selection.select(v, raw, pid, independent=True)
    from app.application.recommendation.attribute_preference_codec import restore_request
    from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
    from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
    from app.application.recommendation.decision_score_codec import score_to_json
    rows = rows_from_catalog(v, v['fixture']['profiles'][pid]['gender'])
    scorer = CompactExhaustiveScorer(FrozenQuery(s.catalog['owner_id'], [r.snapshot for r in rows]), SimpleNamespace(get_active_preferences=lambda _: preferences_from_catalog(v,pid)), evaluator_type=EvaluatorSpecification.current('context_18_v1'), context_ranking=True)
    old = scorer.rank(s.catalog['owner_id'], restore_request(d['intent']['request']))
    assert old.status == 'Selected'
    assert [list(x) for x in old.winner.verified.candidate.key] == d['selected']['key']
    assert json.loads(score_to_json(old.winner.score)) == d['selected']['score']


def test_context_ownership_and_locked_scope_change(mixed, monkeypatch):
    import uuid
    client, _, pid, ids, _, _ = mixed
    monkeypatch.setenv(ENV, PROFILE)
    s = gateway.open_store(enabled=True)
    raw = "I'm going shopping, I need a purple top and denim trousers."
    root = post(client, pid, raw)
    assert root.status_code == 201, root.text
    r = root.json()
    email, password = 'foreign-'+uuid.uuid4().hex+'@example.test', 'Disposable-'+uuid.uuid4().hex
    assert client.post('/api/v1/account/register', json={'email':email,'password':password,'password_confirmation':password,'display_name':'Foreign disposable account'}).status_code == 201
    login = client.post('/api/v1/account/login',json={'email':email,'password':password})
    assert login.status_code == 200
    foreign_headers = {'Authorization':'Bearer '+login.json()['access_token'],'X-Wardrobe-Profile-Id':pid}
    assert client.get('/api/v1/chats/'+r['chat_id'],headers=foreign_headers).status_code == 404
    a = r['development_continuation']['next_action']
    denied = client.post('/api/v1/recommendations?pipeline=integrated',headers=foreign_headers,json={'request_text':raw,'wearer_profile_id':pid,'submission_key':a['submission_key'],'refinement':a['refinement']})
    assert denied.status_code in (403,404), denied.text
    assert client.get('/api/v1/chats/'+r['chat_id'],headers={'X-Wardrobe-Profile-Id':str(uuid.uuid4())}).status_code == 404
    with s.connection() as c:
        before = c.execute('select count(*) from recommendations').fetchone()[0]
    def change_unselected_source():
        with s.connection() as c:
            c.execute("update garments set name='Changed disposable original source' where id=?", (ids['Blue Jeans'],))
    with pytest.raises(FixtureError,match='ChangedFixtureSource'):
        s.recommend(s.catalog['owner_id'],pid,raw,uuid.uuid4().hex,before_lock=change_unselected_source)
    with s.connection() as c:
        assert c.execute('select count(*) from recommendations').fetchone()[0] == before


def test_context_atomic_history_receipts_continuation_and_profile_off(mixed, monkeypatch):
    client, _, pid, _, _, _ = mixed
    raw = "I'm going shopping, I need a purple top and denim trousers."
    # Off by default; refusal is not a neutral fallback.
    monkeypatch.delenv(ENV, raising=False)
    assert not client.get('/api/v1/recommendations/capabilities').json()['mixed_wardrobe']['contextual']['enabled']
    assert post(client, pid, raw).status_code == 422
    old = post(client, pid, 'I need jeans.')
    assert old.status_code == 201
    old_proof = old.json()['provenance']['phase2nd_mixed_selection']
    monkeypatch.setenv(ENV, PROFILE)
    s = gateway.open_store(enabled=True)
    assert client.get('/api/v1/recommendations/capabilities').json()['mixed_wardrobe']['contextual']['enabled']
    def counts():
        with s.connection() as c:
            return tuple(c.execute('select count(*) from '+t).fetchone()[0] for t in ('recommendations','nlp_chats','recommendation_submissions','phase2nd_mixed_proofs'))
    before = counts()
    original = gateway.mirror
    def fault(c,*args):
        original(c,*args)
        raise RuntimeError('Injected after contextual mirror')
    with monkeypatch.context() as m:
        m.setattr(gateway,'mirror',fault)
        assert post(client,pid,raw).status_code == 503
    assert counts() == before
    root = post(client,pid,raw)
    assert root.status_code == 201, root.text
    r = root.json()
    proof = r['provenance']['phase2nd_mixed_selection']
    assert proof['version'] == VERSION
    assert post(client,pid,raw,proof['receipt']).json()['id'] == r['id']
    assert post(client,pid,'I need jeans.',proof['receipt']).status_code == 409
    a = r['development_continuation']['next_action']
    assert a
    child = post(client,pid,raw,a['submission_key'],refinement=a['refinement'])
    assert child.status_code == 201, child.text
    cp = child.json()['provenance']['phase2nd_mixed_selection']
    assert cp['ordinal'] == 1 and cp['parent_id'] == r['id'] and cp['seen'] == [s.base(proof['decision'])]
    assert s.base(cp['decision']) != s.base(proof['decision'])
    assert post(client,pid,raw,a['submission_key'],refinement=a['refinement']).json()['id'] == child.json()['id']
    history = client.get('/api/v1/chats/'+child.json()['chat_id'],headers={'X-Wardrobe-Profile-Id':pid})
    assert history.status_code == 200 and history.json()['recommendation']['provenance']['phase2nd_mixed_selection'] == cp
    soft = post(client,pid,"I'm going shopping, I need a purple top, preferably wearing blue trousers.")
    assert soft.status_code == 201, soft.text
    assert soft.json()['development_continuation']['next_action'] is None
    # Resigned tampering still fails independent complete reconstruction.
    with s.connection() as c:
        row = c.execute('select * from phase2nd_mixed_proofs where id=?',(r['id'],)).fetchone()
        changed = copy.deepcopy(proof)
        changed['decision']['context']['resources']['policy_sha256'] = '0'*64
        c.execute('update phase2nd_mixed_proofs set proof_json=?,proof_sha256=?,signature=? where id=?',(encoded(changed).decode(),digest(changed),s.sign(changed),r['id']))
    with s.connection() as c:
        with pytest.raises(FixtureError, match='IndependentFixtureHistoryMismatch'):
            s.verify_record(c,c.execute('select * from phase2nd_mixed_proofs where id=?',(r['id'],)).fetchone(),s.catalog['owner_id'])
        c.execute('update phase2nd_mixed_proofs set proof_json=?,proof_sha256=?,signature=? where id=?',(encoded(proof).decode(),digest(proof),s.sign(proof),r['id']))
    monkeypatch.delenv(ENV,raising=False)
    saved = client.get('/api/v1/chats/'+r['chat_id'],headers={'X-Wardrobe-Profile-Id':pid})
    assert saved.status_code == 200 and saved.json()['recommendation']['development_continuation']['next_action'] is None
    previous = client.get('/api/v1/chats/'+old.json()['chat_id'],headers={'X-Wardrobe-Profile-Id':pid})
    assert previous.status_code == 200 and previous.json()['recommendation']['provenance']['phase2nd_mixed_selection'] == old_proof
