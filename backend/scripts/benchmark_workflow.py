"""Record repeatable local API workflow latency evidence.

This is a single-process smoke benchmark, not a capacity or model-accuracy
benchmark.  It deliberately forces the labelled development AI fallback so
results remain reproducible without GPU weights.
"""

import argparse
from io import BytesIO
import json
import os
from pathlib import Path
import statistics
import sys
import time
import uuid

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("SMART_WARDROBE_ALLOW_DEV_IDENTITY", "true")
os.environ.setdefault("SMART_WARDROBE_AI_MODE", "development")

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


ROOT = Path(__file__).resolve().parents[2]


def jpeg() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (256, 256), "steelblue").save(buffer, "JPEG")
    return buffer.getvalue()


def timed(samples: dict[str, list[float]], name: str, operation):
    started = time.perf_counter()
    result = operation()
    samples.setdefault(name, []).append(round((time.perf_counter() - started) * 1000, 2))
    return result


def summary(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {"runs": len(values), "mean_ms": round(statistics.fmean(values), 2), "median_ms": round(statistics.median(values), 2), "p95_ms": ordered[max(0, round(0.95 * len(ordered)) - 1)]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a repeatable local API latency smoke benchmark.")
    parser.add_argument("--runs", type=int, default=3, help="Workflow iterations (default: 3).")
    parser.add_argument("--output", type=Path, default=ROOT / "storage" / "verification" / "workflow-latency.json")
    args = parser.parse_args()
    if args.runs < 1:
        raise ValueError("runs must be at least one")
    samples: dict[str, list[float]] = {}
    with TestClient(app, headers={"X-User-Id": str(uuid.uuid4())}) as client:
        timed(samples, "health", lambda: client.get("/health").raise_for_status())
        for _ in range(args.runs):
            response = timed(samples, "upload_to_review", lambda: client.post("/api/v1/processing/jobs", files={"file": ("benchmark.jpg", jpeg(), "image/jpeg")}))
            response.raise_for_status()
            job_id = response.json()["id"]
            timed(samples, "get_job", lambda: client.get(f"/api/v1/processing/jobs/{job_id}").raise_for_status())
            timed(samples, "list_garments", lambda: client.get("/api/v1/wardrobe/garments").raise_for_status())
    report = {"kind": "single-process local API smoke benchmark; not a capacity, load, or model-accuracy benchmark", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "metrics": {name: summary(values) for name, values in samples.items()}, "raw_ms": samples}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
