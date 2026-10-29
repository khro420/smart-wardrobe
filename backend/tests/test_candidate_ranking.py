"""Stream completion, all tie-breaks, fairness, strict contexts and no writes."""
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import Mock
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.application.recommendation.recommendation_scorer import RecommendationScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.request_candidate_session import RequestCandidateSession
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.scoring_policy import ScoringProfile
from app.application.recommendation.candidate_ranker import CandidateRanker
from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore,RecommendationScore
from app.domain.value_objects.scored_candidate import ScoredCandidate
from app.domain.value_objects.ranking_outcome import RankingOutcome
from app.domain.value_objects.request_candidate_evaluation import RequestEvaluation,EvaluatedCandidate
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.infrastructure.persistence.postgresql_repository import connection
from app.infrastructure.persistence.active_preference_query_adapter import SqliteActivePreferenceQuery
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from tests.test_structural_candidates import Query,garment
from tests.test_suitability_policy import annotated,tag
from tests.test_recommendation_scoring import verified,pair,five_fields
from tests.test_preference_modelling import pref
from tests.test_suitability_tag_workflow import review_and_confirm


class Preferences:
    def __init__(self,rows=()):
        self.rows = rows
        self.calls = 0

    def get_active_preferences(self,user_id):
        self.calls += 1
        return self.rows


def rank(rows,request=None,preferences=(),profile="compatibility_deferred",engine=None):
    engine = engine or RequestCandidateEngine(Query(rows),evaluator_factory=SuitabilityRequestEvaluator)
    return RecommendationScorer(engine,Preferences(preferences)).rank("owner",request or StructuredOutfitRequest(),profile)


def test_rank_worked_candidates_both_profiles_and_order_independence():
    rows = pair() + [replace(pair(("vintage","classic"),"grey")[1],garment_id="b2")]
    prefs = [pref("colours",["black"],"0.6",identifier="c"),pref("styles",["classic"],"0.4",identifier="s")]
    for profile,bottom,total in (("three_component_experimental","b2",F(69,100)),("compatibility_deferred","b",F(87,100))):
        result = rank(rows,five_fields(),prefs,profile)
        reverse = rank(list(reversed(rows)),five_fields(),list(reversed(prefs)),profile)
        assert result.status == "Selected" and result.complete and result.scored_count == 2
        assert result.winner.score.total == total
        assert result.winner.verified.candidate.members[1].garment.garment_id == bottom
        assert reverse.winner.verified.candidate.key == result.winner.verified.candidate.key


def test_single_dress_is_not_penalised_by_an_unavailable_pair_measure():
    rows = pair() + [annotated("d","vest_dress",style_tags=("vintage",))]
    result = rank(rows,profile="three_component_experimental")
    assert result.status == "ProfileUnavailable" and result.winner is None and not result.complete
    result = rank(rows)
    assert result.status == "Selected" and result.scored_count == 2
    assert result.winner.verified.candidate.members[0].garment.garment_id == "d"  # Stable key: one_piece before upper.
    assert result.winner.score.compatibility.summary.state == "Unavailable"
    assert result.winner.score.weights == (F(7,10),F(0),F(3,10))


@pytest.mark.parametrize("stage",["total","request","compatibility","preference","identifier"])
def test_every_tie_break(stage):
    # Synthetic exact scores exercise ordering only, not fashion evaluation.
    a,b = verified([annotated("a","vest_dress"),annotated("z","vest_dress")])
    weights = (F(1),F(0),F(0)) if stage == "preference" else (F(0),F(0),F(1))
    values_a,values_b = (F(1,2),F(1,2),F(1,2)),(F(1,2),F(1,2),F(1,2))
    if stage == "total": values_a,values_b = (F(0),F(0),F(1)),(F(1),F(1),F(1,2))
    if stage == "request": values_a = (F(1),F(0),F(1,2))
    if stage == "compatibility": values_a = (F(1,2),F(1),F(1,2))
    if stage == "preference": values_a = (F(1,2),F(1,2),F(1))
    def scored(item,values):
        components = tuple(ComponentScore(ScoreEvidence(name,value,"Available")) for name,value in zip(("r","c","p"),values))
        return ScoredCandidate(item,RecommendationScore(*components,sum(w*x for w,x in zip(weights,values)),"unit","unit",weights))
    first,second = scored(a,values_a),scored(b,values_b)
    assert CandidateRanker().better(first,second)
    assert not CandidateRanker().better(second,first)
    with pytest.raises(ValueError): CandidateRanker().better(replace(first,score=replace(first.score,profile_name="other")),second)


def test_unavailable_policy_default_unchanged_and_zero_optional_fields():
    query = Query([garment("d","vest_dress")])
    prefs = Preferences()
    result = RecommendationScorer(RequestCandidateEngine(query),prefs).rank("owner",StructuredOutfitRequest(occasion="campus"),"compatibility_deferred")
    assert result.status == "PolicyUnavailable" and prefs.calls == 0 and query.calls == 0
    result = rank([garment("d","vest_dress")])
    assert result.winner.score.total == 0 and result.winner.score.request_match.summary.state == "NotApplicable"


@pytest.mark.parametrize("rows,outfit_request,status",[([],StructuredOutfitRequest(),"NoEligibleGarments"),([garment("t","vest")],StructuredOutfitRequest(),"InsufficientStructure"),([annotated("d","vest_dress")],StructuredOutfitRequest(colours=("blue",)),"InsufficientEvidence"),([annotated("d","vest_dress",primary_colour="red")],StructuredOutfitRequest(colours=("blue",)),"NoMatchingCandidates")])
def test_no_result_states(rows,outfit_request,status):
    result = rank(rows,outfit_request)
    assert result.status == status and result.complete and result.winner is None and result.scored_count == 0


@pytest.mark.parametrize("failure,status",[(RuntimeError("private"),"ProcessingFailure"),(KeyboardInterrupt(),"Interrupted")])
def test_stream_failure_after_provisional_best_discards_it(failure,status):
    from app.application.recommendation.recommendation_engine import RecommendationEngine
    from app.application.recommendation.candidate_generator import CandidateGenerator
    class BrokenGenerator(CandidateGenerator):
        def enumerate(self,garments,evaluator):
            yield from super().enumerate(garments,evaluator)
            raise failure
    engine = RequestCandidateEngine(structural_engine=RecommendationEngine(Query([garment("d","vest_dress")]),generator=BrokenGenerator()))
    result = rank([],engine=engine)
    assert result.status == status and not result.complete and result.winner is None and result.scored_count == 1


def test_incomplete_stream_stop_is_not_success_and_consumed_session_rejected():
    session = RequestCandidateEngine(Query([garment("d","vest_dress")])).generate_candidates("owner",StructuredOutfitRequest())
    next(session)
    engine = Mock(); engine.generate_candidates.return_value = session
    result = rank([],engine=engine)
    assert result.status == "InvalidScoringInput" and not result.winner


def test_tampered_empty_evaluation_rejected_before_any_scoring():
    request = StructuredOutfitRequest(colours=("blue",))
    base = RequestCandidateEngine(Query([annotated("d","vest_dress",primary_colour="blue")])).generate_candidates("owner",request)
    good = next(base)
    # Genuine session type with invalid condition coverage from a tampered producer.
    from app.domain.value_objects.candidate_generation_result import CandidateGenerationResult
    from app.application.recommendation.recommendation_engine import CandidateGenerationSession
    structural = CandidateGenerationSession([good.candidate],CandidateGenerationResult("Pending",False))
    evaluator = RequestConstraintEvaluator()
    evaluator.evaluate = lambda *_: RequestEvaluation(())
    session = RequestCandidateSession(structural,request,evaluator)
    engine = Mock(); engine.generate_candidates.return_value = session
    result = rank([],request,engine=engine)
    assert result.status == "InvalidScoringInput" and result.scored_count == 0


def test_invalid_preferences_return_no_winner_and_weights_have_no_hidden_fallback():
    result = rank([garment("d","vest_dress")],preferences=[pref(),pref(identifier="duplicate")])
    assert result.status == "InvalidPreferenceData" and not result.winner
    assert rank([garment("d","vest_dress")],profile="unknown").status == "ProfileUnavailable"


def test_actual_query_scoring_has_no_recommendation_or_history_writes():
    owner = str(uuid.uuid4())
    with TestClient(app,headers={"X-User-Id":owner}) as client:
        identifier,_ = review_and_confirm(client)
        assert client.put("/api/v1/account/preferences/styles",json={"preference_value":{"values":["vintage"]},"weight":1}).status_code == 200
        with connection() as conn:
            before = tuple(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("recommendations","recommendation_items","nlp_chats","user_preferences"))
        engine = RequestCandidateEngine(SqliteConfirmedGarmentQuery(),evaluator_factory=SuitabilityRequestEvaluator)
        result = RecommendationScorer(engine,SqliteActivePreferenceQuery()).rank(owner,StructuredOutfitRequest(occasion="campus",formality="casual"),"compatibility_deferred")
        assert result.status == "Selected" and result.winner.verified.candidate.members[0].garment.garment_id == identifier
        assert result.winner.score.preference.contribution == 1
        with connection() as conn:
            after = tuple(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("recommendations","recommendation_items","nlp_chats","user_preferences"))
        assert after == before
        with connection() as conn:
            conn.execute("UPDATE garments SET processing_item_id=NULL WHERE id=?",(identifier,))
        assert RecommendationScorer(engine,SqliteActivePreferenceQuery()).rank(owner,StructuredOutfitRequest(),"compatibility_deferred").status == "NoEligibleGarments"


def test_result_cannot_falsely_certify_winner_or_partial_success():
    with pytest.raises(ValueError): RankingOutcome("Selected",complete=True)
    with pytest.raises(ValueError): RankingOutcome("ProcessingFailure",complete=True)
    with pytest.raises(ValueError): CandidateRanker().better(garment("d","vest_dress"),None)
    result = rank([garment("d","vest_dress")])
    with pytest.raises(ValueError): replace(result,scored_count=0)
    other = rank([garment("d","vest_dress")])
    with pytest.raises(ValueError): CandidateRanker().better(result.winner,other.winner)


def test_foreign_owner_and_mismatched_session_request_are_rejected():
    outfit_request = StructuredOutfitRequest(colours=("blue",))
    session = RequestCandidateEngine(Query([annotated("d","vest_dress",primary_colour="blue")])).generate_candidates("owner",outfit_request)
    engine = Mock(); engine.generate_candidates.return_value = session
    result = rank([],StructuredOutfitRequest(),engine=engine)
    assert result.status == "InvalidScoringInput" and result.winner is None
    from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate,InvalidScoringInput
    session = RequestCandidateEngine(Query([garment("d","vest_dress")])).generate_candidates("owner",StructuredOutfitRequest())
    gate = ScoringEligibilityGate(session,"foreign",StructuredOutfitRequest())
    with pytest.raises(InvalidScoringInput): gate.verify(next(session))


def test_unsupported_and_unknown_preferences_do_not_fabricate_a_perfect_score():
    unsupported = replace(pref("style_note"),value_json='{"value":"relaxed neutral outfits"}')
    result = rank([garment("d","vest_dress")],preferences=[unsupported])
    assert result.winner.score.preference.summary.state == "NoSupportedPreferences"
    assert result.winner.score.total == 0 and result.diagnostics
    assert rank([garment("d","vest_dress")],preferences=[pref()]).winner.score.preference.summary.state == "Unknown"


def test_close_failure_and_incomplete_stop_discard_provisional_result():
    from app.application.recommendation.recommendation_engine import CandidateGenerationSession
    from app.domain.value_objects.candidate_generation_result import CandidateGenerationResult
    structural = CandidateGenerationSession([verified([garment("d","vest_dress")])[0].candidate],CandidateGenerationResult("Pending",False))
    session = RequestCandidateSession(structural,StructuredOutfitRequest(),RequestConstraintEvaluator())
    session.close = Mock(side_effect=RuntimeError("private close failure"))
    engine = Mock(); engine.generate_candidates.return_value = session
    result = rank([],engine=engine)
    assert result.status == "ProcessingFailure" and result.scored_count == 1 and not result.winner
    class IncompleteSession(RequestCandidateSession):
        def __next__(self):
            raise StopIteration
    incomplete = IncompleteSession(None,StructuredOutfitRequest(),RequestConstraintEvaluator())
    engine.generate_candidates.return_value = incomplete
    assert rank([],engine=engine).status == "ProcessingFailure"
