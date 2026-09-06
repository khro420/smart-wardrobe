"""Run one real, reproducible YOLO -> TryOffDiff v2 verification sample."""

from argparse import ArgumentParser
from datetime import datetime, timezone
from io import BytesIO
import hashlib
import json
from pathlib import Path
import shutil
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps


BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from app.infrastructure.ai.garment_segmentation_adapter import YoloGarmentAdapter
from app.infrastructure.ai.tryoffdiff_runtime import (
    MODEL_CLASS, MODEL_FILENAME, MODEL_REPOSITORY, MODEL_REVISION, MODEL_SHA256, TryOffDiffRuntime,
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _panel(payload: bytes, title: str) -> Image.Image:
    with Image.open(BytesIO(payload)) as source:
        image = source.convert("RGBA")
    canvas = Image.new("RGB", (512, 570), "white")
    checker = Image.new("RGB", (512, 512), "#f1f5f9")
    image = ImageOps.contain(image, (480, 480), Image.Resampling.LANCZOS)
    if image.mode == "RGBA":
        checker.paste(image, ((512 - image.width) // 2, (512 - image.height) // 2), image)
    else:
        checker.paste(image, ((512 - image.width) // 2, (512 - image.height) // 2))
    canvas.paste(checker, (0, 58))
    ImageDraw.Draw(canvas).text((16, 18), title, fill="#111827", font=_font(22))
    return canvas


def main() -> None:
    parser = ArgumentParser(description="Verify real multi-garment TryOffDiff inference.")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--guidance", type=float, default=2.0)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    source = args.source
    if source is None:
        candidates = sorted((BACKEND / "datasets" / "deepfashion2_yolo_seg" / "images" / "validation").glob("*"))
        if not candidates:
            raise FileNotFoundError("Pass --source or provide the converted DeepFashion2 validation split.")
        source = candidates[0]
    source = source.resolve()

    weights = BACKEND / "models" / "cv" / "best.pt"
    detections = YoloGarmentAdapter(weights).analyse(source)
    if not detections:
        raise RuntimeError("YOLO did not find a supported garment in the verification image.")
    detection = max(detections, key=lambda candidate: candidate.confidence)
    runtime = TryOffDiffRuntime(BACKEND / "models" / "vtoff", args.device)
    generated = runtime.generate(
        source, detection.category, seed=args.seed,
        guidance_scale=args.guidance, inference_steps=args.steps,
    )

    evidence_dir = PROJECT / "storage" / "verification" / "vtoff" / "smoke"
    run_dir = BACKEND / "runs" / "vtoff" / "smoke"
    for folder in (evidence_dir, run_dir):
        folder.mkdir(parents=True, exist_ok=True)

    source_bytes = source.read_bytes()
    source_buffer = BytesIO()
    with Image.open(source) as image:
        image.convert("RGB").save(source_buffer, "PNG")
    source_png = source_buffer.getvalue()
    payloads = {"source.png": source_png, "crop.png": detection.crop_png,
                "mask.png": detection.mask_png, "generated.png": generated.png_bytes}
    for name, payload in payloads.items():
        (evidence_dir / name).write_bytes(payload)

    comparison = Image.new("RGB", (1536, 570), "white")
    for index, (payload, title) in enumerate((
        (source_png, "Conditioning source"),
        (detection.crop_png, "Observed segmentation fallback"),
        (generated.png_bytes, "Synthetic VTOFF (review required)"),
    )):
        comparison.paste(_panel(payload, title), (index * 512, 0))
    comparison.save(evidence_dir / "comparison.png")

    result = {
        "kind": "real TryOffDiff v2 smoke verification (not paired AIR-03 quality evaluation)",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source), "source_sha256": _sha256(source_bytes),
        "category": detection.category, "segmentation_confidence": detection.confidence,
        "model": {"repository": MODEL_REPOSITORY, "revision": MODEL_REVISION,
                  "file": MODEL_FILENAME, "sha256": MODEL_SHA256, "class": MODEL_CLASS},
        "parameters": {"seed": generated.seed, "inference_steps": generated.inference_steps,
                       "guidance_scale": generated.guidance_scale, "device": args.device},
        "latency_seconds": generated.latency_seconds,
        "peak_vram_bytes": generated.peak_vram_bytes,
        "output_size": [512, 512], "output_sha256": _sha256(generated.png_bytes),
        "review_policy": "Generated output is synthetic; crop remains default and user approval is required.",
    }
    (evidence_dir / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    for path in evidence_dir.iterdir():
        if path.is_file():
            shutil.copyfile(path, run_dir / path.name)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
