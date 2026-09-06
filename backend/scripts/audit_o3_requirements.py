"""Build a fail-closed O3 visualisation acceptance matrix from release evidence."""

from argparse import ArgumentParser
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "backend" / "runs" / "o3"
VERIFICATION = ROOT / "storage" / "verification" / "o3"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"status": "missing"}


def entry(identifier: str, status: str, acceptance: str, evidence: str, note: str | None = None) -> dict:
    value = {"requirements": identifier, "status": status, "acceptance": acceptance, "evidence": evidence}
    if note:
        value["note"] = note
    return value


def main() -> None:
    parser = ArgumentParser(description="Audit O3 without converting absent model or dataset evidence into passes.")
    parser.add_argument("--pytest-xml", type=Path, default=RUNS / "pytest.xml")
    parser.add_argument("--frontend-lint-pass", action="store_true")
    parser.add_argument("--frontend-build-pass", action="store_true")
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()

    suite = ET.parse(args.pytest_xml).getroot()
    if suite.tag != "testsuite":
        suite = suite.find("testsuite")
    if suite is None:
        raise RuntimeError("O3 pytest XML contains no test suite.")
    tests = {name: int(suite.attrib.get(name, 0)) for name in ("tests", "failures", "errors", "skipped")}
    tests_pass = tests["tests"] >= 4 and not any(tests[name] for name in ("failures", "errors", "skipped"))
    ui_pass = args.frontend_lint_pass and args.frontend_build_pass
    smoke = load_json(ROOT / "storage" / "verification" / "vton" / "smoke" / "results.json")
    paired = load_json(ROOT / "storage" / "verification" / "vton" / "dresscode_paired_evaluation" / "results.json")
    smoke_pass = smoke.get("status") == "complete" and not smoke.get("errors")
    paired_pass = (
        paired.get("status") == "complete" and not paired.get("errors")
        and set(paired.get("scope", {}).get("garment_groups", [])) == {"upper_body", "lower_body", "dresses"}
        and paired.get("scope", {}).get("per_group", 0) >= 10
        and all(paired.get("metrics", {}).get(name, {}).get("count", 0) >= 30 for name in ("ssim", "lpips", "dists"))
    )
    software_pass = tests_pass and ui_pass
    matrix = [
        entry("FR-18", "passed" if tests_pass else "failed", "Recommendations persist confirmed garment references and can be saved or supplied directly to visualisation.", "tests/test_workflow.py; tests/test_o2_recommendation_boundary.py"),
        entry("FR-25", "passed" if ui_pass and tests_pass else "failed", "Visualise actions exist for homepage recommendations, wardrobe outfits, assistant results and persisted recommendation history.", "frontend/app/page.tsx; frontend/app/wardrobe/page.tsx; frontend/app/history/page.tsx"),
        entry("FR-26", "passed" if tests_pass else "failed", "Unknown, duplicate, unavailable, unreviewed, foreign and unsupported garment references fail before request creation.", "tests/test_vton_contracts.py; app/application/visualisation/outfit_identifier_validator.py"),
        entry("FR-27", "passed" if tests_pass else "failed", "Personal-image listing is limited to available owner-scoped protected media.", "tests/test_vton_contracts.py; personal_image_service.py"),
        entry("FR-28", "passed" if ui_pass else "failed", "The user can select one authorised personal image.", "frontend/app/try-on/page.tsx"),
        entry("FR-29", "passed" if ui_pass and tests_pass else "failed", "The user can upload a JPEG or PNG personal image up to the documented limit.", "frontend/app/try-on/page.tsx; tests/test_vton_contracts.py"),
        entry("FR-30", "passed" if tests_pass else "failed", "Decoded format, byte size, resolution, ownership and model preprocessing are validated.", "protected_media_store.py; vton_preprocessing.py; tests/test_vton_contracts.py"),
        entry("FR-31", "passed" if tests_pass else "failed", "Personal photographs are private media and require owner-authorised retrieval.", "protected_media_store.py; tests/test_vton_contracts.py"),
        entry("FR-32", "passed" if smoke_pass and tests_pass else "blocked", "The exact protected personal and frozen garment media reach a real VTON adapter.", "storage/verification/vton/smoke/results.json; tests/test_vton_contracts.py", None if smoke_pass else "Run verify_vton_inference.py after installing the pinned assets."),
        entry("FR-33", "passed" if software_pass else "failed", "Queued, processing, completed, failed and cancelled states have visible UI states.", "frontend/app/try-on/result/page.tsx; tests/test_vton_contracts.py"),
        entry("FR-34", "passed" if tests_pass else "failed", "Only the owner can retrieve a completed output and incomplete requests return no output media.", "tests/test_vton_contracts.py; visualisation_result_service.py"),
        entry("FR-35", "passed" if ui_pass else "failed", "Every result is identified as AI-generated and disclaims physical-fit accuracy.", "frontend/app/try-on/result/page.tsx; visualisation_result_service.py"),
        entry("FR-36", "passed" if software_pass else "failed", "Retry creates a new request from persisted source and person identifiers.", "frontend/app/try-on/result/page.tsx; outfit_visualisation_service.py"),
        entry("FR-37", "passed" if tests_pass else "failed", "Invalid output and inference failures cannot produce a falsely completed record.", "vton_preprocessing.py; visualisation_result_service.py; tests/test_vton_contracts.py"),
        entry("FR-38", "passed" if tests_pass else "failed", "Requests retain source, person/media provenance, configuration, model, timestamps, metrics and controlled error fields.", "migrations/002_vton_runtime_metadata.sql; tests/test_vton_contracts.py"),
        entry("FR-39", "passed" if software_pass else "failed", "An unfinished visualisation can be cancelled without modifying wardrobe records.", "outfit_visualisation_service.py; frontend/app/try-on/result/page.tsx; tests/test_vton_contracts.py"),
        entry("AIR-06", "passed" if software_pass else "failed", "All defined entry points use validated garment IDs/reviewed media and show the physical-fit disclaimer.", "tests/test_vton_contracts.py; frontend/app/history/page.tsx; frontend/app/try-on/"),
        entry("AIR-07", "passed" if smoke_pass and paired_pass else "blocked", "VTON records model/version, config, processing time, hardware, status, errors and balanced category evidence.", "storage/verification/vton/smoke/results.json; storage/verification/vton/dresscode_paired_evaluation/results.json", None if paired_pass else ("Officially licensed balanced DressCode evaluation remains required." if smoke_pass else "Real smoke inference and officially licensed balanced DressCode evaluation remain required.")),
    ]
    passed = sum(item["status"] == "passed" for item in matrix)
    incomplete = [item["requirements"] for item in matrix if item["status"] != "passed"]
    result = {
        "objective": "O3 Integrated Application with Visualisation and Interaction",
        "status": "complete" if not incomplete else "incomplete",
        "requirements_passed": passed, "requirements_total": len(matrix),
        "incomplete_requirements": incomplete, "matrix": matrix,
        "release_checks": {"backend": tests, "frontend_lint": args.frontend_lint_pass, "frontend_build": args.frontend_build_pass},
        "model_evidence": {"smoke": smoke.get("status"), "dresscode_paired": paired.get("status")},
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "audited_at": datetime.now(timezone.utc).isoformat(),
    }
    serialised = json.dumps(result, indent=2)
    for directory in (RUNS, VERIFICATION):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "requirements-audit.json").write_text(serialised, encoding="utf-8")
    print(json.dumps({"status": result["status"], "passed": f"{passed}/{len(matrix)}", "incomplete": incomplete}, indent=2))
    if incomplete and not args.allow_incomplete:
        raise RuntimeError(f"O3 remains incomplete: {', '.join(incomplete)}")


if __name__ == "__main__":
    main()
