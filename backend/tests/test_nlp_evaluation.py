"""Metric/integrity verification; evaluation examples are not used to tune rules."""
import pytest
from scripts import evaluate_nlp
from app.domain.value_objects.nlp_result import NLPOutcome
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest


def test_fixed_dataset_distribution_and_denominators():
    result = evaluate_nlp.evaluate()
    assert result["case_count"] == 120 and result["supported_case_count"] == 90
    assert result["field_denominator"] == 450 and result["explicit_field_denominator"] == 130
    assert len({item["id"] for item in result["cases"]}) == 120
    assert result["dataset_sha256"] == evaluate_nlp.EXPECTED_HASH
    assert all(item["recommendation_result"] == "NotEvaluated" for item in result["cases"])


def test_bad_interpreter_cannot_pass_on_absent_fields(monkeypatch):
    class EmptyInterpreter:
        from app.application.nlp.vocabulary import Vocabulary
        vocabulary = Vocabulary.load()
        def interpret(self, text):
            return NLPOutcome("Supported", "test", "test", text, StructuredOutfitRequest())
    monkeypatch.setattr(evaluate_nlp, "NLPInterpreter", EmptyInterpreter)
    result = evaluate_nlp.evaluate()
    assert result["intent_accuracy"] == 0.75
    assert result["explicitly_supplied_field_accuracy"] == 0
    assert not result["rn27_passed"]
    assert result["combined_exact_match_accuracy"] < result["field_extraction_accuracy"]


def test_changed_evaluation_labels_are_rejected(tmp_path):
    changed = tmp_path / "changed.json"
    changed.write_bytes(evaluate_nlp.DATASET.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash changed"):
        evaluate_nlp.evaluate(changed)
