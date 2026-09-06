"""Prepare a fixed, category-stratified blind review sheet for AIR-05 labels."""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw, ImageFont, ImageOps


BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent


def _font(size: int):
    try: return ImageFont.truetype("arial.ttf", size)
    except OSError: return ImageFont.load_default()


def main() -> None:
    parser = ArgumentParser(description="Prepare blind garment-attribute review sheets.")
    parser.add_argument("--per-category", type=int, default=3)
    args = parser.parse_args()
    samples = json.loads((ROOT / "storage" / "verification" / "embeddings" / "samples.json").read_text(encoding="utf-8"))["records"]
    by_category: dict[str, list[dict]] = {}
    for record in samples: by_category.setdefault(record["category"], []).append(record)
    selected = [record for category in sorted(by_category) for record in by_category[category][:args.per_category]]

    evidence = ROOT / "storage" / "verification" / "attributes"
    run_dir = BACKEND / "runs" / "attributes"
    evidence.mkdir(parents=True, exist_ok=True); run_dir.mkdir(parents=True, exist_ok=True)
    pages = []
    for page_index in range(0, len(selected), 12):
        page_records = selected[page_index:page_index + 12]
        sheet = Image.new("RGB", (1200, 1320), "white")
        draw = ImageDraw.Draw(sheet)
        draw.text((24, 18), "AIR-05 blind manual labelling sheet - no model predictions shown", fill="#111827", font=_font(24))
        for offset, record in enumerate(page_records):
            row, column = divmod(offset, 4)
            left, top = column * 300, row * 420 + 72
            with Image.open(record["crop"]) as source:
                image = ImageOps.contain(source.convert("RGBA"), (270, 330), Image.Resampling.LANCZOS)
            panel = Image.new("RGBA", (280, 340), (241, 245, 249, 255))
            panel.alpha_composite(image, ((280 - image.width) // 2, (340 - image.height) // 2))
            sheet.paste(panel.convert("RGB"), (left + 10, top))
            draw.text((left + 12, top + 346), record["id"], fill="#111827", font=_font(11))
            draw.text((left + 12, top + 366), record["category"], fill="#475569", font=_font(14))
        page_number = page_index // 12 + 1
        path = evidence / f"blind-label-sheet-{page_number}.png"
        sheet.save(path, "PNG", optimize=True)
        pages.append(str(path))
    manifest = {
        "kind": "AIR-05 blind manual attribute labelling manifest",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sampling": "first three records per category from the fixed-seed stratified embedding sample",
        "sample_count": len(selected), "per_category": args.per_category,
        "labels_requested": ["coarse_primary_colour", "colour_temperature", "single_colour_dominant"],
        "labels_not_requested": ["fit", "style", "material", "pattern", "custom_tags"],
        "reason": "The latter fields lack reliable ground truth and remain explicitly user-editable.",
        "review_sheets": pages,
        "records": [{key: record[key] for key in ("id", "category", "crop", "source_image", "source_label", "source_line")} for record in selected],
    }
    serialised = json.dumps(manifest, indent=2)
    (evidence / "label-manifest.json").write_text(serialised, encoding="utf-8")
    shutil.copyfile(evidence / "label-manifest.json", run_dir / "label-manifest.json")
    print(json.dumps({"sample_count": len(selected), "sheets": pages}, indent=2))


if __name__ == "__main__":
    main()
