"""Evaluate pinned CatVTON on an officially licensed paired DressCode manifest."""

from argparse import ArgumentParser
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import sys
import time

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from app.domain.value_objects.visualisation_plan import VTONConfiguration, VisualisationGarment, VisualisationPlan
from app.infrastructure.ai.catvton_runtime import CatVTONRuntime, MODEL_VERSION
from scripts.evaluate_vtoff_paired import _compute_metrics, _hardware, _metric_summary, _sha256

GROUP_CATEGORY = {"upper_body": "short_sleeve_top", "lower_body": "trousers", "dresses": "long_sleeve_dress"}


def main() -> None:
    parser = ArgumentParser(description="Run category-balanced paired DressCode VTON evaluation.")
    parser.add_argument("--audit", type=Path, default=PROJECT / "storage" / "verification" / "vtoff" / "dresscode_dataset_audit.json")
    parser.add_argument("--per-group", type=int, default=10)
    parser.add_argument("--sample-seed", type=int, default=20260906)
    parser.add_argument("--generation-seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--guidance", type=float, default=2.5)
    parser.add_argument("--model-dir", type=Path, default=BACKEND / "models" / "vton")
    parser.add_argument("--output-dir", type=Path, default=PROJECT / "storage" / "verification" / "vton" / "dresscode_paired_evaluation")
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

    generated_dir = args.output_dir / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    configuration = VTONConfiguration(steps=args.steps, guidance=args.guidance, seed=args.generation_seed)
    runtime = CatVTONRuntime(args.model_dir, "cuda")
    records, errors = [], []
    import torch
    started = time.perf_counter()
    for pair in selected:
        group = pair["garment_group"]
        target = Path(pair["person"])
        garment = Path(pair["product"])
        destination = generated_dir / f"{pair['id']}.png"
        try:
            plan = VisualisationPlan(
                "outfit", pair["id"], "evaluation-person", "evaluation-person-media",
                (VisualisationGarment("evaluation-garment", "evaluation-garment-media", GROUP_CATEGORY[group], "garment", 1),),
                configuration,
            )
            torch.cuda.reset_peak_memory_stats()
            item_started = time.perf_counter()
            result = runtime.generate(plan, target.read_bytes(), garment.read_bytes())
            destination.write_bytes(result.image)
            records.append({
                "id": pair["id"], "garment_group": group, "person": str(target),
                "garment": str(garment), "target": str(target), "generated": str(destination),
                "latency_ms": round((time.perf_counter() - item_started) * 1000, 3),
                "peak_vram_bytes": torch.cuda.max_memory_allocated(),
                "person_sha256": _sha256(target), "garment_sha256": _sha256(garment),
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
    result = {
        "status": "complete" if len(records) == len(selected) and not errors else "failed",
        "model": {"name": "CatVTON", "version": MODEL_VERSION},
        "dataset": {"name": "DressCode", "audit": str(args.audit), "licence_authorised": True},
        "scope": {"sample_count": len(records), "per_group": args.per_group, "garment_groups": sorted(GROUP_CATEGORY)},
        "configuration": configuration.to_dict(), "sample_seed": args.sample_seed,
        "metrics": metric_summary,
        "runtime": {"hardware": _hardware(torch), "wall_time_seconds": round(time.perf_counter() - started, 3)},
        "records": records, "errors": errors,
        "limitations": ["Paired reconstruction does not establish measurement-accurate physical fit.", "DressCode access remains governed by its authors' licence agreement."],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    evidence = args.output_dir / "results.json"
    evidence.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "sample_count": len(records), "evidence": str(evidence)}, indent=2))
    if result["status"] != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
