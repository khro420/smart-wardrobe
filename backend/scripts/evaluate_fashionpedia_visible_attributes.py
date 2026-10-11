"""Evaluate zero-shot *visible* garment attributes against Fashionpedia.

This is a local, inference-only evaluation.  It deliberately limits the scope
to attributes Fashionpedia annotates visually and that the application could
reasonably present as suggestions.  It never evaluates or infers fabric
composition, garment size, comfort, or physical fit.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import random
import shutil
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import torch
from transformers import AutoProcessor, SiglipModel


BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent

# Fashionpedia field -> the only ontology names we expose as a single-choice
# suggestion.  These are visible properties, not claims about construction.
FIELDS = {
    "pattern": {"supercategories": {"textile pattern", "animal"}},
    "neckline": {"supercategories": {"neckline type"}},
    "sleeve_length": {
        "supercategories": {"length"},
        "names": {"sleeveless", "short (length)", "elbow-length", "three quarter", "wrist-length"},
    },
    "silhouette": {"supercategories": {"silhouette"}},
}
COARSE = {
    "pattern": lambda name: "solid" if name == "plain (pattern)" else "patterned",
    "sleeve_length": lambda name: "sleeveless" if name == "sleeveless" else ("short" if name in {"short (length)", "elbow-length"} else "long"),
    "neckline": lambda name: "v-neck" if name == "v-neck" else ("round-crew" if name in {"round (neck)", "crew (neck)"} else "other"),
}


def digest(path: Path) -> str:
    hasher = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def normalise(label: str) -> str:
    return label.replace(" (length)", "").replace(" (pattern)", "").replace(" (neck)", "").replace(" (neckline)", "")


def choose_records(data: dict, per_field: int, seed: int) -> tuple[dict[str, list[dict]], dict[int, str]]:
    attributes = {item["id"]: item for item in data["attributes"]}
    image_names = {item["id"]: item["file_name"] for item in data["images"]}
    candidates: dict[str, list[dict]] = defaultdict(list)
    for annotation in data["annotations"]:
        if annotation.get("iscrowd") or annotation.get("area", 0) < 2_500:
            continue
        for field, rule in FIELDS.items():
            matched = [attributes[attr_id] for attr_id in annotation.get("attribute_ids", [])
                       if attributes[attr_id]["supercategory"] in rule["supercategories"]
                       and ("names" not in rule or attributes[attr_id]["name"] in rule["names"])]
            # A single-label evaluation must not silently choose among multiple
            # Fashionpedia ground-truth labels for the same field.
            if len(matched) == 1 and annotation["image_id"] in image_names:
                candidates[field].append({
                    "annotation_id": annotation["id"], "image_id": annotation["image_id"],
                    "file_name": image_names[annotation["image_id"]], "bbox": annotation["bbox"],
                    "ground_truth_id": matched[0]["id"], "ground_truth": matched[0]["name"],
                    "category_id": annotation["category_id"],
                })
    selected: dict[str, list[dict]] = {}
    for field, pool in candidates.items():
        by_label: dict[int, list[dict]] = defaultdict(list)
        for record in pool:
            by_label[record["ground_truth_id"]].append(record)
        rng = random.Random(f"{seed}:{field}")
        for records in by_label.values():
            rng.shuffle(records)
        # Stratified round-robin: broad, fixed coverage of labels rather than
        # a class-frequency dominated sample.
        rows: list[dict] = []
        labels = sorted(by_label)
        index = 0
        while len(rows) < per_field and any(by_label.values()):
            label = labels[index % len(labels)]
            if by_label[label]:
                rows.append(by_label[label].pop())
            index += 1
        selected[field] = rows
    return selected, image_names


def crop(image_path: Path, bbox: list[float]) -> Image.Image:
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    x, y, width, height = bbox
    left, top = max(0, int(x)), max(0, int(y))
    right, bottom = min(image.width, int(x + width)), min(image.height, int(y + height))
    if right <= left or bottom <= top:
        raise ValueError(f"Invalid Fashionpedia bounding box {bbox} for {image_path.name}")
    return image.crop((left, top, right, bottom))


def score(actual: list[str], predicted: list[str], labels: list[str]) -> dict:
    return {
        "accuracy": float(accuracy_score(actual, predicted)),
        "macro_precision": float(precision_score(actual, predicted, labels=labels, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(actual, predicted, labels=labels, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(actual, predicted, labels=labels, average="macro", zero_division=0)),
    }


def failure_sheet(record: dict, output: Path) -> None:
    canvas = Image.new("RGB", (1000, 600), "white")
    with Image.open(record["crop"]) as source:
        preview = ImageOps.contain(source.convert("RGB"), (560, 540), Image.Resampling.LANCZOS)
    canvas.paste(preview, ((580 - preview.width) // 2, 42))
    draw = ImageDraw.Draw(canvas)
    draw.text((600, 45), f"Fashionpedia visible-attribute failure", fill="#7f1d1d", font=font(23))
    draw.text((600, 104), f"Field: {record['field']}", fill="#334155", font=font(19))
    draw.text((600, 152), f"GT: {normalise(record['ground_truth'])}", fill="#166534", font=font(18))
    draw.text((600, 201), f"Pred: {normalise(record['prediction'])}", fill="#991b1b", font=font(18))
    draw.text((600, 270), f"Instance: {record['annotation_id']}", fill="#475569", font=font(15))
    draw.multiline_text((600, 318), "This is a zero-shot visible-attribute\nsuggestion benchmark. It does not measure\nmaterial composition, real size, comfort,\nor physical fit.", fill="#334155", font=font(16), spacing=8)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, "PNG", optimize=True)


def main() -> None:
    parser = ArgumentParser(description="Evaluate visible Fashionpedia attributes with a pinned local SigLIP model.")
    parser.add_argument("--dataset-root", type=Path, default=BACKEND / "datasets" / "fashionpedia")
    parser.add_argument("--per-field", type=int, default=20)
    parser.add_argument("--sample-seed", type=int, default=20261010)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--attribute-head-checkpoint", type=Path, help="Optional Fashionpedia-trained head checkpoint.")
    parser.add_argument("--evidence-name", default="fashionpedia_attributes")
    args = parser.parse_args()
    if not 10 <= args.per_field <= 100:
        raise ValueError("--per-field must be between 10 and 100")

    root = args.dataset_root.resolve()
    annotations = root / "instances_attributes_val2020.json"
    # The official ``val_test2020.zip`` extracts to ``test/`` even though it
    # includes every validation image referenced by the public val annotation.
    image_dir = next((candidate for candidate in (root / "val2020", root / "test") if candidate.is_dir()), None)
    if not annotations.is_file() or image_dir is None:
        raise RuntimeError("Expected official Fashionpedia validation files: instances_attributes_val2020.json and val2020/ or test/")
    data = json.loads(annotations.read_text(encoding="utf-8"))
    if len(data.get("attributes", [])) != 294 or not data.get("annotations"):
        raise RuntimeError("Fashionpedia annotation audit failed: expected the official localized-attributes validation annotation.")
    selected, _ = choose_records(data, args.per_field, args.sample_seed)
    missing = [record["file_name"] for rows in selected.values() for record in rows if not (image_dir / record["file_name"]).is_file()]
    if missing:
        raise RuntimeError(f"Fashionpedia image audit failed: {len(missing)} selected validation images are missing (first: {missing[0]}).")

    model_path = BACKEND / "models" / "vtoff" / "siglip-base-patch16-512"
    processor = AutoProcessor.from_pretrained(model_path, local_files_only=True)
    model = SiglipModel.from_pretrained(model_path, local_files_only=True).to(args.device).eval()
    heads = None
    head_labels = None
    if args.attribute_head_checkpoint:
        checkpoint = torch.load(args.attribute_head_checkpoint, map_location=args.device, weights_only=False)
        head_labels = {field: [item["name"] for item in labels] for field, labels in checkpoint["vocabulary"].items()}
        heads = torch.nn.ModuleDict({field: torch.nn.Sequential(torch.nn.LayerNorm(768), torch.nn.Linear(768, len(labels)))
                                    for field, labels in checkpoint["vocabulary"].items()}).to(args.device).eval()
        heads.load_state_dict(checkpoint["heads"])
    attrs = {item["id"]: item for item in data["attributes"]}
    output_root = ROOT / "storage" / "verification" / args.evidence_name
    run_root = BACKEND / "runs" / args.evidence_name
    for directory in (output_root, run_root):
        directory.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    records: list[dict] = []
    with torch.inference_mode():
        for field, rows in selected.items():
            if heads is not None and field not in heads:
                continue
            choices = sorted({attrs[item["id"]]["name"] for item in attrs.values()
                              if item["supercategory"] in FIELDS[field]["supercategories"]
                              and ("names" not in FIELDS[field] or item["name"] in FIELDS[field]["names"])} )
            prompts = [f"a photo of a garment with {normalise(choice)}" for choice in choices]
            for source in rows:
                image = crop(image_dir / source["file_name"], source["bbox"])
                if heads is None:
                    inputs = processor(text=prompts, images=image, padding="max_length", return_tensors="pt")
                    inputs = {key: value.to(args.device) for key, value in inputs.items()}
                    logits = model(**inputs).logits_per_image[0]
                    prediction = choices[int(torch.argmax(logits).item())]
                else:
                    pixels = processor(images=image, return_tensors="pt")["pixel_values"].to(args.device)
                    features = model.get_image_features(pixel_values=pixels)
                    prediction = head_labels[field][int(torch.argmax(heads[field](features.float())[0]).item())]
                crop_path = output_root / "crops" / f"{field}-{source['annotation_id']}.png"
                crop_path.parent.mkdir(parents=True, exist_ok=True)
                image.save(crop_path, "PNG", optimize=True)
                target = COARSE[field](source["ground_truth"]) if heads and field in COARSE and set(head_labels[field]) == set({COARSE[field](name) for name in choices}) else source["ground_truth"]
                records.append({**source, "field": field, "ground_truth": target, "prediction": prediction, "crop": str(crop_path),
                                "correct": prediction == target})
    elapsed = time.perf_counter() - started
    metrics = {}
    for field in sorted({record["field"] for record in records}):
        rows = [record for record in records if record["field"] == field]
        labels = sorted({record["ground_truth"] for record in rows} | {record["prediction"] for record in rows})
        metrics[field] = {"sample_count": len(rows), "labels_observed": sorted({record["ground_truth"] for record in rows}),
                          **score([record["ground_truth"] for record in rows], [record["prediction"] for record in rows], labels)}
    failures = [record for record in records if not record["correct"]]
    failure_dir = output_root / "failures"
    run_failure_dir = run_root / "failures"
    for directory in (failure_dir, run_failure_dir):
        directory.mkdir(parents=True, exist_ok=True)
        for old in directory.glob("*.png"):
            old.unlink()
    failure_records = []
    for index, record in enumerate(failures[:20], 1):
        filename = f"{index:02d}-{record['field']}-{record['annotation_id']}.png"
        failure_sheet(record, failure_dir / filename)
        shutil.copyfile(failure_dir / filename, run_failure_dir / filename)
        failure_records.append({"annotation_id": record["annotation_id"], "field": record["field"], "ground_truth": record["ground_truth"], "prediction": record["prediction"], "sheet": str(failure_dir / filename)})
    audit = {
        "status": "ok", "dataset": "Fashionpedia official validation localized attribute annotations",
        "dataset_root": str(root), "annotation_sha256": digest(annotations),
        "validation_images": len(data["images"]), "validation_instances": len(data["annotations"]),
        "categories": len(data["categories"]), "attributes": len(data["attributes"]),
        "provenance": "Official CVDF Fashionpedia release; local-only evaluation asset; excluded from Git.",
    }
    result = {
        "status": "complete", "errors": [], "created_at": datetime.now(timezone.utc).isoformat(),
        "kind": "Fashionpedia held-out visible garment-attribute evaluation",
        "scope": {"split": "Fashionpedia validation", "sample_seed": args.sample_seed, "per_field": args.per_field,
                  "sample_count": len(records), "fields": list(FIELDS),
                  "limitation": "Visible-image reconstruction/classification evidence only. It does not establish actual fabric composition, physical garment size, comfort, or physical fit. Unsupported subjective attributes remain user-editable."},
        "dataset_audit": audit,
        "model": {"name": "google/siglip-base-patch16-512", "local_asset": str(model_path), "asset_config_sha256": digest(model_path / "config.json"), "mode": "Fashionpedia-trained frozen-encoder heads" if heads else "zero-shot; no Fashionpedia training or tuning", "attribute_head_checkpoint": str(args.attribute_head_checkpoint) if args.attribute_head_checkpoint else None},
        "configuration": {"device": args.device, "prompt_template": "a photo of a garment with {attribute}", "candidate_selection": "Fashionpedia ontology field candidates"},
        "metrics": metrics,
        "runtime": {"elapsed_seconds": elapsed, "device": args.device, "hardware": {"operating_system": platform.platform(), "machine": platform.machine()}},
        "failures": failure_records, "records": records,
    }
    for target in (output_root, run_root):
        (target / "fashionpedia_dataset_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
        (target / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "sample_count": len(records), "metrics": metrics, "evidence": str(output_root / "results.json")}, indent=2))


if __name__ == "__main__":
    main()
