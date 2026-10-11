"""Prepare a local-only, leakage-safe DressCode fine-tuning manifest.

This script does not copy, alter, publish, or train on DressCode.  It records
only paths to authorised local assets and reserves every official paired-test
example for the final evaluation.  The resulting manifest is intentionally
written below ignored ``storage/`` rather than committed with the application.
"""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random


BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
GROUPS = ("upper_body", "lower_body", "dresses")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_pairs(path: Path) -> list[tuple[str, str]]:
    return [tuple(line.split()) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _label_map(group_root: Path, person_name: str) -> Path:
    # DressCode stores the parsing result for ``000000_0.jpg`` as
    # ``label_maps/000000_4.png``.  This is source data, not a generated label.
    prefix, _ = person_name.rsplit("_", 1)
    return group_root / "label_maps" / f"{prefix}_4.png"


def main() -> None:
    parser = ArgumentParser(description="Prepare a held-out DressCode fine-tuning manifest without touching source data.")
    parser.add_argument("--dataset-root", type=Path, default=BACKEND / "datasets" / "DressCode")
    parser.add_argument("--output", type=Path, default=PROJECT / "storage" / "verification" / "finetuning" / "dresscode_split_manifest.json")
    parser.add_argument("--validation-per-group", type=int, default=256)
    parser.add_argument("--seed", type=int, default=20261010)
    parser.add_argument("--license-confirmed", action="store_true", help="Record the operator's confirmation that their signed agreement permits this academic fine-tuning experiment.")
    args = parser.parse_args()
    if not args.license_confirmed:
        raise SystemExit("Refusing to prepare a training manifest without --license-confirmed.")
    if args.validation_per_group < 1:
        raise SystemExit("--validation-per-group must be positive.")

    root = args.dataset_root.resolve()
    groups: dict[str, dict] = {}
    split_records: dict[str, list[dict]] = {"train": [], "validation": []}
    all_test_paths: set[str] = set()
    issues: list[str] = []
    for group_index, group in enumerate(GROUPS):
        group_root = root / group
        train_manifest = group_root / "train_pairs.txt"
        test_manifest = group_root / "test_pairs_paired.txt"
        if not train_manifest.is_file() or not test_manifest.is_file():
            raise FileNotFoundError(f"Missing pair manifest for {group}: {group_root}")
        test_pairs = _read_pairs(test_manifest)
        all_test_paths.update(name for pair in test_pairs for name in pair)
        records = []
        for person_name, garment_name in _read_pairs(train_manifest):
            person = group_root / "images" / person_name
            garment = group_root / "images" / garment_name
            label_map = _label_map(group_root, person_name)
            if not person.is_file() or not garment.is_file() or not label_map.is_file():
                issues.append(f"{group}: missing person, garment, or label map for {person_name} {garment_name}")
                continue
            if person_name in all_test_paths or garment_name in all_test_paths:
                issues.append(f"{group}: official test image appears in train pair {person_name} {garment_name}")
                continue
            records.append({"id": f"{group}-{person.stem}-{garment.stem}", "garment_group": group, "person": str(person), "garment": str(garment), "label_map": str(label_map)})
        if len(records) <= args.validation_per_group:
            raise RuntimeError(f"{group} has only {len(records)} eligible train pairs.")
        validation_ids = {row["id"] for row in random.Random(args.seed + group_index).sample(records, args.validation_per_group)}
        train = [row for row in records if row["id"] not in validation_ids]
        validation = [row for row in records if row["id"] in validation_ids]
        split_records["train"].extend(train)
        split_records["validation"].extend(validation)
        groups[group] = {"train_pairs_manifest": str(train_manifest), "train_pairs_manifest_sha256": _sha256(train_manifest), "paired_test_manifest": str(test_manifest), "paired_test_manifest_sha256": _sha256(test_manifest), "eligible_pairs": len(records), "train_count": len(train), "validation_count": len(validation)}

    train_ids = {row["id"] for row in split_records["train"]}
    validation_ids = {row["id"] for row in split_records["validation"]}
    result = {"kind": "Local-only DressCode fine-tuning split manifest", "created_at": datetime.now(timezone.utc).isoformat(), "status": "ok" if not issues and not train_ids & validation_ids else "failed", "dataset_root": str(root), "operator_license_confirmed_for_academic_finetuning": True, "training_files_copied": 0, "test_examples_used_for_training": 0, "split_seed": args.seed, "groups": groups, "counts": {"train": len(split_records["train"]), "validation": len(split_records["validation"]), "official_paired_test": len(all_test_paths) // 2}, "overlap": {"train_validation_ids": len(train_ids & validation_ids)}, "records": split_records, "issues": issues, "limitations": ["The official paired test split is excluded from train and validation.", "This manifest supplies VTON supervision and parser-label supervision; it does not create ground-truth garment-removal targets for VTOFF.", "DressCode remains private, locally stored, and governed by the signed author agreement."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "counts": result["counts"], "issues": len(issues), "output": str(args.output)}, indent=2))
    if result["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
