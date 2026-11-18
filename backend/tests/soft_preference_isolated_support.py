"""Read-only test observers around actual engines; never installed in production."""
from dataclasses import asdict,replace
from types import SimpleNamespace
from unittest.mock import patch
from app.application.recommendation.request_local_bounded_ranking import PrimaryRecord,CompletedLedger,bounded_rank
from app.application.recommendation.request_local_preference_evidence import PreparedLocalPreference
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions
from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier
from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
from app.application.recommendation.decision_score_codec import score_to_json
from app.domain.value_objects.scored_candidate import ScoredCandidate
from app.domain.value_objects.attribute_conditions import encode,digest

def capture_actual_scores(collection,parsed,engine,*,preferences=()):
    from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
    from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
    from app.application.recommendation.candidate_ranker import CandidateRanker
    from app.application.recommendation.outfit_assistant_service import CapturedCandidateEngine
    from app.application.recommendation import aggregated_decision_scorer as reference_module,compact_exhaustive_scorer as compact_module
    policy=AttributeEvidencePolicy.load();owner=collection[0].snapshot.user_id;request=parsed.mandatory_request
    a=PreparedAttributeConditions.prepare(parsed.hard_intent.conditions,collection,policy) if parsed.hard_intent else None
    v=IndependentAttributeVerifier.prepare(parsed.hard_intent.conditions,collection,policy) if parsed.hard_intent else None
    class Query:
        def get_confirmed_available_garments(self,who):assert who==owner;return tuple(item.snapshot for item in collection)
    spec=EvaluatorSpecification.current('context_18_v1');query=Query();prefs=SimpleNamespace(get_active_preferences=lambda who:preferences)
    actual=[];audit=[];public_scores=[]
    if engine=='reference':
        class Observer(CandidateRanker):
            def better(self,candidate,current):actual.append(candidate);return super().better(candidate,current)
        captured=CapturedCandidateEngine(RequestCandidateEngine(query,evaluator_specification=spec,attribute_context=a,attribute_verifier=v))
        with patch.object(reference_module,'CandidateRanker',Observer):outcome=AggregatedDecisionRecommendationScorer(captured,prefs).rank(owner,request)
        counts=captured.session.result
    elif engine=='compact_exhaustive':
        original=compact_module.asdict
        def observe(value):
            from app.domain.value_objects.recommendation_score import RecommendationScore
            if type(value) is RecommendationScore:public_scores.append(value)
            return original(value)
        scorer=CompactExhaustiveScorer(query,prefs,evaluator_type=spec,attribute_context=a,attribute_verifier=v,audit=audit.append)
        with patch.object(compact_module,'asdict',observe):outcome=scorer.rank(owner,request)
        passing=[row for row in audit if row['verified']]
        assert len(passing)==len(public_scores)
        by_key={tuple(tuple(x) for x in row['key']):score for row,score in zip(passing,public_scores)}
        # Reacquire real gate-sealed mandatory certificates; never fabricate the
        # eligibility seal or reconstruct it from an audit boolean.
        stream=RequestCandidateEngine(query,evaluator_specification=spec,attribute_context=a,attribute_verifier=v).generate_candidates(owner,request)
        gate=ScoringEligibilityGate(stream,owner,request)
        for item in stream:actual.append(ScoredCandidate(gate.verify(item),by_key[item.candidate.key]))
        counts=stream.result
    else:raise ValueError('Unknown fixture engine.')
    assert counts.complete and counts.passed==len(actual)
    completion=CompletedLedger(counts.examined,counts.passed,counts.failed,counts.unknown,counts.complete)
    return outcome,tuple(actual),completion

def rank_actual(collection,parsed,engine,*,preferences=(),wearer_scope='isolated-already-eligible-fixture'):
    outcome,actual,completion=capture_actual_scores(collection,parsed,engine,preferences=preferences)
    policy=AttributeEvidencePolicy.load()
    optional=PreparedLocalPreference(parsed.local_intent,collection,policy,account_id=collection[0].snapshot.user_id,wearer_scope=wearer_scope) if parsed.local_intent else None
    scope=optional.scope_hash if optional else digest({'fixture':'no_soft','owner':collection[0].snapshot.user_id})
    records=tuple(PrimaryRecord(row.verified.candidate.key,row.score.request_match.contribution,row.score.compatibility.contribution,row.score.preference.contribution,row.score.total,scope,encode(score_to_json(row.score))) for row in actual)
    by_key={row.verified.candidate.key:row.verified for row in actual};before=[encode(score_to_json(row.score)) for row in actual]
    resolution=parsed.local_intent.to_dict()['optional']['resolution']['state'] if optional else 'Absent'
    def lookup(key):return optional.evaluate(by_key[key])
    result=bounded_rank(lambda:iter(records),completion,lookup if optional else None,resolution=resolution)
    assert before==[encode(score_to_json(row.score)) for row in actual]
    if outcome.winner:assert result.baseline.key==outcome.winner.verified.candidate.key
    return result,actual,optional
