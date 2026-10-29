"""Frozen wedding differential oracles and real disposable application boundaries."""
from dataclasses import asdict, replace
from fractions import Fraction
from itertools import product
import json
from pathlib import Path
import uuid
import pytest
from app.application.nlp.contextual_nlp_interpreter import ContextualNLPInterpreter
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.recommendation.contextual_suitability_evaluator import ContextualSuitabilityEvaluator
from app.application.recommendation.general_context_evaluator import GeneralContextEvaluator, EvaluatorSpecification
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate, InvalidScoringInput
from app.domain.value_objects.request_candidate_evaluation import EvaluatedCandidate
from app.domain.value_objects.contextual_garment_evidence import project_contextual_evidence
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.ports.assistant_runtime import assistant_service
from app.infrastructure.persistence import postgresql_repository as db
from tests.test_contextual_wedding import reviewed, contextual_request, patch, review
from tests.test_rule_based_compatibility import Preferences
from tests.test_structural_candidates import Query
from tests.test_release_configuration import release, submit
from tests.test_forward_style_semantics import lifecycle

FROZEN = json.loads((Path(__file__).with_name('fixtures')/'contextual_wedding_labels.v1.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('identifier,text,status,role,code', FROZEN['cases'], ids=[c[0] for c in FROZEN['cases']])
def test_frozen_wedding_interpretation_and_policy_equivalence(identifier, text, status, role, code):
    old, new = ContextualNLPInterpreter().interpret(text), GeneralContextInterpreter().interpret(text)
    assert old.status == new.status == status
    if status == 'Supported':
        left, right = old.structured_request, new.structured_request
        assert {k: v for k, v in left.to_dict().items() if k != 'context'} == {k: v for k, v in right.to_dict().items() if k != 'context'}
        assert (right.context.role.value or 'unspecified') == role
        assert right.context.dress_code.value == code
        old_evaluator, new_evaluator = ContextualSuitabilityEvaluator(), GeneralContextEvaluator()
        assert old_evaluator.supports(left) == new_evaluator.supports(right)
        if old_evaluator.supports(left):
            assert bool(new_evaluator.plan(right).assumptions) == (left.context.assumed_role == 'guest')


@pytest.mark.parametrize('code,outer_decision', list(product([None, 'casual', 'smart_casual'], [(), ('deny',)])))
def test_all_four_structures_every_candidate_exact_scores_and_winners(code, outer_decision):
    suffix = '' if code is None else '; the dress code is '+code.replace('_', ' ')
    text = "I'm going to a wedding"+suffix
    style = 'casual' if code == 'casual' else 'smart casual'
    rows = [reviewed('upper', 'long_sleeve_top', (style,)), reviewed('lower', 'trousers', (style,)),
            reviewed('dress', styles=(style,)), reviewed('outer', 'long_sleeve_outwear', (style,), decisions=outer_decision)]
    old_request = ContextualNLPInterpreter().interpret(text).structured_request
    new_request = GeneralContextInterpreter().interpret(text).structured_request
    old_audit, new_audit = [], []
    old = CompactExhaustiveScorer(Query(rows), Preferences(), evaluator_type=ContextualSuitabilityEvaluator, audit=old_audit.append).rank('owner', old_request)
    new = CompactExhaustiveScorer(Query(rows), Preferences(), evaluator_type=EvaluatorSpecification.current(), audit=new_audit.append).rank('owner', new_request)
    assert old.status == new.status == 'Selected'
    assert len(old_audit) == len(new_audit) == 4
    assert old_audit == new_audit
    assert old.scored_count == new.scored_count == (2 if outer_decision else 4)
    assert asdict(old.winner.score) == asdict(new.winner.score)
    assert old.winner.verified.candidate.key == new.winner.verified.candidate.key
    assert new.winner.score.weights == (Fraction(3, 5), Fraction(1, 5), Fraction(1, 5))
    reference = AggregatedDecisionRecommendationScorer(RequestCandidateEngine(Query(rows), evaluator_specification=EvaluatorSpecification.current()), Preferences()).rank('owner', new_request)
    assert reference.status == 'Selected'
    assert reference.winner.verified.candidate.key == new.winner.verified.candidate.key
    assert asdict(reference.winner.score) == asdict(new.winner.score)
    session = RequestCandidateEngine(Query(rows), evaluator_specification=EvaluatorSpecification.current()).generate_candidates('owner', new_request)
    gate = ScoringEligibilityGate(session, 'owner', new_request)
    item = new.winner.verified.evaluated
    with pytest.raises(InvalidScoringInput):
        gate.verify(EvaluatedCandidate(item.candidate, replace(item.evaluation, conditions=())))
    session.close()


def test_malformed_stale_and_deny_evidence_differential():
    good = reviewed()
    variants = [good, replace(good, category='sling_dress'), replace(good, style_tags=('casual',)),
                replace(good, custom_tags=('rec:v1:occasion:broken:allow',)),
                replace(good, contextual_suitability=project_contextual_evidence(None, True)),
                replace(good, invalid_attributes=('style_tags',))]
    raw = {'schema_version': 'wrong', 'style_review': None, 'occasion_overrides': {'wedding': ['allow', 'deny', 'bad']}}
    variants.append(replace(good, contextual_suitability=project_contextual_evidence(raw, True)))
    left = contextual_request('smart_casual')
    right = GeneralContextInterpreter().interpret("I'm going to a wedding; the dress code is smart casual").structured_request
    for garment in variants:
        old, new = ContextualSuitabilityEvaluator(), GeneralContextEvaluator()
        for field in ('occasion', 'formality'):
            assert old.member_condition(garment, left, field) == new.member_condition(garment, right, field)


def test_temporal_information_adds_no_score_bonus_or_new_clothing_attributes():
    interpreter = GeneralContextInterpreter()
    rows = [reviewed()]
    values = []
    for text in ("I'm going to a wedding", "I'm going to a wedding tomorrow", "I'm going to a wedding tonight"):
        request = interpreter.interpret(text).structured_request
        result = CompactExhaustiveScorer(Query(rows), Preferences(), evaluator_type=EvaluatorSpecification.current()).rank('owner', request)
        assert result.status == 'Selected'
        values.append(asdict(result.winner.score))
    assert values[0] == values[1] == values[2]


@pytest.fixture
def general_api(release, monkeypatch):
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE', 'general_context_v1')
    configure_local_workflow()
    return release


def test_actual_api_provenance_history_profile_restart_replay_and_auth(general_api, monkeypatch):
    client, create = general_api
    gid = create(['smart casual'])
    patch(client, gid, {'category': 'vest_dress', 'primary_colour': 'blue'})
    _, missing = submit(client, "I'm going to a wedding")
    assert missing['outcome'] == 'InsufficientEvidence' and missing['context_reason'] == 'required_attribute_unknown'
    assert review(client, gid, review_style=True).status_code == 200
    key, text = uuid.uuid4().hex, "I'm going to a wedding tomorrow"
    response, selected = submit(client, text, key)
    assert response.status_code == 201, selected
    original = selected['recommendation']
    proof = original['provenance']['general_context']
    assert proof['assumptions'] == ['Guest role assumed because you did not specify your role.']
    assert proof['temporal'] == ['tomorrow']
    assert proof['members'][0]['conditions'][0]['basis'] == 'reviewed_attribute_inference'
    assert original['provenance']['context_bundle'] == EvaluatorSpecification.current().registry_sha256
    assert client.get('/api/v1/chats/'+original['chat_id']).json()['recommendation']['provenance'] == original['provenance']
    assert review(client, gid, wedding_choice='deny').status_code == 200
    _, denied = submit(client, text)
    assert denied['outcome'] == 'NoMatchingCandidates'
    for profile in ('general_context_v1', 'wedding_guest_v1', 'disabled'):
        monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE', profile)
        configure_local_workflow()
        response, replay = submit(client, text, key)
        assert response.status_code == 200 and replay['replayed']
        assert replay['recommendation']['provenance'] == original['provenance']
        assert replay['score_metadata'] == selected['score_metadata']
    token = client.headers['Authorization']
    assert client.post('/api/v1/account/logout').status_code == 204
    assert client.get('/api/v1/recommendations/capabilities', headers={'Authorization': token}).status_code == 401


def test_old_wedding_result_replays_unchanged_under_new_profile(general_api, monkeypatch):
    client, create = general_api
    gid = create(['smart casual'])
    patch(client, gid, {'category': 'vest_dress'})
    review(client, gid, review_style=True)
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE', 'wedding_guest_v1')
    configure_local_workflow()
    key, text = uuid.uuid4().hex, "I'm going to a wedding"
    _, original = submit(client, text, key)
    assert original['outcome'] == 'Selected'
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE', 'general_context_v1')
    configure_local_workflow()
    _, replay = submit(client, text, key)
    assert replay['replayed'] and replay['recommendation'] == original['recommendation']


def test_recognised_unavailable_contexts_never_generate_or_drop_conditions(general_api):
    client, create = general_api
    gid = create(['smart casual'])
    patch(client, gid, {'category': 'vest_dress'})
    review(client, gid, review_style=True, wedding_choice='allow')
    data = json.loads((Path(__file__).with_name('fixtures')/'general_context_labels.v1.json').read_text())
    for identifier, text, status, _, available in data['cases']:
        # These exact four Phase 1 inactive labels intentionally advance under
        # the separately approved Date/Dinner bundle; new independent tests
        # exercise their supported paths. All other unavailable labels remain.
        if status == 'Supported' and not available and identifier not in ('G03', 'G08', 'G22', 'G23'):
            response, result = submit(client, text)
            assert response.status_code == 422 and result['outcome'] == 'PolicyUnavailable', result
            assert result['context_summary']['available'] is False
    capabilities = client.get('/api/v1/recommendations/capabilities').json()
    assert [s['id'] for s in capabilities['context_support']['situations'] if s['policy_available']] == ['ceremony.wedding', 'professional.job_interview', 'social.date', 'academic.presentation', 'social.meal', 'everyday.academic_attendance', 'everyday.shopping', 'everyday.casual_outing']
    with db.connection() as conn:
        assert conn.execute('SELECT count(*) FROM nlp_chats').fetchone()[0] == 0
    assert client.get('/api/v1/wardrobe/quota').json()['limit'] == 100


def test_generic_snapshot_revalidation_still_rolls_back(general_api):
    client, create = general_api
    gid = create(['smart casual'])
    patch(client, gid, {'category': 'vest_dress'})
    review(client, gid, review_style=True)
    service = assistant_service()
    original = service.repository.persist_assistant
    def change_review(command):
        review(client, gid, wedding_choice='deny')
        return original(command)
    service.repository.persist_assistant = change_review
    response, result = submit(client, "I'm going to a wedding")
    assert response.status_code == 409 and result['outcome'] == 'WardrobeChanged'
    with db.connection() as conn:
        assert conn.execute('SELECT count(*) FROM nlp_chats').fetchone()[0] == 0


def test_explanation_cannot_switch_policy_bundle_after_selection(general_api, monkeypatch):
    from app.application.recommendation import outfit_assistant_service as module
    client, create = general_api
    gid = create(['smart casual'])
    patch(client, gid, {'category': 'vest_dress'})
    review(client, gid, review_style=True)
    class MismatchedExplanation:
        specification = replace(EvaluatorSpecification.current(), registry_sha256='0'*64)
        def explain(self, *args):
            raise AssertionError('A mismatched explanation must never be used.')
    monkeypatch.setattr(module, 'GeneralContextEvaluator', MismatchedExplanation)
    response, result = submit(client, "I'm going to a wedding")
    assert response.status_code == 503 and result['outcome'] == 'ProcessingFailure'
    with db.connection() as conn:
        assert conn.execute('SELECT count(*) FROM nlp_chats').fetchone()[0] == 0
