"""Synthetic exact differential evidence; no fashion-quality validation claim."""
from dataclasses import asdict,FrozenInstanceError
from itertools import product
import pytest
from app.application.recommendation.prepared_compatibility_aggregation import PreparedCompatibilityAggregation
from app.application.recommendation.cached_rule_based_compatibility_scorer import CachedRuleBasedCompatibilityScorer
from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
from app.application.recommendation.prepared_decision_scorer import PreparedDecisionRecommendationScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from tests.test_rule_based_compatibility import g,candidate,Preferences
from tests.test_structural_candidates import Query
from tests.test_compatibility_pair_cache import signature
from tests.test_recommendation_persistence import store
from tests.test_outfit_assistant import assistant_store,service


@pytest.mark.parametrize('capacity',[0,1,256])
def test_every_structure_numeric_unknown_and_pair_diagnostics(capacity):
    a=CachedRuleBasedCompatibilityScorer();b=PreparedCompatibilityAggregation(aggregation_capacity=capacity)
    for colour,style,structure in product(('blue','red',None,'#182a46'),(('classic',),('sporty',),('classic','vintage'),None,()),('pair','trio','dress','dress_outer')):
        rows=[g('d','vest_dress',colour,style)] if structure.startswith('dress') else [g('t','vest',colour,style),g('b','trousers')]
        if structure in ('trio','dress_outer'):rows.append(g('o','long_sleeve_outwear','white',('vintage',)))
        # Each comparison owns fresh garment snapshots; conflicts must not be
        # hidden by numeric summary reuse in a previous fixture.
        a=CachedRuleBasedCompatibilityScorer();b=PreparedCompatibilityAggregation(aggregation_capacity=capacity)
        first=a.evaluate(candidate(rows));second=b.evaluate(candidate(rows))
        assert first==second and asdict(first)==asdict(second)
        assert b.evaluate(candidate(rows))==second
        assert b.aggregation_cache_info.currsize<=capacity
        with pytest.raises(FrozenInstanceError):second.summary.value=None


@pytest.mark.parametrize('capacity',[0,1,256])
def test_bounded_reuse_does_not_retain_candidate_identity(capacity):
    scorer=PreparedCompatibilityAggregation(aggregation_capacity=capacity)
    for i in range(300):
        outfit=candidate([g('t'+str(i),'vest'),g('b'+str(i),'trousers')])
        raw=scorer.evaluate(outfit)
        assert raw.details[2].name=='colour:t'+str(i)+':b'+str(i)
    assert scorer.aggregation_cache_info.currsize<=capacity


@pytest.mark.parametrize('structured',[StructuredOutfitRequest(),StructuredOutfitRequest(style='classic'),StructuredOutfitRequest(colours=('red',)),StructuredOutfitRequest(occasion='campus')])
def test_complete_stream_and_rejections_match_original(structured):
    rows=[g('t','vest'),g('b','trousers','red',('sporty',)),g('d','vest_dress',None,None),g('o','long_sleeve_outwear')]
    a=PreparedDecisionRecommendationScorer(RequestCandidateEngine(Query(rows)),Preferences()).rank('owner',structured)
    b=AggregatedDecisionRecommendationScorer(RequestCandidateEngine(Query(list(reversed(rows)))),Preferences()).rank('owner',structured)
    assert signature(a)==signature(b)


def test_actual_service_persists_identical_score_and_provenance(assistant_store):
    from app.application.recommendation.assistant_scoring_selection import DECISION
    a=service(assistant_store);a.execution_engine='reference';a.scoring_profile=DECISION;a.scorer_factory=PreparedDecisionRecommendationScorer
    b=service(assistant_store);b.execution_engine='reference';b.scoring_profile=DECISION;b.scorer_factory=AggregatedDecisionRecommendationScorer
    first=a.recommend('owner','reference','Suggest an outfit with vintage style')
    second=b.recommend('owner','trial','Suggest an outfit with vintage style')
    assert first['status']==second['status']=='Selected'
    for key in ('score_metadata','provenance','scoring_display','total_score','compatibility_score'):
        assert first[key]==second[key],key


@pytest.mark.parametrize('capacity',[-1,257,True,None])
def test_invalid_cache_configuration(capacity):
    with pytest.raises(ValueError):PreparedCompatibilityAggregation(aggregation_capacity=capacity)


def test_cache_does_not_keep_dead_session_alive():
    import weakref
    scorer=PreparedCompatibilityAggregation()
    scorer.evaluate(candidate([g('t','vest'),g('b','trousers')]))
    ref=weakref.ref(scorer)
    del scorer
    assert ref() is None
