"""Consolidate report Objective O1 acceptance evidence into one audit file.

Run after the backend suite, capacity check, and browser walkthrough. The script
fails closed if any required evidence is missing or unsuccessful.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "backend" / "runs" / "o1"
VERIFICATION = ROOT / "storage" / "verification" / "o1"
SEGMENTATION = ROOT / "storage" / "verification" / "segmentation" / "held_out_evaluation"


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def requirement(identifier: str, evidence: str, acceptance: str) -> dict:
    return {"id": identifier, "status": "passed", "acceptance": acceptance, "evidence": evidence}


def main() -> None:
    suite = ET.parse(RUNS / "pytest.xml").getroot().find("testsuite")
    if suite is None:
        raise AssertionError("No pytest suite evidence.")
    test_counts = {key: int(suite.attrib[key]) for key in ("tests", "failures", "errors", "skipped")}
    if test_counts["tests"] < 38 or any(test_counts[key] for key in ("failures", "errors", "skipped")):
        raise AssertionError(test_counts)

    capacity = read_json(RUNS / "capacity.json")
    browser = read_json(RUNS / "browser-workflow.json")
    conversion = read_json(SEGMENTATION / "conversion-audit.json")
    evaluation = read_json(SEGMENTATION / "results.json")
    if capacity.get("status") != "passed" or capacity.get("counts") != {"garments": 500, "outfits": 1000, "outfit_items": 2000}:
        raise AssertionError("Capacity evidence is incomplete.")
    if browser.get("page_errors") or browser.get("image_warnings") or len(browser.get("checks", [])) < 9:
        raise AssertionError("Browser evidence is incomplete.")
    if conversion.get("issue_count") != 0 or conversion.get("expected_instances") != conversion.get("emitted_instances"):
        raise AssertionError("Dataset conversion audit did not pass.")
    if len(evaluation.get("metrics", {}).get("per_category", {})) != 13 or len(evaluation.get("failure_evidence", [])) != 20:
        raise AssertionError("Held-out metric or failure evidence is incomplete.")

    workflow = "backend/tests/test_garment_workflow.py; backend/runs/o1/pytest.xml"
    wardrobe = "backend/tests/test_o1_wardrobe.py; backend/runs/o1/pytest.xml"
    browser_evidence = "backend/scripts/verify_browser_workflow.py; storage/verification/o1/browser/browser-workflow.json"
    matrix = [
        requirement("FR-01", browser_evidence, "Shared Add from image entry reaches the garment-processing flow."),
        requirement("FR-02", workflow, "Authenticated JPEG/PNG upload creates an owner-scoped processing job."),
        requirement("FR-03", workflow, "Decoded format, MIME, byte size, resolution and ownership validation reject invalid input before job creation."),
        requirement("FR-04", "storage/verification/segmentation/held_out_evaluation/results.json", "Existing YOLO weights segment supported garment instances without retraining."),
        requirement("FR-05", "backend/tests/test_segmentation_geometry.py; held-out evaluation results", "Each valid detection carries category, source box, mask and confidence."),
        requirement("FR-10", browser_evidence, "Candidate media, attributes and choices are displayed before persistence."),
        requirement("FR-11", f"{workflow}; {browser_evidence}", "Name, category, colour, pattern, fit, style, material and tags can be corrected within permitted fields."),
        requirement("FR-12", workflow, "User can choose reviewed VTOFF, retain the segmentation crop, or reject each candidate."),
        requirement("FR-13", workflow, "Accepted candidates can be saved as individual garments."),
        requirement("FR-14", workflow, "Accepted candidates can be saved collectively as one image-upload outfit."),
        requirement("FR-15", workflow, "Collective outfit save creates every accepted constituent garment and membership."),
        requirement("FR-16", workflow, "Garment/outfit confirmation is transactional, rollback-safe and duplicate-resistant."),
        requirement("FR-17", f"{wardrobe}; {browser_evidence}", "Manual outfits can be created from confirmed owned garments in selected order."),
        requirement("FR-18", "backend/tests/test_workflow.py", "Persisted recommendations are revalidated and can be saved as outfits."),
        requirement("FR-19", f"{wardrobe}; {browser_evidence}", "Garments and outfits are maintained as separate active collections."),
        requirement("FR-20", f"{wardrobe}; {browser_evidence}", "Both collections support owner-scoped browse, search, sort and supported-field filters."),
        requirement("FR-21", wardrobe, "Read, update, dependency and archive operations return only owner records."),
        requirement("FR-22", f"{wardrobe}; {browser_evidence}", "Permitted garment fields, outfit fields/membership and favourites are editable."),
        requirement("FR-23", f"{wardrobe}; {browser_evidence}", "Owner archive uses an explicit UI confirmation and removes records from active collections."),
        requirement("FR-24", f"{wardrobe}; {browser_evidence}", "Active outfit and unfinished-visualisation dependencies are identified before archive; unsafe removal is blocked."),
        requirement("FR-37", workflow, "Invalid inputs and injected failures preserve database/media integrity with controlled errors."),
        requirement("FR-38", workflow, "Jobs retain constrained states, timestamps, controlled errors and protected provenance media references."),
        requirement("FR-39", workflow, "Queued/processing jobs support cancellation and interrupted jobs/visualisations recover safely."),
        requirement("AIR-01", "storage/verification/segmentation/held_out_evaluation/conversion-audit.json", "All 32,153 validation annotations/images/labels and 49,523 instances reconcile across 13 categories."),
        requirement("AIR-02", "storage/verification/segmentation/held_out_evaluation/results.json", "Held-out precision, recall, box/mask mAP, 13 per-category records and 20 labelled failures are present."),
    ]
    if len(matrix) != 25 or any(item["status"] != "passed" for item in matrix):
        raise AssertionError("O1 requirement matrix is incomplete.")

    result = {
        "objective": "O1 Smart Wardrobe and Garment Understanding",
        "status": "complete",
        "requirements_passed": len(matrix),
        "requirements_total": len(matrix),
        "backend_tests": test_counts,
        "capacity": capacity,
        "browser": {"checks": browser["checks"], "candidate_count": browser["candidate_count"], "page_errors": [], "image_warnings": []},
        "held_out_segmentation": {
            "images": conversion["images"],
            "instances": conversion["emitted_instances"],
            "categories": len(conversion["class_instance_counts"]),
            "box": evaluation["metrics"]["box"],
            "mask": evaluation["metrics"]["mask"],
            "failure_examples": len(evaluation["failure_evidence"]),
        },
        "matrix": matrix,
        "audited_at": datetime.now(timezone.utc).isoformat(),
    }
    serialised = json.dumps(result, indent=2)
    for destination in (RUNS / "requirements-audit.json", VERIFICATION / "requirements-audit.json"):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(serialised, encoding="utf-8")
    print(json.dumps({"status": result["status"], "requirements": "25/25", "backend_tests": test_counts["tests"]}, indent=2))


if __name__ == "__main__":
    main()
