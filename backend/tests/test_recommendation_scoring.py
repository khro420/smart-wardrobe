from dataclasses import FrozenInstanceError,replace
from fractions import Fraction as F
import json
import pytest
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate,InvalidScoringInput
from app.application.recommendation.request_match_scorer import RequestMatchScorer
from app.application.recommendation.preference_scorer import PreferenceScorer
from app.application.recommendation.compatibility_scorer import CompatibilityScorer,ProfileUnavailable
from app.application.recommendation.scoring_policy import ScoringProfile,DEFAULT_SCORING_POLICY
from app.application.recommendation.preference_normalizer import PreferenceNormalizer
from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore,RecommendationScore
from app.domain.value_objects.request_candidate_evaluation import RequestEvaluation,EvaluatedCandidate,MandatoryCondition
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest,GarmentCategoryConstraint
from app.domain.value_objects.scored_candidate import VerifiedScoringInput
from tests.test_suitability_policy import annotated,tag
from tests.test_structural_candidates import Query
from tests.test_preference_modelling import pref


def verified(rows,request=None):
    request = request or StructuredOutfitRequest()
    session = RequestCandidateEngine(Query(rows),evaluator_factory=SuitabilityRequestEvaluator).generate_candidates("owner",request)
    gate = ScoringEligibilityGate(session,"owner",request)
    return [gate.verify(item) for item in session]


def pair(second_styles=("classic",),second_colour="black"):
    tags = (tag(),tag("formality","casual"))
    return [annotated("t","vest",tags,primary_colour="blue",style_tags=("vintage",)),annotated("b","trousers",tags,primary_colour=second_colour,style_tags=second_styles)]


def five_fields():
    return StructuredOutfitRequest(occasion="campus",formality="casual",style="vintage",colours=("blue",),garment_categories=(GarmentCategoryConstraint("group","top"),GarmentCategoryConstraint("category","trousers")))


def test_worked_exact_request_preference_compatibility_and_total():
    profile = ScoringProfile.load("three_component_experimental")
    preferences = PreferenceNormalizer().normalize("owner",[pref("colours",["black"],"0.6",identifier="c"),pref("styles",["classic"],"0.4",identifier="s")])
    for rows,expected in ((pair(),(F(9,10),F(0),F(4,5),F(61,100))),(pair(("vintage","classic"),"grey"),(F(1),F(1,2),F(1,5),F(69,100)))):
        item = verified(rows,five_fields())[0]
        r,c,p = RequestMatchScorer().score(item),CompatibilityScorer().score(item,profile),PreferenceScorer().score(item,preferences)
        total = sum(w*x.contribution for w,x in zip(profile.weights,(r,c,p)))
        assert (r.contribution,c.contribution,p.contribution,total) == expected
        score = RecommendationScore(r,c,p,total,profile.name,profile.version,profile.weights)
        with pytest.raises(FrozenInstanceError): score.total = F(1)


def test_no_fields_and_preferences_are_not_perfect_defaults():
    item = verified([annotated("d","vest_dress")])[0]
    r = RequestMatchScorer().score(item)
    p = PreferenceScorer().score(item,PreferenceNormalizer().normalize("owner",[]))
    assert r.summary.state == "NotApplicable" and r.summary.value is None and r.contribution == 0
    assert p.summary.state == "NoPreferences" and p.contribution == 0
    assert CompatibilityScorer().score(item,ScoringProfile.load("compatibility_deferred")).summary.state == "Unavailable"
    with pytest.raises(ProfileUnavailable): CompatibilityScorer().score(item,ScoringProfile.load("three_component_experimental"))


def test_missing_vs_confirmed_nonmatch_preference_and_request_style():
    prefs = PreferenceNormalizer().normalize("owner",[pref("styles",["classic"])])
    first = verified(pair(second_styles=None),StructuredOutfitRequest(style="vintage"))[0]
    score = PreferenceScorer().score(first,prefs)
    request = RequestMatchScorer().score(first)
    assert score.contribution == 0 and score.summary.state == "Partial"
    assert request.contribution == F(1,2) and request.summary.state == "Partial"
    assert "missing:b" in request.details[0].reasons
    second = verified(pair(second_styles=("vintage",)))[0]
    assert PreferenceScorer().score(second,prefs).summary.state == "Available"
    malformed = verified([replace(g,style_tags=None,invalid_attributes=("style_tags",)) for g in pair()])[0]
    unknown = PreferenceScorer().score(malformed,prefs)
    assert unknown.details[0].state == "Unknown" and "malformed:b" in unknown.details[0].reasons


def test_category_colour_alternatives_and_formality_require_common_value():
    prefs = PreferenceNormalizer().normalize("owner",[pref("colours",["blue","red"],identifier="c"),pref("garment_categories",[{"kind":"group","value":"top"},{"kind":"category","value":"vest"}],identifier="g"),pref("formality",["casual","smart_casual"],identifier="f")])
    rows = pair()
    assert PreferenceScorer().score(verified(rows)[0],prefs).contribution == 1
    rows[1] = replace(rows[1],custom_tags=(tag("formality","smart_casual"),))
    score = PreferenceScorer().score(verified(rows)[0],prefs)
    assert score.contribution == F(2,3)
    detail = next(x for x in score.details if x.name == "formality")
    assert detail.state == "Unknown"  # No common affirmed level, not proven unsuitable.


def test_unknown_kept_in_weighted_denominator_and_not_renormalized():
    prefs = PreferenceNormalizer().normalize("owner",[pref("colours",["blue"],"0.6",identifier="c"),pref("styles",["classic"],"0.4",identifier="s")])
    item = verified([replace(x,style_tags=None) for x in pair()])[0]
    p = PreferenceScorer().score(item,prefs)
    assert p.contribution == F(3,5) and p.summary.state == "Partial"


def test_compatibility_partial_pairs_not_evidence_only_denominator():
    rows = pair(second_styles=("vintage",)) + [annotated("o","long_sleeve_outwear",style_tags=None)]
    item = next(x for x in verified(rows) if len(x.candidate.members) == 3)
    c = CompatibilityScorer().score(item,ScoringProfile.load("three_component_experimental"))
    assert c.contribution == F(1,3) and c.summary.state == "Partial"
    assert c.summary.observed == 1 and c.summary.possible == 3


@pytest.mark.parametrize("weights",[["0.1","0.2","0.7"],[.1,.2,.7]])
def test_exact_weight_loading_no_float_validation_error(tmp_path,weights):
    raw = json.loads(DEFAULT_SCORING_POLICY.read_text())
    raw["profiles"]["three_component_experimental"]["weights"] = weights
    path = tmp_path / "weights.json"; path.write_text(json.dumps(raw))
    assert ScoringProfile.load("three_component_experimental",path).weights == (F(1,10),F(1,5),F(7,10))


@pytest.mark.parametrize("weights",[["NaN","0","1"],["-0.1","0.1","1"],["0.5","0.2","0.2"],[True,0,0],["0","0","0"],["1","0"]])
def test_invalid_weights(tmp_path,weights):
    raw = json.loads(DEFAULT_SCORING_POLICY.read_text())
    raw["profiles"]["three_component_experimental"]["weights"] = weights
    path = tmp_path / "weights.json"; path.write_text(json.dumps(raw))
    with pytest.raises(ValueError): ScoringProfile.load("three_component_experimental",path)


def test_bare_empty_coverage_wrong_context_and_unknown_fail_rejected():
    request = StructuredOutfitRequest(colours=("blue",))
    session = RequestCandidateEngine(Query(pair())).generate_candidates("owner",request)
    with pytest.raises(InvalidScoringInput): ScoringEligibilityGate(session,"owner",StructuredOutfitRequest())
    gate = ScoringEligibilityGate(session,"owner",request)
    item = next(session)
    with pytest.raises(InvalidScoringInput): gate.verify(item.candidate)
    with pytest.raises(InvalidScoringInput): gate.verify(EvaluatedCandidate(item.candidate,RequestEvaluation(())))
    with pytest.raises(InvalidScoringInput): ScoringEligibilityGate(session,"owner",request)
    with pytest.raises(ValueError): VerifiedScoringInput(item,request,"owner",id(session))
    for state in ("Fail","Unknown"):
        with pytest.raises(ValueError): EvaluatedCandidate(item.candidate,RequestEvaluation((MandatoryCondition("colours","blue",state),)))


def test_component_bounds_and_nested_immutability():
    for value in (F(-1),F(2)):
        with pytest.raises(ValueError): ScoreEvidence("x",value,"Available")
    reasons = ["missing:x"]
    detail = ScoreEvidence("x",None,"Unknown",0,1,reasons)
    reasons.clear()
    details = [detail]
    component = ComponentScore(detail,details)
    details.clear()
    assert component.details[0].reasons == ("missing:x",)
    with pytest.raises(FrozenInstanceError): detail.state = "Available"


def test_colour_preference_unknown_and_known_nonmatch_are_distinct():
    prefs = PreferenceNormalizer().normalize("owner",[pref("colours",["blue"])])
    unknown = PreferenceScorer().score(verified([annotated("d","vest_dress",primary_colour="#182a46")])[0],prefs)
    nonmatch = PreferenceScorer().score(verified([annotated("d","vest_dress",primary_colour="red")])[0],prefs)
    assert unknown.summary.state == "Unknown" and unknown.summary.value is None
    assert nonmatch.summary.state == "Available" and nonmatch.summary.value == 0


def test_no_compatibility_evidence_is_unknown_not_perfect():
    item = verified([replace(x,style_tags=None) for x in pair()])[0]
    score = CompatibilityScorer().score(item,ScoringProfile.load("three_component_experimental"))
    assert score.summary.state == "Unknown" and score.summary.value is None and score.contribution == 0
