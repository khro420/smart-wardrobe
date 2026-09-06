"""Generate reproducible deterministic segmentation-baseline evidence.

Run from ``backend`` with the existing segmentation weights. This script performs
inference only; it never trains or changes the model. It deterministically scans
numbered DeepFashion2 validation images until 10-20 garment pairs are collected.
"""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from app.infrastructure.ai.garment_segmentation_adapter import YoloGarmentAdapter, get_garment_adapter
from app.infrastructure.ai.segmentation_standardisation import CANVAS_SIZE, CONTENT_SIZE, standardise_garment_png


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _checkerboard(size: tuple[int, int]) -> Image.Image:
    board = Image.new("RGBA", size, "white")
    draw = ImageDraw.Draw(board)
    tile = 20
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=(226, 232, 240, 255))
    return board


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _panel(payload: bytes) -> Image.Image:
    with Image.open(BytesIO(payload)) as source:
        image = source.convert("RGBA")
    image.thumbnail((480, 480), Image.Resampling.LANCZOS)
    panel = _checkerboard((CANVAS_SIZE, CANVAS_SIZE))
    panel.alpha_composite(image, ((CANVAS_SIZE - image.width) // 2, (CANVAS_SIZE - image.height) // 2))
    return panel.convert("RGB")


def _comparison(original: bytes, standardised: bytes, label: str) -> bytes:
    header = 72
    gap = 16
    canvas = Image.new("RGB", (CANVAS_SIZE * 2 + gap, CANVAS_SIZE + header), "white")
    canvas.paste(_panel(original), (0, header))
    canvas.paste(_panel(standardised), (CANVAS_SIZE + gap, header))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 8), label, fill="black", font=_font(18))
    draw.text((12, 38), "Original segmentation crop", fill="#334155", font=_font(16))
    draw.text((CANVAS_SIZE + gap + 12, 38), "Deterministic segmentation baseline", fill="#334155", font=_font(16))
    output = BytesIO()
    canvas.save(output, "JPEG", quality=92)
    return output.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=15, help="Number of pairs (10-20).")
    parser.add_argument("--max-images", type=int, default=60, help="Maximum numbered validation images to inspect.")
    args = parser.parse_args()
    if not 10 <= args.limit <= 20:
        parser.error("--limit must be between 10 and 20")

    evidence_dir = PROJECT / "storage/verification/vtoff_standardisation"
    pairs_dir = evidence_dir / "pairs"
    components_dir = evidence_dir / "components"
    run_dir = BACKEND / "runs/vtoff_standardisation"
    for directory in (pairs_dir, components_dir, run_dir):
        directory.mkdir(parents=True, exist_ok=True)

    adapter = get_garment_adapter()
    if not isinstance(adapter, YoloGarmentAdapter):
        raise RuntimeError("Existing YOLO segmentation weights are required; development fallback is not verification evidence.")

    samples: list[dict[str, object]] = []
    for number in range(1, args.max_images + 1):
        source = BACKEND / f"datasets/deepfashion2_yolo_seg/images/validation/{number:06d}.jpg"
        if not source.exists():
            continue
        for candidate_index, detection in enumerate(adapter.analyse(source)):
            standardised = standardise_garment_png(detection.crop_png)
            pair_number = len(samples) + 1
            stem = f"{pair_number:02d}-{source.stem}-{candidate_index}-{detection.category}"
            original_name = f"{stem}-original.png"
            standardised_name = f"{stem}-standardised.png"
            pair_name = f"{stem}-comparison.jpg"
            (components_dir / original_name).write_bytes(detection.crop_png)
            (components_dir / standardised_name).write_bytes(standardised.png_bytes)
            (pairs_dir / pair_name).write_bytes(_comparison(
                detection.crop_png,
                standardised.png_bytes,
                f"{pair_number:02d}. {source.name} - {detection.category} ({detection.confidence:.1%})",
            ))

            left, top, right, bottom = standardised.output_mask_box
            centred_error = [abs((left + right) - CANVAS_SIZE), abs((top + bottom) - CANVAS_SIZE)]
            longest_edge = max(right - left, bottom - top)
            if centred_error[0] > 1 or centred_error[1] > 1 or longest_edge != CONTENT_SIZE:
                raise AssertionError(f"Standardisation geometry failed for {stem}: {standardised.output_mask_box}")
            samples.append({
                "pair": pair_number,
                "source_image": source.relative_to(BACKEND).as_posix(),
                "candidate_index": candidate_index,
                "category": detection.category,
                "confidence": round(detection.confidence, 6),
                "original_file": f"components/{original_name}",
                "original_size": list(standardised.source_size),
                "original_mask_box": list(standardised.source_mask_box),
                "original_sha256": _sha256(detection.crop_png),
                "standardised_file": f"components/{standardised_name}",
                "standardised_size": [CANVAS_SIZE, CANVAS_SIZE],
                "standardised_mask_box": list(standardised.output_mask_box),
                "standardised_sha256": _sha256(standardised.png_bytes),
                "comparison_file": f"pairs/{pair_name}",
                "centred_error_pixels": centred_error,
                "longest_mask_edge_pixels": longest_edge,
            })
            if len(samples) == args.limit:
                break
        if len(samples) == args.limit:
            break

    if len(samples) != args.limit:
        raise RuntimeError(f"Only {len(samples)} candidates were found; requested {args.limit}.")

    report = {
        "kind": "deterministic segmentation baseline verification (not generative AIR-03 evidence)",
        "method": "Retain the tight RGBA segmentation crop; crop to alpha bounds, scale the longest edge to 448 px, and centre on a transparent 512 x 512 PNG.",
        "generative_reconstruction": False,
        "model": adapter.model_metadata,
        "pair_count": len(samples),
        "selection_policy": "This baseline is evaluation-only and is not stored as a VTOFF candidate.",
        "invariants": {
            "canvas_size": [CANVAS_SIZE, CANVAS_SIZE],
            "longest_mask_edge_pixels": CONTENT_SIZE,
            "maximum_centre_error_pixels": 1,
            "transparent_background": True,
        },
        "samples": samples,
    }
    encoded_report = json.dumps(report, indent=2)
    (evidence_dir / "results.json").write_text(encoded_report, encoding="utf-8")
    (run_dir / "results.json").write_text(encoded_report, encoding="utf-8")
    print(encoded_report)


if __name__ == "__main__":
    main()
