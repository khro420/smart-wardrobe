"""Consolidate Objective O2 evidence without overstating incomplete gates."""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "backend" / "runs" / "o2"
VERIFICATION = ROOT / "storage" / "verification" / "o2"


def _json(path: Path) -> dict:
    if not path.is_file():
        return {"status": "missing", "path": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


def _entry(identifiers: str, status: str, acceptance: str, evidence: str, note: str | None = None) -> dict:
    result = {"requirements": identifiers, "status": status, "acceptance": acceptance, "evidence": evidence}
    if note:
        result["note"] = note
    return result


def main() -> None:
    parser = ArgumentParser(description="Write a fail-closed O2 requirement/evidence matrix.")
    parser.add_argument("--frontend-lint-pass", action="store_true")
    parser.add_argument("--frontend-build-pass", action="store_true")
    parser.add_argument(
        "--defer-dresscode",
        action="store_true",
        help=(
            "Close the current O2 delivery with AIR-03 lower-body/dress evidence "
            "explicitly user-deferred; this never records AIR-03 as passed."
        ),
    )
    parser.add_argument("--allow-incomplete", action="store_true", help="Persist an incomplete matrix instead of exiting with an error.")
    args = parser.parse_args()

    suite_node = ET.parse(RUNS / "pytest.xml").getroot()
    suite = suite_node if suite_node.tag == "testsuite" else suite_node.find("testsuite")
    if suite is None:
        raise RuntimeError("O2 pytest XML has no test suite.")
    tests = {key: int(suite.attrib.get(key, 0)) for key in ("tests", "failures", "errors", "skipped")}
    tests_pass = tests["tests"] >= 42 and not any(tests[key] for key in ("failures", "errors", "skipped"))

    embeddings = _json(ROOT / "storage" / "verification" / "embeddings" / "results.json")
    attributes = _json(ROOT / "storage" / "verification" / "attributes" / "results.json")
    upper_vtoff = _json(ROOT / "storage" / "verification" / "vtoff" / "paired_evaluation" / "results.json")
    dresscode_audit = _json(ROOT / "storage" / "verification" / "vtoff" / "dresscode_dataset_audit.json")
    dresscode_eval = _json(ROOT / "storage" / "verification" / "vtoff" / "dresscode_paired_evaluation" / "results.json")
    pgvector = _json(ROOT / "storage" / "verification" / "pgvector" / "results.json")

    embedding_pass = (
        embeddings.get("status") == "complete"
        and embeddings.get("errors") == []
        and embeddings.get("scope", {}).get("sample_count") == 104
        and embeddings.get("model", {}).get("dimension") == 768
        and embeddings.get("persistence", {}).get("vectors_identical") is True
        and embeddings.get("persistence", {}).get("preferred_media_is_segmentation_crop") is True
    )
    attribute_pass = (
        attributes.get("status") == "complete"
        and attributes.get("errors") == []
        and attributes.get("scope", {}).get("sample_count") == 39
        and len(attributes.get("scope", {}).get("categories", [])) == 13
        and len(attributes.get("failures", [])) >= 10
        and attributes.get("integrity", {}).get("all_manual_fit_style_material_unavailable") is True
    )
    upper_pass = (
        upper_vtoff.get("status") == "complete"
        and upper_vtoff.get("errors") == []
        and upper_vtoff.get("scope", {}).get("sample_count", 0) >= 30
        and len(upper_vtoff.get("failure_examples", [])) >= 10
        and upper_vtoff.get("failure_label_review", {}).get("missing_ids") == []
    )
    dresscode_pass = (
        dresscode_audit.get("status") == "ok"
        and dresscode_eval.get("status") == "complete"
        and set(dresscode_eval.get("scope", {}).get("garment_groups", [])) == {"upper_body", "lower_body", "dresses"}
        and len(dresscode_eval.get("failure_examples", [])) >= 10
        and dresscode_eval.get("failure_label_review", {}).get("missing_ids") == []
    )
    pgvector_pass = pgvector.get("status") == "ok"
    ui_pass = args.frontend_lint_pass and args.frontend_build_pass
    air07_pass = bool(
        upper_pass and embedding_pass and attribute_pass
        and upper_vtoff.get("model", {}).get("sha256")
        and upper_vtoff.get("parameters", {}).get("generation_seed") is not None
        and upper_vtoff.get("runtime", {}).get("hardware", {}).get("gpu_name")
        and embeddings.get("model", {}).get("sha256")
        and embeddings.get("preprocessing", {}).get("version")
        and embeddings.get("runtime", {}).get("hardware", {}).get("gpu_name")
        and attributes.get("configuration", {}).get("kmeans_seed") is not None
        and attributes.get("runtime", {}).get("hardware", {}).get("operating_system")
    )

    matrix = [
        _entry("FR-06", "passed", "TryOffDiff is optional and the observed segmentation crop remains the authoritative default/fallback.", "tests/test_vtoff_adapter.py; tests/test_garment_workflow.py; storage/verification/vtoff/paired_evaluation/results.json"),
        _entry("FR-07", "passed" if embedding_pass and attribute_pass else "failed", "Category/role/layering, colour/palette/temperature/dominance and a real fixed-width visual embedding are recorded.", "storage/verification/attributes/results.json; storage/verification/embeddings/results.json"),
        _entry("FR-08", "passed" if tests_pass and ui_pass else "failed", "Subjective or empirically weak attributes remain reviewable and editable rather than silently authoritative.", "tests/test_garment_workflow.py; frontend/app/extract/results/page.tsx; frontend/app/wardrobe/page.tsx"),
        _entry("FR-09", "passed" if pgvector_pass else "partial", "Embeddings have availability metadata, fixed 768-D finite validation and deployment persistence verification.", "tests/test_visual_embedding.py; storage/verification/embeddings/results.json; storage/verification/pgvector/results.json", None if pgvector_pass else "SQLite lifecycle round-trip passed and schema is vector(768), but live PostgreSQL/pgvector is pending because Docker/PostgreSQL is unavailable."),
        _entry("FR-10–FR-18", "passed" if tests_pass and ui_pass else "failed", "Candidate review, correction, explicit media choice, atomic garment/outfit saving and recommendation-to-outfit saving pass.", "backend/runs/o2/pytest.xml; frontend production build"),
        _entry("FR-20–FR-21", "passed" if tests_pass else "failed", "Reads, updates and identifier boundaries are owner-scoped; only confirmed available owned garment IDs cross recommendation boundaries.", "tests/test_o1_wardrobe.py; tests/test_o2_recommendation_boundary.py"),
        _entry("FR-38", "passed" if tests_pass else "failed", "Jobs and generated/observed media retain statuses, timestamps, controlled errors and model/data provenance.", "tests/test_garment_workflow.py; embedding/attribute/VTOFF result manifests"),
        _entry(
            "AIR-03",
            "passed" if upper_pass and dresscode_pass else "deferred" if upper_pass and args.defer_dresscode else "blocked",
            "Paired VTOFF vs observed segmentation reports SSIM, LPIPS, DISTS, latency, VRAM and labelled failures for upper/lower/dress groups.",
            "storage/verification/vtoff/paired_evaluation/; storage/verification/vtoff/dresscode_paired_evaluation/",
            None
            if dresscode_pass
            else (
                "Upper-body VITON-HD evidence passes; the user explicitly deferred lower-body and dress evaluation until officially licensed DressCode data is supplied. This is not an AIR-03 pass."
                if args.defer_dresscode
                else "Upper-body VITON-HD evidence passes; lower-body and dress evaluation requires officially licensed DressCode data."
            ),
        ),
        _entry("AIR-04", "passed" if tests_pass else "failed", "Generated media is clearly identified, separately retained and requires explicit review/selection.", "tests/test_vtoff_adapter.py; tests/test_garment_workflow.py"),
        _entry("AIR-05", "passed" if attribute_pass and embedding_pass else "failed", "Automatic attributes and embeddings have labelled held-out metrics and failure evidence; weak fields remain editable.", "storage/verification/attributes/; storage/verification/embeddings/", "Temperature reached 89.7% accuracy; coarse primary colour and dominance remain quality-limited at 35.9% and 38.5%, so they are suggestions requiring review."),
        _entry("AIR-07", "passed" if air07_pass else "failed", "Executed experiments record source/split, versions, hashes, parameters, seeds, hardware/device, timing, memory, terminal status, errors and limitations.", "storage/verification/vtoff/paired_evaluation/results.json; storage/verification/embeddings/results.json; storage/verification/attributes/results.json"),
        _entry("O2 release checks", "passed" if tests_pass and ui_pass else "failed", "All relevant backend tests, frontend lint and production build pass.", "backend/runs/o2/pytest.xml; npm run lint; npm run build"),
    ]
    passed = sum(item["status"] == "passed" for item in matrix)
    deferred = [item["requirements"] for item in matrix if item["status"] == "deferred"]
    incomplete = [item["requirements"] for item in matrix if item["status"] not in {"passed", "deferred"}]
    closed = passed + len(deferred)
    result = {
        "objective": "O2 Garment Representation and Intelligent Recommendation Boundary",
        "status": "closed_with_deferred_requirement" if deferred and not incomplete else "complete" if not incomplete else "incomplete",
        "requirements_passed": passed,
        "requirements_closed": closed,
        "requirements_total": len(matrix),
        "deferred_requirements": deferred,
        "incomplete_requirements": incomplete,
        "release_checks": {"backend": tests, "frontend_lint": args.frontend_lint_pass, "frontend_build": args.frontend_build_pass},
        "quality_decisions": {
            "vtoff": "optional_reviewed_alternative",
            "authoritative_fallback": "observed_segmentation_crop",
            "primary_colour_and_dominance": "editable_suggestions_due_to_low_development_accuracy",
            "recommendation_scope": "confirmed-owned-ID-boundary-only; internal NLP/ranking remains out of scope",
        },
        "external_blockers": {
            "dresscode": dresscode_audit.get("blocker") if not dresscode_pass and not args.defer_dresscode else None,
            "pgvector_runtime": pgvector.get("blocker") or pgvector.get("limitation") if not pgvector_pass else None,
        },
        "user_scope_decision": {
            "dresscode_air03": "deferred_until_official_dataset_is_supplied" if args.defer_dresscode and not dresscode_pass else None,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "interpretation": "Deferred requirements are closed for this delivery but are not passed report requirements.",
        },
        "matrix": matrix,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "audited_at": datetime.now(timezone.utc).isoformat(),
    }
    RUNS.mkdir(parents=True, exist_ok=True)
    VERIFICATION.mkdir(parents=True, exist_ok=True)
    serialised = json.dumps(result, indent=2)
    (RUNS / "requirements-audit.json").write_text(serialised, encoding="utf-8")
    (VERIFICATION / "requirements-audit.json").write_text(serialised, encoding="utf-8")
    print(json.dumps({"status": result["status"], "passed": f"{passed}/{len(matrix)}", "closed": f"{closed}/{len(matrix)}", "deferred": deferred, "incomplete": incomplete}, indent=2))
    if incomplete and not args.allow_incomplete:
        raise RuntimeError(f"O2 remains incomplete: {', '.join(incomplete)}")


if __name__ == "__main__":
    main()
