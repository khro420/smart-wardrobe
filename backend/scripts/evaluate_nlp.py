"""Fixed-label interpreter evaluation; never generates labels from predictions."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from app.application.nlp.nlp_interpreter import NLPInterpreter

DATASET = BACKEND / "tests/fixtures/nlp_evaluation.v1.json"
FIELDS = ("occasion", "style", "colours", "garment_categories", "formality")
EXPECTED_HASH = "ced6418193e866649b635c6671ff2a1387becbd0435eb9eb0dc3a04a439760ba"


def normalized_fields(fields):
    result = {field: fields.get(field) for field in FIELDS}
    if result["colours"] is not None:
        result["colours"] = sorted(set(result["colours"]))
    if result["garment_categories"] is not None:
        constraints = []
        for item in result["garment_categories"]:
            kind, value = item.split(":", 1) if isinstance(item, str) else (item["kind"], item["value"])
            constraints.append((kind, value))
        result["garment_categories"] = sorted(set(constraints))
    return result


def field_tokens(value):
    if value is None:
        return set()
    return set(value) if isinstance(value, list) else {value}


def evaluate(dataset=DATASET):
    payload = Path(dataset).read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_HASH:
        raise ValueError("Fixed evaluation dataset hash changed; review/version labels before evaluation.")
    raw = json.loads(payload)
    if {key: len(value) for key, value in raw["groups"].items()} != {"detailed": 40, "partial": 30, "unsupported": 30, "no_feasible_outfit": 20}:
        raise ValueError("Evaluation requires the approved 120-case group distribution.")
    interpreter = NLPInterpreter()
    cases, confusion, per_field = [], Counter(), {field: Counter() for field in FIELDS}
    intent_correct = combined_correct = field_correct = supplied_correct = supplied_total = supported_count = 0
    for group, examples in raw["groups"].items():
        for case_id, text, fields in examples:
            expected_status = "UnsupportedRequest" if group == "unsupported" else "Supported"
            expected = normalized_fields(fields)
            actual = interpreter.interpret(text)
            actual_fields = normalized_fields(actual.structured_request.to_dict()) if actual.structured_request else normalized_fields({})
            intent_ok = actual.status == expected_status
            intent_correct += intent_ok
            confusion[(expected_status, actual.status)] += 1
            checks = {}
            if expected_status == "Supported":
                supported_count += 1
                for field in FIELDS:
                    checks[field] = actual.status == "Supported" and actual_fields[field] == expected[field]
                    field_correct += checks[field]
                    if expected[field] is not None:
                        supplied_total += 1
                        supplied_correct += checks[field]
                    expected_tokens = field_tokens(expected[field])
                    actual_tokens = field_tokens(actual_fields[field])
                    per_field[field]["tp"] += len(expected_tokens & actual_tokens)
                    per_field[field]["fp"] += len(actual_tokens - expected_tokens)
                    per_field[field]["fn"] += len(expected_tokens - actual_tokens)
            combined_ok = intent_ok and (all(checks.values()) if checks else True)
            combined_correct += combined_ok
            cases.append({"id": case_id, "group": group, "original_request": text, "expected_status": expected_status,
                          "expected_fields": expected, "actual_status": actual.status, "reason": actual.reason,
                          "actual_fields": actual_fields if actual.structured_request else None, "field_correct": checks,
                          "intent_correct": intent_ok, "combined_exact_match": combined_ok,
                          "recommendation_result": "NotEvaluated",
                          "wardrobe_scenario": raw["no_feasible_scenario"] if group == "no_feasible_outfit" else None})
    metrics = {}
    for field, counts in per_field.items():
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        precision = tp / (tp+fp) if tp+fp else 0.0
        recall = tp / (tp+fn) if tp+fn else 0.0
        metrics[field] = {**dict(counts), "precision": precision, "recall": recall, "f1": 2*precision*recall/(precision+recall) if precision+recall else 0.0}
    intent_accuracy = intent_correct / len(cases)
    extraction_accuracy = field_correct / (supported_count * len(FIELDS))
    source_paths = sorted((BACKEND / "app/application/nlp").rglob("*.py")) + sorted((BACKEND / "app/application/nlp/config").glob("*.json")) + [BACKEND / "app/domain/value_objects/structured_outfit_request.py", BACKEND / "app/domain/value_objects/nlp_result.py", Path(__file__)]
    return {"evaluated_at": datetime.now(timezone.utc).isoformat(), "dataset_sha256": digest,
            "vocabulary_version": interpreter.vocabulary.version, "methodology": raw["methodology"],
            "python": platform.python_version(), "source_sha256": {str(path.relative_to(BACKEND)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths},
            "case_count": len(cases), "supported_case_count": supported_count,
            "intent_accuracy": intent_accuracy, "field_extraction_accuracy": extraction_accuracy,
            "explicitly_supplied_field_accuracy": supplied_correct / supplied_total,
            "field_denominator": supported_count * len(FIELDS), "explicit_field_denominator": supplied_total,
            "combined_exact_match_accuracy": combined_correct / len(cases), "per_field": metrics,
            "intent_confusion_matrix": [{"expected": expected, "actual": actual, "count": count} for (expected, actual), count in confusion.items()],
            "rn27_passed": intent_accuracy >= 0.8 and extraction_accuracy >= 0.8,
            "rn27_operationalization": "At least 80% intent accuracy and 80% five-field accuracy on labelled supported requests; combined exact match has no extra threshold.",
            "cases": cases}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate()
    encoded = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key not in ("cases", "source_sha256")}, indent=2))
