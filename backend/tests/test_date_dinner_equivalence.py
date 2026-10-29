"""Independent exact structure/score oracle and no context-dependent score bonuses."""
from dataclasses import asdict, replace
from fractions import Fraction
import pytest
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate, InvalidScoringInput
from app.domain.value_objects.request_candidate_evaluation import EvaluatedCandidate
from tests.test_contextual_wedding import reviewed
from tests.test_rule_based_compatibility import Preferences
from tests.test_structural_candidates import Query


@pytest.mark.parametrize('occasion', ['date', 'dinner'])
@pytest.mark.parametrize('outer_state', ['allow', 'deny', 'unknown'])
def test_all_structures_independent_expected_arithmetic_and_reference(occasion, outer_state):
    rows = [reviewed('top-A', 'long_sleeve_top', ('casual',)), reviewed('bottom-A', 'trousers', ('casual',)),
            reviewed('dress-A', styles=('casual',)), reviewed('outer-A', 'long_sleeve_outwear', () if outer_state == 'unknown' else ('casual',), review=outer_state != 'unknown')]  # Truly missing style; unreviewed labels now qualify.
    if outer_state == 'deny':
        rows[-1] = replace(rows[-1], custom_tags=('rec:v1:occasion:'+occasion+':deny',))
    request = GeneralContextInterpreter().interpret('Suggest an outfit for '+occasion).structured_request
    audit = []
    compact = CompactExhaustiveScorer(Query(rows), Preferences(), evaluator_type=EvaluatorSpecification.current(), audit=audit.append).rank('owner', request)
    assert compact.status == 'Selected' and len(audit) == 4
    assert compact.scored_count == (4 if outer_state == 'allow' else 2)
    for candidate in audit:
        has_outer = any(role == 'outerwear' for role, _ in candidate['key'])
        admitted = outer_state == 'allow' or not has_outer
        assert candidate['verified'] is admitted
        if admitted:
            assert all(c['state'] == 'Pass' for c in candidate['evaluation']['conditions'])
            score = candidate['score']
            assert score['request_match']['summary']['value'] == 1
            assert score['preference']['summary']['value'] is None
            assert score['total'] == (Fraction(7, 10) if len(candidate['key']) == 1 else Fraction(4, 5))
        else:
            assert candidate['score'] is None
            assert candidate['evaluation']['conditions'][-1]['state'] == ('Fail' if outer_state == 'deny' else 'Unknown')
    assert compact.winner.score.weights == (Fraction(3, 5), Fraction(1, 5), Fraction(1, 5))
    # Blue paired members have compatibility=1; a singleton has missing pair
    # evidence midpoint=1/2. R=1 and P=0 with this fixture independently imply
    # 4/5 for paired structures and 7/10 for the singleton.
    expected = (('one_piece', 'dress-A'), ('outerwear', 'outer-A')) if outer_state == 'allow' else (('upper', 'top-A'), ('lower', 'bottom-A'))
    assert compact.winner.verified.candidate.key == expected
    assert compact.winner.score.total == Fraction(4, 5)
    reference = AggregatedDecisionRecommendationScorer(RequestCandidateEngine(Query(rows), evaluator_specification=EvaluatorSpecification.current()), Preferences()).rank('owner', request)
    assert reference.winner.verified.candidate.key == expected
    assert asdict(reference.winner.score) == asdict(compact.winner.score)
    session = RequestCandidateEngine(Query(rows), evaluator_specification=EvaluatorSpecification.current()).generate_candidates('owner', request)
    gate = ScoringEligibilityGate(session, 'owner', request)
    item = compact.winner.verified.evaluated
    with pytest.raises(InvalidScoringInput):
        gate.verify(EvaluatedCandidate(item.candidate, replace(item.evaluation, conditions=())))
    session.close()


@pytest.mark.parametrize('texts', [
    ["I'm going on a date", 'I have a date tonight', 'Suggest an outfit for a date', "I'm going on a date at a restaurant"],
    ["I'm going to dinner", "I'm meeting friends for dinner", "I'm going out for dinner tonight", "I'm meeting friends for dinner at a restaurant"],
])
def test_paraphrase_time_venue_and_companions_do_not_change_exact_scores(texts):
    scores, keys = [], []
    for text in texts:
        request = GeneralContextInterpreter().interpret(text).structured_request
        result = CompactExhaustiveScorer(Query([reviewed(styles=('casual',))]), Preferences(), evaluator_type=EvaluatorSpecification.current()).rank('owner', request)
        assert result.status == 'Selected'
        assert request.formality is None
        assert result.winner.score.total == Fraction(7, 10)
        scores.append(asdict(result.winner.score)); keys.append(result.winner.verified.candidate.key)
    assert all(score == scores[0] for score in scores) and all(key == keys[0] for key in keys)


@pytest.mark.parametrize('occasion', ['date', 'dinner'])
def test_social_preparation_at_100_is_outside_candidate_loop(occasion, monkeypatch):
    from app.application.recommendation.context_evidence_resolver import ContextEvidenceResolver
    from app.application.recommendation import general_context_evaluator as module
    request = GeneralContextInterpreter().interpret('Suggest an outfit for '+occasion+'; the dress code is casual').structured_request
    rows = [reviewed(str(i), styles=('casual',)) for i in range(100)]
    calls = {'resolve': 0, 'compile': 0, 'candidates': 0}
    old_resolve, old_compile = ContextEvidenceResolver.resolve, module.compile_context
    def resolve(*args):
        calls['resolve'] += 1
        assert calls['candidates'] in (0, 100)
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
    assert calls == {'resolve': 404, 'compile': 5, 'candidates': 100}
