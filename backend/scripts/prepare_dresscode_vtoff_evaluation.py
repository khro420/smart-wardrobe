"""Audit an officially obtained DressCode paired test set for VTOFF.

DressCode is access-controlled by its authors. This script deliberately does
not download, redistribute or train on it. The operator must obtain the dataset
under the official agreement, place it locally, and explicitly confirm that
condition before a manifest can be produced.
"""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from PIL import Image


BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
OFFICIAL_REPOSITORY = "https://github.com/aimagelab/dress-code"
OFFICIAL_LICENSE = "https://github.com/aimagelab/dress-code/blob/main/LICENCE"
GROUPS = ("upper_body", "lower_body", "dresses")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _persist(payload: dict) -> None:
    evidence = ROOT / "storage" / "verification" / "vtoff"
    run_dir = BACKEND / "runs" / "vtoff"
    evidence.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    serialised = json.dumps(payload, indent=2)
    (evidence / "dresscode_dataset_audit.json").write_text(serialised, encoding="utf-8")
    (run_dir / "dresscode_dataset_audit.json").write_text(serialised, encoding="utf-8")


def main() -> None:
    parser = ArgumentParser(description="Audit officially licensed DressCode paired test data.")
    parser.add_argument("--dataset-root", type=Path, default=BACKEND / "datasets" / "dresscode")
    parser.add_argument("--license-confirmed", action="store_true", help="Confirm the official DressCode agreement covers this local copy.")
    args = parser.parse_args()
    root = args.dataset_root.resolve()
    base = {
        "kind": "DressCode paired-test audit for category-wide VTOFF",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "official_repository": OFFICIAL_REPOSITORY,
        "official_license": OFFICIAL_LICENSE,
        "dataset_root": str(root),
        "license_confirmed_by_operator": bool(args.license_confirmed),
        "training_files_read": 0,
        "files_redistributed": 0,
    }
    if not root.is_dir() or not args.license_confirmed:
        missing = [] if root.is_dir() else [str(root)]
        reason = "Pass --license-confirmed only after obtaining DressCode under the authors' official agreement."
        if missing:
            reason = f"DressCode is not present at {root}; obtain it from the official authors first."
        payload = {**base, "status": "blocked", "missing": missing, "blocker": reason, "pairs": []}
        _persist(payload)
        raise RuntimeError(reason)

    pairs: list[dict] = []
    group_audits = {}
    seen_pair_ids: set[str] = set()
    for group in GROUPS:
        group_dir = root / group
        images_dir = group_dir / "images"
        pairs_file = group_dir / "test_pairs_paired.txt"
        missing = [str(path) for path in (group_dir, images_dir, pairs_file) if not path.exists()]
        if missing:
            payload = {**base, "status": "failed", "missing": missing, "pairs": []}
            _persist(payload)
            raise RuntimeError(f"DressCode {group} test structure is incomplete: {missing}")
        group_pairs = []
        for line_number, raw in enumerate(pairs_file.read_text(encoding="utf-8-sig").splitlines(), 1):
            fields = raw.split()
            if not fields:
                continue
            if len(fields) != 2:
                raise RuntimeError(f"Expected two filenames in {pairs_file}:{line_number}")
            person_name, product_name = fields
            if Path(person_name).name != person_name or Path(product_name).name != product_name:
                raise RuntimeError(f"Unsafe pair filename in {pairs_file}:{line_number}")
            person, product = images_dir / person_name, images_dir / product_name
            if not person.is_file() or not product.is_file() or person.resolve() == product.resolve():
                raise RuntimeError(f"Missing or invalid pair in {pairs_file}:{line_number}")
            for image_path in (person, product):
                with Image.open(image_path) as image:
                    image.verify()
            pair_id = f"{group}-{Path(person_name).stem}-{Path(product_name).stem}"
            if pair_id in seen_pair_ids:
                raise RuntimeError(f"Duplicate DressCode pair identifier: {pair_id}")
            seen_pair_ids.add(pair_id)
            record = {
                "id": pair_id,
                "garment_group": group,
                "person": str(person.resolve()),
                "product": str(product.resolve()),
                "pair_line": line_number,
            }
            group_pairs.append(record)
            pairs.append(record)
        if not group_pairs:
            raise RuntimeError(f"No paired test examples found for {group}.")
        group_audits[group] = {
            "pair_count": len(group_pairs),
            "pair_manifest": str(pairs_file.resolve()),
            "pair_manifest_sha256": _sha256(pairs_file),
        }

    payload = {
        **base,
        "status": "ok",
        "groups": group_audits,
        "paired_examples": len(pairs),
        "pairs": pairs,
        "limitations": "Only official paired test manifests were read. The audit does not establish permission beyond the operator's explicit confirmation.",
    }
    _persist(payload)
    print(json.dumps({"status": "ok", "paired_examples": len(pairs), "groups": group_audits}, indent=2))


if __name__ == "__main__":
    main()
