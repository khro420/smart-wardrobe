"""Evaluate TryOffDiff v2 on a deterministic cleaned VITON-HD paired sample.

The script is deliberately resumable: generated images and YOLO segmentation
baselines are reused when their files already exist. It reports full-reference
quality metrics against the paired product photograph and distribution metrics
for the exact sampled subset. VITON-HD is upper-body only, so these results must
not be presented as validation of lower-body or dress generation.
"""

from argparse import ArgumentParser
from datetime import datetime, timezone
from io import BytesIO
import gc
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

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("TORCH_HOME", str(BACKEND / ".cache" / "torch"))

from app.infrastructure.ai.garment_segmentation_adapter import YoloGarmentAdapter
from app.infrastructure.ai.segmentation_standardisation import standardise_garment_png
from app.infrastructure.ai.tryoffdiff_runtime import (
    MODEL_CLASS, MODEL_FILENAME, MODEL_REPOSITORY, MODEL_REVISION, MODEL_SHA256,
    TryOffDiffRuntime, _pad_to_square,
)


UPPER_CATEGORIES = {
    "short_sleeve_top", "long_sleeve_top", "short_sleeve_outwear",
    "long_sleeve_outwear", "vest", "sling",
}
GROUP_CATEGORIES = {
    "upper_body": UPPER_CATEGORIES,
    "lower_body": {"shorts", "trousers", "skirt"},
    "dresses": {"short_sleeve_dress", "long_sleeve_dress", "vest_dress", "sling_dress"},
}
GROUP_DEFAULT_CATEGORY = {
    "upper_body": "short_sleeve_top",
    "lower_body": "trousers",
    "dresses": "long_sleeve_dress",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sample_pairs(pairs: list[dict], limit: int, seed: int) -> list[dict]:
    if limit <= 0 or limit > len(pairs):
        limit = len(pairs)
    selected = random.Random(seed).sample(pairs, limit)
    return sorted(selected, key=lambda pair: pair["id"])


def _sample_groups(pairs: list[dict], per_group: int, seed: int) -> list[dict]:
    selected = []
    for index, group in enumerate(GROUP_CATEGORIES):
        candidates = [pair for pair in pairs if pair.get("garment_group") == group]
        if len(candidates) < per_group:
            raise RuntimeError(f"DressCode {group} has {len(candidates)} pairs; {per_group} requested.")
        selected.extend(random.Random(seed + index).sample(candidates, per_group))
    return sorted(selected, key=lambda pair: pair["id"])


def _save_rgb_512(source: Path, target: Path) -> None:
    with Image.open(source) as image:
        normalized = _pad_to_square(image)
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized.save(target, "PNG", optimize=True)


def _save_baseline(payload: bytes, target: Path) -> float:
    standardized = standardise_garment_png(payload)
    with Image.open(BytesIO(standardized.png_bytes)) as rgba:
        white = Image.new("RGB", rgba.size, "white")
        white.paste(rgba.convert("RGBA"), mask=rgba.convert("RGBA").getchannel("A"))
        white.save(target, "PNG", optimize=True)
        return float(np.mean(np.asarray(rgba.getchannel("A")) > 0))


def _tensor(path: Path, device):
    import torch
    with Image.open(path) as image:
        array = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0).to(device)


def _metric_summary(values: list[float]) -> dict:
    clean = [float(value) for value in values if math.isfinite(float(value))]
    if not clean:
        return {"mean": None, "median": None, "min": None, "max": None, "count": 0}
    return {
        "mean": statistics.fmean(clean), "median": statistics.median(clean),
        "min": min(clean), "max": max(clean), "count": len(clean),
    }


def _font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


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


def _failure_sheet(record: dict, destination: Path) -> None:
    paths = (
        (record["person"], "Person input"),
        (record["target"], "Paired product target"),
        (record["generated"], "TryOffDiff output"),
        (record.get("baseline"), "Observed YOLO crop baseline"),
    )
    panel_width, panel_height = 512, 620
    sheet = Image.new("RGB", (panel_width * len(paths), panel_height), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (path, title) in enumerate(paths):
        panel = Image.new("RGB", (512, 512), "#f1f5f9")
        if path and Path(path).exists():
            with Image.open(path) as source:
                image = ImageOps.contain(source.convert("RGB"), (500, 500), Image.Resampling.LANCZOS)
            panel.paste(image, ((512 - image.width) // 2, (512 - image.height) // 2))
        sheet.paste(panel, (index * panel_width, 108))
        draw.text((index * panel_width + 12, 12), title, fill="#111827", font=_font(20))
    metrics = record["generated_metrics"]
    caption = (
        f"{record['id']} | SSIM {metrics['ssim']:.4f} | LPIPS {metrics['lpips']:.4f} | "
        f"DISTS {metrics['dists']:.4f} | YOLO confidence {record.get('segmentation_confidence')}"
    )
    draw.text((12, 48), caption, fill="#991b1b", font=_font(18))
    draw.text((12, 76), f"Failure label: {record['failure_label']}", fill="#7f1d1d", font=_font(17))
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, "PNG", optimize=True)


def _compute_metrics(records: list[dict], device: str) -> None:
    import pyiqa
    import torch
    from DISTS_pytorch import DISTS

    metric_device = torch.device(device if device == "cuda" and torch.cuda.is_available() else "cpu")
    ssim = pyiqa.create_metric("ssim", device=metric_device)
    lpips = pyiqa.create_metric("lpips", device=metric_device)
    # Use the package named by the TryOffDiff evaluation instructions rather
    # than silently substituting a different DISTS implementation.
    dists = DISTS().eval().to(metric_device)
    for record in records:
        target = _tensor(Path(record["target"]), metric_device)
        for label, path_key in (("generated_metrics", "generated"), ("baseline_metrics", "baseline")):
            path = record.get(path_key)
            if not path or not Path(path).exists():
                record[label] = None
                continue
            candidate = _tensor(Path(path), metric_device)
            with torch.inference_mode():
                record[label] = {
                    "ssim": float(ssim(candidate, target).item()),
                    "lpips": float(lpips(candidate, target).item()),
                    "dists": float(dists(candidate, target).item()),
                }
            del candidate
        del target
    del ssim, lpips, dists
    gc.collect()
    if metric_device.type == "cuda":
        torch.cuda.empty_cache()


def main() -> None:
    parser = ArgumentParser(description="Run a reproducible paired VTOFF evaluation.")
    parser.add_argument("--audit", type=Path, default=PROJECT / "storage" / "verification" / "vtoff" / "paired_dataset_audit.json")
    parser.add_argument("--limit", type=int, default=50, help="Deterministic sample size; 0 means the full cleaned test set.")
    parser.add_argument("--per-group", type=int, default=10, help="DressCode examples per upper/lower/dress group.")
    parser.add_argument("--sample-seed", type=int, default=20260905)
    parser.add_argument("--generation-seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--guidance", type=float, default=2.0)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--failure-limit", type=int, default=12)
    parser.add_argument("--failure-labels", type=Path)
    parser.add_argument("--prepare-failure-labels", action="store_true", help="Write provisional failure sheets/template without claiming a complete DressCode evaluation.")
    parser.add_argument("--refresh-generated", action="store_true", help="Regenerate outputs when cached generation provenance does not match this run.")
    parser.add_argument("--skip-distribution", action="store_true")
    args = parser.parse_args()

    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    is_dresscode = any(pair.get("garment_group") for pair in audit.get("pairs", []))
    if is_dresscode and audit.get("status") != "ok":
        raise RuntimeError("The DressCode audit is not complete and licensed for this run.")
    pairs = _sample_groups(audit["pairs"], args.per_group, args.sample_seed) if is_dresscode else _sample_pairs(audit["pairs"], args.limit, args.sample_seed)
    if len(pairs) < 2:
        raise RuntimeError("Paired evaluation requires at least two examples.")

    evaluation_name = "dresscode_paired_evaluation" if is_dresscode else "paired_evaluation"
    evidence = PROJECT / "storage" / "verification" / "vtoff" / evaluation_name
    run_dir = BACKEND / "runs" / "vtoff" / evaluation_name
    generated_dir, target_dir = evidence / "generated", evidence / "targets"
    baseline_dir, failure_dir = evidence / "baselines", evidence / "failures"
    for folder in (generated_dir, target_dir, baseline_dir, failure_dir, run_dir):
        folder.mkdir(parents=True, exist_ok=True)

    runtime = TryOffDiffRuntime(BACKEND / "models" / "vtoff", args.device)
    yolo = YoloGarmentAdapter(BACKEND / "models" / "cv" / "best.pt")
    records: list[dict] = []
    for index, pair in enumerate(pairs, 1):
        identifier = pair["id"]
        person, product = Path(pair["person"]), Path(pair["product"])
        generated_path, target_path = generated_dir / f"{identifier}.png", target_dir / f"{identifier}.png"
        baseline_path = baseline_dir / f"{identifier}.png"
        if not target_path.exists():
            _save_rgb_512(product, target_path)

        garment_group = pair.get("garment_group", "upper_body")
        relevant_categories = GROUP_CATEGORIES[garment_group]
        detections = yolo.analyse(person)
        relevant = [candidate for candidate in detections if candidate.category in relevant_categories and candidate.crop_png]
        selected = max(relevant, key=lambda candidate: candidate.confidence) if relevant else None
        generation_category = selected.category if selected else GROUP_DEFAULT_CATEGORY[garment_group]
        generation_metadata_path = generated_dir / f"{identifier}.json"
        generation_provenance = {
            "generation_seed": args.generation_seed,
            "inference_steps": args.steps,
            "guidance_scale": args.guidance,
            "generation_category": generation_category,
            "garment_group": garment_group,
            "model_sha256": MODEL_SHA256,
            "person_sha256": _sha256(person),
            "product_sha256": _sha256(product),
        }
        cached = json.loads(generation_metadata_path.read_text(encoding="utf-8")) if generated_path.exists() and generation_metadata_path.exists() else None
        cache_matches = cached is not None and all(cached.get(key) == value for key, value in generation_provenance.items())
        # Older VITON-HD evidence predates the stronger cache manifest. Preserve
        # it only for that already-reported slice; all DressCode caches are strict.
        legacy_viton_cache = not is_dresscode and cached is not None and "generation_seed" not in cached
        if cached is not None and (cache_matches or legacy_viton_cache) and not args.refresh_generated:
            generation = cached
        else:
            if cached is not None and not cache_matches and not args.refresh_generated and is_dresscode:
                raise RuntimeError(
                    f"Cached generation provenance does not match {identifier}; rerun with --refresh-generated to replace it explicitly."
                )
            output = runtime.generate(
                person, generation_category, seed=args.generation_seed,
                guidance_scale=args.guidance, inference_steps=args.steps,
            )
            generated_path.write_bytes(output.png_bytes)
            generation = {
                **generation_provenance,
                "latency_seconds": output.latency_seconds,
                "peak_vram_bytes": output.peak_vram_bytes,
                "generated_sha256": _sha256(generated_path),
            }
            generation_metadata_path.write_text(json.dumps(generation, indent=2), encoding="utf-8")

        coverage = None
        if selected and not baseline_path.exists():
            coverage = _save_baseline(selected.crop_png, baseline_path)
        elif baseline_path.exists():
            with Image.open(baseline_path) as baseline_image:
                coverage = float(np.mean(np.any(np.asarray(baseline_image.convert("RGB")) < 250, axis=2)))

        record = {
            "id": identifier, "person": str(person), "product_original": str(product),
            "garment_group": garment_group, "generation_category": generation_category,
            "target": str(target_path), "generated": str(generated_path),
            "baseline": str(baseline_path) if selected else None,
            "segmentation_category": selected.category if selected else None,
            "segmentation_confidence": selected.confidence if selected else None,
            "segmentation_foreground_coverage": coverage,
            **generation,
        }
        records.append(record)
        print(f"[{index}/{len(pairs)}] {identifier} generated={generated_path.exists()} baseline={selected is not None}", flush=True)

    # Free the 3.4 GB generation model before perceptual metric networks load.
    del runtime, yolo
    gc.collect()
    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    _compute_metrics(records, args.device)
    distribution: dict[str, float | None] = {"fid": None, "kid": None}
    distribution_note = "Skipped by command-line option."
    if not args.skip_distribution:
        from cleanfid import fid
        # Clean-FID lists both lower- and uppercase extensions. Windows globbing
        # is case-insensitive, which otherwise counts every image twice.
        if os.name == "nt":
            fid.EXTENSIONS = {extension.lower() for extension in fid.EXTENSIONS}
        distribution = {
            "fid": float(fid.compute_fid(str(target_dir), str(generated_dir), device=args.device, num_workers=0, batch_size=16, use_dataparallel=False)),
            "kid": float(fid.compute_kid(str(target_dir), str(generated_dir), device=args.device, num_workers=0, batch_size=16, use_dataparallel=False)),
        }
        distribution_note = "Subset FID/KID are indicative only; they are unstable at this sample size and are not full-test benchmark claims."

    generated_metrics = [record["generated_metrics"] for record in records]
    baseline_metrics = [record["baseline_metrics"] for record in records if record["baseline_metrics"]]
    metric_summary = {
        "generated": {name: _metric_summary([metric[name] for metric in generated_metrics]) for name in ("ssim", "lpips", "dists")},
        "segmentation_baseline": {name: _metric_summary([metric[name] for metric in baseline_metrics]) for name in ("ssim", "lpips", "dists")},
        **distribution,
    }
    if is_dresscode:
        metric_summary["per_garment_group"] = {
            group: {
                "generated": {
                    name: _metric_summary([
                        record["generated_metrics"][name]
                        for record in records if record["garment_group"] == group
                    ])
                    for name in ("ssim", "lpips", "dists")
                },
                "segmentation_baseline": {
                    name: _metric_summary([
                        record["baseline_metrics"][name]
                        for record in records if record["garment_group"] == group and record["baseline_metrics"]
                    ])
                    for name in ("ssim", "lpips", "dists")
                },
            }
            for group in GROUP_CATEGORIES
        }
    paired_baselines = [record for record in records if record["baseline_metrics"]]
    metric_summary["paired_comparison_vs_segmentation_baseline"] = {
        name: {
            "generated_mean_minus_baseline_mean": (
                statistics.fmean(record["generated_metrics"][name] for record in paired_baselines)
                - statistics.fmean(record["baseline_metrics"][name] for record in paired_baselines)
            ),
            "generated_wins": sum(
                (record["generated_metrics"][name] > record["baseline_metrics"][name])
                if name == "ssim" else
                (record["generated_metrics"][name] < record["baseline_metrics"][name])
                for record in paired_baselines
            ),
            "paired_count": len(paired_baselines),
            "direction": "higher is better" if name == "ssim" else "lower is better",
        }
        for name in ("ssim", "lpips", "dists")
    }
    confidences = [record["segmentation_confidence"] for record in paired_baselines]
    lpips_values = [record["generated_metrics"]["lpips"] for record in paired_baselines]
    confidence_lpips_correlation = float(np.corrcoef(confidences, lpips_values)[0, 1]) if len(paired_baselines) > 2 else None

    # Higher LPIPS/DISTS and lower SSIM indicate worse full-reference fidelity.
    failures = sorted(
        records,
        key=lambda record: record["generated_metrics"]["lpips"] + record["generated_metrics"]["dists"] - record["generated_metrics"]["ssim"],
        reverse=True,
    )[: max(1, min(args.failure_limit, len(records)))]
    failure_labels_path = args.failure_labels or BACKEND / "scripts" / (
        "dresscode_vtoff_failure_labels.json" if is_dresscode else "vtoff_failure_labels.json"
    )
    failure_labels = json.loads(failure_labels_path.read_text(encoding="utf-8")) if failure_labels_path.exists() else {}
    missing_failure_labels = [record["id"] for record in failures if not str(failure_labels.get(record["id"], "")).strip()]
    for rank, record in enumerate(failures, 1):
        record["failure_label"] = failure_labels.get(
            record["id"],
            "High perceptual error on the paired target; manual failure classification is pending.",
        )
        _failure_sheet(record, failure_dir / f"{rank:02d}_{record['id']}.png")

    label_template = {
        record["id"]: failure_labels.get(record["id"], "Describe the visible reconstruction failure without using metric values alone.")
        for record in failures
    }
    (evidence / "failure-label-template.json").write_text(json.dumps(label_template, indent=2), encoding="utf-8")

    import cleanfid
    import DISTS_pytorch
    results = {
        "status": "review_pending" if is_dresscode and missing_failure_labels else "complete",
        "errors": [],
        "kind": "paired TryOffDiff v2 DressCode category-wide evaluation" if is_dresscode else "paired TryOffDiff v2 upper-body evaluation",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": ({
            "dataset": "officially licensed DressCode paired test manifests",
            "garment_groups": list(GROUP_CATEGORIES), "sample_count": len(records),
            "population": audit["paired_examples"], "per_group": args.per_group,
            "sample_seed": args.sample_seed, "sampling": "fixed-seed stratified random sample without replacement",
            "limitation": "Development-size paired audit; not a full DressCode benchmark and not training evidence.",
        } if is_dresscode else {
            "dataset": "cleaned VITON-HD test pairs", "garment_group": "upper-body only",
            "sample_count": len(records), "cleaned_population": audit["paired_examples"],
            "sample_seed": args.sample_seed, "sampling": "fixed-seed simple random sample without replacement",
            "limitation": "Does not validate lower-body or dress generation; DressCode access is required for that.",
        }),
        "dataset_audit": ({
            "path": str(args.audit), "official_repository": audit["official_repository"],
            "official_license": audit["official_license"], "license_confirmed_by_operator": audit["license_confirmed_by_operator"],
            "groups": audit["groups"],
        } if is_dresscode else {
            "path": str(args.audit), "archive_sha256": audit["archive"]["sha256"], "exclusions": audit["exclusions"],
        }),
        "model": {"repository": MODEL_REPOSITORY, "revision": MODEL_REVISION, "file": MODEL_FILENAME,
                  "sha256": MODEL_SHA256, "class": MODEL_CLASS},
        "parameters": {"generation_seed": args.generation_seed, "steps": args.steps, "guidance_scale": args.guidance, "device": args.device},
        "metrics": metric_summary,
        "distribution_metric_note": distribution_note,
        "runtime": {
            "latency_seconds": _metric_summary([record["latency_seconds"] for record in records]),
            "peak_vram_bytes": max((record.get("peak_vram_bytes") or 0) for record in records),
            "hardware": _hardware(torch),
        },
        "segmentation_baseline_coverage": {"available": len(baseline_metrics), "missing": len(records) - len(baseline_metrics)},
        "runtime_policy_evidence": {
            "segmentation_confidence_vs_generated_lpips_pearson_r": confidence_lpips_correlation,
            "interpretation": "Segmentation confidence gates category reliability only; this sample does not support using it as a generated-fidelity score.",
        },
        "failure_examples": [
            {"id": record["id"], "label": record["failure_label"],
             "path": str(failure_dir / f"{rank:02d}_{record['id']}.png")}
            for rank, record in enumerate(failures, 1)
        ],
        "failure_label_review": {
            "labels_path": str(failure_labels_path),
            "required": len(failures),
            "completed": len(failures) - len(missing_failure_labels),
            "missing_ids": missing_failure_labels,
            "template": str(evidence / "failure-label-template.json"),
        },
        "versions": {"python": platform.python_version(), "torch": torch.__version__, "pyiqa": __import__("pyiqa").__version__,
                     "clean_fid": getattr(cleanfid, "__version__", "0.1.35"), "dists_pytorch": getattr(DISTS_pytorch, "__version__", "0.1")},
    }
    (evidence / "samples.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    (evidence / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    if run_dir.exists():
        for path in run_dir.iterdir():
            if path.is_file():
                path.unlink()
    for name in ("samples.json", "results.json", "failure-label-template.json"):
        shutil.copyfile(evidence / name, run_dir / name)
    run_failures = run_dir / "failures"
    run_failures.mkdir(parents=True, exist_ok=True)
    for old in run_failures.glob("*.png"):
        old.unlink()
    for path in failure_dir.glob("*.png"):
        shutil.copyfile(path, run_failures / path.name)
    print(json.dumps(results, indent=2), flush=True)
    if is_dresscode and missing_failure_labels and not args.prepare_failure_labels:
        raise RuntimeError(
            f"DressCode metrics were generated, but {len(missing_failure_labels)} qualitative failure labels remain. "
            f"Complete {failure_labels_path} from {evidence / 'failure-label-template.json'} and rerun."
        )


if __name__ == "__main__":
    main()
