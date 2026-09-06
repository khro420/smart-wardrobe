"""Evaluate report-supported automatic garment attributes on blind labels.

This is an inference-only AIR-05 audit. It uses held-out DeepFashion2 ground-
truth polygon crops, a fixed coarse-colour conversion, and manually assigned
labels created without exposing model predictions. It does not train or tune.
"""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score


BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

COLOUR_ANCHORS_RGB = {
    "black": (18, 18, 18),
    "white": (242, 242, 242),
    "grey": (128, 128, 128),
    "red": (205, 38, 38),
    "orange": (232, 124, 24),
    "yellow": (225, 205, 40),
    "green": (54, 145, 69),
    "blue": (45, 105, 196),
    "purple": (120, 62, 151),
    "pink": (224, 104, 163),
    "brown": (120, 77, 43),
    "beige": (213, 188, 145),
}


def _font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _rgb_to_lab(rgb: tuple[int, int, int]) -> np.ndarray:
    pixel = np.asarray([[list(reversed(rgb))]], dtype=np.uint8)
    return cv2.cvtColor(pixel, cv2.COLOR_BGR2LAB)[0, 0].astype(np.float32)


COLOUR_ANCHORS_LAB = {name: _rgb_to_lab(rgb) for name, rgb in COLOUR_ANCHORS_RGB.items()}


def coarse_colour(hex_colour: str) -> str:
    """Map a model hex output to the fixed audit vocabulary in CIE Lab."""
    if not isinstance(hex_colour, str) or len(hex_colour) != 7 or not hex_colour.startswith("#"):
        raise ValueError(f"Invalid model colour: {hex_colour!r}")
    rgb = tuple(int(hex_colour[index:index + 2], 16) for index in (1, 3, 5))
    lab = _rgb_to_lab(rgb)
    return min(COLOUR_ANCHORS_LAB, key=lambda name: float(np.linalg.norm(lab - COLOUR_ANCHORS_LAB[name])))


def _score(actual: list, predicted: list, labels: list) -> dict:
    return {
        "accuracy": float(accuracy_score(actual, predicted)),
        "macro_precision": float(precision_score(actual, predicted, labels=labels, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(actual, predicted, labels=labels, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(actual, predicted, labels=labels, average="macro", zero_division=0)),
    }


def _failure_sheet(record: dict, destination: Path) -> None:
    canvas = Image.new("RGB", (900, 650), "white")
    draw = ImageDraw.Draw(canvas)
    with Image.open(record["crop"]) as source:
        image = ImageOps.contain(source.convert("RGBA"), (520, 520), Image.Resampling.LANCZOS)
    panel = Image.new("RGBA", (540, 540), (241, 245, 249, 255))
    panel.alpha_composite(image, ((540 - image.width) // 2, (540 - image.height) // 2))
    canvas.paste(panel.convert("RGB"), (12, 98))
    draw.text((16, 16), f"AIR-05 labelled failure: {record['id']}", fill="#7f1d1d", font=_font(21))
    draw.text((16, 52), record["category"], fill="#334155", font=_font(17))
    y = 120
    labels = (
        ("Primary colour", "coarse_primary_colour"),
        ("Temperature", "colour_temperature"),
        ("Dominant >60%", "single_colour_dominant"),
    )
    for title, key in labels:
        draw.text((575, y), title, fill="#111827", font=_font(17))
        draw.text((575, y + 29), f"GT: {record['ground_truth'][key]}", fill="#166534", font=_font(16))
        draw.text((575, y + 54), f"Pred: {record['prediction'][key]}", fill="#991b1b" if key in record["failed_fields"] else "#166534", font=_font(16))
        y += 125
    draw.text((575, y + 5), f"Model hex: {record['prediction']['primary_hex']}", fill="#475569", font=_font(15))
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, "PNG", optimize=True)


def main() -> None:
    parser = ArgumentParser(description="Evaluate supported automatic attributes against blind labels.")
    parser.add_argument("--failure-limit", type=int, default=12)
    args = parser.parse_args()
    if not 10 <= args.failure_limit <= 20:
        raise ValueError("Use 10-20 labelled failure examples for the report audit.")

    manifest_path = ROOT / "storage" / "verification" / "attributes" / "label-manifest.json"
    labels_path = BACKEND / "scripts" / "attribute_ground_truth.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    labelled = json.loads(labels_path.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in labelled["labels"]}
    manifest_ids = [item["id"] for item in manifest["records"]]
    if set(manifest_ids) != set(by_id) or len(manifest_ids) != len(by_id):
        raise RuntimeError("Blind labels must match the fixed manifest exactly once.")

    from app.infrastructure.ai.cv.extraction.attributes import AttributeExtractor

    extractor = AttributeExtractor()
    records = []
    latencies = []
    for source in manifest["records"]:
        with Image.open(source["crop"]) as image:
            rgba = np.asarray(image.convert("RGBA"))
        bgr = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2BGR)
        mask = rgba[:, :, 3]
        started = time.perf_counter()
        output = extractor.extract(bgr, mask, source["category"])
        latencies.append(time.perf_counter() - started)
        colour = output["color"]
        prediction = {
            "primary_hex": colour["primary_color"],
            "coarse_primary_colour": coarse_colour(colour["primary_color"]),
            "colour_temperature": colour["color_temperature"],
            "single_colour_dominant": colour["is_dominant"],
        }
        ground_truth = by_id[source["id"]]
        failed = [key for key in ("coarse_primary_colour", "colour_temperature", "single_colour_dominant") if prediction[key] != ground_truth[key]]
        palette = colour["color_palette"]
        if any(not item["hex"].startswith("#") or not 0.0 <= item["coverage"] <= 1.0 for item in palette):
            raise RuntimeError(f"Invalid palette for {source['id']}")
        if any(palette[index]["coverage"] < palette[index + 1]["coverage"] for index in range(len(palette) - 1)):
            raise RuntimeError(f"Unsorted palette for {source['id']}")
        records.append({
            **source,
            "ground_truth": {key: ground_truth[key] for key in ("coarse_primary_colour", "colour_temperature", "single_colour_dominant")},
            "prediction": prediction,
            "failed_fields": failed,
            "rule_attributes": output["attributes"],
            "manual_attributes": output["manual"],
            "palette": palette,
        })

    fields = {
        "coarse_primary_colour": list(COLOUR_ANCHORS_RGB),
        "colour_temperature": ["warm", "cool", "neutral"],
        "single_colour_dominant": [False, True],
    }
    metrics = {}
    for field, classes in fields.items():
        actual = [record["ground_truth"][field] for record in records]
        predicted = [record["prediction"][field] for record in records]
        metrics[field] = _score(actual, predicted, classes)

    expected_manual = {"fit": None, "style": None, "material": None}
    if any(record["manual_attributes"] != expected_manual for record in records):
        raise RuntimeError("Unsupported subjective attributes must remain unavailable for review.")
    if any(record["rule_attributes"]["garment_type"] == "unknown" for record in records):
        raise RuntimeError("A held-out category lacks the report's role/layering mapping.")

    failures = sorted((record for record in records if record["failed_fields"]), key=lambda item: (-len(item["failed_fields"]), item["id"]))[:args.failure_limit]
    evidence = ROOT / "storage" / "verification" / "attributes"
    run_dir = BACKEND / "runs" / "attributes"
    failure_dir = evidence / "failures"
    run_failure_dir = run_dir / "failures"
    for directory in (evidence, run_dir, failure_dir, run_failure_dir):
        directory.mkdir(parents=True, exist_ok=True)
    for directory in (failure_dir, run_failure_dir):
        for old in directory.glob("*.png"):
            old.unlink()
    failure_records = []
    for index, record in enumerate(failures, 1):
        filename = f"{index:02d}-{record['id']}.png"
        _failure_sheet(record, failure_dir / filename)
        shutil.copyfile(failure_dir / filename, run_failure_dir / filename)
        failure_records.append({"id": record["id"], "failed_fields": record["failed_fields"], "sheet": str(failure_dir / filename)})

    results = {
        "status": "complete",
        "errors": [],
        "kind": "AIR-05 held-out automatic garment attribute evaluation",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "split": "DeepFashion2 validation",
            "sample_count": len(records),
            "categories": sorted({record["category"] for record in records}),
            "sampling": manifest["sampling"],
            "label_protocol": labelled["label_protocol"],
            "not_claimed": "No accuracy claim is made for fit, style, material, pattern or custom tags; these remain reviewable/user-editable.",
        },
        "configuration": {
            "colour_extractor": "OpenCV Lab temperature plus deterministic k-means palette",
            "kmeans_clusters": extractor.color_analyzer.num_dominant_colors,
            "kmeans_seed": 42,
            "dominance_threshold": "top cluster > 0.60",
            "coarse_colour_mapping": "nearest fixed RGB anchor after conversion to OpenCV CIE Lab",
            "coarse_colour_anchors_rgb": COLOUR_ANCHORS_RGB,
        },
        "metrics": metrics,
        "integrity": {
            "rule_mapped_category_count": len({record["category"] for record in records}),
            "all_manual_fit_style_material_unavailable": True,
            "all_palettes_valid_and_sorted": True,
        },
        "runtime": {
            "device": "CPU",
            "latency_seconds": {"mean": float(np.mean(latencies)), "median": float(np.median(latencies)), "min": min(latencies), "max": max(latencies)},
            "peak_vram_bytes": 0,
            "hardware": {
                "operating_system": platform.platform(),
                "machine": platform.machine(),
                "processor": platform.processor() or "not reported by platform",
                "logical_cpu_count": os.cpu_count(),
            },
        },
        "failures": failure_records,
        "versions": {"python": platform.python_version(), "opencv": cv2.__version__, "numpy": np.__version__},
    }
    record_payload = {"records": records}
    for name, payload in (("results.json", results), ("predictions.json", record_payload)):
        serialised = json.dumps(payload, indent=2)
        (evidence / name).write_text(serialised, encoding="utf-8")
        (run_dir / name).write_text(serialised, encoding="utf-8")
    shutil.copyfile(labels_path, evidence / "ground-truth.json")
    shutil.copyfile(labels_path, run_dir / "ground-truth.json")
    print(json.dumps(results, indent=2), flush=True)


if __name__ == "__main__":
    main()
