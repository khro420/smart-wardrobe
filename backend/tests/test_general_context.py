"""Independent semantic labels, configuration rejection and prepared-fact bounds."""
from dataclasses import asdict, replace, FrozenInstanceError
from itertools import product
import json
from pathlib import Path
import pytest
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.recommendation.context_policy_registry import ContextPolicyRegistry, CONFIG
from app.application.recommendation.general_context_evaluator import GeneralContextEvaluator, EvaluatorSpecification, construct_evaluator
from app.application.recommendation.contextual_selection import contextual_selection
from app.application.recommendation.compact_mandatory_verifier import CompactMandatoryFacts, CompactEligibilityVerifier
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.domain.value_objects.general_context_request import ContextSlot, SourceSpan
from tests.test_contextual_wedding import reviewed, expected_member
from tests.test_rule_based_compatibility import Preferences
from tests.test_structural_candidates import Query

LABELS = json.loads((Path(__file__).with_name('fixtures')/'general_context_labels.v1.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('identifier,text,status,situation,available', LABELS['cases'], ids=[c[0] for c in LABELS['cases']])
def test_independently_frozen_interpretation_and_capability(identifier, text, status, situation, available):
    result = GeneralContextInterpreter().interpret(text)
    assert result.status == status, (identifier, result)
    assert result.original_text == text
    if result.structured_request:
        request = result.structured_request
        assert request.context.situation.value == situation
        # Approved Phase 2 current-contract transitions. The original fixture
        # remains the unchanged Phase 1 record, not a newly relabelled result.
        if identifier in ('G03', 'G08', 'G22', 'G23'):
            assert available is False and situation in ('social.date', 'social.meal')
            assert ContextPolicyRegistry.load().version == 'context-registry-1.4.0'  # Approved saved-style contract; frozen labels retained.
            available = True
        assert GeneralContextEvaluator().supports(request) is available
        for name, slot in vars(request.context).items():
            if isinstance(slot, ContextSlot):
                for span in slot.spans:
                    assert text[span.start:span.end] == span.text, (name, span)


def test_original_spans_separate_code_formality_time_and_soft_language():
    text = "  I’m attending a wedding as a guest; the dress code is smart casual tonight with blue  "
    request = GeneralContextInterpreter().interpret(text).structured_request
    assert request.context.dress_code.value == 'smart_casual'
    assert request.context.formality.state == 'Unspecified'
    assert request.context.temporal.values == ('tonight',)
    assert request.context.role.value == 'guest'
    assert request.colours == ('blue',)
    assert request.context.venue.state == 'Unspecified'
    soft = GeneralContextInterpreter().interpret('Suggest a wedding outfit; prefer blue').structured_request
    assert soft.colours is None and soft.context.soft_preferences.values == ('colours:blue',)
    assert not GeneralContextEvaluator().supports(soft)
    with pytest.raises(FrozenInstanceError):
        request.context.role = ContextSlot()
    with pytest.raises(ValueError):
        replace(request.context, role=ContextSlot('Known', ('guest',), (SourceSpan(0, 5, 'wrong'),)))


@pytest.mark.parametrize('state', ['Known', 'Unspecified', 'Ambiguous', 'Conflicting', 'Unsupported'])
def test_semantic_state_is_not_a_numeric_confidence(state):
    slot = ContextSlot(state, () if state == 'Unspecified' else ('guest',))
    assert slot.state == state
    if state != 'Known':
        assert slot.value is None


@pytest.mark.parametrize('code,style,review,decisions', list(product(
    [None, 'casual', 'smart_casual'], [('smart casual',), ('casual',), ('classic',), ()],
    [True, False], [(), ('allow',), ('deny',), ('allow', 'deny')])))
def test_independent_member_truth_table(code, style, review, decisions):
    suffix = '' if code is None else '; the dress code is '+code.replace('_', ' ')
    request = GeneralContextInterpreter().interpret("I'm going to a wedding"+suffix).structured_request
    garment = reviewed(styles=style, review=review, decisions=decisions)
    expected = expected_member(style, review, decisions, code=code)
    result = GeneralContextEvaluator().member_condition(garment, request, 'occasion')
    assert result[0] == expected
    facts = CompactMandatoryFacts((garment,), request, EvaluatorSpecification.current())
    primary = facts.evaluate(('one_piece',), (0,))
    assert primary[0][2] == {'Pass': 1, 'Fail': 0, 'Unknown': -1}[expected]
    if all(condition[2] == 1 for condition in primary):
        assert CompactEligibilityVerifier('owner', (garment,), request, EvaluatorSpecification.current()).verify(('one_piece',), (0,), primary)


@pytest.mark.parametrize('mutation', ['unknown_field', 'operator', 'reference', 'additional_policy', 'code', 'duplicate', 'evidence', 'assumption'])
def test_registry_rejects_malformed_or_unapproved_capabilities(tmp_path, mutation):
    data = json.loads((CONFIG/'context_policy_registry.v1.json').read_text())
    binding = data['bindings'][0]
    if mutation == 'unknown_field': data['python_class'] = 'anything'
    if mutation == 'operator': binding['predicates'][0]['operator'] = 'eval'
    if mutation == 'reference': binding['situation'] = 'missing'
    if mutation == 'additional_policy': data['bindings'].append(dict(binding, situation='social.date'))
    if mutation == 'code': binding['predicates'][0]['dress_code'] = 'formal'
    if mutation == 'duplicate': binding['predicates'][1]['id'] = 'W01'
    if mutation == 'evidence': binding['evidence_contract'] = 'detector_confidence'
    if mutation == 'assumption': binding['assumed_role'] = 'groom'
    target = tmp_path/'registry.json'
    target.write_text(json.dumps(data))
    with pytest.raises((ValueError, TypeError)):
        ContextPolicyRegistry.load(target)


def test_duplicate_json_key_missing_binding_and_forged_bundle_fail_closed(tmp_path):
    target = tmp_path/'registry.json'
    target.write_text('{"version":1,"version":2}')
    with pytest.raises(ValueError): ContextPolicyRegistry.load(target)
    specification = EvaluatorSpecification.current()
    with pytest.raises(ValueError): replace(specification, registry_sha256='0'*64).construct()
    with pytest.raises(ValueError): construct_evaluator(GeneralContextEvaluator)
    request = GeneralContextInterpreter().interpret("I'm going to a wedding").structured_request
    assert not GeneralContextEvaluator().supports(replace(request, occasion='date'))
    assert not GeneralContextEvaluator().supports(replace(request, style='classic'))
    assert not GeneralContextEvaluator().supports(replace(request, context=replace(request.context, taxonomy_sha256='0'*64)))


@pytest.mark.parametrize('mutation', ['duplicate_id', 'duplicate_phrase', 'unknown_field', 'projection_mismatch'])
def test_taxonomy_and_binding_references_are_validated_together(tmp_path, mutation):
    data = json.loads((CONFIG/'situation_taxonomy.v1.json').read_text())
    if mutation == 'duplicate_id': data['situations'][1]['id'] = data['situations'][0]['id']
    if mutation == 'duplicate_phrase': data['situations'][1]['phrases'] = ['wedding']
    if mutation == 'unknown_field': data['situations'][0]['inherits_policy'] = 'formal'
    if mutation == 'projection_mismatch': data['situations'][0]['projection_occasion'] = 'party'
    target = tmp_path/'taxonomy.json'
    target.write_text(json.dumps(data))
    with pytest.raises(ValueError): ContextPolicyRegistry.load(taxonomy_path=target)


def test_context_facets_and_conflicting_time_cannot_be_fabricated_or_erased():
    interpreter = GeneralContextInterpreter()
    beach = interpreter.interpret("I'm going to the beach").structured_request.context
    assert beach.venue.value == 'beach' and beach.activity.state == 'Unspecified'
    presentation = interpreter.interpret('I have a university presentation').structured_request.context
    assert presentation.venue.value == 'university' and presentation.role.state == 'Unspecified'
    assert interpreter.interpret("I'm going to a wedding tomorrow tonight").status == 'UnsupportedRequest'
    request = interpreter.interpret("I'm going to a wedding").structured_request
    with pytest.raises(ValueError): replace(request.context, role=ContextSlot('Known', ('guest',)))
    with pytest.raises(ValueError): replace(request.context, role=ContextSlot('Known', ('guest', 'groom'), request.context.situation.spans))
    with pytest.raises(ValueError): GeneralContextEvaluator().supports(replace(request, context=replace(request.context, grammar_sha256='0'*64)))


def test_new_profile_requires_explicit_pairing_and_preserves_old_defaults(monkeypatch):
    monkeypatch.delenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE', raising=False)
    assert contextual_selection() is None
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE', 'general_context_v1')
    for enabled, suitability in [('false', 'true'), ('true', 'false')]:
        monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED', enabled)
        monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED', suitability)
        with pytest.raises(ValueError): contextual_selection()
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED', 'true')
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED', 'true')
    interpreter, factory = contextual_selection()
    assert type(interpreter) is GeneralContextInterpreter
    assert factory().specification == EvaluatorSpecification.current()


def test_preparation_at_100_has_no_resolver_or_configuration_work_in_candidate_loop(monkeypatch):
    from app.application.recommendation.context_evidence_resolver import ContextEvidenceResolver
    from app.application.recommendation import general_context_evaluator as module
    request = GeneralContextInterpreter().interpret("I'm going to a wedding; the dress code is smart casual").structured_request
    rows = [reviewed(str(i)) for i in range(100)]
    calls = {'resolve': 0, 'compile': 0, 'candidates': 0}
    old_resolve, old_compile = ContextEvidenceResolver.resolve, module.compile_context
    def resolve(*args):
        calls['resolve'] += 1
        assert calls['candidates'] in (0, 100)  # Preparation or final reconstruction only.
        return old_resolve(*args)
    def compile(*args):
        calls['compile'] += 1
        assert calls['candidates'] in (0, 100)
        return old_compile(*args)
    def checkpoint(stage, *args):
        if stage == 'candidate': calls['candidates'] += 1
    monkeypatch.setattr(ContextEvidenceResolver, 'resolve', resolve)
    monkeypatch.setattr(module, 'compile_context', compile)
    result = CompactExhaustiveScorer(Query(rows), Preferences(), evaluator_type=EvaluatorSpecification.current(), checkpoint=checkpoint).rank('owner', request)
    assert result.status == 'Selected' and result.scored_count == 100
    assert calls['resolve'] == 2*100*2 + 2*1*2
    assert calls['compile'] == 5
