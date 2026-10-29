"""Explicit experimental ranking/evaluation; synthetic fixtures are not validation."""
from dataclasses import asdict,replace
from fractions import Fraction as F
import copy
import json
from pathlib import Path
from unittest.mock import Mock
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.application.recommendation.holistic_recommendation_scorer import HolisticRecommendationScorer
from app.application.recommendation.compatibility_reference_policy import CompatibilityReferencePolicy,DEFAULT_REFERENCES
from app.application.recommendation.holistic_scoring_profile import HolisticScoringProfile,DEFAULT_HOLISTIC_PROFILES
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.recommendation_scorer import RecommendationScorer
from app.application.recommendation.recommendation_engine import RecommendationEngine
from app.application.recommendation.candidate_generator import CandidateGenerator
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.infrastructure.persistence.active_preference_query_adapter import SqliteActivePreferenceQuery
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.persistence.postgresql_repository import connection
from tests.test_holistic_compatibility import policy,structures,garment,FIXTURE,raw_fixture
from tests.test_structural_candidates import Query
from tests.test_candidate_ranking import Preferences
from tests.test_preference_modelling import pref
from tests.test_suitability_tag_workflow import review_and_confirm
from scripts.evaluate_compatibility import evaluate,load_cases,main


def run(rows,request=None,preferences=(),reference_policy=None,profile_path=DEFAULT_HOLISTIC_PROFILES,profile="holistic_experimental",engine=None):
    scorer = HolisticRecommendationScorer(engine or RequestCandidateEngine(Query(rows),evaluator_factory=SuitabilityRequestEvaluator),Preferences(preferences),reference_policy or policy(),profile_path,allow_synthetic=True)
    return scorer.rank("owner",request or StructuredOutfitRequest(),profile)


def coverage(outcome):
    result = {}
    for code,value in outcome.diagnostics:
        if code.startswith("coverage:"):
            field,count = value.split("=")
            result.setdefault(code.split(":",1)[1],{})[field] = int(count)
    return result


def test_all_structures_ranked_no_pair_rejection_and_order_independent():
    first = run(structures())
    second = run(list(reversed(structures())))
    assert first.status == "Selected" and first.complete and first.scored_count == 4
    assert first.winner.score.total == F(21,80)  # .30 * 7/8; R/P unavailable contribute zero.
    assert first.winner.verified.candidate.key == second.winner.verified.candidate.key
    assert first.winner.score == second.winner.score
    assert all(x["reviewed"] == 1 and x["examined"] == 1 for x in coverage(first).values())
    assert first.winner.score.request_match.summary.state == "NotApplicable"
    assert first.winner.score.preference.summary.state == "NoPreferences"


def test_reviewed_and_unknown_are_both_kept_under_fixed_weights():
    rows = [garment("known","vest_dress"),replace(garment("unknown","vest_dress"),primary_colour="red"),replace(garment("zero","vest_dress"),primary_colour="black",style_tags=("classic",))]
    result = run(rows)
    assert result.scored_count == 3 and result.winner.verified.candidate.members[0].garment.garment_id == "known"
    assert result.winner.score.total == F(3,20)
    assert coverage(result)["dress"]["reviewed"] == 2  # Includes reviewed numerical zero.
    assert coverage(result)["dress"]["unknown"] == 1


def test_empty_real_reference_policy_returns_unknown_without_rejecting_dresses():
    result = run(structures(),reference_policy=CompatibilityReferencePolicy.load())
    assert result.status == "Selected" and result.scored_count == 4 and result.complete
    assert result.winner.score.compatibility.summary.state == "Unknown" and result.winner.score.compatibility.summary.value is None
    assert result.winner.score.total == 0
    assert sum(x["reviewed"] for x in coverage(result).values()) == 0


def test_disabled_policy_is_unavailable_not_known_zero():
    raw = raw_fixture(); raw["available"] = False
    result = run([garment("d","vest_dress")],reference_policy=CompatibilityReferencePolicy(raw,True))
    assert result.status == "Selected" and result.winner.score.compatibility.summary.state == "Unavailable"
    assert coverage(result)["dress"]["unavailable"] == 1


def test_old_profiles_and_default_suitability_untouched():
    engine = RequestCandidateEngine(Query(structures()))
    old = RecommendationScorer(engine,Preferences())
    assert old.rank("owner",StructuredOutfitRequest(),"three_component_experimental").status == "ProfileUnavailable"
    assert old.rank("owner",StructuredOutfitRequest(),"compatibility_deferred").status == "Selected"
    assert old.rank("owner",StructuredOutfitRequest(),"holistic_experimental").status == "ProfileUnavailable"
    new = HolisticRecommendationScorer(engine,Preferences())
    assert new.rank("owner",StructuredOutfitRequest(occasion="campus"),"holistic_experimental").status == "PolicyUnavailable"
    with pytest.raises(ValueError): HolisticRecommendationScorer(engine,Preferences(),policy())


@pytest.mark.parametrize("failure,status",[(RuntimeError("private"),"ProcessingFailure"),(KeyboardInterrupt(),"Interrupted")])
def test_late_stream_failure_discards_provisional_best(failure,status):
    class Broken(CandidateGenerator):
        def enumerate(self,garments,evaluator):
            yield from super().enumerate(garments,evaluator)
            raise failure
    engine = RequestCandidateEngine(structural_engine=RecommendationEngine(Query([garment("d","vest_dress")]),generator=Broken()))
    result = run([],engine=engine)
    assert result.status == status and not result.complete and result.winner is None and result.scored_count == 1


def test_mandatory_fail_unknown_and_malformed_preferences_never_selected():
    assert run([garment("d","vest_dress")],StructuredOutfitRequest(colours=("red",))).status == "NoMatchingCandidates"
    assert run([replace(garment("d","vest_dress"),primary_colour="#182a46")],StructuredOutfitRequest(colours=("navy",))).status == "InsufficientEvidence"
    assert run([garment("d","vest_dress")],preferences=[pref(),pref(identifier="duplicate")]).status == "InvalidPreferenceData"
    assert run([garment("d","vest_dress")],profile="unknown").status == "ProfileUnavailable"


def test_actual_phase1_eligibility_no_history_or_preference_writes():
    owner = str(uuid.uuid4())
    with TestClient(app,headers={"X-User-Id":owner}) as client:
        identifier,_ = review_and_confirm(client)
        assert client.patch(f"/api/v1/wardrobe/garments/{identifier}",json={"pattern":"plain"}).status_code == 200
        tables = ("recommendations","recommendation_items","nlp_chats","user_preferences")
        with connection() as conn:
            before = tuple(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables)
        scorer = HolisticRecommendationScorer(RequestCandidateEngine(SqliteConfirmedGarmentQuery(),evaluator_factory=SuitabilityRequestEvaluator),SqliteActivePreferenceQuery())
        result = scorer.rank(owner,StructuredOutfitRequest(occasion="campus",formality="casual"),"holistic_experimental")
        assert result.status == "Selected" and result.winner.score.compatibility.summary.state == "Unknown"
        with connection() as conn:
            assert tuple(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables) == before
            conn.execute("UPDATE garments SET processing_item_id=NULL WHERE id=?",(identifier,))
        assert scorer.rank(owner,StructuredOutfitRequest(),"holistic_experimental").status == "NoEligibleGarments"


def fixture_cases(tmp_path,partition="development"):
    rows = [garment("blue-dress","vest_dress"),replace(garment("red-dress","vest_dress"),primary_colour="red")]
    preferences = [pref("colours",["red"],"1")]
    raw = {"schema_version":"1.0.0","version":"synthetic-cases-test-only","kind":"synthetic_fixture","validation_locked":True,"cases":[{
        "case_id":"synthetic-sensitivity","partition":partition,"source_ids":["synthetic-new-garments"],"user_id":"owner","wardrobe":[asdict(x) for x in rows],"request":{},"preferences":[asdict(x) for x in preferences]}]}
    path = tmp_path / "cases.json"; path.write_text(json.dumps(raw))
    profiles = json.loads(DEFAULT_HOLISTIC_PROFILES.read_text())
    # Explicit test-only weights, not additional deployed profiles.
    profiles["profiles"]["synthetic_compatibility_heavy"] = ["0.4","0.5","0.1"]
    pp = tmp_path / "profiles.json"; pp.write_text(json.dumps(profiles))
    return path,pp


def test_reproducible_tool_coverage_and_explicit_weight_sensitivity(tmp_path):
    cases,profiles = fixture_cases(tmp_path)
    names = ("holistic_experimental","synthetic_compatibility_heavy")
    first = evaluate(FIXTURE,cases,profiles,names,allow_synthetic=True)
    assert first == evaluate(FIXTURE,cases,profiles,names,allow_synthetic=True)
    case = first["cases"][0]
    assert case["winner_changes_across_profiles"] is True
    assert case["results"][0]["winner_key"] != case["results"][1]["winner_key"]
    assert case["results"][0]["coverage_by_structure"]["dress"]["reviewed_fraction"] == .5
    assert first["fashion_accuracy"] is None and first["independent_validation_complete"] is False


def test_dataset_partition_leakage_and_validation_guards(tmp_path):
    cases,profiles = fixture_cases(tmp_path,"validation")
    output = tmp_path / "output.json"
    args = ["--references",str(FIXTURE),"--cases",str(cases),"--profiles-file",str(profiles),"--allow-synthetic-fixtures","--partition","validation","--output",str(output)]
    with pytest.raises(SystemExit): main(args)
    main([*args,"--confirm-locked-validation"])
    assert json.loads(output.read_text())["synthetic_cases"] is True
    raw = json.loads(cases.read_text())
    raw["cases"][0]["source_ids"] = ["synthetic-source-dress"]
    cases.write_text(json.dumps(raw))
    with pytest.raises(ValueError): load_cases(cases,True,policy())


def test_empty_production_audit_no_fabricated_coverage_or_reviews():
    report = evaluate()
    assert report["approved_reference_count"] == 0 and report["evaluated_case_count"] == 0
    assert report["candidate_coverage"] is None and report["fashion_accuracy"] is None
    assert report["activation_approved"] is False


def test_incomplete_stop_and_close_failure_never_publish_a_winner():
    from app.application.recommendation.request_candidate_session import RequestCandidateSession
    from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
    from app.application.recommendation.recommendation_engine import CandidateGenerationSession
    from app.domain.value_objects.candidate_generation_result import CandidateGenerationResult
    from tests.test_recommendation_scoring import verified
    candidate = verified([garment("d","vest_dress")])[0].candidate
    class Incomplete(RequestCandidateSession):
        def __next__(self):
            if self.result.passed:
                raise StopIteration
            return super().__next__()
    for incomplete in (True,False):
        structural = CandidateGenerationSession([candidate],CandidateGenerationResult("Pending",False))
        session = (Incomplete if incomplete else RequestCandidateSession)(structural,StructuredOutfitRequest(),RequestConstraintEvaluator())
        if not incomplete:
            session.close = Mock(side_effect=RuntimeError("close failed"))
        engine = Mock(); engine.generate_candidates.return_value = session
        result = run([],engine=engine)
        assert result.status == "ProcessingFailure" and result.scored_count == 1 and not result.complete and result.winner is None


@pytest.mark.parametrize("mutation",["duplicate_id","source_overlap","real_claim"])
def test_evaluation_partition_integrity(tmp_path,mutation):
    cases,_ = fixture_cases(tmp_path)
    raw = json.loads(cases.read_text())
    if mutation in ("duplicate_id","source_overlap"):
        other = copy.deepcopy(raw["cases"][0])
        if mutation == "source_overlap":
            other["case_id"] = "other"; other["partition"] = "validation"
        raw["cases"].append(other)
    else:
        raw["kind"] = "held_out_review_dataset"
    cases.write_text(json.dumps(raw))
    with pytest.raises(ValueError): load_cases(cases,True,policy())


@pytest.mark.parametrize("weights",[["NaN","0","1"],[True,0,0],["0.4","0.3","0.2"]])
def test_holistic_profile_invalid_weights(tmp_path,weights):
    raw = json.loads(DEFAULT_HOLISTIC_PROFILES.read_text()); raw["profiles"]["holistic_experimental"] = weights
    path = tmp_path / "bad.json"; path.write_text(json.dumps(raw))
    with pytest.raises(ValueError): HolisticScoringProfile.load("holistic_experimental",path)
