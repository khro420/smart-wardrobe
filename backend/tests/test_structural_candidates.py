"""Phase 3A expected combinations and streaming/contract regressions."""
import ast
from dataclasses import FrozenInstanceError, replace
from itertools import combinations
from pathlib import Path
import uuid
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient

from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest, GarmentCategoryConstraint
from app.domain.value_objects.outfit_candidate import OutfitCandidate, CandidateMember
from app.application.recommendation.recommendation_engine import RecommendationEngine, CandidateProcessingError
from app.application.recommendation.mandatory_rule_evaluator import MandatoryRuleEvaluator
from app.main import app
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.persistence.postgresql_repository import connection
from tests.test_o2_recommendation_boundary import confirmed_garment


def garment(identifier, category, owner="owner"):
    role, layer = GARMENT_STRUCTURE.get(category, (None, None))
    return ConfirmedGarmentSnapshot(identifier, owner, "available", category, identifier, "media", False, "time", structural_role=role, layering_index=layer)


class Query:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0
    def get_confirmed_available_garments(self, user_id):
        self.calls += 1
        return self.rows
    def list_available_garment_ids(self, user_id):
        raise AssertionError("Legacy query must not be used.")


def exhaust(rows):
    session = RecommendationEngine(Query(rows)).generate_homepage_candidates("owner")
    return list(session), session.result


@pytest.mark.parametrize("categories,count,status", [
    ([],0,"NoEligibleGarments"), (["vest"],0,"InsufficientStructure"),
    (["trousers"],0,"InsufficientStructure"), (["long_sleeve_outwear"],0,"InsufficientStructure"),
    (["vest","trousers"],1,"StructuralCandidates"), (["sling_dress"],1,"StructuralCandidates"),
    (["vest","trousers","long_sleeve_outwear"],2,"StructuralCandidates"),
    (["sling_dress","short_sleeve_outwear"],2,"StructuralCandidates")])
def test_compositions_and_controlled_outcomes(categories,count,status):
    candidates, result = exhaust(tuple(garment(str(i), category) for i,category in enumerate(categories)))
    assert len(candidates) == count and result.status == status and result.complete
    assert all(item.validity == "STRUCTURALLY_VALID" for item in candidates)


@pytest.mark.parametrize("category,expected", GARMENT_STRUCTURE.items())
def test_all_categories_have_exact_slots(category, expected):
    row = garment("target", category)
    partners = [garment("bottom","trousers")] if expected[0] == "top" else [garment("top","vest")] if expected[0] == "bottom" else [garment("dress","sling_dress")] if expected[0] == "outerwear" else []
    candidates, _ = exhaust([row, *partners])
    appearances = [member for candidate in candidates for member in candidate.members if member.garment.garment_id == "target"]
    assert appearances
    assert all(item.role == {"top":"upper","bottom":"lower","dress":"one_piece","outerwear":"outerwear"}[expected[0]] for item in appearances)


def test_candidate_sets_against_independent_subset_oracle():
    rows = [garment("t1","vest"),garment("t2","sling"),garment("b1","trousers"),garment("b2","skirt"),garment("d1","vest_dress"),garment("o1","long_sleeve_outwear"),garment("o2","short_sleeve_outwear")]
    expected = set()
    allowed = [{"top":1,"bottom":1}, {"top":1,"bottom":1,"outerwear":1}, {"dress":1}, {"dress":1,"outerwear":1}]
    for length in range(1,4):
        for subset in combinations(rows,length):
            counts = {role:sum(item.structural_role == role for item in subset) for role in {item.structural_role for item in subset}}
            if counts in allowed:
                expected.add(frozenset(item.garment_id for item in subset))
    candidates, result = exhaust(rows)
    assert {frozenset(item.garment.garment_id for item in candidate.members) for candidate in candidates} == expected
    assert result.candidate_count == (2*2+1)*(1+2) == 15
    assert len({item.candidate_id for item in candidates}) == 15


def test_determinism_duplicates_and_input_order():
    rows = [garment("t","vest"),garment("b","trousers"),garment("d","vest_dress"),garment("o","long_sleeve_outwear")]
    first, _ = exhaust(rows)
    second, _ = exhaust(list(reversed(rows))+[rows[0]])
    assert [item.key for item in first] == [item.key for item in second]
    assert [item.candidate_id for item in first] == [item.candidate_id for item in second]
    assert all(tuple(member.item_order for member in item.members) == tuple(range(1,len(item.members)+1)) for item in first)


@pytest.mark.parametrize("bad", [garment("x","unknown"),replace(garment("x","vest"),structural_role="bottom"),replace(garment("x","vest"),user_id="foreign"),replace(garment("x","vest"),status="archived"),replace(garment("x","vest"),garment_id=""),{"id":"x"}])
def test_invalid_garments_excluded(bad):
    candidates,result = exhaust([bad])
    assert not candidates and result.status == "NoEligibleGarments" and result.exclusions


def test_conflicting_duplicate_is_processing_failure():
    row = garment("t","vest")
    candidates,result = exhaust([row,replace(row,name="different")])
    assert not candidates and result.status == "ProcessingFailure" and not result.complete


def test_missing_optional_attributes_do_not_gate_structure():
    candidates,result = exhaust([garment("t","vest"),garment("b","trousers")])
    assert result.complete and candidates[0].members[0].garment.style_tags is None


def test_immutable_candidates_and_invalid_combinations():
    top,bottom = garment("t","vest"),garment("b","trousers")
    members = [CandidateMember(top,"upper",1),CandidateMember(bottom,"lower",2)]
    candidate = OutfitCandidate(members)
    members.clear()
    assert len(candidate.members) == 2
    with pytest.raises(FrozenInstanceError):
        candidate.members[0].role = "outerwear"
    with pytest.raises(ValueError):
        OutfitCandidate([CandidateMember(top,"upper",1)])
    with pytest.raises(ValueError):
        OutfitCandidate([CandidateMember(top,"upper",1),CandidateMember(top,"lower",2)])


def test_evaluator_rejects_dress_plus_top_and_multiple_slots():
    evaluator = MandatoryRuleEvaluator()
    assert not evaluator.is_structurally_valid([garment("d","vest_dress"),garment("t","vest")])
    assert not evaluator.is_structurally_valid([garment("t","vest"),garment("t2","sling"),garment("b","trousers")])
    assert not evaluator.is_structurally_valid([garment("u","unknown")])


@pytest.mark.parametrize("fields", [{"occasion":"campus"},{"style":"vintage"},{"colours":("blue",)},{"formality":"casual"},{"garment_categories":(GarmentCategoryConstraint("group","top"),)}])
def test_phase_3b_conditions_return_capability_without_retrieval(fields):
    query = Query(())
    session = RecommendationEngine(query).generate_nlp_candidates("owner",StructuredOutfitRequest(**fields))
    assert list(session) == [] and session.result.status == "PolicyUnavailable" and not session.result.complete
    assert query.calls == 0


def test_generic_nlp_and_homepage_share_structural_results():
    engine = RecommendationEngine(Query([garment("t","vest"),garment("b","trousers")]))
    assert [item.key for item in engine.generate_nlp_candidates("owner",StructuredOutfitRequest())] == [item.key for item in engine.generate_homepage_candidates("owner")]


def test_no_structural_candidates_is_distinct():
    evaluator = Mock()
    evaluator.is_structurally_valid.return_value = False
    session = RecommendationEngine(Query([garment("d","vest_dress")]),evaluator=evaluator).generate_homepage_candidates("owner")
    assert list(session) == [] and session.result.status == "NoStructuralCandidates" and session.result.complete


def test_lazy_partial_stream_cannot_claim_completion():
    query = Query([garment("t","vest"),garment("b","trousers"),garment("d","vest_dress")])
    with RecommendationEngine(query).generate_homepage_candidates("owner") as session:
        assert session.result.status == "Pending" and session.result.candidate_count == 0
        next(session)
        assert session.result.status == "Running" and not session.result.complete
    assert session.result.status == "Interrupted" and not session.result.complete
    assert query.calls == 1 and list(session) == []


def test_stream_failure_never_becomes_success():
    from app.application.recommendation.candidate_generator import CandidateGenerator
    class BrokenGenerator(CandidateGenerator):
        def enumerate(self, garments, evaluator):
            yield from super().enumerate(garments,evaluator)
            raise RuntimeError("private failure")
    session = RecommendationEngine(Query([garment("d","vest_dress")]),generator=BrokenGenerator()).generate_homepage_candidates("owner")
    next(session)
    with pytest.raises(CandidateProcessingError,match="discard"):
        next(session)
    assert session.result.status == "ProcessingFailure" and not session.result.complete and session.result.candidate_count == 1


def test_acquisition_failure_is_controlled():
    query = Mock()
    query.get_confirmed_available_garments.side_effect = RuntimeError("database unavailable")
    session = RecommendationEngine(query).generate_homepage_candidates("owner")
    assert list(session) == [] and session.result.status == "ProcessingFailure" and not session.result.complete


def test_real_phase1_query_without_saved_outfits():
    owner = str(uuid.uuid4())
    with TestClient(app,headers={"X-User-Id":owner}) as client:
        top = confirmed_garment(client,"top","navy")
        bottom = confirmed_garment(client,"bottom","black")
        excluded = confirmed_garment(client,"excluded","red")
        with connection() as conn:
            conn.execute("UPDATE garments SET category='vest' WHERE id=?",(top,))
            conn.execute("UPDATE garments SET category='trousers' WHERE id=?",(bottom,))
            conn.execute("UPDATE garments SET processing_item_id=NULL WHERE id=?",(excluded,))
            assert conn.execute("SELECT COUNT(*) FROM outfits WHERE user_id=?",(owner,)).fetchone()[0] == 0
        session = RecommendationEngine(SqliteConfirmedGarmentQuery()).generate_homepage_candidates(owner)
        candidates = list(session)
        assert session.result.complete and len(candidates) == 1
        assert {item.garment.garment_id for item in candidates[0].members} == {top,bottom}


def test_new_components_have_no_persistence_or_live_service_dependency():
    folder = Path(__file__).resolve().parents[1] / "app/application/recommendation"
    for name in ("garment_retrieval_service.py","candidate_generator.py","mandatory_rule_evaluator.py","recommendation_engine.py","structural_policy.py"):
        for node in ast.walk(ast.parse((folder/name).read_text(encoding="utf-8"))):
            if isinstance(node,ast.ImportFrom):
                assert not (node.module or "").startswith(("app.infrastructure","fastapi","app.application.recommendation.recommendation_service"))


def test_keyboard_interruption_is_incomplete():
    from app.application.recommendation.candidate_generator import CandidateGenerator
    class InterruptedGenerator(CandidateGenerator):
        def enumerate(self, garments, evaluator):
            yield from super().enumerate(garments,evaluator)
            raise KeyboardInterrupt
    session = RecommendationEngine(Query([garment("d","vest_dress")]),generator=InterruptedGenerator()).generate_homepage_candidates("owner")
    next(session)
    with pytest.raises(KeyboardInterrupt):
        next(session)
    assert session.result.status == "Interrupted" and not session.result.complete


def test_multiple_outerwear_rejected_and_each_single_layer_generated():
    rows = [garment("d","vest_dress"),garment("o1","long_sleeve_outwear"),garment("o2","short_sleeve_outwear")]
    assert not MandatoryRuleEvaluator().is_structurally_valid(rows)
    candidates,result = exhaust(rows)
    assert result.candidate_count == 3 and all(len(candidate.members) <= 2 for candidate in candidates)


def test_result_metadata_is_immutable_and_cannot_claim_incomplete_success():
    from app.domain.value_objects.candidate_generation_result import CandidateGenerationResult
    with pytest.raises(ValueError):
        CandidateGenerationResult("Running",True)
    with pytest.raises(ValueError):
        CandidateGenerationResult("StructuralCandidates",False)
    _,result = exhaust([])
    with pytest.raises(FrozenInstanceError):
        result.complete = False
