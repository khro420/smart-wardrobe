"""Evaluate pinned CatVTON on an officially licensed paired DressCode manifest."""

from argparse import ArgumentParser
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import subprocess
import sys
import time

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from app.domain.value_objects.visualisation_plan import VTONConfiguration, VisualisationGarment, VisualisationPlan
from app.infrastructure.ai.catvton_runtime import CatVTONRuntime, MODEL_VERSION
from scripts.evaluate_vtoff_paired import _compute_metrics, _failure_sheet, _hardware, _metric_summary, _sha256

GROUP_CATEGORY = {"upper_body": "short_sleeve_top", "lower_body": "trousers", "dresses": "long_sleeve_dress"}


def _thermal_gate(max_temperature: int | None, resume_temperature: int) -> None:
    """Pause between examples so a laptop GPU does not sustain unsafe heat."""
    if max_temperature is None:
        return
    while True:
        try:
            output = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"], text=True
            )
            temperature = int(output.strip().splitlines()[0])
        except Exception:
            return
        if temperature <= max_temperature:
            return
        while temperature > resume_temperature:
            time.sleep(20)
            try:
                output = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"], text=True
                )
                temperature = int(output.strip().splitlines()[0])
            except Exception:
                return


def main() -> None:
    parser = ArgumentParser(description="Run category-balanced paired DressCode VTON evaluation.")
    parser.add_argument("--audit", type=Path, default=PROJECT / "storage" / "verification" / "vtoff" / "dresscode_dataset_audit.json")
    parser.add_argument("--per-group", type=int, default=10)
    parser.add_argument("--sample-seed", type=int, default=20260906)
    parser.add_argument("--generation-seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--guidance", type=float, default=2.5)
    parser.add_argument("--model-dir", type=Path, default=BACKEND / "models" / "vton")
    parser.add_argument("--attention-checkpoint", type=Path, help="Optional local CatVTON attention-only experiment checkpoint; production assets remain unchanged.")
    parser.add_argument("--output-dir", type=Path, default=PROJECT / "storage" / "verification" / "vton" / "dresscode_paired_evaluation")
    parser.add_argument("--failure-limit", type=int, default=12)
    parser.add_argument("--failure-labels", type=Path, default=BACKEND / "scripts" / "dresscode_vton_failure_labels.json")
    parser.add_argument("--prepare-failure-labels", action="store_true")
    parser.add_argument("--thermal-max", type=int, default=None, help="Optional GPU temperature gate between generated examples.")
    parser.add_argument("--thermal-resume", type=int, default=65, help="Resume threshold when --thermal-max pauses evaluation.")
    args = parser.parse_args()

    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    if audit.get("status") != "ok" or audit.get("license_confirmed_by_operator") is not True:
        raise RuntimeError("DressCode evaluation requires a complete audit with explicit authorised licence evidence.")
    selected = []
    for offset, group in enumerate(GROUP_CATEGORY):
        candidates = [pair for pair in audit.get("pairs", []) if pair.get("garment_group") == group]
        if len(candidates) < args.per_group:
            raise RuntimeError(f"DressCode {group} has {len(candidates)} pairs; {args.per_group} required.")
        selected.extend(random.Random(args.sample_seed + offset).sample(candidates, args.per_group))
    selected.sort(key=lambda item: item["id"])

    generated_dir, failure_dir = args.output_dir / "generated", args.output_dir / "failures"
    generated_dir.mkdir(parents=True, exist_ok=True)
    failure_dir.mkdir(parents=True, exist_ok=True)
    configuration = VTONConfiguration(steps=args.steps, guidance=args.guidance, seed=args.generation_seed)
    previous_evidence = args.output_dir / "results.json"
    previous = json.loads(previous_evidence.read_text(encoding="utf-8")) if previous_evidence.exists() else {}
    reusable = {
        row["id"]: row for row in previous.get("records", [])
        if previous.get("configuration") == configuration.to_dict()
        and previous.get("sample_seed") == args.sample_seed
    }
    import torch
    runtime = CatVTONRuntime(args.model_dir, "cuda")
    model_version = MODEL_VERSION
    checkpoint_sha256 = None
    if args.attention_checkpoint:
        if not args.attention_checkpoint.is_file():
            raise FileNotFoundError(f"Attention checkpoint not found: {args.attention_checkpoint}")
        runtime._load()
        checkpoint = torch.load(args.attention_checkpoint, map_location="cpu", weights_only=True)
        state = checkpoint.get("attention_state_dict")
        if not isinstance(state, dict):
            raise RuntimeError("Checkpoint does not contain attention_state_dict.")
        runtime._pipeline.attn_modules.load_state_dict(state, strict=True)
        checkpoint_sha256 = _sha256(args.attention_checkpoint)
        model_version = f"{MODEL_VERSION}+attention-experiment-{checkpoint_sha256[:12]}"
    records, errors = [], []
    started = time.perf_counter()
    for pair in selected:
        group = pair["garment_group"]
        target = Path(pair["person"])
        garment = Path(pair["product"])
        destination = generated_dir / f"{pair['id']}.png"
        try:
            _thermal_gate(args.thermal_max, args.thermal_resume)
            person_sha256, garment_sha256 = _sha256(target), _sha256(garment)
            cached = reusable.get(pair["id"])
            if (
                cached and destination.is_file()
                and cached.get("person_sha256") == person_sha256
                and cached.get("garment_sha256") == garment_sha256
                and cached.get("generated_sha256") == _sha256(destination)
            ):
                records.append({
                    **cached, "target": str(target), "generated": str(destination),
                    "person_sha256": person_sha256, "garment_sha256": garment_sha256,
                })
                continue
            plan = VisualisationPlan(
                "outfit", pair["id"], "evaluation-person", "evaluation-person-media",
                (VisualisationGarment("evaluation-garment", "evaluation-garment-media", GROUP_CATEGORY[group], "garment", 1),),
                configuration,
            )
            torch.cuda.reset_peak_memory_stats()
            item_started = time.perf_counter()
            result = runtime.generate(plan, target.read_bytes(), (garment.read_bytes(),))
            destination.write_bytes(result.image)
            records.append({
                "id": pair["id"], "garment_group": group, "person": str(target),
                "garment": str(garment), "target": str(target), "generated": str(destination),
                "latency_ms": round((time.perf_counter() - item_started) * 1000, 3),
                "peak_vram_bytes": torch.cuda.max_memory_allocated(),
                "person_sha256": person_sha256, "garment_sha256": garment_sha256,
                "generated_sha256": _sha256(destination),
            })
        except Exception as exc:
            errors.append({"id": pair["id"], "type": type(exc).__name__, "message": str(exc)})
            break
    if not errors:
        _compute_metrics(records, "cuda")
    metric_summary = {
        metric: _metric_summary([row["generated_metrics"][metric] for row in records if row.get("generated_metrics")])
        for metric in ("ssim", "lpips", "dists")
    }
    metric_summary["per_garment_group"] = {
        group: {
            metric: _metric_summary([
                row["generated_metrics"][metric] for row in records
                if row["garment_group"] == group and row.get("generated_metrics")
            ]) for metric in ("ssim", "lpips", "dists")
        } for group in GROUP_CATEGORY
    }
    failures = sorted(
        (row for row in records if row.get("generated_metrics")),
        key=lambda row: row["generated_metrics"]["lpips"] + row["generated_metrics"]["dists"] - row["generated_metrics"]["ssim"],
        reverse=True,
    )[:max(1, min(args.failure_limit, len(records)))]
    failure_labels = json.loads(args.failure_labels.read_text(encoding="utf-8")) if args.failure_labels.exists() else {}
    missing_failure_labels = [row["id"] for row in failures if not str(failure_labels.get(row["id"], "")).strip()]
    for rank, row in enumerate(failures, 1):
        row["failure_label"] = failure_labels.get(row["id"], "High perceptual error; manual reconstruction review is pending.")
        _failure_sheet(row, failure_dir / f"{rank:02d}_{row['id']}.png", output_name="CatVTON output")
    (args.output_dir / "failure-label-template.json").write_text(json.dumps({
        row["id"]: failure_labels.get(row["id"], "Describe the visible reconstruction failure without using metric values alone.")
        for row in failures
    }, indent=2), encoding="utf-8")
    manifest_path = args.model_dir / "manifest.json"
    result = {
        "status": ("failed" if errors or len(records) != len(selected) else "review_pending" if missing_failure_labels else "complete"),
        "model": {"name": "CatVTON", "version": model_version, "assets_manifest": str(manifest_path), "assets_manifest_sha256": _sha256(manifest_path), "attention_checkpoint": str(args.attention_checkpoint) if args.attention_checkpoint else None, "attention_checkpoint_sha256": checkpoint_sha256},
        "dataset": {"name": "DressCode", "audit": str(args.audit), "licence_authorised": True},
        "scope": {"sample_count": len(records), "per_group": args.per_group, "garment_groups": sorted(GROUP_CATEGORY)},
        "configuration": configuration.to_dict(), "sample_seed": args.sample_seed,
        "metrics": metric_summary,
        "runtime": {"hardware": _hardware(torch), "wall_time_seconds": round(time.perf_counter() - started, 3)},
        "records": records, "errors": errors,
        "failure_examples": [{"id": row["id"], "label": row["failure_label"], "path": str(failure_dir / f"{rank:02d}_{row['id']}.png")} for rank, row in enumerate(failures, 1)],
        "failure_label_review": {"labels_path": str(args.failure_labels), "required": len(failures), "completed": len(failures) - len(missing_failure_labels), "missing_ids": missing_failure_labels, "template": str(args.output_dir / "failure-label-template.json")},
        "limitations": ["Paired reconstruction does not establish measurement-accurate physical fit.", "DressCode access remains governed by its authors' licence agreement."],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    evidence = args.output_dir / "results.json"
    evidence.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "sample_count": len(records), "evidence": str(evidence)}, indent=2))
    if result["status"] != "complete" and not (result["status"] == "review_pending" and args.prepare_failure_labels):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
