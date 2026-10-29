"""All populated examples here are SYNTHETIC, never human review evidence."""
from dataclasses import asdict, replace
import copy
import hashlib
import json
from pathlib import Path
import pytest

from scripts.compatibility_evidence_dataset import validate, import_bundle, quality_report, load_json, write_new
from scripts.audit_compatibility_coverage import scan, synthetic_wardrobe, baseline
from app.application.recommendation.compatibility_reference_policy import CompatibilityReferencePolicy
from app.application.recommendation.compatibility_evidence_mapper import CompatibilityEvidenceMapper
from app.domain.value_objects.outfit_candidate import OutfitCandidate, CandidateMember


def dataset():
    return {"schema_version": "compatibility-evidence-1.0.0", "dataset_version": "synthetic-tests-1", "kind": "synthetic_fixture", "validation_locked": True, "records": []}


def example(name="synthetic-reference", partition="reference", rating=0, colour="blue"):
    row = synthetic_wardrobe(10)[0][8]  # one actual dress, not a duplicated pair
    row = replace(row, garment_id=name, primary_colour=colour)
    policy = CompatibilityReferencePolicy.load()
    outfit = OutfitCandidate((CandidateMember(row, "one_piece", 1),))
    sig = CompatibilityEvidenceMapper(policy).signature(outfit)[0]
    image = name + ".synthetic-no-image"
    return {"example_id": name, "partition": partition, "review_status": "reviewed", "approval_status": "approved",
        "independently_reviewed": False, "lookup_reference": partition == "reference", "source_ids": [name],
        "evidence_source": "synthetic test fixture; no real garment or reviewer", "captured_at": "2026-10-01T10:00:00Z",
        "images": [{"image_ref": image, "sha256": hashlib.sha256(name.encode()).hexdigest(), "garment_ids": [name]}],
        "garments": [{"role": "one_piece", "snapshot": json.loads(json.dumps(asdict(row)))}], "signature": sig.to_dict(),
        "reviews": [{"reviewer_id": "synthetic-a", "rating": rating, "reviewed_at": "2026-10-02T10:00:00Z", "image_refs": [image], "dataset_version": "synthetic-tests-1"},
                    {"reviewer_id": "synthetic-b", "rating": rating, "reviewed_at": "2026-10-02T10:00:00Z", "image_refs": [image], "dataset_version": "synthetic-tests-1"}],
        "adjudication": {"reviewer_id": "synthetic-adjudicator", "decision": "accepted", "note": "Synthetic arithmetic only", "reviewed_at": "2026-10-03T10:00:00Z"},
        "normalized_value": {"numerator": rating, "denominator": 4}}


def populated():
    raw = dataset(); raw["records"] = [example()]; return raw


def test_empty_real_collection_and_no_fabricated_quality():
    raw = dataset(); raw["kind"] = "human_review_collection"
    bundle = import_bundle(raw)
    assert bundle["policy"]["references"] == [] and bundle["activation_approved"] is False
    q = quality_report(raw)
    assert q["exact_agreement"] is None and q["held_out_compatibility_pair_order_agreement"] is None


def test_synthetic_requires_opt_in_and_cannot_claim_real_review():
    with pytest.raises(ValueError): validate(populated())
    raw = populated(); raw["records"][0]["independently_reviewed"] = True
    with pytest.raises(ValueError): validate(raw, True)


def test_import_preserves_exact_zero_provenance_and_no_activation():
    raw = populated(); bundle = import_bundle(raw, True)
    policy = CompatibilityReferencePolicy(bundle["policy"], True)
    assert next(iter(policy.approved.values())).value == 0
    assert bundle["dataset"]["records"][0]["reviews"][0]["reviewed_at"]
    assert bundle["policy"]["activation_approved"] is False
    assert quality_report(raw)["exact_agreement"] == 1
    sources = next(iter(policy.approved.values())).source_ids
    assert raw["records"][0]["source_ids"][0] in sources
    assert "group:"+raw["records"][0]["source_ids"][0] in sources


@pytest.mark.parametrize("mutate", [
    lambda r: r.update(extra="unsupported"),
    lambda r: r.update(partition="unknown"),
    lambda r: r.update(lookup_reference="true"),
    lambda r: r.update(independently_reviewed=1),
    lambda r: r["reviews"][0].update(rating=True),
    lambda r: r["reviews"][0].update(rating=5),
    lambda r: r["reviews"][0].update(reviewed_at="2026-10-02"),
    lambda r: r["reviews"][0].update(reviewed_at="2026-09-01T10:00:00Z"),
    lambda r: r["reviews"][0].update(dataset_version="wrong"),
    lambda r: r["reviews"][0].update(image_refs=["wrong-image"]),
    lambda r: r["reviews"][1].update(reviewer_id="synthetic-a"),
    lambda r: r["adjudication"].update(decision="pending"),
    lambda r: r["adjudication"].update(reviewed_at="2026-09-01T10:00:00Z"),
    lambda r: r["normalized_value"].update(numerator=1),
    lambda r: r["normalized_value"].update(denominator=0),
    lambda r: r["images"][0].update(sha256="missing"),
    lambda r: r["images"][0].update(garment_ids=["unrelated"]),
    lambda r: r["signature"].update(structure="top_bottom"),
    lambda r: r["signature"]["members"][0].update(colour="red"),
    lambda r: r["garments"][0].update(role="upper"),
    lambda r: r["garments"][0]["snapshot"].update(category="new-category"),
    lambda r: r["garments"][0]["snapshot"].update(primary_colour="#182a46"),
    lambda r: r["garments"][0]["snapshot"].update(style_tags=["unapproved"]),
    lambda r: r["garments"][0]["snapshot"].update(pattern="solid"),
])
def test_invalid_records_rejected(mutate):
    raw = populated(); mutate(raw["records"][0])
    with pytest.raises((ValueError, TypeError)): validate(raw, True)


def test_unknown_incomplete_and_unreviewed_are_not_zero():
    raw = populated(); r = raw["records"][0]
    r.update(review_status="unreviewed", approval_status="draft", lookup_reference=False,
             reviews=[], normalized_value=None, adjudication=None, signature=None)
    r["garments"][0]["snapshot"]["style_tags"] = None
    assert validate(raw, True) == raw
    assert import_bundle(raw, True)["policy"]["references"] == []
    r["approval_status"] = "approved"
    with pytest.raises(ValueError): validate(raw, True)


@pytest.mark.parametrize("overlap", ["source", "image", "garment"])
def test_partition_leakage_rejected_even_renamed_examples(overlap):
    raw = populated(); second = example("synthetic-held-out", "validation")
    first = raw["records"][0]
    if overlap == "source": second["source_ids"] = first["source_ids"]
    if overlap == "image": second["images"][0]["sha256"] = first["images"][0]["sha256"]
    if overlap == "garment":
        second["garments"][0]["snapshot"] = copy.deepcopy(first["garments"][0]["snapshot"])
        second["images"][0]["garment_ids"] = [first["example_id"]]
    raw["records"].append(second)
    with pytest.raises(ValueError, match="leakage"): validate(raw, True)


def test_seen_signature_new_garments_allowed_and_validation_never_imported():
    raw = populated(); raw["records"].append(example("synthetic-held-out", "validation", 1))
    bundle = import_bundle(raw, True)
    assert len(bundle["policy"]["references"]) == 1
    assert quality_report(raw)["shared_signature_consistency"][0]["rating_range_exact"] == "1/4"
    raw["records"][1]["lookup_reference"] = True
    with pytest.raises(ValueError): validate(raw, True)


def test_duplicate_reference_signature_requires_explicit_exemplar_selection():
    raw = populated(); raw["records"].append(example("synthetic-another-reference"))
    with pytest.raises(ValueError, match="exemplar"): validate(raw, True)
    raw["records"][1]["lookup_reference"] = False
    assert len(import_bundle(raw, True)["policy"]["references"]) == 1


def test_validation_lock_duplicate_ids_and_unknown_review():
    raw = populated(); raw["records"].append(example("synthetic-held-out", "validation")); raw["validation_locked"] = False
    with pytest.raises(ValueError, match="locked"): validate(raw, True)
    raw = populated(); raw["records"].append(copy.deepcopy(raw["records"][0]))
    with pytest.raises(ValueError, match="Duplicate"): validate(raw, True)
    raw = populated(); raw["records"][0]["reviews"] = []
    with pytest.raises(ValueError): validate(raw, True)


def test_coverage_all_structures_zero_unknown_different_garments_and_order():
    raw = populated(); p = CompatibilityReferencePolicy(import_bundle(raw, True)["policy"], True)
    rows, _ = synthetic_wardrobe(20)
    result = scan(rows, p, raw["records"])
    assert result["total_structural_candidates"] == 198
    assert all(result["by_structure"][s]["candidates"] for s in result["by_structure"])
    assert result["by_structure"]["dress"]["covered"] == 2
    assert result["by_structure"]["dress"]["reviewed_zero"] == 2
    assert result["by_structure"]["dress"]["seen_signature_different_garments"] == 2
    assert not result["hypothetical_whole_session_gate_permits"]
    assert scan(tuple(reversed(rows)), p)["by_structure"] == result["by_structure"]
    assert baseline(rows)[0] == result["total_structural_candidates"]
    unknown = scan((replace(rows[0], primary_colour=None), rows[8]), p)
    assert unknown["by_structure"]["top_bottom"]["incomplete_evidence"] == 1


def test_200_shape_is_not_maximum_and_no_candidate_truncation():
    _, (t,b,d,o) = synthetic_wardrobe(200)
    _, (t2,b2,d2,o2) = synthetic_wardrobe(200, heavy=True)
    assert (t*b+d)*(1+o) == 134820
    assert (t2*b2+d2)*(1+o2) == 300763


def test_duplicate_json_and_safe_output(tmp_path):
    source = tmp_path / "bad.json"; source.write_text('{"a":1,"a":2}')
    with pytest.raises(ValueError): load_json(source)
    with pytest.raises(ValueError): write_new(source, {}, (source,))
    with pytest.raises(ValueError): write_new(Path(__file__).parents[1]/"app"/"forbidden.json", {})
    destination = tmp_path/"new.json"; write_new(destination, {})
    with pytest.raises(FileExistsError): write_new(destination, {})


def test_json_schema_and_runtime_accept_valid_fixture():
    import jsonschema
    schema = load_json(Path(__file__).parents[2]/"docs/datasets/compatibility_reviews.schema.v1.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(populated(), schema, format_checker=jsonschema.FormatChecker())
    validate(populated(), True)


def test_collection_all_four_structures_reuses_actual_production_signatures():
    from app.application.recommendation.recommendation_engine import RecommendationEngine
    from scripts.audit_compatibility_coverage import OfflineQuery
    rows = synthetic_wardrobe(10)[0]
    # One garment per role, each reused across appropriate reference structures.
    rows = (rows[0], rows[4], rows[8], rows[9])
    p = CompatibilityReferencePolicy.load(); mapper = CompatibilityEvidenceMapper(p)
    raw = dataset()
    with RecommendationEngine(OfflineQuery(rows)).generate_homepage_candidates("synthetic-owner") as session:
        for index, outfit in enumerate(session):
            record = example("synthetic-structure-"+str(index))
            image = record["images"][0]
            image["garment_ids"] = [x.garment.garment_id for x in outfit.members]
            record["garments"] = [{"role": x.role, "snapshot": json.loads(json.dumps(asdict(x.garment)))} for x in outfit.members]
            record["signature"] = mapper.signature(outfit)[0].to_dict()
            raw["records"].append(record)
        assert session.result.complete
    validate(raw, True)
    imported = CompatibilityReferencePolicy(import_bundle(raw, True)["policy"], True)
    coverage = scan(rows, imported, raw["records"])
    assert coverage["total_structural_candidates"] == 4
    assert coverage["hypothetical_whole_session_gate_permits"]
    assert all(x["covered"] == 1 for x in coverage["by_structure"].values())
    assert all(x["same_reference_garments"] == 1 for x in coverage["by_structure"].values())


@pytest.mark.parametrize("field,value", [("primary_colour", None), ("primary_colour", "#xyz"), ("pattern", None), ("style_tags", None)])
def test_missing_evidence_counts_unknown_not_reviewed_zero(field, value):
    rows = (replace(synthetic_wardrobe(10)[0][8], **{field:value}),)
    result = scan(rows, CompatibilityReferencePolicy.load())
    counts = result["by_structure"]["dress"]
    assert counts["candidates"] == counts["incomplete_evidence"] == 1
    assert counts["reviewed_zero"] == counts["covered"] == 0
    assert counts["unique_complete_signatures"] == 0
    assert counts["coverage_fraction"] == 0


def test_unavailable_policy_not_missing_reference_and_no_false_session_success(monkeypatch):
    from scripts import audit_compatibility_coverage as tool
    raw = import_bundle(populated(), True)["policy"]; raw["available"] = False
    p = CompatibilityReferencePolicy(raw, True)
    rows = (synthetic_wardrobe(10)[0][8],)
    result = scan(rows, p)
    assert result["by_structure"]["dress"]["unavailable_policy"] == 1
    assert not result["hypothetical_whole_session_gate_permits"]
    class Broken:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def __iter__(self): raise RuntimeError("synthetic late failure")
    class Engine:
        def __init__(self, *args): pass
        def generate_homepage_candidates(self, *args): return Broken()
    monkeypatch.setattr(tool, "RecommendationEngine", Engine)
    with pytest.raises(RuntimeError, match="late failure"): scan(rows, p)


def test_heldout_order_agreement_is_measured_only_on_seen_signatures():
    raw = populated()
    second = example("synthetic-red-reference", rating=4, colour="red")
    raw["records"] += [second, example("synthetic-blue-heldout", "validation", 1),
                       example("synthetic-red-heldout", "validation", 3, "red"),
                       example("synthetic-green-heldout", "validation", 2, "green")]
    validate(raw, True)
    q = quality_report(raw)
    assert q["held_out_with_lookup"] == 2 and q["held_out_ordering_pairs"] == 1
    assert q["held_out_compatibility_pair_order_agreement"] == 1
    assert q["weight_sensitivity"] is None
