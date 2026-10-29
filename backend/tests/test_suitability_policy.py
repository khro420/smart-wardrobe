"""Approved declaration-policy tests; no independently reviewed suitability claims."""
from dataclasses import FrozenInstanceError,replace
import json
from unittest.mock import Mock
import pytest
from app.application.recommendation.suitability_policy import SuitabilityPolicy,DEFAULT_POLICY
from app.application.recommendation.suitability_evidence_mapper import SuitabilityEvidenceParser
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.request_candidate_session import RequestProcessingError
from app.domain.value_objects.garment_suitability_evidence import GarmentSuitabilityEvidence,SuitabilityDeclaration
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest,GarmentCategoryConstraint
from app.application.nlp.nlp_interpreter import NLPInterpreter
from tests.test_structural_candidates import garment,Query


def annotated(identifier,category,tags=None,**fields):
    return replace(garment(identifier,category),custom_tags=tags,**fields)


def tag(field="occasion",value="campus",decision="allow"):
    return f"rec:v1:{field}:{value}:{decision}"


def run(rows,request,reverse=False):
    engine = RequestCandidateEngine(Query(list(reversed(rows)) if reverse else rows),evaluator_factory=SuitabilityRequestEvaluator)
    session = engine.generate_candidates("owner",request)
    return list(session),session


@pytest.mark.parametrize("field,values",[("occasion",("campus","work","casual_outing","shopping","dinner","party","date","travel")),("formality",("casual","smart_casual"))])
def test_all_enabled_values_allow_deny_and_no_inference(field,values):
    for value in values:
        request = StructuredOutfitRequest(**{field:value})
        for decision,state in (("allow","MatchingCandidates"),("deny","NoMatchingCandidates")):
            candidates,session = run([annotated("d","vest_dress",[tag(field,value,decision)])],request)
            assert session.result.status == state and session.result.complete
            assert bool(candidates) == (decision == "allow")
        candidates,session = run([annotated("d","vest_dress",["casual","formal","sporty","office"])],request)
        assert not candidates and session.result.status == "InsufficientEvidence"


@pytest.mark.parametrize("categories",[("vest","trousers"),("vest","trousers","long_sleeve_outwear"),("vest_dress",),("vest_dress","short_sleeve_outwear")])
def test_all_four_compositions_require_all_worn_garments(categories):
    rows = [annotated(str(i),category,[tag(),tag("formality","casual")]) for i,category in enumerate(categories)]
    request = StructuredOutfitRequest(occasion="campus",formality="casual")
    passing,session = run(rows,request)
    assert len(passing) == (2 if len(categories)>1 and "outwear" in categories[-1] else 1)
    assert any(len(item.candidate.members) == len(categories) for item in passing)
    rows[-1] = replace(rows[-1],custom_tags=None)
    passing,session = run(rows,request)
    assert not any(len(item.candidate.members) == len(categories) for item in passing)
    if "outwear" in categories[-1]:
        assert len(passing) == 1 and session.result.unknown == 1
    else:
        assert not passing and session.result.status == "InsufficientEvidence"


@pytest.mark.parametrize("tags,flags,expected",[(None,(),"Unknown"),([],(),"Unknown"),(["campus","occasion:campus:allow"],(),"Unknown"),([tag(),tag(decision="deny")],(),"Unknown"),([tag()],("custom_tags",),"Unknown"),([tag(value="work")],(),"Unknown"),([tag("formality","smart_casual")],(),"Unknown"),([tag(),"rec:v1:occasion:campus:maybe"],(),"Unknown"),([tag(),"rec:v2:occasion:campus:allow"],(),"Unknown"),([tag(),"rec:v1:occasion:wedding:allow"],(),"Unknown"),([tag(),"REC:v1:occasion:campus:allow"],(),"Unknown"),([tag(),"rec:bad"],(),"Unknown"),([tag(),"ordinary tag"],(),"Pass"),([tag(),"rec:v1:formality:formal:allow"],(),"Pass")])
def test_missing_conflicting_unknown_and_malformed_annotations(tags,flags,expected):
    evidence = SuitabilityEvidenceParser().parse(annotated("d","vest_dress",tags,invalid_attributes=flags))
    assert evidence.state_for("occasion","campus") == expected


def test_no_formality_hierarchy_or_style_to_suitability():
    rows = [annotated("d","vest_dress",[tag("formality","smart_casual")],style_tags=("casual","formal","sporty"),fit="regular",material="cotton")]
    candidates,session = run(rows,StructuredOutfitRequest(formality="casual"))
    assert not candidates and session.result.status == "InsufficientEvidence"
    rows[0] = replace(rows[0],custom_tags=(tag("formality","casual"),tag("formality","smart_casual")))
    assert run(rows,StructuredOutfitRequest(formality="casual"))[0]


def test_definite_failure_overrides_unknown_in_same_outfit_and_other_fields():
    rows = [annotated("t","vest",[tag(decision="deny")]),annotated("b","trousers",None)]
    candidates,session = run(rows,StructuredOutfitRequest(occasion="campus",formality="casual",colours=("blue",)))
    assert not candidates and session.result.failed == 1 and session.result.unknown == 0
    rows = [annotated("d","vest_dress",[tag()])]
    candidates,session = run(rows,StructuredOutfitRequest(occasion="campus",garment_categories=(GarmentCategoryConstraint("category","trousers"),)))
    assert not candidates and session.result.status == "NoMatchingCandidates"


@pytest.mark.parametrize("fields",[{"occasion":"exercise"},{"formality":"formal"},{"occasion":"wedding"},{"formality":"unknown"}])
def test_unavailable_values_terminate_before_retrieval(fields):
    query = Query(())
    session = RequestCandidateEngine(query,evaluator_factory=SuitabilityRequestEvaluator).generate_candidates("owner",StructuredOutfitRequest(**fields))
    assert not list(session) and query.calls == 0
    assert session.result.status == "PolicyUnavailable" and not session.result.complete


def test_default_remains_unavailable_and_no_fields_are_behaviourally_identical():
    rows = [annotated("d","vest_dress",[tag()],primary_colour="blue",style_tags=("vintage",))]
    query = Query(rows)
    default = RequestCandidateEngine(query).generate_candidates("owner",StructuredOutfitRequest(occasion="campus"))
    assert not list(default) and default.result.status == "PolicyUnavailable" and query.calls == 0
    request = StructuredOutfitRequest(colours=("blue",),style="vintage")
    old = RequestCandidateEngine(Query(rows)).generate_candidates("owner",request)
    new,new_session = run(rows,request)
    assert list(old) == new and old.result == new_session.result


def test_combined_five_fields_preserves_minimum_rules_and_request():
    interpreted = NLPInterpreter().interpret("Recommend an outfit for campus with vintage style, casual clothes, using blue and black colours with a top and trousers.")
    request = interpreted.structured_request
    assert request is not None and request.occasion == "campus" and request.formality == "casual"
    original = request.to_dict()
    tags = [tag(),tag("formality","casual")]
    rows = [annotated("t","vest",tags,primary_colour="blue",style_tags=("vintage",)),annotated("b","trousers",tags,primary_colour="black",style_tags=("classic",))]
    candidates,session = run(rows,request)
    assert len(candidates) == 1 and session.result.complete and request.to_dict() == original
    assert {c.field for c in candidates[0].evaluation.conditions} == {"occasion","formality","style","colours","garment_categories"}
    rows[0] = replace(rows[0],primary_colour="#182a46")
    candidates,session = run(rows,replace(request,colours=("navy",)))
    assert not candidates and session.result.status == "InsufficientEvidence"


def test_determinism_tag_order_and_cache_conflict_detection():
    tags = [tag(),tag("formality","casual")]
    rows = [annotated("t","vest",tags),annotated("b","trousers",tags),annotated("d","vest_dress",tags),annotated("o","long_sleeve_outwear",tags)]
    request = StructuredOutfitRequest(occasion="campus",formality="casual")
    first,a = run(rows,request)
    second,b = run([replace(g,custom_tags=tuple(reversed(g.custom_tags))) for g in rows],request,reverse=True)
    assert [x.candidate.key for x in first] == [x.candidate.key for x in second] and a.result == b.result
    evaluator = a.evaluator
    assert evaluator.parser.cache_size == 4
    assert evaluator.parser.parse(rows[0]) is evaluator.parser.parse(rows[0])
    with pytest.raises(ValueError): evaluator.parser.parse(replace(rows[0],custom_tags=()))


def test_stream_close_failure_interruption_and_no_false_success():
    rows = [annotated("d1","vest_dress",[tag()]),annotated("d2","vest_dress",[tag()])]
    session = RequestCandidateEngine(Query(rows),evaluator_factory=SuitabilityRequestEvaluator).generate_candidates("owner",StructuredOutfitRequest(occasion="campus"))
    assert next(session) and not session.result.complete
    session.close()
    assert not session.result.complete and session.result.status == "Interrupted"
    for failure,status in ((RuntimeError("private"),"ProcessingFailure"),(KeyboardInterrupt(),"Interrupted")):
        evaluator = SuitabilityRequestEvaluator()
        evaluator.parser.parse = Mock(side_effect=failure)
        session = RequestCandidateEngine(Query(rows),evaluator_factory=lambda:evaluator).generate_candidates("owner",StructuredOutfitRequest(occasion="campus"))
        with pytest.raises(RequestProcessingError if isinstance(failure,Exception) else KeyboardInterrupt): next(session)
        assert session.result.status == status and not session.result.complete


def test_failure_after_emitting_candidate_does_not_certify_partial_stream():
    rows = [annotated("d1","vest_dress",[tag()]),annotated("d2","vest_dress",[tag()])]
    evaluator = SuitabilityRequestEvaluator()
    first = evaluator.parser.parse(rows[0])
    evaluator.parser.parse = Mock(side_effect=[first,RuntimeError("later failure")])
    session = RequestCandidateEngine(Query(rows),evaluator_factory=lambda:evaluator).generate_candidates("owner",StructuredOutfitRequest(occasion="campus"))
    assert next(session) and session.result.passed == 1 and not session.result.complete
    with pytest.raises(RequestProcessingError): next(session)
    assert session.result.status == "ProcessingFailure" and not session.result.complete


def test_immutable_evidence_and_policy():
    declarations = [SuitabilityDeclaration("occasion","campus","allow")]
    malformed = ["formality"]
    evidence = GarmentSuitabilityEvidence(declarations,malformed,"Parsed")
    declarations.clear(); malformed.clear()
    assert evidence.state_for("occasion","campus") == "Pass" and evidence.malformed_fields == ("formality",)
    with pytest.raises(FrozenInstanceError): evidence.source_state = "Empty"
    with pytest.raises(FrozenInstanceError): evidence.declarations[0].decision = "deny"
    with pytest.raises(ValueError): GarmentSuitabilityEvidence([["occasion","campus","allow"]],(),"Parsed")
    policy = SuitabilityPolicy.load()
    with pytest.raises(FrozenInstanceError): policy.version = "other"
    with pytest.raises(ValueError): replace(policy,enabled_formality=("casual","formal"))


@pytest.mark.parametrize("updates",[{"default_activation":True},{"enabled_occasions":["campus"]},{"enabled_formality":["casual","formal"]},{"reserved_prefix":"rec:v2"},{"aggregation":"any"}])
def test_invalid_policy_rejected(tmp_path,updates):
    raw = json.loads(DEFAULT_POLICY.read_text())
    path = tmp_path / "policy.json"; path.write_text(json.dumps(dict(raw,**updates)))
    with pytest.raises(ValueError): SuitabilityPolicy.load(path)


def test_query_failures_preserve_controlled_status_and_empty_structure():
    query = Mock()
    query.get_confirmed_available_garments.side_effect = RuntimeError("private")
    session = RequestCandidateEngine(query,evaluator_factory=SuitabilityRequestEvaluator).generate_candidates("owner",StructuredOutfitRequest(occasion="campus"))
    assert not list(session) and session.result.status == "ProcessingFailure" and not session.result.complete
    assert run([],StructuredOutfitRequest(occasion="campus"))[1].result.status == "NoEligibleGarments"
    assert run([annotated("t","vest",[tag()])],StructuredOutfitRequest(occasion="campus"))[1].result.status == "InsufficientStructure"
