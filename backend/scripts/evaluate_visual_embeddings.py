"""Evaluate and persist real SigLIP garment embeddings on held-out data.

Ground-truth DeepFashion2 polygons provide category-labelled garment crops. The
script reports leave-one-out nearest-neighbour category retrieval, writes labelled
failure sheets, and exercises the real processing-to-confirmed-garment persistence
path in an isolated runtime. It never trains or fine-tunes the embedding model.
"""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import shutil
import statistics
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from sklearn.metrics import accuracy_score, f1_score


BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
CLASS_NAMES = [
    "short_sleeve_top", "long_sleeve_top", "short_sleeve_outwear", "long_sleeve_outwear",
    "vest", "sling", "shorts", "trousers", "skirt", "short_sleeve_dress",
    "long_sleeve_dress", "vest_dress", "sling_dress",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _font(size: int):
    try: return ImageFont.truetype("arial.ttf", size)
    except OSError: return ImageFont.load_default()


def _hardware(torch_module) -> dict:
    hardware = {
        "operating_system": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "not reported by platform",
        "logical_cpu_count": os.cpu_count(),
        "cuda_available": bool(torch_module.cuda.is_available()),
        "cuda_runtime": torch_module.version.cuda,
    }
    if torch_module.cuda.is_available():
        properties = torch_module.cuda.get_device_properties(torch_module.cuda.current_device())
        hardware.update(gpu_name=properties.name, gpu_total_memory_bytes=properties.total_memory)
    return hardware


def _collect_instances(labels_dir: Path, images_dir: Path) -> dict[int, list[dict]]:
    instances = {index: [] for index in range(len(CLASS_NAMES))}
    image_lookup = {path.stem: path for path in images_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"}}
    for label_path in sorted(labels_dir.glob("*.txt")):
        image_path = image_lookup.get(label_path.stem)
        if image_path is None:
            continue
        for line_index, line in enumerate(label_path.read_text(encoding="utf-8").splitlines()):
            values = line.split()
            if len(values) < 7 or (len(values) - 1) % 2:
                continue
            class_id = int(values[0])
            if class_id in instances:
                instances[class_id].append({"image": image_path, "label": label_path, "line": line_index, "polygon": [float(value) for value in values[1:]]})
    return instances


def _crop_instance(record: dict, destination: Path) -> None:
    with Image.open(record["image"]) as source:
        rgb = source.convert("RGB")
    polygon = record["polygon"]
    points = [(round(polygon[index] * rgb.width), round(polygon[index + 1] * rgb.height)) for index in range(0, len(polygon), 2)]
    mask = Image.new("L", rgb.size, 0)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    box = mask.getbbox()
    if box is None:
        raise RuntimeError(f"Empty ground-truth polygon in {record['label']} line {record['line'] + 1}")
    crop = rgb.crop(box).convert("RGBA")
    crop.putalpha(mask.crop(box))
    destination.parent.mkdir(parents=True, exist_ok=True)
    crop.save(destination, "PNG", optimize=True)


def _failure_sheet(query: dict, neighbour: dict, destination: Path) -> None:
    canvas = Image.new("RGB", (1024, 610), "white")
    draw = ImageDraw.Draw(canvas)
    for index, (record, title) in enumerate(((query, "Query (ground truth)"), (neighbour, "Nearest neighbour"))):
        with Image.open(record["crop"]) as source:
            image = ImageOps.contain(source.convert("RGBA"), (480, 480), Image.Resampling.LANCZOS)
            panel = Image.new("RGBA", (500, 500), (241, 245, 249, 255))
            panel.alpha_composite(image, ((500 - image.width) // 2, (500 - image.height) // 2))
        canvas.paste(panel.convert("RGB"), (index * 512 + 6, 100))
        draw.text((index * 512 + 12, 12), title, fill="#111827", font=_font(20))
        draw.text((index * 512 + 12, 44), record["category"], fill="#991b1b", font=_font(18))
    draw.text((12, 75), f"Cosine similarity {query['top1_similarity']:.4f}; wrong-category retrieval", fill="#7f1d1d", font=_font(16))
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, "PNG", optimize=True)


def main() -> None:
    parser = ArgumentParser(description="Evaluate real visual garment embeddings.")
    parser.add_argument("--per-category", type=int, default=8)
    parser.add_argument("--sample-seed", type=int, default=20260905)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--failure-limit", type=int, default=12)
    args = parser.parse_args()
    if args.per_category < 2:
        raise ValueError("Use at least two instances per category for leave-one-out retrieval.")

    evidence = ROOT / "storage" / "verification" / "embeddings"
    run_dir = BACKEND / "runs" / "embeddings"
    inputs_dir, failures_dir = evidence / "inputs", evidence / "failures"
    for directory in (evidence, run_dir, inputs_dir, failures_dir): directory.mkdir(parents=True, exist_ok=True)

    labels_dir = BACKEND / "datasets" / "deepfashion2_yolo_seg" / "labels" / "validation"
    images_dir = BACKEND / "datasets" / "deepfashion2_yolo_seg" / "images" / "validation"
    instances = _collect_instances(labels_dir, images_dir)
    randomiser = random.Random(args.sample_seed)
    selected = []
    for class_id, category in enumerate(CLASS_NAMES):
        if len(instances[class_id]) < args.per_category:
            raise RuntimeError(f"Not enough held-out instances for {category}: {len(instances[class_id])}")
        for record in randomiser.sample(instances[class_id], args.per_category):
            identifier = f"{category}-{Path(record['image']).stem}-line{record['line'] + 1}"
            crop = inputs_dir / f"{identifier}.png"
            _crop_instance(record, crop)
            selected.append({"id": identifier, "category": category, "class_id": class_id, "source_image": str(record["image"]), "source_label": str(record["label"]), "source_line": record["line"] + 1, "crop": str(crop)})

    with tempfile.TemporaryDirectory(prefix="o2-embedding-runtime-", dir=BACKEND / "runs") as runtime_dir:
        os.environ["SMART_WARDROBE_DATA_DIR"] = runtime_dir
        os.environ["SMART_WARDROBE_AI_MODE"] = "production"
        os.environ["SMART_WARDROBE_ALLOW_DEV_IDENTITY"] = "true"
        os.environ["SMART_WARDROBE_VTOFF_ENABLED"] = "false"
        os.environ["SMART_WARDROBE_EMBEDDING_ENABLED"] = "true"
        os.environ["SMART_WARDROBE_EMBEDDING_DEVICE"] = args.device

        from app.infrastructure.ai.attribute_embedding_adapter import (
            EMBEDDING_DIMENSION, EMBEDDING_MODEL_REPOSITORY, EMBEDDING_MODEL_REVISION,
            EMBEDDING_MODEL_SHA256, EMBEDDING_PREPROCESSING_VERSION, get_attribute_adapter,
        )
        from app.infrastructure.persistence.vector_repository import VectorRepository

        adapter = get_attribute_adapter()
        vectors = []
        latencies = []
        peak_vram = 0
        for index, record in enumerate(selected, 1):
            attributes = adapter.extract(record["crop"]).values
            vector = VectorRepository().validate(attributes["embedding"])
            norm = math.sqrt(sum(value * value for value in vector))
            if abs(norm - 1.0) > 1e-5:
                raise RuntimeError(f"Embedding {record['id']} is not L2 normalised: {norm}")
            record.update({
                "embedding": vector, "embedding_l2_norm": norm,
                "embedding_latency_seconds": attributes["embedding_latency_seconds"],
                "embedding_peak_vram_bytes": attributes["embedding_peak_vram_bytes"],
            })
            vectors.append(vector)
            latencies.append(attributes["embedding_latency_seconds"])
            peak_vram = max(peak_vram, attributes["embedding_peak_vram_bytes"] or 0)
            print(f"[{index}/{len(selected)}] {record['id']}", flush=True)

        matrix = np.asarray(vectors, dtype=np.float32)
        similarities = matrix @ matrix.T
        np.fill_diagonal(similarities, -np.inf)
        actual = [record["category"] for record in selected]
        predicted = []
        precision_at_5 = []
        reciprocal_ranks = []
        for index, record in enumerate(selected):
            ranking = np.argsort(-similarities[index])
            top = int(ranking[0])
            predicted.append(selected[top]["category"])
            record["top1_id"] = selected[top]["id"]
            record["top1_category"] = selected[top]["category"]
            record["top1_similarity"] = float(similarities[index, top])
            precision_at_5.append(sum(selected[int(item)]["category"] == record["category"] for item in ranking[:5]) / 5)
            first_same = next(rank for rank, item in enumerate(ranking, 1) if selected[int(item)]["category"] == record["category"])
            reciprocal_ranks.append(1 / first_same)

        errors = [record for record in selected if record["top1_category"] != record["category"]]
        failures = sorted(errors, key=lambda record: record["top1_similarity"], reverse=True)[:args.failure_limit]
        by_id = {record["id"]: record for record in selected}
        for rank, record in enumerate(failures, 1):
            _failure_sheet(record, by_id[record["top1_id"]], failures_dir / f"{rank:02d}-{record['id']}.png")

        # Exercise the actual processing item -> confirmed garment persistence
        # using the same real adapter, with VTOFF disabled to preserve the crop.
        from fastapi.testclient import TestClient
        from app.main import app
        persistence_source = Path(selected[0]["source_image"])
        with TestClient(app, headers={"X-User-Id": "embedding-persistence-owner"}) as client:
            uploaded = client.post("/api/v1/processing/jobs", files={"file": (persistence_source.name, persistence_source.read_bytes(), "image/jpeg")})
            if uploaded.status_code != 202:
                raise RuntimeError(uploaded.text)
            job = client.get(f"/api/v1/processing/jobs/{uploaded.json()['id']}").json()
            if job["status"] != "review_required" or not job["items"]:
                raise RuntimeError(job)
            item = job["items"][0]
            reviewed = client.post(f"/api/v1/processing/jobs/{job['id']}/review", json={"items": [{"item_id": item["id"], "decision": "accepted"}]})
            saved = client.post(f"/api/v1/processing/jobs/{job['id']}/confirm", json={"save_mode": "garments", "item_ids": [item["id"]]})
            if reviewed.status_code != 200 or saved.status_code != 201:
                raise RuntimeError(f"Review/save failed: {reviewed.text} / {saved.text}")
            garment = next(value for value in client.get("/api/v1/wardrobe/garments").json() if value["id"] == saved.json()["garment_ids"][0])
            processing_vector = VectorRepository().validate(item["embedding"])
            garment_vector = VectorRepository().validate(garment["embedding"])
            persistence = {
                "processing_item_dimension": len(processing_vector), "garment_dimension": len(garment_vector),
                "vectors_identical": processing_vector == garment_vector,
                "preferred_media_is_segmentation_crop": item["preferred_media_id"] == item["crop_media_id"],
                "generated_media_present": item["vtoff_media_id"] is not None,
                "owner": "isolated synthetic test identity",
            }
            if (
                not persistence["vectors_identical"]
                or not persistence["preferred_media_is_segmentation_crop"]
                or persistence["generated_media_present"]
            ):
                raise RuntimeError(persistence)

    import torch, transformers
    results = {
        "status": "complete",
        "errors": [],
        "kind": "held-out DeepFashion2 SigLIP visual embedding evaluation",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "split": "validation", "sampling": "fixed-seed stratified by all 13 ground-truth categories",
            "sample_seed": args.sample_seed, "per_category": args.per_category, "sample_count": len(selected),
            "limitation": "This is a small category-retrieval development evaluation, not evidence of general semantic similarity or recommendation-ranking quality.",
        },
        "model": {"repository": EMBEDDING_MODEL_REPOSITORY, "revision": EMBEDDING_MODEL_REVISION, "sha256": EMBEDDING_MODEL_SHA256, "dimension": EMBEDDING_DIMENSION},
        "preprocessing": {"version": EMBEDDING_PREPROCESSING_VERSION, "input": "ground-truth polygon RGBA crop", "normalisation": "L2"},
        "metrics": {
            "leave_one_out_top1_category_accuracy": float(accuracy_score(actual, predicted)),
            "leave_one_out_macro_f1": float(f1_score(actual, predicted, labels=CLASS_NAMES, average="macro", zero_division=0)),
            "mean_precision_at_5": statistics.fmean(precision_at_5),
            "mean_reciprocal_rank_first_same_category": statistics.fmean(reciprocal_ranks),
        },
        "runtime": {
            "device": args.device, "latency_seconds": {"mean": statistics.fmean(latencies), "median": statistics.median(latencies), "min": min(latencies), "max": max(latencies)},
            "peak_vram_bytes": peak_vram,
            "hardware": _hardware(torch),
        },
        "persistence": persistence,
        "failures": [{"id": record["id"], "ground_truth": record["category"], "retrieved": record["top1_category"], "similarity": record["top1_similarity"], "sheet": str(failures_dir / f"{rank:02d}-{record['id']}.png")} for rank, record in enumerate(failures, 1)],
        "versions": {"python": platform.python_version(), "torch": torch.__version__, "transformers": transformers.__version__, "numpy": np.__version__},
    }
    samples = {"source_dataset": "DeepFashion2 held-out validation", "source_label_sha256": _sha256(Path(selected[0]["source_label"])), "records": selected}
    for destination, payload in ((evidence / "results.json", results), (evidence / "samples.json", samples)):
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copyfile(destination, run_dir / destination.name)
    for old in (run_dir / "failures",):
        old.mkdir(parents=True, exist_ok=True)
        for path in old.glob("*.png"): path.unlink()
    for path in failures_dir.glob("*.png"): shutil.copyfile(path, run_dir / "failures" / path.name)
    print(json.dumps(results, indent=2), flush=True)


if __name__ == "__main__":
    main()
