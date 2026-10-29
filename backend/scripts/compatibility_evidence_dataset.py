"""Offline human-review collection/import contract. Never changes live policy.

The validator verifies recorded declarations, not reviewer honesty or image truth.
Full snapshots permit reuse of the unchanged production signature implementation.
"""
import argparse
from datetime import datetime
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from app.application.recommendation.compatibility_reference_policy import CompatibilityReferencePolicy, DEFAULT_REFERENCES, artifact_hash
from app.application.recommendation.compatibility_evidence_mapper import CompatibilityEvidenceMapper
from app.domain.value_objects.outfit_candidate import OutfitCandidate, CandidateMember
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot

VERSION = "compatibility-evidence-1.0.0"


def fields(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected.split()):
        raise ValueError("Unexpected or missing fields: " + expected)


def text(value):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError("Nonblank trimmed text required.")
    return value


def timestamp(value):
    text(value)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("ISO-8601 timestamp required.") from exc
    if parsed.tzinfo is None:
        raise ValueError("Timezone-aware timestamp required.")
    return parsed


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON number")))


def candidate(record):
    members = []
    for index, member in enumerate(record["garments"], 1):
        fields(member, "role snapshot")
        members.append(CandidateMember(ConfirmedGarmentSnapshot(**member["snapshot"]), member["role"], index))
    return OutfitCandidate(tuple(members))


def source_tokens(record):
    # Namespace-separated and global garment IDs/pseudonyms: collectors must use
    # stable IDs across partitions. Content hashes catch renamed image references.
    return ({"group:" + x for x in record["source_ids"]}
            | {"garment:" + x["snapshot"]["garment_id"] for x in record["garments"]}
            | {"image:" + x["sha256"] for x in record["images"]})


def validate(raw, allow_synthetic=False):
    fields(raw, "schema_version dataset_version kind validation_locked records")
    if raw["schema_version"] != VERSION or raw["kind"] not in ("human_review_collection", "synthetic_fixture"):
        raise ValueError("Unsupported dataset contract.")
    text(raw["dataset_version"])
    synthetic = raw["kind"] == "synthetic_fixture"
    if synthetic and not allow_synthetic:
        raise ValueError("Synthetic data requires explicit fixture opt-in.")
    if type(raw["validation_locked"]) is not bool or not isinstance(raw["records"], list):
        raise ValueError("Explicit validation lock and records required.")
    policy = CompatibilityReferencePolicy.load()
    mapper = CompatibilityEvidenceMapper(policy)
    ids, sources, garment_versions, selections = set(), {}, {}, set()
    for record in raw["records"]:
        fields(record, "example_id partition review_status approval_status independently_reviewed lookup_reference source_ids evidence_source captured_at images garments signature reviews adjudication normalized_value")
        identifier = text(record["example_id"])
        if identifier in ids:
            raise ValueError("Duplicate example ID.")
        ids.add(identifier)
        if record["partition"] not in ("reference", "development", "validation"):
            raise ValueError("Unsupported dataset partition.")
        if record["partition"] == "validation" and not raw["validation_locked"]:
            raise ValueError("Validation partition must be locked before evaluation.")
        if record["review_status"] not in ("unreviewed", "reviewed") or record["approval_status"] not in ("draft", "approved", "rejected"):
            raise ValueError("Unsupported review/approval status.")
        if type(record["lookup_reference"]) is not bool or type(record["independently_reviewed"]) is not bool:
            raise ValueError("Review declarations must be booleans.")
        if synthetic and record["independently_reviewed"]:
            raise ValueError("Synthetic data cannot claim independent human review.")
        text(record["evidence_source"])
        captured = timestamp(record["captured_at"])
        if not isinstance(record["source_ids"], list) or not record["source_ids"] or len(set(map(text, record["source_ids"]))) != len(record["source_ids"]):
            raise ValueError("Unique stable source groups required.")
        if not isinstance(record["garments"], list) or not record["garments"]:
            raise ValueError("Actual garment snapshots required.")
        outfit = candidate(record)
        signature, *_ = mapper.signature(outfit)
        expected = policy.parse_signature(record["signature"]) if record["signature"] is not None else None
        if signature != expected or (expected is not None and expected.to_dict() != record["signature"]):
            raise ValueError("Signature must exactly match canonical snapshot evidence; incomplete evidence uses null.")
        if not isinstance(record["images"], list) or not record["images"]:
            raise ValueError("Reviewed image references required.")
        image_ids = set()
        for image in record["images"]:
            fields(image, "image_ref sha256 garment_ids")
            if text(image["image_ref"]) in image_ids:
                raise ValueError("Duplicate image reference.")
            image_ids.add(image["image_ref"])
            if not isinstance(image["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", image["sha256"]):
                raise ValueError("Image SHA-256 required.")
            if not isinstance(image["garment_ids"], list) or not image["garment_ids"] or len(set(image["garment_ids"])) != len(image["garment_ids"]) or not set(image["garment_ids"]) <= {x.garment.garment_id for x in outfit.members}:
                raise ValueError("Image must reference actual unique garment IDs.")
        if {g for image in record["images"] for g in image["garment_ids"]} != {x.garment.garment_id for x in outfit.members}:
            raise ValueError("Image evidence must cover every garment.")
        for member in record["garments"]:
            snap = member["snapshot"]
            key, digest = snap["garment_id"], artifact_hash(snap)
            if key in garment_versions and garment_versions[key] != digest:
                raise ValueError("Conflicting snapshots for the same stable garment ID.")
            garment_versions[key] = digest
        for token in source_tokens(record):
            if token in sources and sources[token] != record["partition"]:
                raise ValueError("Garment/image/source leakage across partitions.")
            sources[token] = record["partition"]
        reviews, reviewers = record["reviews"], set()
        if not isinstance(reviews, list):
            raise ValueError("Review list required.")
        latest = captured
        for review in reviews:
            fields(review, "reviewer_id rating reviewed_at image_refs dataset_version")
            rid = text(review["reviewer_id"])
            if rid in reviewers or type(review["rating"]) is not int or not 0 <= review["rating"] <= 4:
                raise ValueError("Distinct reviewers and integer 0-4 ratings required.")
            reviewers.add(rid)
            reviewed_at = timestamp(review["reviewed_at"])
            if reviewed_at < captured or review["dataset_version"] != raw["dataset_version"] or not isinstance(review["image_refs"], list) or len(review["image_refs"]) != len(set(review["image_refs"])) or set(review["image_refs"]) != image_ids:
                raise ValueError("Review must identify the dataset and all actual reviewed images after capture.")
            latest = max(latest, reviewed_at)
        value = record["normalized_value"]
        if record["review_status"] == "unreviewed":
            if reviews or value is not None or record["adjudication"] is not None or record["approval_status"] != "draft" or record["independently_reviewed"]:
                raise ValueError("Unreviewed examples cannot claim ratings or approval.")
        else:
            if not reviews:
                raise ValueError("Reviewed examples require actual review declarations.")
            fields(value, "numerator denominator")
            if any(type(value[x]) is not int for x in value) or value["denominator"] <= 0 or Fraction(value["numerator"], value["denominator"]) != Fraction(sum(x["rating"] for x in reviews), 4 * len(reviews)):
                raise ValueError("Incorrect normalized review value.")
        adjudication = record["adjudication"]
        if adjudication is not None:
            fields(adjudication, "reviewer_id decision note reviewed_at")
            text(adjudication["reviewer_id"]); text(adjudication["note"])
            if adjudication["decision"] not in ("accepted", "pending", "rejected") or timestamp(adjudication["reviewed_at"]) < latest:
                raise ValueError("Invalid adjudication chronology/decision.")
        if record["approval_status"] == "approved":
            if record["review_status"] != "reviewed" or len(reviewers) < 2 or adjudication is None or adjudication["decision"] != "accepted" or (not synthetic and not record["independently_reviewed"]):
                raise ValueError("Approval requires independent reviews and accepted adjudication.")
        if record["lookup_reference"]:
            if record["partition"] != "reference" or record["approval_status"] != "approved" or signature is None:
                raise ValueError("Only approved complete reference-partition examples can enter lookup.")
            if signature.key in selections:
                raise ValueError("Select exactly one explicitly adjudicated exemplar per signature.")
            selections.add(signature.key)
    return raw


def import_bundle(raw, allow_synthetic=False):
    validate(raw, allow_synthetic)
    policy_raw = load_json(DEFAULT_REFERENCES)
    policy_raw.update(version="isolated-" + raw["dataset_version"],
                      kind="synthetic_fixture" if raw["kind"] == "synthetic_fixture" else "reviewed_reference_policy", references=[])
    # Reserve all nonvalidation source tokens, including unselected examples, so
    # subsequent evaluation cannot hide development/reference source reuse.
    all_sources = sorted({token for r in raw["records"] if r["partition"] != "validation"
                          for token in (source_tokens(r) | set(r["source_ids"])
                                        | {x["snapshot"]["garment_id"] for x in r["garments"]}
                                        | {x["sha256"] for x in r["images"]})})
    for record in sorted(raw["records"], key=lambda r: r["example_id"]):
        if record["lookup_reference"]:
            policy_raw["references"].append({
                "reference_id": record["example_id"], "signature": record["signature"],
                "ratings": [{"reviewer_id": x["reviewer_id"], "rating": x["rating"]} for x in record["reviews"]],
                "adjudication": {k: record["adjudication"][k] for k in ("reviewer_id", "decision", "note")},
                "source_ids": all_sources, "approval_status": "approved",
                "independently_reviewed": record["independently_reviewed"], "normalized_value": record["normalized_value"],
            })
    policy = CompatibilityReferencePolicy(policy_raw, allow_synthetic)
    return {"schema_version": VERSION, "dataset_hash": artifact_hash(raw), "policy_hash": policy.hash,
            "activation_approved": False, "dataset": raw, "policy": policy_raw}


def quality_report(raw):
    """Descriptive ordinal agreement only, not general fashion accuracy."""
    from itertools import combinations
    reviews = [r for r in raw["records"] if r["review_status"] == "reviewed"]
    differences = [abs(a["rating"] - b["rating"]) for r in reviews for a, b in combinations(r["reviews"], 2)]
    signatures = {}
    for r in reviews:
        if r["signature"] is not None:
            signatures.setdefault(artifact_hash(r["signature"]), []).append(r)
    repeated = []
    for rows in signatures.values():
        if len(rows) > 1:
            values = [Fraction(r["normalized_value"]["numerator"], r["normalized_value"]["denominator"]) for r in rows]
            repeated.append({"example_ids": sorted(r["example_id"] for r in rows), "rating_range_exact": str(max(values)-min(values))})
    held_out = [r for r in reviews if r["partition"] == "validation"]
    lookup = {artifact_hash(r["signature"]): Fraction(r["normalized_value"]["numerator"], r["normalized_value"]["denominator"])
              for r in reviews if r["lookup_reference"]}
    measured = [(r, lookup[artifact_hash(r["signature"])] ) for r in held_out
                if r["signature"] is not None and artifact_hash(r["signature"]) in lookup]
    agreements = []
    for (a, predicted_a), (b, predicted_b) in combinations(measured, 2):
        actual_a = Fraction(a["normalized_value"]["numerator"], a["normalized_value"]["denominator"])
        actual_b = Fraction(b["normalized_value"]["numerator"], b["normalized_value"]["denominator"])
        sign = lambda x: (x > 0) - (x < 0)
        agreements.append(sign(predicted_a-predicted_b) == sign(actual_a-actual_b))
    from app.domain.value_objects.compatibility_signature import STRUCTURES
    return {"evidence_kind": raw["kind"], "reviewed_examples": len(reviews), "reviewer_pairs": len(differences),
            "exact_agreement": sum(x == 0 for x in differences)/len(differences) if differences else None,
            "mean_absolute_rating_difference": sum(differences)/len(differences) if differences else None,
            "shared_signature_consistency": repeated, "held_out_reviewed_examples": len(held_out),
            "held_out_with_lookup": len(measured), "held_out_ordering_pairs": len(agreements),
            "held_out_compatibility_pair_order_agreement": sum(agreements)/len(agreements) if agreements else None,
            "reviewed_by_structure": {s: sum(r["signature"] is not None and r["signature"]["structure"] == s for r in reviews) for s in STRUCTURES},
            "cross_structure_score_validity": None, "weight_sensitivity": None,
            "limitations": ["Descriptive pair agreement is not chance-corrected reliability.",
                            "Ranking, structure comparability and weight sensitivity require separately reviewed ranking sessions.",
                            "Provenance declarations cannot prove reviewer independence or source authenticity."]}


def write_new(path, value, inputs=()):
    path = Path(path).resolve()
    repo = BACKEND.parent
    if path in {Path(x).resolve() for x in inputs} or any(path.is_relative_to(root) for root in (BACKEND / "app", repo / "frontend", BACKEND / "tests")):
        raise ValueError("Output cannot overwrite inputs or application/test trees.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="New isolated bundle; never production config")
    parser.add_argument("--allow-synthetic-fixtures", action="store_true")
    args = parser.parse_args()
    try:
        raw = load_json(args.dataset)
        bundle = import_bundle(raw, args.allow_synthetic_fixtures)
        bundle["quality"] = quality_report(raw)
        write_new(args.output, bundle, (args.dataset,))
        print(json.dumps({"approved_reference_count": len(bundle["policy"]["references"]), "dataset_hash": bundle["dataset_hash"], "activation_approved": False}))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
