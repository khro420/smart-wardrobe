"""Create an audited Fashionpedia training manifest without touching validation."""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
FIELDS = {
    "pattern": {"supercategories": {"textile pattern", "animal"}},
    "neckline": {"supercategories": {"neckline type"}},
    "sleeve_length": {"supercategories": {"length"}, "names": {"sleeveless", "short (length)", "elbow-length", "three quarter", "wrist-length"}},
    "silhouette": {"supercategories": {"silhouette"}},
}


def file_hash(path: Path) -> str:
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, default=BACKEND / "datasets" / "fashionpedia")
    parser.add_argument("--coarse", action="store_true", help="Emit the smaller app-facing visible-attribute taxonomy.")
    args = parser.parse_args()
    dataset = args.dataset_root.resolve()
    annotation_path = dataset / "instances_attributes_train2020.json"
    image_root = dataset / "train"
    if not annotation_path.is_file() or not image_root.is_dir():
        raise RuntimeError("Expected official Fashionpedia instances_attributes_train2020.json and train/.")
    payload = json.loads(annotation_path.read_text(encoding="utf-8"))
    images = {item["id"]: item["file_name"] for item in payload["images"]}
    attrs = {item["id"]: item for item in payload["attributes"]}
    if len(images) != 45623 or len(attrs) != 294:
        raise RuntimeError("Official Fashionpedia training annotation audit failed.")
    missing = [name for name in images.values() if not (image_root / name).is_file()]
    if missing:
        raise RuntimeError(f"Training image audit failed: {len(missing)} images absent (first {missing[0]}).")
    candidates = {field: sorted(item["id"] for item in attrs.values()
                                if item["supercategory"] in rule["supercategories"]
                                and ("names" not in rule or item["name"] in rule["names"]))
                  for field, rule in FIELDS.items()}
    rows: list[dict] = []
    for ann in payload["annotations"]:
        if ann.get("iscrowd") or ann.get("area", 0) < 2500:
            continue
        for field, ids in candidates.items():
            actual = [attribute_id for attribute_id in ann.get("attribute_ids", []) if attribute_id in ids]
            if len(actual) == 1:
                rows.append({"field": field, "annotation_id": ann["id"], "image_id": ann["image_id"],
                             "file_name": images[ann["image_id"]], "bbox": ann["bbox"], "label_id": actual[0]})
    evidence = ROOT / "storage" / "verification" / "fashionpedia_attributes"
    evidence.mkdir(parents=True, exist_ok=True)
    if args.coarse:
        def coarse(field, name):
            if field == "pattern": return "solid" if name == "plain (pattern)" else "patterned"
            if field == "sleeve_length": return "sleeveless" if name == "sleeveless" else ("short" if name in {"short (length)", "elbow-length"} else "long")
            if field == "neckline": return "v-neck" if name == "v-neck" else ("round-crew" if name in {"round (neck)", "crew (neck)"} else "other")
            return None
        rows = [{**row, "label_id": coarse(row["field"], attrs[row["label_id"]]["name"])} for row in rows if row["field"] != "silhouette"]
        candidates = {"pattern": ["solid", "patterned"], "sleeve_length": ["sleeveless", "short", "long"], "neckline": ["v-neck", "round-crew", "other"]}
        vocabulary = {field: [{"id": label, "name": label} for label in labels] for field, labels in candidates.items()}
    else:
        vocabulary = {field: [{"id": i, "name": attrs[i]["name"]} for i in ids] for field, ids in candidates.items()}
    output = {
        "status": "ok", "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "Fashionpedia official training localized-attribute annotation",
        "dataset_root": str(dataset), "annotation_sha256": file_hash(annotation_path),
        "source_counts": {"images": len(images), "instances": len(payload["annotations"]), "attributes": len(attrs)},
        "rows": rows,
        "label_vocabulary": vocabulary,
        "field_counts": dict(Counter(row["field"] for row in rows)),
        "integrity": {"all_training_images_present": True, "validation_used_for_training": False,
                      "limitation": "Only visibly annotated Fashionpedia properties are included. This manifest does not label physical fit, garment size, comfort, or actual material composition."},
    }
    name = "fashionpedia_coarse_training_manifest.json" if args.coarse else "fashionpedia_training_manifest.json"
    (evidence / name).write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({"status": output["status"], "field_counts": output["field_counts"], "rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
