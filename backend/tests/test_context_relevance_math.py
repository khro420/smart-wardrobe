"""Phase A definitions only. Frozen score labels are inputs, not scorer results."""
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.recommendation.context_relevance_policy import (
    ContextRelevancePolicy, POLICY_SHA256, CATALOGUE_SHA256, CONFIG,
    PROFILE, SELECTION_MODE, FALLBACK_MODE, _read,
)
from app.domain.value_objects.context_relevance import RelativeObjective, ObjectiveResolution
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest


@pytest.fixture(scope='module')
def policy():
    return ContextRelevancePolicy.load()


def request(text):
    outcome = GeneralContextInterpreter().interpret(text)
    assert outcome.status == 'Supported', (text, outcome.status)
    return outcome.structured_request


def alternate(tmp_path, *, policy_mutation=None, catalogue_mutation=None):
    raw_policy = json.loads((CONFIG/'context_relevance_policy.v1.json').read_text())
    raw_catalogue = json.loads((CONFIG/'context_relevance_objectives.v1.json').read_text())
    if policy_mutation:
        policy_mutation(raw_policy)
    if catalogue_mutation:
        catalogue_mutation(raw_catalogue)
    paths = (tmp_path/'policy.json', tmp_path/'objectives.json')
    for path, data in zip(paths, (raw_policy, raw_catalogue), strict=True):
        path.write_text(json.dumps(data), encoding='utf-8')
    return paths, tuple(hashlib.sha256(path.read_bytes()).hexdigest() for path in paths)


@pytest.mark.parametrize('text,situation,target', [
    ("I'm going shopping.", 'everyday.shopping', 'casual'),
    ("I'm going to class.", 'everyday.academic_attendance', 'casual'),
    ("I'm going out with friends.", 'everyday.casual_outing', 'casual'),
    ("I'm going on a date tonight.", 'social.date', 'smart casual'),
    ("I'm meeting friends for dinner.", 'social.meal', 'smart casual'),
])
def test_five_automatic_objectives_without_style_review_or_preferences(policy, text, situation, target):
    parsed = request(text)
    before = parsed.to_dict()
    result = policy.resolve(parsed)
    assert (result.state, result.reason) == ('Resolved', 'automatic_default')
    assert (result.objective.situation, result.objective.target, result.objective.authority) == (situation, target, 'prototype_convention')
    assert 'prototype' in result.objective.explanation
    assert 'unreviewed' in result.objective.limitations
    assert result.objective.semantic_test == ('style', (target,), 'base_members', 'mean')
    assert parsed.to_dict() == before
    assert parsed.style is None and parsed.formality is None
    assert result.baseline_fallback_eligible_reason is None


@pytest.mark.parametrize('text', [
    'Suggest an outfit for dinner with casual style',
    'Suggest an outfit for shopping with smart casual style',
])
def test_explicit_supported_style_overrides_without_rewriting_request(policy, text):
    parsed = request(text)
    result = policy.resolve(parsed)
    assert result.reason == 'explicit_style_precedence'
    assert result.objective.target == parsed.style
    assert result.objective.authority == 'explicit_user_style'
    assert result.objective.identifier == 'user-stated-style'
    assert parsed.formality is None


@pytest.mark.parametrize('text', [
    "I'm going shopping; the dress code is casual.",
    "I'm meeting friends for dinner; the dress code is smart casual.",
])
def test_separate_supported_code_does_not_inherit_unspecified_default(policy, text):
    result = policy.resolve(request(text))
    assert result.state == 'ObjectiveUnavailable'
    assert result.objective is None
    assert result.baseline_fallback_eligible_reason == 'objective_unavailable'


def test_explicit_style_and_supported_code_preserve_both(policy):
    parsed = request('Suggest an outfit for dinner with casual style; the dress code is casual.')
    assert parsed.formality == 'casual'
    result = policy.resolve(parsed)
    assert result.state == 'Resolved' and result.objective.target == 'casual'
    assert parsed.formality == 'casual'


@pytest.mark.parametrize('text', [
    "I'm going shopping; the dress code is formal.",
    "I'm going shopping; the dress code is black tie.",
    "I'm going shopping; prefer blue.",
])
def test_existing_unavailable_capability_never_becomes_fallback(policy, text):
    result = policy.resolve(request(text))
    assert result.state == 'AdmissionUnavailable'
    assert result.objective is None
    assert result.baseline_fallback_eligible_reason is None


@pytest.mark.parametrize('text', [
    "I'm going to a wedding.", "I'm presenting my project at university.",
    "I'm being interviewed for a job; the dress code is smart casual.",
    "I'm going hiking.", "I'm going to the beach.",
])
def test_specialist_and_inactive_contexts_retain_existing_dispatch(policy, text):
    result = policy.resolve(request(text))
    assert result.state == 'OutOfScope'
    assert result.baseline_fallback_eligible_reason is None


def test_generic_request_does_not_select_new_scoring(policy):
    result = policy.resolve(StructuredOutfitRequest())
    assert result.state == 'OutOfScope'


@pytest.mark.parametrize('field', ['grammar_sha256', 'taxonomy_sha256'])
def test_forged_bundle_is_error_not_missing_objective_fallback(policy, field):
    parsed = request("I'm going shopping.")
    forged = replace(parsed, context=replace(parsed.context, **{field:'0'*64}))
    with pytest.raises(ValueError, match='bundle identity'):
        policy.resolve(forged)


def test_flat_request_projection_cannot_be_changed_to_invent_style(policy):
    parsed = replace(request("I'm going shopping."), style='smart casual')
    result = policy.resolve(parsed)
    assert (result.state, result.reason) == ('AdmissionUnavailable', 'invalid_context_projection')
    assert result.baseline_fallback_eligible_reason is None


@pytest.mark.parametrize('index', range(5))
def test_missing_entry_is_explicit_normal_state_under_pinned_server_bundle(tmp_path, index):
    paths, hashes = alternate(tmp_path, catalogue_mutation=lambda data:data['entries'].pop(index))
    bundle = ContextRelevancePolicy.load(*paths, expected_hashes=hashes)
    texts = ["I'm going shopping.", "I'm going to class.", "I'm going out with friends.",
             "I'm going on a date tonight.", "I'm meeting friends for dinner."]
    result = bundle.resolve(request(texts[index]))
    assert result.state == 'ObjectiveUnavailable' and result.objective is None
    assert result.baseline_fallback_eligible_reason == 'objective_unavailable'


def test_explicit_style_works_without_catalogue_default(tmp_path):
    paths, hashes = alternate(tmp_path, catalogue_mutation=lambda data:data.update(entries=[]))
    bundle = ContextRelevancePolicy.load(*paths, expected_hashes=hashes)
    result = bundle.resolve(request('Suggest an outfit for dinner with casual style'))
    assert result.reason == 'explicit_style_precedence' and result.objective.target == 'casual'


@pytest.mark.parametrize('field,value', [
    ('version','next'), ('profile','experimental_compatibility_decision_v1'),
    ('default_activation',True), ('default_activation',0), ('weights',['1','0','0']),
    ('maximum_configuration_bytes',65537), ('maximum_objectives',6),
    ('operator','eval'), ('selection_mode','random'), ('fallback_mode','silent'),
    ('explicit_style_precedence',False), ('outerwear_in_base_R',True),
    ('human_appropriateness_validation','PASSED'), ('authority','independently_verified'),
])
def test_rejects_unapproved_policy_semantics_even_with_matching_file_hash(tmp_path, field, value):
    paths, hashes = alternate(tmp_path, policy_mutation=lambda data:data.update({field:value}))
    with pytest.raises(ValueError, match='policy semantics'):
        ContextRelevancePolicy.load(*paths, expected_hashes=hashes)


@pytest.mark.parametrize('mutation', [
    lambda d:d.update(version='future'),
    lambda d:d.update(basis='validated_fashion'),
    lambda d:d.update(policy_version='future'),
    lambda d:d.update(execute='module.path'),
    lambda d:d['entries'].append(d['entries'][0]),
    lambda d:d['entries'].__setitem__(1,d['entries'][0]),
    lambda d:d['entries'][0].update(situation='ceremony.wedding'),
    lambda d:d['entries'][0].update(target='smart casual'),
    lambda d:d['entries'][0].update(allowed_venues=['luxury_store']),
    lambda d:d['entries'][0].update(allowed_companions=['friends']),
    lambda d:d['entries'][0].update(binding_id='wedding_guest_equivalent_v1'),
    lambda d:d['entries'][0].update(authority='external_dress_code'),
    lambda d:d['entries'][0].update(objective_id='arbitrary'),
    lambda d:d['entries'][0].update(explanation=''),
    lambda d:d['entries'][0].update(limitations='x'*1201),
])
def test_rejects_catalogue_expansion_or_invalid_authority(tmp_path, mutation):
    paths, hashes = alternate(tmp_path, catalogue_mutation=mutation)
    with pytest.raises(ValueError):
        ContextRelevancePolicy.load(*paths, expected_hashes=hashes)


def test_alternate_paths_require_explicit_server_identity(tmp_path):
    paths, _ = alternate(tmp_path)
    with pytest.raises(ValueError, match='expected hashes'):
        ContextRelevancePolicy.load(*paths)


def test_tampered_default_bundle_cannot_be_accepted_by_version_only(tmp_path):
    paths, _ = alternate(tmp_path)
    with pytest.raises(ValueError, match='configuration hash'):
        ContextRelevancePolicy.load(*paths, expected_hashes=(POLICY_SHA256,CATALOGUE_SHA256))


@pytest.mark.parametrize('raw', [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}',
                                 b'\xff', b'{', b'['*1100+b']'*1100, b' '*65537],
                         ids=['duplicate-key','nan','infinity','encoding','syntax','depth','size'])
def test_bounded_strict_json_rejects_duplicates_nonfinite_bad_encoding_depth_size(tmp_path, raw):
    path = tmp_path/'invalid.json'
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        _read(path,hashlib.sha256(raw).hexdigest())


def test_exact_default_hashes_and_weights(policy):
    assert (policy.policy_sha256,policy.catalogue_sha256)==(POLICY_SHA256,CATALOGUE_SHA256)
    assert policy.weights==(F(3,5),F(1,5),F(1,5))
    assert PROFILE=='context_relevance_decision_v1'
    assert SELECTION_MODE=='best_evidenced_with_coverage_v1' and FALLBACK_MODE=='baseline_disclosed_v1'
    assert len(policy.entries)==5 and type(policy.entries) is tuple


def test_immutable_definitions_and_no_resolve_io(policy):
    parsed=request("I'm going shopping.")
    with patch.object(Path,'open',side_effect=AssertionError('resolution must not read config')):
        result=policy.resolve(parsed)
    with pytest.raises(FrozenInstanceError):
        result.objective.target='smart casual'
    with pytest.raises(FrozenInstanceError):
        result.state='ObjectiveUnavailable'
    with pytest.raises(FrozenInstanceError):
        policy.entries=()


@pytest.mark.parametrize('patches', [
    {'state':'Unknown'}, {'state':[]}, {'reason':'anything'}, {'objective':None},
    {'policy_sha256':'not-a-hash'}, {'version':'future'},
])
def test_objective_resolution_rejects_forged_inconsistent_contract(policy, patches):
    result=policy.resolve(request("I'm going shopping."))
    with pytest.raises(ValueError):
        replace(result,**patches)


def test_frozen_hand_authored_rows_remain_exact_arithmetic_inputs():
    labels=json.loads((Path(__file__).with_name('fixtures')/'context_relevance_labels.v1.json').read_text())
    assert len(labels['cases'])==14 and len(labels['point_rows'])==20
    assert 'BEFORE SCORER IMPLEMENTATION' in labels['status']
    for key,casual,smart,c,p,tc,ts in labels['point_rows']:
        assert F(3,5)*F(casual)+F(1,5)*F(c)+F(1,5)*F(p)==F(tc),key
        assert F(3,5)*F(smart)+F(1,5)*F(c)+F(1,5)*F(p)==F(ts),key
    # This checks frozen arithmetic only; no production ranking is invoked.


def test_integrated_selection_remains_default_off_and_preserves_old_profile_default():
    import inspect
    from app.application.recommendation.assistant_scoring_selection import AssistantScoringSelection
    from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
    assert AssistantScoringSelection().context_ranking=='disabled'
    assert AssistantScoringSelection().profile=='compatibility_deferred'
    assert inspect.signature(OutfitAssistantService).parameters['context_ranking_profile'].default=='disabled'
