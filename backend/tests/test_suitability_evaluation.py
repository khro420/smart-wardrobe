"""Fixed scenario expectations test logic, not real-world appropriateness."""
import json
from pathlib import Path
import pytest
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from tests.test_suitability_policy import annotated,run

DATA = json.loads((Path(__file__).with_name("fixtures") / "suitability_evaluation.v1.json").read_text())


@pytest.mark.parametrize("case",DATA["cases"],ids=lambda case:case["id"])
def test_fixed_policy_scenarios(case):
    candidates,session = run([annotated("d","vest_dress",case["tags"])],StructuredOutfitRequest(**case["request"]))
    assert session.result.status == case["expected"]
    assert bool(candidates) == (case["expected"] == "MatchingCandidates")
