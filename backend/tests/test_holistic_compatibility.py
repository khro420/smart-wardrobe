"""Synthetic compatibility expectations are arithmetic tests, not review evidence."""
from dataclasses import FrozenInstanceError,replace,asdict
from fractions import Fraction as F
import copy
import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from app.application.recommendation.compatibility_reference_policy import CompatibilityReferencePolicy,DEFAULT_REFERENCES,EXISTING_REVIEW_PATTERNS
from app.application.recommendation.compatibility_evidence_mapper import CompatibilityEvidenceMapper
from app.application.recommendation.holistic_compatibility_scorer import HolisticCompatibilityScorer
from app.application.recommendation.holistic_scoring_profile import HolisticScoringProfile
from app.domain.value_objects.compatibility_signature import CompatibilityDescriptor,CompatibilitySignature,STRUCTURES
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from tests.test_recommendation_scoring import verified
from tests.test_suitability_policy import annotated

FIXTURE = Path(__file__).with_name("fixtures") / "compatibility_references.synthetic.v1.json"


def raw_fixture(): return json.loads(FIXTURE.read_text())
def policy(): return CompatibilityReferencePolicy.load(FIXTURE,allow_synthetic=True)
def garment(identifier,category,**updates):
    return annotated(identifier,category,style_tags=("vintage",),primary_colour="blue",pattern="plain",**updates)


def structures():
    return [garment("t","vest"),garment("b","trousers"),garment("d","vest_dress"),garment("o","long_sleeve_outwear")]


def test_all_structures_synthetic_exact_ratings_and_dress_is_one_member():
    scorer = HolisticCompatibilityScorer(policy())
    profile = HolisticScoringProfile.load("holistic_experimental")
    expected = {"top_bottom":F(3,4),"top_bottom_outerwear":F(5,8),"dress":F(1,2),"dress_outerwear":F(7,8)}
    results = {}
    for item in verified(structures()):
        signature,*_ = scorer.evidence.signature(item.candidate)
        result = scorer.score(item,profile)
        results[signature.structure] = result.summary.value
        assert result.summary.state == "Available" and result.summary.observed == result.summary.possible
        if signature.structure == "dress":
            assert len(signature.members) == 1 and signature.members[0][0] == "one_piece"
    assert results == expected
    assert results["dress"] != results["top_bottom"]


def test_equivalent_within_structure_alias_normalization_and_cache():
    p = policy()
    mapper = CompatibilityEvidenceMapper(p)
    first = verified([garment("d","vest_dress")])[0]
    second = verified([replace(garment("other","short_sleeve_dress"),primary_colour="#0000FF",pattern=" PLAIN ")])[0]
    assert mapper.signature(first.candidate)[0] == mapper.signature(second.candidate)[0]
    assert mapper.classify(first.candidate.members[0].garment) is mapper.classify(first.candidate.members[0].garment)
    assert mapper.cache_size == 2
    with pytest.raises(ValueError): mapper.classify(replace(first.candidate.members[0].garment,pattern="stripe"))


@pytest.mark.parametrize("updates,reason",[({"style_tags":None},"style:missing"),({"style_tags":()},"style:empty"),({"style_tags":("unapproved",)},"style:unrecognized"),({"style_tags":None,"invalid_attributes":("style_tags",)},"style:malformed"),({"primary_colour":None},"colour:missing"),({"primary_colour":"#xyz"},"colour:malformed"),({"primary_colour":"#182a46"},"colour:unrecognized"),({"pattern":None},"pattern:missing"),({"pattern":"solid"},"pattern:unrecognized"),({"pattern":"plain","invalid_attributes":("pattern",)},"pattern:malformed")])
def test_incomplete_evidence_remains_unknown(updates,reason):
    row = replace(garment("d","vest_dress"),**updates)
    item = verified([row])[0]
    result = HolisticCompatibilityScorer(policy()).score(item,HolisticScoringProfile.load("holistic_experimental"))
    assert result.summary.state == "Unknown" and result.summary.value is None and result.contribution == 0
    assert any(reason in x for x in result.details[0].reasons)


def test_missing_reference_zero_draft_unavailable_distinguished():
    profile = HolisticScoringProfile.load("holistic_experimental")
    zero = verified([replace(garment("d","vest_dress"),style_tags=("classic",),primary_colour="black")])[0]
    result = HolisticCompatibilityScorer(policy()).score(zero,profile)
    assert result.summary.state == "Available" and result.summary.value == 0
    unknown = verified([replace(garment("u","vest_dress"),primary_colour="red")])[0]
    assert "missing_approved_reference" in HolisticCompatibilityScorer(policy()).score(unknown,profile).summary.reasons
    raw = raw_fixture(); raw["references"][2]["approval_status"] = "draft"
    assert HolisticCompatibilityScorer(CompatibilityReferencePolicy(raw,True)).score(verified([garment("d","vest_dress")])[0],profile).summary.state == "Unknown"
    raw["available"] = False
    assert HolisticCompatibilityScorer(CompatibilityReferencePolicy(raw,True)).score(zero,profile).summary.state == "Unavailable"


def test_multiple_styles_preserved_sorted_and_not_first_selected():
    raw = raw_fixture()
    raw["references"][2]["signature"]["members"][0]["styles"] = ["vintage","classic"]
    p = CompatibilityReferencePolicy(raw,True)
    scorer = HolisticCompatibilityScorer(p)
    first = verified([replace(garment("d","vest_dress"),style_tags=("classic","vintage"))])[0]
    second = verified([replace(garment("e","vest_dress"),style_tags=("vintage","classic"))])[0]
    assert scorer.evidence.signature(first.candidate)[0] == scorer.evidence.signature(second.candidate)[0]
    assert scorer.score(first,HolisticScoringProfile.load("holistic_experimental")).summary.value == F(1,2)
    assert scorer.score(verified([garment("f","vest_dress")])[0],HolisticScoringProfile.load("holistic_experimental")).summary.state == "Unknown"


@pytest.mark.parametrize("mutation",["duplicate_signature","duplicate_id","bad_rating","bool_rating","bad_normalized","missing_reviewer","bad_approval","wrong_structure","unknown_style","unknown_pattern","invalid_activation"])
def test_config_validation(mutation):
    raw = raw_fixture(); item = raw["references"][0]
    if mutation == "duplicate_signature":
        extra = copy.deepcopy(item); extra["reference_id"] = "other"; raw["references"].append(extra)
    if mutation == "duplicate_id": raw["references"][1]["reference_id"] = item["reference_id"]
    if mutation == "bad_rating": item["ratings"][0]["rating"] = 5
    if mutation == "bool_rating": item["ratings"][0]["rating"] = True
    if mutation == "bad_normalized": item["normalized_value"]["numerator"] = 1
    if mutation == "missing_reviewer": item["ratings"][0]["reviewer_id"] = ""
    if mutation == "bad_approval": item["adjudication"]["decision"] = "pending"
    if mutation == "wrong_structure": item["signature"]["structure"] = "dress"
    if mutation == "unknown_style": item["signature"]["members"][0]["styles"] = ["unapproved"]
    if mutation == "unknown_pattern": raw["patterns"].append("newpattern")
    if mutation == "invalid_activation": raw["activation_approved"] = True
    with pytest.raises(ValueError): CompatibilityReferencePolicy(raw,True)


def test_fixture_opt_in_required_and_production_empty():
    with pytest.raises(ValueError): CompatibilityReferencePolicy.load(FIXTURE)
    real = CompatibilityReferencePolicy.load()
    assert not real.synthetic and len(real.approved) == 0 and len(real.references) == 0
    raw = raw_fixture(); raw["kind"] = "reviewed_reference_policy"
    with pytest.raises(ValueError): CompatibilityReferencePolicy(raw)


def test_immutable_policy_reference_and_nested_signature():
    raw = raw_fixture(); p = CompatibilityReferencePolicy(raw,True)
    raw["references"][0]["ratings"][0]["rating"] = 0
    reference = p.references[0]
    assert reference.ratings[0][1] == 2  # Sorted first reference is synthetic-dress.
    with pytest.raises(FrozenInstanceError): p.available = False
    with pytest.raises(TypeError): p.approved[reference.signature.key] = reference
    with pytest.raises(FrozenInstanceError): reference.value = F(1)
    styles = ["vintage"]
    descriptor = CompatibilityDescriptor(styles,"blue","plain")
    members = [["one_piece",descriptor]]
    signature = CompatibilitySignature("dress",members)
    styles.clear(); members.clear()
    assert signature.members[0][1].styles == ("vintage",)


def test_pattern_set_comes_from_existing_review_options():
    path = Path(__file__).resolve().parents[2] / "frontend/app/extract/results/page.tsx"
    line = next(x for x in path.read_text(encoding="utf-8").splitlines() if x.startswith("const patterns ="))
    assert set(json.loads(line.split("=",1)[1].strip().rstrip(";"))) == EXISTING_REVIEW_PATTERNS


def test_current_primary_cannot_be_overridden_by_secondary_or_palette():
    from app.shared_contracts.confirmed_garment_snapshot import GarmentPaletteEntry
    item = verified([replace(garment("d","vest_dress"),primary_colour="red",secondary_colour="blue",colour_palette=(GarmentPaletteEntry("#0000ff",1),))])[0]
    result = HolisticCompatibilityScorer(policy()).score(item,HolisticScoringProfile.load("holistic_experimental"))
    assert result.summary.state == "Unknown" and "missing_approved_reference" in result.summary.reasons
