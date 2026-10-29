"""Phase 3B-1 minimum conditions, cache, exhaustive equivalence and integration."""
from dataclasses import FrozenInstanceError, replace
from unittest.mock import Mock
import uuid
import pytest
from fastapi.testclient import TestClient

from tests.test_structural_candidates import garment, Query
from tests.test_o2_recommendation_boundary import confirmed_garment
from app.main import app
from app.infrastructure.persistence.postgresql_repository import connection
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.request_candidate_session import RequestProcessingError
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.recommendation.colour_classifier import ColourClassifier
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.application.nlp.nlp_interpreter import NLPInterpreter
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest, GarmentCategoryConstraint
from app.domain.value_objects.request_candidate_evaluation import MandatoryCondition, RequestEvaluation, AttributeEvidence


def run(rows,request,optimized=True):
    session = RequestCandidateEngine(Query(rows),optimized=optimized).generate_candidates("owner",request)
    return list(session),session


def dressed(identifier,category,colour=None,styles=None,**fields):
    return replace(garment(identifier,category),primary_colour=colour,style_tags=styles,**fields)


@pytest.mark.parametrize("value,name,state", [("gray","grey","Known"),(" NAVY   BLUE ","navy","Known"),("cream","cream","Known"),("#FFF","white","Known"),("#000080","navy","Known"),("#0000ff","blue","Known"),("#00007f",None,"Unrecognized"),("#123456",None,"Unrecognized"),("#ffffff00",None,"Malformed"),("#xyz",None,"Malformed"),(None,None,"Missing"),("",None,"Missing"),("light blue",None,"Unrecognized")])
def test_named_colours_and_exact_anchors_only(value,name,state):
    evidence = ColourClassifier().classify(value)
    assert evidence.state == state and evidence.values == ((name,) if name else ())


def test_collective_categories_and_overlapping_group():
    request = StructuredOutfitRequest(garment_categories=[GarmentCategoryConstraint("group","top"),GarmentCategoryConstraint("category","vest"),GarmentCategoryConstraint("category","trousers")])
    rows = [garment("t","vest"),garment("b","trousers"),garment("d","vest_dress")]
    candidates,session = run(rows,request)
    assert len(candidates) == 1 and session.result.passed == 1 and session.result.failed == 1
    assert all(condition.state == "Pass" for condition in candidates[0].evaluation.conditions)


def test_global_colours_collective_and_primary_precedence():
    rows = [dressed("t","vest","navy blue",("vintage",),secondary_colour="#ff0000"),dressed("b","trousers","#000000",("classic",))]
    candidates,session = run(rows,StructuredOutfitRequest(colours=("navy","black")))
    assert len(candidates) == 1 and session.result.complete
    assert {condition.value for condition in candidates[0].evaluation.conditions} == {"navy","black"}
    candidates,session = run(rows,StructuredOutfitRequest(colours=("red",)))
    assert not candidates and session.result.status == "NoMatchingCandidates"


@pytest.mark.parametrize("styles,flags,state", [(("vintage",),(),"Pass"),(("classic",),(),"Fail"),((),(),"Fail"),(None,(),"Unknown"),(("unmapped",),(),"Unknown"),(("vintage",),("style_tags",),"Unknown"),(("classic","unmapped"),(),"Unknown"),(("vintage","classic"),(),"Pass")])
def test_style_known_missing_empty_conflicting_malformed(styles,flags,state):
    rows = [dressed("d","vest_dress",styles=styles,invalid_attributes=flags)]
    candidates,session = run(rows,StructuredOutfitRequest(style="vintage"))
    assert bool(candidates) == (state == "Pass")
    assert session.result.status == {"Pass":"MatchingCandidates","Fail":"NoMatchingCandidates","Unknown":"InsufficientEvidence"}[state]


def test_style_base_only_and_unknown_not_aesthetic_claim():
    rows = [dressed("t","vest",styles=("vintage",)),dressed("b","trousers",styles=None),dressed("o","long_sleeve_outwear",styles=("sporty",))]
    candidates,session = run(rows,StructuredOutfitRequest(style="vintage"))
    assert len(candidates) == 2
    assert all(item.validity == "APPROVED_MINIMUM_REQUEST_CONDITIONS" for item in candidates)
    rows = [dressed("d","vest_dress",styles=("classic",)),dressed("o","long_sleeve_outwear",styles=("vintage",))]
    candidates,session = run(rows,StructuredOutfitRequest(style="vintage"))
    assert not candidates and session.result.status == "NoMatchingCandidates"


def test_fail_overrides_unknown_and_unknown_never_matches():
    rows = [dressed("d","vest_dress",None,None)]
    candidates,session = run(rows,StructuredOutfitRequest(colours=("blue",),style="vintage"))
    assert not candidates and session.result.unknown == 1
    request = StructuredOutfitRequest(colours=("blue",),garment_categories=(GarmentCategoryConstraint("category","trousers"),))
    candidates,session = run(rows,request,optimized=False)
    assert not candidates and session.result.failed == 1 and session.result.unknown == 0


@pytest.mark.parametrize("fields", [{"occasion":"campus"},{"formality":"formal"},{"colours":("unsupported",)},{"style":"unknown"}])
def test_unavailable_policies_stop_before_retrieval(fields):
    query = Query(())
    session = RequestCandidateEngine(query).generate_candidates("owner",StructuredOutfitRequest(**fields))
    assert list(session) == [] and session.result.status == "PolicyUnavailable" and query.calls == 0


@pytest.mark.parametrize("rows,status", [([],"NoEligibleGarments"),([garment("t","vest")],"InsufficientStructure")])
def test_structural_empty_outcomes_preserved(rows,status):
    candidates,session = run(rows,StructuredOutfitRequest())
    assert not candidates and session.result.status == status and session.result.complete


def test_cache_is_per_session_and_classifies_each_garment_once():
    classifier = Mock(wraps=ColourClassifier())
    mapper = GarmentEvidenceMapper(classifier=classifier)
    evaluator = RequestConstraintEvaluator(mapper=mapper)
    rows = [dressed("t","vest","blue"),dressed("b","trousers","black"),dressed("o","long_sleeve_outwear","white")]
    engine = RequestCandidateEngine(Query(rows),evaluator_factory=lambda:evaluator)
    session = engine.generate_candidates("owner",StructuredOutfitRequest(colours=("blue",)))
    assert len(list(session)) == 2 and classifier.classify.call_count == 3
    assert session.evidence_cache_size == 3
    other = RequestCandidateEngine(Query(rows)).generate_candidates("owner",StructuredOutfitRequest(colours=("blue",)))
    assert other.evidence_cache_size == 0


def test_optimized_exhaustive_and_order_equivalence():
    rows = [dressed("t","vest","blue",("vintage",)),dressed("t2","sling",None,None),dressed("b","trousers","black",("classic",)),dressed("b2","skirt","red",()),dressed("d","vest_dress",None,None),dressed("o","long_sleeve_outwear","#ffffff",None)]
    requests = [StructuredOutfitRequest(),StructuredOutfitRequest(colours=("blue",)),StructuredOutfitRequest(style="vintage"),StructuredOutfitRequest(colours=("blue",),style="vintage",garment_categories=(GarmentCategoryConstraint("category","trousers"),))]
    for request in requests:
        fast,fast_session = run(rows,request)
        slow,slow_session = run(list(reversed(rows)),request,optimized=False)
        assert [item.candidate.key for item in fast] == [item.candidate.key for item in slow]
        assert fast_session.result == slow_session.result


def test_stream_interruption_and_processing_failure():
    rows = [dressed("t","vest","blue"),dressed("b","trousers","black"),dressed("d","vest_dress","blue")]
    with RequestCandidateEngine(Query(rows)).generate_candidates("owner",StructuredOutfitRequest(colours=("blue",))) as session:
        next(session)
        assert not session.result.complete
    assert session.result.status == "Interrupted"
    evaluator = Mock()
    evaluator.supports.return_value = True
    evaluator.evaluate.side_effect = RuntimeError("private details")
    session = RequestCandidateEngine(Query(rows),evaluator_factory=lambda:evaluator).generate_candidates("owner",StructuredOutfitRequest())
    with pytest.raises(RequestProcessingError,match="discard"):
        list(session)
    assert session.result.status == "ProcessingFailure" and not session.result.complete


def test_value_objects_are_immutable():
    ids = ["g"]
    condition = MandatoryCondition("colours","blue","Pass",ids)
    ids.clear()
    assert condition.evidence_ids == ("g",)
    with pytest.raises(FrozenInstanceError):
        condition.state = "Fail"
    with pytest.raises(ValueError):
        AttributeEvidence([["blue"]],"Known","test")
    assert RequestEvaluation([condition,MandatoryCondition("style","vintage","Unknown")]).state == "Unknown"


def test_real_phase1_and_phase2_integration():
    owner = str(uuid.uuid4())
    with TestClient(app,headers={"X-User-Id":owner}) as client:
        top = confirmed_garment(client,"Top","blue")
        bottom = confirmed_garment(client,"Bottom","black")
        request = NLPInterpreter().interpret("Suggest an outfit using blue and black colours with a top and trousers.").structured_request
        assert client.patch(f"/api/v1/wardrobe/garments/{top}",json={"category":"vest","primary_colour":"blue"}).status_code == 200
        assert client.patch(f"/api/v1/wardrobe/garments/{bottom}",json={"category":"trousers","primary_colour":"black"}).status_code == 200
        session = RequestCandidateEngine(SqliteConfirmedGarmentQuery()).generate_candidates(owner,request)
        assert len(list(session)) == 1 and session.result.complete
        with connection() as conn:
            conn.execute("UPDATE garments SET processing_item_id=NULL WHERE id=?",(bottom,))
        session = RequestCandidateEngine(SqliteConfirmedGarmentQuery()).generate_candidates(owner,request)
        assert list(session) == [] and session.result.status == "InsufficientStructure"


def test_structural_failure_and_keyboard_interrupt_propagate():
    query = Mock()
    query.get_confirmed_available_garments.side_effect = RuntimeError("private")
    session = RequestCandidateEngine(query).generate_candidates("owner",StructuredOutfitRequest())
    assert list(session) == [] and session.result.status == "ProcessingFailure" and not session.result.complete
    evaluator = Mock()
    evaluator.supports.return_value = True
    evaluator.evaluate.side_effect = KeyboardInterrupt
    session = RequestCandidateEngine(Query([garment("d","vest_dress")]),evaluator_factory=lambda:evaluator).generate_candidates("owner",StructuredOutfitRequest())
    with pytest.raises(KeyboardInterrupt):
        next(session)
    assert session.result.status == "Interrupted" and not session.result.complete


def test_no_match_unknown_and_failure_aggregation():
    from app.domain.value_objects.request_candidate_evaluation import GarmentRequestEvidence
    with pytest.raises(ValueError):
        AttributeEvidence(("blue",),"Missing","test")
    rows = [dressed("d1","vest_dress",None),dressed("d2","vest_dress","red")]
    candidates,session = run(rows,StructuredOutfitRequest(colours=("blue",)))
    assert not candidates and session.result.status == "InsufficientEvidence" and session.result.unknown == 1 and session.result.failed == 1


def test_exact_anchor_configuration_independently_matches_standard_values():
    expected = {"#000000":"black","#ffffff":"white","#808080":"grey","#000080":"navy","#0000ff":"blue","#ff0000":"red","#008000":"green","#ffff00":"yellow","#ffa500":"orange","#ffc0cb":"pink","#800080":"purple","#a52a2a":"brown","#f5f5dc":"beige"}
    classifier = ColourClassifier()
    assert dict(classifier.anchors) == expected
    for hex_value,name in expected.items():
        assert classifier.classify(hex_value).values == (name,)
    assert classifier.classify("#fffdd0").state == "Unrecognized"  # No invented cream anchor.
