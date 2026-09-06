"""Safely extract and audit the paired VITON-HD test subset for VTOFF.

Only ``test/image`` and ``test/cloth`` are extracted. The duplicate/leaked test
filenames published by TryOffDiff are excluded before the paired manifest is
written. Training files are never extracted because this project is not retraining.
"""

from argparse import ArgumentParser
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import zipfile

from PIL import Image


BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
ARCHIVE_SIZE = 4_709_595_268
SOURCE_URL = "https://www.kaggle.com/api/v1/datasets/download/marquis03/high-resolution-viton-zalando-dataset"
EXCLUSION_SOURCE = "rizavelioglu/tryoffdiff references/vitonhd_duplicate_filenames.json"
EXCLUSION_SHA256 = "ff2032dae23fe68dd7c97034beea2c1d42fa98cf850a57c3e1f58a8208e1b17e"
EXCLUDED_TEST = {
    "02015_00.jpg", "09660_00.jpg", "14196_00.jpg", "11934_00.jpg", "07980_00.jpg", "14471_00.jpg",
    "07309_00.jpg", "03527_00.jpg", "12178_00.jpg", "11675_00.jpg", "01261_00.jpg", "13105_00.jpg",
    "11921_00.jpg", "11504_00.jpg", "03696_00.jpg", "02771_00.jpg", "10665_00.jpg", "13102_00.jpg",
    "02770_00.jpg", "08989_00.jpg", "02245_00.jpg", "07726_00.jpg", "11676_00.jpg", "04452_00.jpg",
    "11606_00.jpg", "12181_00.jpg", "08735_00.jpg", "01260_00.jpg", "01008_00.jpg", "09493_00.jpg",
    "14112_00.jpg", "07977_00.jpg", "03444_00.jpg", "12598_00.jpg", "09744_00.jpg", "07560_00.jpg",
    "11085_00.jpg", "14041_00.jpg", "07475_00.jpg", "10330_00.jpg", "06132_00.jpg", "09996_00.jpg",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_metadata(payload: bytes) -> tuple[int, int, str]:
    with Image.open(BytesIO(payload)) as image:
        image.verify()
        return image.width, image.height, image.format or "unknown"


def main() -> None:
    parser = ArgumentParser(description="Extract and audit paired VITON-HD VTOFF test data.")
    parser.add_argument("--archive", type=Path, default=BACKEND / "datasets" / "vitonhd" / "zalando-hd-resized.zip")
    parser.add_argument("--output", type=Path, default=BACKEND / "datasets" / "vitonhd" / "paired_test")
    args = parser.parse_args()
    archive, output = args.archive.resolve(), args.output.resolve()
    if not archive.exists() or archive.stat().st_size != ARCHIVE_SIZE:
        raise RuntimeError(f"Expected complete {ARCHIVE_SIZE}-byte VITON-HD archive at {archive}")
    image_dir, cloth_dir = output / "image", output / "cloth"
    image_dir.mkdir(parents=True, exist_ok=True)
    cloth_dir.mkdir(parents=True, exist_ok=True)

    extracted: dict[str, set[str]] = {"image": set(), "cloth": set()}
    unsafe_names: list[str] = []
    with zipfile.ZipFile(archive) as bundle:
        bad_member = bundle.testzip()
        if bad_member:
            raise RuntimeError(f"Archive CRC check failed at {bad_member}")
        for member in bundle.infolist():
            pure = PurePosixPath(member.filename)
            if pure.is_absolute() or ".." in pure.parts:
                unsafe_names.append(member.filename)
                continue
            parts = pure.parts
            if len(parts) < 3 or tuple(parts[-3:-1]) not in {("test", "image"), ("test", "cloth")}:
                continue
            folder, filename = parts[-2], parts[-1]
            if not filename.lower().endswith((".jpg", ".jpeg", ".png")) or filename in EXCLUDED_TEST:
                continue
            payload = bundle.read(member)
            image_metadata(payload)
            target = (image_dir if folder == "image" else cloth_dir) / filename
            target.write_bytes(payload)
            extracted[folder].add(filename)
    if unsafe_names:
        raise RuntimeError(f"Archive contains unsafe paths: {unsafe_names[:3]}")

    paired = sorted(extracted["image"] & extracted["cloth"])
    image_only = sorted(extracted["image"] - extracted["cloth"])
    cloth_only = sorted(extracted["cloth"] - extracted["image"])
    if not paired or image_only or cloth_only:
        raise RuntimeError(f"Paired audit failed: pairs={len(paired)}, image_only={len(image_only)}, cloth_only={len(cloth_only)}")

    audit = {
        "kind": "cleaned paired VITON-HD test audit for VTOFF",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_url": SOURCE_URL,
        "archive": {"path": str(archive), "size_bytes": archive.stat().st_size, "sha256": sha256(archive)},
        "exclusions": {"source": EXCLUSION_SOURCE, "sha256": EXCLUSION_SHA256, "count": len(EXCLUDED_TEST)},
        "extracted_folders": ["test/image", "test/cloth"],
        "training_files_extracted": 0,
        "person_images": len(extracted["image"]), "product_images": len(extracted["cloth"]),
        "paired_examples": len(paired), "unpaired_examples": 0,
        "pairs": [{"id": Path(name).stem, "person": str(image_dir / name), "product": str(cloth_dir / name)} for name in paired],
    }
    evidence = PROJECT / "storage" / "verification" / "vtoff"
    run_dir = BACKEND / "runs" / "vtoff"
    evidence.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(audit, indent=2)
    (evidence / "paired_dataset_audit.json").write_text(encoded, encoding="utf-8")
    shutil.copyfile(evidence / "paired_dataset_audit.json", run_dir / "paired_dataset_audit.json")
    print(json.dumps({key: audit[key] for key in ("person_images", "product_images", "paired_examples", "unpaired_examples")}, indent=2))


if __name__ == "__main__":
    main()
