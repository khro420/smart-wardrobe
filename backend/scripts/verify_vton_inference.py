"""Run one pinned CatVTON inference and write reproducible hardware evidence."""

from argparse import ArgumentParser
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

from PIL import Image

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from app.domain.value_objects.visualisation_plan import VTONConfiguration, VisualisationGarment, VisualisationPlan
from app.infrastructure.ai.catvton_runtime import CatVTONRuntime, MODEL_VERSION
from app.infrastructure.ai.vton_preprocessing import validate_generated_output


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hardware() -> dict:
    import torch
    result = {
        "operating_system": platform.platform(), "python": platform.python_version(),
        "logical_cpu_count": os.cpu_count(), "ram_bytes": None,
        "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
    }
    try:
        import psutil
        result["ram_bytes"] = psutil.virtual_memory().total
    except ImportError:
        pass
    if torch.cuda.is_available():
        properties = torch.cuda.get_device_properties(0)
        result.update(gpu_name=properties.name, gpu_total_memory_bytes=properties.total_memory)
    return result


def main() -> None:
    parser = ArgumentParser(description="Verify local-only CatVTON inference on one input pair.")
    parser.add_argument("--person", type=Path, required=True)
    parser.add_argument("--garment", type=Path, required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--model-dir", type=Path, default=BACKEND / "models" / "vton")
    parser.add_argument("--output-dir", type=Path, default=PROJECT / "storage" / "verification" / "vton" / "smoke")
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--guidance", type=float, default=2.5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    configuration = VTONConfiguration(steps=args.steps, guidance=args.guidance, seed=args.seed)
    current_plan = VisualisationPlan(
        "outfit", "verification", "person", "person-media",
        (VisualisationGarment("garment", "garment-media", args.category, "garment", 1),),
        configuration,
    )
    manifest_path = args.model_dir / "manifest.json"
    record = {
        "status": "running", "started_at": datetime.now(timezone.utc).isoformat(),
        "model": {
            "name": "CatVTON", "version": MODEL_VERSION,
            "manifest": str(manifest_path),
            "manifest_sha256": sha256(manifest_path) if manifest_path.is_file() else None,
        },
        "configuration": configuration.to_dict(), "mode": current_plan.mode,
        "inputs": {
            "person": str(args.person.resolve()), "person_sha256": sha256(args.person),
            "garment": str(args.garment.resolve()), "garment_sha256": sha256(args.garment),
        },
        "hardware": hardware(), "errors": [],
    }
    started = time.perf_counter()
    try:
        person_payload, garment_payload = args.person.read_bytes(), args.garment.read_bytes()
        result = CatVTONRuntime(args.model_dir, "cuda").generate(current_plan, person_payload, garment_payload)
        validate_generated_output(result, current_plan, person_payload)
        output = args.output_dir / "output.png"
        output.write_bytes(result.image)
        with Image.open(output) as image:
            image.verify()
        record.update(
            status="complete", output=str(output), output_sha256=sha256(output),
            model_version=result.model_version, inference_latency_ms=result.latency_ms,
            inference=result.metadata,
        )
    except Exception as exc:
        record["status"] = "failed"
        record["errors"] = [{"type": type(exc).__name__, "message": str(exc)}]
    record["wall_time_ms"] = round((time.perf_counter() - started) * 1000, 3)
    record["completed_at"] = datetime.now(timezone.utc).isoformat()
    evidence = args.output_dir / "results.json"
    evidence.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps({"status": record["status"], "evidence": str(evidence), "errors": record["errors"]}, indent=2))
    if record["status"] != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
