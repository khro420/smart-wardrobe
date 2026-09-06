"""Audit and evaluate the existing DeepFashion2 YOLO-seg model without retraining.

The conversion audit checks every held-out source annotation against its emitted
YOLO label.  Only after that audit passes does Ultralytics calculate held-out
box/mask metrics.  A deterministic sample is then used to create labelled
false-positive/false-negative evidence images for qualitative analysis.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import sys
import time

import cv2
import numpy as np
from ultralytics import YOLO


BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

DATASET = BACKEND / "datasets" / "deepfashion2_yolo_seg"
SOURCE = BACKEND / "datasets" / "deepfashion2" / "validation"
DATA_YAML = DATASET / "data.yaml"
WEIGHTS = BACKEND / "models" / "cv" / "best.pt"
RUNS = BACKEND / "runs" / "held_out_segmentation"
VERIFICATION = BACKEND.parent / "storage" / "verification" / "segmentation" / "held_out_evaluation"

CLASS_NAMES = [
    "short_sleeve_top", "long_sleeve_top", "short_sleeve_outwear",
    "long_sleeve_outwear", "vest", "sling", "shorts", "trousers",
    "skirt", "short_sleeve_dress", "long_sleeve_dress", "vest_dress",
    "sling_dress",
]
CATEGORY_MAP = {number: number - 1 for number in range(1, 14)}


def polygon_area(points: list[float]) -> float:
    contour = np.asarray(points, dtype=np.float32).reshape(-1, 2)
    return abs(float(cv2.contourArea(contour))) if len(contour) >= 3 else 0.0


def expected_labels(annotation: dict, width: int, height: int) -> list[list[float]]:
    """Replicate the committed conversion policy for a source annotation."""
    expected: list[list[float]] = []
    image_area = width * height
    for key, item in annotation.items():
        if not key.startswith("item") or item.get("category_id") not in CATEGORY_MAP:
            continue
        segments = item.get("segmentation") or []
        if not segments:
            continue
        polygon = max(segments, key=len)
        if len(polygon) < 6 or len(polygon) > 400 or polygon_area(polygon) > 0.75 * image_area:
            continue
        normalised = []
        valid = True
        for index in range(0, len(polygon), 2):
            x, y = polygon[index] / width, polygon[index + 1] / height
            if not 0 <= x <= 1 or not 0 <= y <= 1:
                valid = False
                break
            normalised.extend([x, y])
        if valid:
            expected.append([float(CATEGORY_MAP[item["category_id"]]), *normalised])
    return expected


def parse_label(path: Path) -> tuple[list[list[float]], list[str]]:
    labels, errors = [], []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            values = [float(value) for value in line.split()]
        except ValueError:
            errors.append(f"line {line_number}: non-numeric value")
            continue
        if len(values) < 7 or (len(values) - 1) % 2 or int(values[0]) != values[0] or not 0 <= values[0] < len(CLASS_NAMES):
            errors.append(f"line {line_number}: invalid YOLO-seg shape/class")
        elif any(not 0 <= coordinate <= 1 for coordinate in values[1:]):
            errors.append(f"line {line_number}: coordinate outside [0,1]")
        else:
            labels.append(values)
    return labels, errors


def audit_conversion() -> dict:
    image_dir, label_dir, annotation_dir = DATASET / "images" / "validation", DATASET / "labels" / "validation", SOURCE / "annos"
    image_paths = sorted(image_dir.glob("*.jpg"))
    issues: list[dict] = []
    class_counts = Counter()
    expected_instances = emitted_instances = empty_labels = 0
    started = time.perf_counter()
    for image_path in image_paths:
        label_path, annotation_path = label_dir / f"{image_path.stem}.txt", annotation_dir / f"{image_path.stem}.json"
        if not label_path.exists() or not annotation_path.exists():
            issues.append({"image": image_path.name, "issue": "missing label or source annotation"})
            continue
        image = cv2.imread(str(image_path))
        if image is None:
            issues.append({"image": image_path.name, "issue": "unreadable converted image"})
            continue
        expected = expected_labels(json.loads(annotation_path.read_text(encoding="utf-8")), image.shape[1], image.shape[0])
        actual, parse_errors = parse_label(label_path)
        expected_instances += len(expected)
        emitted_instances += len(actual)
        if not actual:
            empty_labels += 1
        for label in actual:
            class_counts[CLASS_NAMES[int(label[0])]] += 1
        if parse_errors or len(actual) != len(expected):
            issues.append({"image": image_path.name, "issue": "; ".join(parse_errors) or "emitted label count differs from conversion policy", "expected_instances": len(expected), "actual_instances": len(actual)})
    return {
        "split": "validation", "images": len(image_paths), "label_files": len(list(label_dir.glob("*.txt"))),
        "source_annotations": len(list(annotation_dir.glob("*.json"))), "expected_instances": expected_instances,
        "emitted_instances": emitted_instances, "empty_label_files": empty_labels,
        "class_instance_counts": dict(sorted(class_counts.items())), "issues": issues[:100],
        "issue_count": len(issues), "seconds": round(time.perf_counter() - started, 2),
    }


def box_from_polygon(label: list[float], width: int, height: int) -> tuple[int, tuple[float, float, float, float]]:
    points = np.asarray(label[1:], dtype=np.float32).reshape(-1, 2)
    points[:, 0] *= width
    points[:, 1] *= height
    return int(label[0]), (float(points[:, 0].min()), float(points[:, 1].min()), float(points[:, 0].max()), float(points[:, 1].max()))


def iou(left: tuple[float, float, float, float], right: tuple[float, float, float, float]) -> float:
    x1, y1 = max(left[0], right[0]), max(left[1], right[1])
    x2, y2 = min(left[2], right[2]), min(left[3], right[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = (left[2] - left[0]) * (left[3] - left[1]) + (right[2] - right[0]) * (right[3] - right[1]) - intersection
    return intersection / union if union else 0.0


def failure_evidence(model: YOLO, sample_size: int, failure_limit: int, imgsz: int, device: str | None) -> list[dict]:
    image_paths = sorted((DATASET / "images" / "validation").glob("*.jpg"))
    rng = random.Random(20260905)
    sample = image_paths if sample_size >= len(image_paths) else sorted(rng.sample(image_paths, sample_size))
    candidates = []
    for image_path in sample:
        image = cv2.imread(str(image_path))
        labels, errors = parse_label(DATASET / "labels" / "validation" / f"{image_path.stem}.txt")
        if image is None or errors:
            continue
        ground_truth = [box_from_polygon(label, image.shape[1], image.shape[0]) for label in labels]
        result = model.predict(str(image_path), imgsz=imgsz, device=device, conf=0.25, verbose=False)[0]
        predictions = []
        if result.boxes is not None:
            for box, category, confidence in zip(result.boxes.xyxy.cpu().numpy(), result.boxes.cls.cpu().numpy(), result.boxes.conf.cpu().numpy()):
                predictions.append((int(category), tuple(float(value) for value in box), float(confidence)))
        matched_gt, matched_predictions = set(), set()
        for prediction_index, (category, box, _) in enumerate(predictions):
            choices = [(iou(box, ground_box), ground_index) for ground_index, (ground_category, ground_box) in enumerate(ground_truth) if ground_category == category and ground_index not in matched_gt]
            if choices:
                overlap, ground_index = max(choices)
                if overlap >= 0.5:
                    matched_gt.add(ground_index)
                    matched_predictions.add(prediction_index)
        missed = [ground_truth[index] for index in range(len(ground_truth)) if index not in matched_gt]
        extra = [predictions[index] for index in range(len(predictions)) if index not in matched_predictions]
        score = len(missed) + len(extra)
        if score:
            candidates.append({"path": image_path, "image": image, "missed": missed, "extra": extra, "score": score})
    candidates.sort(key=lambda candidate: (-candidate["score"], candidate["path"].name))
    output = VERIFICATION / "failure_examples"
    output.mkdir(parents=True, exist_ok=True)
    evidence = []
    for rank, candidate in enumerate(candidates[:failure_limit], 1):
        image = candidate["image"].copy()
        for category, box in candidate["missed"]:
            x1, y1, x2, y2 = (int(value) for value in box)
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 180, 0), 2)
            cv2.putText(image, f"FN {CLASS_NAMES[category]}", (x1, max(18, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 180, 0), 2)
        for category, box, confidence in candidate["extra"]:
            x1, y1, x2, y2 = (int(value) for value in box)
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 220), 2)
            cv2.putText(image, f"FP {CLASS_NAMES[category]} {confidence:.2f}", (x1, min(image.shape[0] - 6, y2 + 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 220), 2)
        filename = f"{rank:02d}-{candidate['path'].stem}-fn{len(candidate['missed'])}-fp{len(candidate['extra'])}.jpg"
        cv2.imwrite(str(output / filename), image)
        evidence.append({"rank": rank, "image": candidate["path"].name, "file": str((output / filename).relative_to(BACKEND.parent)), "false_negatives": [CLASS_NAMES[item[0]] for item in candidate["missed"]], "false_positives": [CLASS_NAMES[item[0]] for item in candidate["extra"]], "score": candidate["score"]})
    return evidence


def metric_value(values, index: int) -> float | None:
    if values is None or index >= len(values):
        return None
    value = float(values[index])
    return round(value, 5) if np.isfinite(value) else None


def metrics_report(metrics) -> dict:
    indices = list(getattr(metrics.box, "ap_class_index", []))
    box_precision, box_recall = getattr(metrics.box, "p", []), getattr(metrics.box, "r", [])
    seg_precision, seg_recall = getattr(metrics.seg, "p", []), getattr(metrics.seg, "r", [])
    box_ap = getattr(metrics.box, "all_ap", np.empty((0, 10)))
    seg_ap = getattr(metrics.seg, "all_ap", np.empty((0, 10)))
    per_category = {}
    for class_id, name in enumerate(CLASS_NAMES):
        position = indices.index(class_id) if class_id in indices else None
        per_category[name] = {
            "box_precision": metric_value(box_precision, position) if position is not None else None,
            "box_recall": metric_value(box_recall, position) if position is not None else None,
            "box_map50": metric_value(box_ap[:, 0], position) if position is not None and len(box_ap) else None,
            "box_map50_95": metric_value(getattr(metrics.box, "maps", []), class_id),
            "mask_precision": metric_value(seg_precision, position) if position is not None else None,
            "mask_recall": metric_value(seg_recall, position) if position is not None else None,
            "mask_map50": metric_value(seg_ap[:, 0], position) if position is not None and len(seg_ap) else None,
            "mask_map50_95": metric_value(getattr(metrics.seg, "maps", []), class_id),
        }
    return {
        "box": {"precision": round(float(metrics.box.mp), 5), "recall": round(float(metrics.box.mr), 5), "map50": round(float(metrics.box.map50), 5), "map50_95": round(float(metrics.box.map), 5)},
        "mask": {"precision": round(float(metrics.seg.mp), 5), "recall": round(float(metrics.seg.mr), 5), "map50": round(float(metrics.seg.map50), 5), "map50_95": round(float(metrics.seg.map), 5)},
        "per_category": per_category,
        "speed_ms": {key: round(float(value), 3) for key, value in metrics.speed.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit and evaluate existing held-out DeepFashion2 YOLO segmentation weights.")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default=None, help="Ultralytics device selector; default selects automatically.")
    parser.add_argument("--failure-sample", type=int, default=1000, help="Deterministic held-out images examined for qualitative failure evidence.")
    parser.add_argument("--failure-limit", type=int, default=20, help="Number of labelled failure images to save.")
    parser.add_argument("--audit-only", action="store_true", help="Write and print the conversion audit without model evaluation.")
    args = parser.parse_args()
    if not WEIGHTS.exists():
        raise FileNotFoundError(f"Existing trained weights were not found: {WEIGHTS}")
    VERIFICATION.mkdir(parents=True, exist_ok=True)
    audit = audit_conversion()
    (VERIFICATION / "conversion-audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    if audit["issue_count"]:
        raise RuntimeError(f"Conversion audit found {audit['issue_count']} issue(s); inspect {VERIFICATION / 'conversion-audit.json'} before evaluating.")
    if args.audit_only:
        print(json.dumps(audit, indent=2))
        return
    started = time.perf_counter()
    model = YOLO(str(WEIGHTS))
    metrics = model.val(data=str(DATA_YAML), split="val", imgsz=args.imgsz, batch=args.batch, device=args.device, project=str(RUNS), name="metrics", exist_ok=True, plots=True, save_json=False, verbose=True)
    failures = failure_evidence(model, args.failure_sample, args.failure_limit, args.imgsz, args.device)
    report = {
        "kind": "held-out DeepFashion2 segmentation evaluation; existing weights only, no retraining",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "weights": {"path": str(WEIGHTS.relative_to(BACKEND)), "sha256": hashlib.sha256(WEIGHTS.read_bytes()).hexdigest()},
        "data_yaml": str(DATA_YAML.relative_to(BACKEND)), "conversion_audit": audit,
        "metrics": metrics_report(metrics), "failure_evidence": failures,
        "failure_evidence_sample_size": min(args.failure_sample, audit["images"]),
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "ultralytics_output": str(RUNS / "metrics"),
    }
    for destination in (VERIFICATION / "results.json", RUNS / "metrics" / "results.json"):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
