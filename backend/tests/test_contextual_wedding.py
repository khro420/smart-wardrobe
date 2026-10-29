"""Independent labelled evidence rules, real disposable APIs and old-profile boundaries."""
from dataclasses import asdict, replace
from fractions import Fraction
from itertools import product
import json
from pathlib import Path
import uuid
import pytest
from app.application.nlp.contextual_nlp_interpreter import ContextualNLPInterpreter
from app.application.nlp.nlp_interpreter import NLPInterpreter
from app.application.recommendation.contextual_suitability_evaluator import ContextualSuitabilityEvaluator
from app.application.recommendation.contextual_selection import contextual_selection
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer, EXPERIMENTAL
from app.application.recommendation.compact_mandatory_verifier import CompactMandatoryFacts
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
from app.domain.value_objects.contextual_garment_evidence import KEY, project_contextual_evidence
from app.domain.value_objects.contextual_outfit_request import ContextualOutfitRequest
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.ports.assistant_runtime import assistant_service
from tests.test_rule_based_compatibility import g, Preferences
from tests.test_structural_candidates import Query
from tests.test_release_configuration import release, submit
from tests.test_forward_style_semantics import lifecycle

LABELS = json.loads((Path(__file__).with_name('fixtures') / 'contextual_wedding_labels.v1.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('identifier,text,status,role,code', LABELS['cases'], ids=[c[0] for c in LABELS['cases']])
def test_frozen_new_nlp_labels(identifier, text, status, role, code):
    actual = ContextualNLPInterpreter().interpret(text)
    assert actual.status == status, (identifier, actual)
    assert actual.original_text == text
    if status == 'Supported':
        request = actual.structured_request
        assert isinstance(request, ContextualOutfitRequest)
        assert (request.occasion, request.context.role, request.formality, request.context.dress_code) == ('wedding', role, code, code)
        assert request.context.assumed_role == ('guest' if role == 'unspecified' else None)
        assert request.to_dict()['context'] == asdict(request.context)


def test_original_fixed_labels_delegate_byte_equivalent_structures():
    old, new = NLPInterpreter(), ContextualNLPInterpreter()
    data = json.loads((Path(__file__).with_name('fixtures') / 'nlp_evaluation.v1.json').read_text())
    for cases in data['groups'].values():
        for row in cases:
            expected, actual = old.interpret(row[1]), new.interpret(row[1])
            if 'wedding' in row[1].lower():
                # U15 deliberately gains support only in the new opt-in profile.
                # Its original frozen label and v1 failure remain untouched.
                assert row[0] == 'U15' and expected.status == 'UnsupportedRequest'
                assert actual.status == 'Supported'
                continue
            assert actual == expected, row[0]
            if actual.structured_request:
                assert type(actual.structured_request) is type(expected.structured_request)
                assert asdict(actual.structured_request) == asdict(expected.structured_request)


def contextual_request(code=None):
    suffix = '' if code is None else '; the dress code is ' + code.replace('_', ' ')
    return ContextualNLPInterpreter().interpret("I'm going to a wedding" + suffix).structured_request


def reviewed(identifier='d', category='vest_dress', styles=('smart casual',), decisions=(), review=True):
    raw = {'schema_version': '1.0.0', 'style_review': {'source': 'owner_review', 'styles': list(styles),
           'category': category, 'reviewed_at': '2026-10-24T00:00:00+00:00'} if review else None,
           'occasion_overrides': {'wedding': list(decisions)} if decisions else {}}
    return g(identifier, category, styles=styles, contextual_suitability=project_contextual_evidence(raw, True))


# This oracle deliberately does not import/call the production resolver or policy.
def expected_member(style, review, decisions, malformed=False, code=None):
    if 'deny' in decisions:
        return 'Fail'
    if malformed:
        return 'Unknown'
    if decisions == ('allow',):
        return 'Pass'
    return 'Pass' if review and style == ('casual' if code == 'casual' else 'smart casual',) else 'Unknown'


@pytest.mark.parametrize('style,review,decisions', list(product(
    [('smart casual',), ('casual',), ('classic',), (), ('smart casual', 'classic')],
    [True, False], [(), ('allow',), ('deny',), ('allow', 'deny')])) )
def test_independent_declaration_attribute_truth_table(style, review, decisions):
    garment = reviewed(styles=style, review=review, decisions=decisions)
    request = contextual_request()
    expected = expected_member(style, review, decisions)
    evaluator = ContextualSuitabilityEvaluator()
    assert evaluator.member_condition(garment, request, 'occasion')[0] == expected
    facts = CompactMandatoryFacts((garment,), request, ContextualSuitabilityEvaluator)
    assert facts.evaluate(('one_piece',), (0,))[0][2] == {'Pass': 1, 'Fail': 0, 'Unknown': -1}[expected]


@pytest.mark.parametrize('code,style,expected', [('casual', 'casual', 'Pass'), ('casual', 'smart casual', 'Unknown'), ('smart_casual', 'smart casual', 'Pass'), ('smart_casual', 'classic', 'Unknown')])
def test_explicit_dress_code_is_not_hierarchy(code, style, expected):
    request = contextual_request(code)
    evaluator = ContextualSuitabilityEvaluator()
    garment = reviewed(styles=(style,))
    assert evaluator.member_condition(garment, request, 'formality')[0] == expected
    denied = replace(garment, custom_tags=(f'rec:v1:formality:{code}:deny',))
    assert ContextualSuitabilityEvaluator().member_condition(denied, request, 'formality')[0] == 'Fail'
    with pytest.raises(ValueError, match='Conflicting suitability snapshots'):
        evaluator.member_condition(denied, request, 'formality')


@pytest.mark.parametrize('code', ['formal', 'black_tie'])
def test_unsupported_code_never_falls_back(code):
    assert not ContextualSuitabilityEvaluator().supports(contextual_request(code))


def test_malformed_stale_conflicting_and_empty_evidence_do_not_infer():
    evaluator, request = ContextualSuitabilityEvaluator(), contextual_request()
    good = reviewed()
    variants = [replace(good, category='sling_dress'), replace(good, style_tags=('casual',)),
        replace(good, custom_tags=('rec:v1:occasion:broken:allow',)),
        replace(good, contextual_suitability=project_contextual_evidence(None, True)),
        replace(good, invalid_attributes=('style_tags',))]
    for garment in variants:
        assert ContextualSuitabilityEvaluator().member_condition(garment, request, 'occasion')[0] == 'Unknown'
    raw = {'schema_version': 'wrong', 'style_review': None, 'occasion_overrides': {'wedding': ['allow', 'deny', 'bad']}}
    denied = replace(good, contextual_suitability=project_contextual_evidence(raw, True))
    assert ContextualSuitabilityEvaluator().member_condition(denied, request, 'occasion')[0] == 'Fail'


def test_all_members_including_outerwear_and_independent_scoring_agree():
    rows = [reviewed('top', 'long_sleeve_top'), reviewed('bottom', 'trousers'),
            reviewed('dress'), reviewed('outer', 'long_sleeve_outwear', decisions=('deny',))]
    request = contextual_request()
    compact = CompactExhaustiveScorer(Query(rows), Preferences(), evaluator_type=ContextualSuitabilityEvaluator).rank('owner', request)
    reference = AggregatedDecisionRecommendationScorer(RequestCandidateEngine(Query(rows), evaluator_factory=ContextualSuitabilityEvaluator), Preferences()).rank('owner', request)
    assert compact.status == reference.status == 'Selected'
    assert compact.scored_count == reference.scored_count == 2
    assert asdict(compact.winner.score) == asdict(reference.winner.score)
    assert compact.winner.verified.candidate.key == reference.winner.verified.candidate.key
    assert compact.winner.score.weights == (Fraction(3, 5), Fraction(1, 5), Fraction(1, 5))
    assert all(m.garment.garment_id != 'outer' for m in compact.winner.verified.candidate.members)


@pytest.mark.parametrize('profile,enabled,suitability,valid', [('disabled',False,False,True), ('bad',True,True,False), ('wedding_guest_v1',False,True,False), ('wedding_guest_v1',True,False,False), ('wedding_guest_v1',True,True,True)])
def test_opt_in_selection_fails_closed(monkeypatch, profile, enabled, suitability, valid):
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE', profile)
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED', str(enabled).lower())
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED', str(suitability).lower())
    if valid:
        assert bool(contextual_selection()) == (profile != 'disabled')
    else:
        with pytest.raises(ValueError):
            contextual_selection()


@pytest.fixture
def contextual_api(release, monkeypatch):
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE', 'wedding_guest_v1')
    configure_local_workflow()
    assert assistant_service().engine.evaluator_factory is ContextualSuitabilityEvaluator
    return release


def patch(client, gid, payload):
    response = client.patch('/api/v1/wardrobe/garments/' + gid, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def review(client, gid, **actions):
    data = next(g for g in client.get('/api/v1/wardrobe/garments').json() if g['id'] == gid)
    return client.post('/api/v1/wardrobe/garments/' + gid + '/contextual-suitability',
                       json={'revision': data['contextual_edit']['revision'], **actions})


def test_actual_contextual_api_review_selection_history_replay_and_denial(contextual_api):
    client, create = contextual_api
    gid = create(['smart casual'])
    patch(client, gid, {'category': 'vest_dress', 'primary_colour': 'blue'})
    response, result = submit(client, "I'm going to a wedding")
    assert response.status_code == 200 and result['outcome'] == 'InsufficientEvidence'
    assert review(client, gid, review_style=True).status_code == 200
    key = uuid.uuid4().hex
    response, result = submit(client, "I'm going to a wedding", key)
    assert response.status_code == 201, result
    original = result['recommendation']
    evidence = original['provenance']['contextual_wedding']
    assert evidence['context']['role'] == 'unspecified' and evidence['context']['assumed_role'] == 'guest'
    assert evidence['members'][0]['conditions'][0]['rule'] == 'W01'
    assert evidence['members'][0]['conditions'][0]['basis'] == 'reviewed_attribute_inference'
    assert review(client, gid, wedding_choice='deny').status_code == 200
    response, denied = submit(client, "I'm going to a wedding")
    assert denied['outcome'] == 'NoMatchingCandidates'
    response, replay = submit(client, "I'm going to a wedding", key)
    assert response.status_code == 200 and replay['replayed']
    assert replay['recommendation']['provenance'] == original['provenance']
    history = client.get('/api/v1/chats/' + original['chat_id']).json()
    assert history['recommendation']['provenance'] == original['provenance']
    assert history['structured_request']['context']['assumed_role'] == 'guest'
    assert client.get('/api/v1/wardrobe/quota').json()['limit'] == 100


def test_review_races_invalid_values_and_invalidation(contextual_api):
    client, create = contextual_api
    gid = create(['smart casual'])
    data = patch(client, gid, {'category': 'vest_dress'})
    url = '/api/v1/wardrobe/garments/' + gid + '/contextual-suitability'
    stale = {'revision': data['contextual_edit']['revision'], 'review_style': True}
    assert review(client, gid, wedding_choice='deny').status_code == 200
    assert client.post(url, json=stale).status_code == 409
    assert review(client, gid, review_style=True).json()['contextual_edit']['review_current']
    result = patch(client, gid, {'attributes': {'style': ['casual']}})
    assert not result['contextual_edit']['review_current']
    assert result['contextual_edit']['wedding_choice'] == 'deny'
    assert review(client, gid, review_style=True).status_code == 200
    result = patch(client, gid, {'category': 'sling_dress'})
    assert not result['contextual_edit']['review_current']
    for styles in (None, [], ['unknown prose'], ['classic', 'smart casual']):
        patch(client, gid, {'attributes': {'style': styles}})
        assert review(client, gid, review_style=True).status_code == 422
    assert client.post(url, json={**stale, 'review_style': 'true'}).status_code == 422
    assert client.post(url, json={**stale, 'invented': True}).status_code == 422
    assert client.patch('/api/v1/wardrobe/garments/' + gid, json={'attributes': {KEY: {}}}).status_code == 422


def test_snapshot_revalidation_catches_changed_review_without_persistence_edit(contextual_api):
    client, create = contextual_api
    gid = create(['smart casual'])
    patch(client, gid, {'category': 'vest_dress'})
    assert review(client, gid, review_style=True).status_code == 200
    service = assistant_service()
    original = service.repository.persist_assistant
    def mutate_before_commit(command):
        assert review(client, gid, wedding_choice='deny').status_code == 200
        return original(command)
    service.repository.persist_assistant = mutate_before_commit
    response, result = submit(client, "I'm going to a wedding")
    assert response.status_code == 409 and result['outcome'] == 'WardrobeChanged'
    with db.connection() as conn:
        assert conn.execute('SELECT count(*) FROM nlp_chats').fetchone()[0] == 0


def test_new_routes_owner_isolation_and_unsupported_code(contextual_api):
    from app.infrastructure.security import issue_access_token
    client, create = contextual_api
    gid = create(['smart casual'])
    data = patch(client, gid, {'category': 'vest_dress'})
    db.ensure_user('context-foreign')
    foreign = {'Authorization': 'Bearer ' + issue_access_token('context-foreign')}
    response = client.post('/api/v1/wardrobe/garments/' + gid + '/contextual-suitability',
        json={'revision': data['contextual_edit']['revision'], 'review_style': True}, headers=foreign)
    assert response.status_code == 404
    for text in ("I'm going to a formal wedding", "I'm going to a wedding as the bride"):
        response, result = submit(client, text)
        assert response.status_code == 422 and result['outcome'] == 'PolicyUnavailable'
        assert 'not supported' in result['contextual_message']


def test_explicit_other_constraints_and_delegated_metadata(contextual_api):
    client, create = contextual_api
    gid = create(['smart casual'])
    patch(client, gid, {'category': 'vest_dress', 'primary_colour': 'blue'})
    assert review(client, gid, review_style=True).status_code == 200
    for text in ('Suggest a wedding outfit with red', 'Suggest a wedding outfit with classic style',
                 'Suggest a wedding outfit with trousers'):
        response, result = submit(client, text)
        assert response.status_code == 200 and result['outcome'] == 'NoMatchingCandidates'
    response, result = submit(client, 'Suggest an outfit')
    assert response.status_code == 201
    provenance = result['recommendation']['provenance']
    assert provenance['request_evaluator'] == 'SuitabilityRequestEvaluator'
    assert provenance['suitability_policy'] == 'owner-declarations-1.0.0'
    assert provenance['nlp_vocabulary'] == '1.0.0'
    assert provenance['contextual_adapter'] == {'evaluator': 'ContextualSuitabilityEvaluator', 'delegated': True}
    assert 'contextual_wedding' not in provenance


def test_actual_dress_code_needs_each_condition_and_no_hierarchy(contextual_api):
    client, create = contextual_api
    gid = create(['casual'])
    patch(client, gid, {'category': 'vest_dress'})
    assert review(client, gid, review_style=True).status_code == 200
    response, result = submit(client, "I'm going to a wedding; the dress code is casual")
    assert response.status_code == 201, result
    assert {c['rule'] for c in result['recommendation']['provenance']['contextual_wedding']['members'][0]['conditions']} == {'W03'}
    response, result = submit(client, "I'm going to a wedding")
    assert result['outcome'] == 'InsufficientEvidence'
    assert review(client, gid, wedding_choice='allow').status_code == 200
    response, result = submit(client, "I'm going to a wedding; the dress code is smart casual")
    assert result['outcome'] == 'InsufficientEvidence'


def test_corrupt_mirror_rejects_review_atomically(contextual_api):
    client, create = contextual_api
    gid = create(['smart casual'])
    patch(client, gid, {'category': 'vest_dress'})
    with db.connection() as conn:
        conn.execute('UPDATE garments SET additional_attributes=? WHERE id=?', (json.dumps({KEY: {'broken': True}}), gid))
    with db.connection() as conn:
        before = tuple(conn.execute('SELECT attributes_json,additional_attributes FROM garments WHERE id=?', (gid,)).fetchone())
    assert review(client, gid, review_style=True).status_code == 422
    with db.connection() as conn:
        assert tuple(conn.execute('SELECT attributes_json,additional_attributes FROM garments WHERE id=?', (gid,)).fetchone()) == before
    assert submit(client, "I'm going to a wedding")[1]['outcome'] == 'InsufficientEvidence'


def test_automatic_adapter_metadata_cannot_attest_owner_review(contextual_api, monkeypatch):
    from types import SimpleNamespace
    from app.application.garment_processing import garment_processing_orchestrator as processing
    from app.domain.value_objects.garment_attributes import GarmentAttributes
    client, create = contextual_api
    forged = {'schema_version': '1.0.0', 'style_review': None, 'occasion_overrides': {'wedding': ['allow']}}
    monkeypatch.setattr(processing, 'get_attribute_adapter', lambda: SimpleNamespace(extract=lambda _: GarmentAttributes({KEY: forged})))
    gid = create(['smart casual'])
    result = patch(client, gid, {'category': 'vest_dress'})
    assert KEY not in result['attributes']
    assert KEY not in result['additional_attributes']
    assert not result['contextual_edit']['review_current']
