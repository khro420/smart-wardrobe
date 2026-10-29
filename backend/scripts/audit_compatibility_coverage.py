"""Exhaustive offline structural coverage probes, not recommendation scoring.

Retains unique signature keys/counters, never a collection of outfit candidates.
Synthetic metadata is not human evidence or proof of database confirmation.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import platform
import sys
import time
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.compatibility_evidence_dataset import import_bundle, load_json, quality_report, write_new
from app.application.recommendation.compatibility_reference_policy import CompatibilityReferencePolicy, artifact_hash
from app.application.recommendation.compatibility_evidence_mapper import CompatibilityEvidenceMapper
from app.application.recommendation.recommendation_engine import RecommendationEngine
from app.domain.value_objects.compatibility_signature import STRUCTURES
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot


class OfflineQuery:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def get_confirmed_available_garments(self, user_id):
        return tuple(x for x in self.rows if x.user_id == user_id)


def synthetic_wardrobe(size, varied=False, heavy=False):
    if type(size) is not int or size < 10:
        raise ValueError("Synthetic sizes must be integers >=10.")
    if heavy:
        outer = size // 3
        counts = ((size-outer)//2, size-outer-(size-outer)//2, 0, outer)
    else:
        top, bottom, dress = int(size*.4), int(size*.4), int(size*.1)
        counts = (top, bottom, dress, size-top-bottom-dress)
    rows = []
    colours = ("blue", "black", "white", "grey", "navy", "red", "green", "yellow", "orange", "pink", "purple", "brown", "beige", "cream")
    for count, category in zip(counts, ("vest", "trousers", "vest_dress", "long_sleeve_outwear")):
        role, layer = GARMENT_STRUCTURE[category]
        for i in range(count):
            gid = f"synthetic-{category}-{i:04d}"
            rows.append(ConfirmedGarmentSnapshot(gid, "synthetic-owner", "available", category, gid,
                "synthetic-no-image", False, "synthetic-capture", structural_role=role, layering_index=layer,
                primary_colour=colours[i % len(colours)] if varied else "blue",
                style_tags=(("vintage", "classic", "minimal")[i % 3],) if varied else ("vintage",),
                pattern=("plain", "stripe")[i % 2] if varied else "plain"))
    return tuple(rows), counts


def scan(rows, policy, reference_records=(), memory=False):
    if not rows:
        raise ValueError("Coverage session needs an explicit nonempty wardrobe.")
    if len({r.user_id for r in rows}) != 1:
        raise ValueError("Offline wardrobe must have a single owner.")
    mapper = CompatibilityEvidenceMapper(policy)
    counters = {s: {"candidates": 0, "covered": 0, "reviewed_zero": 0, "missing_reference": 0,
                    "incomplete_evidence": 0, "unavailable_policy": 0,
                    "seen_signature_different_garments": 0, "same_reference_garments": 0} for s in STRUCTURES}
    unique = {s: set() for s in STRUCTURES}
    known_garments = {}
    for record in reference_records:
        if record["partition"] == "reference" and record["lookup_reference"]:
            signature = policy.parse_signature(record["signature"])
            known_garments[signature.key] = frozenset(x["snapshot"]["garment_id"] for x in record["garments"])
    if memory:
        tracemalloc.start()
    start = time.perf_counter()
    with RecommendationEngine(OfflineQuery(rows)).generate_homepage_candidates(rows[0].user_id) as session:
        for outfit in session:
            signature, *_ = mapper.signature(outfit)
            roles = tuple(x.role for x in outfit.members)
            structure = next(s for s, expected in STRUCTURES.items() if expected == roles)
            counts = counters[structure]
            counts["candidates"] += 1
            if signature is None:
                counts["incomplete_evidence"] += 1
                continue
            unique[structure].add(signature.key)
            if not policy.available:
                counts["unavailable_policy"] += 1
                continue
            reference = policy.approved.get(signature.key)
            if reference is None:
                counts["missing_reference"] += 1
                continue
            counts["covered"] += 1
            counts["reviewed_zero"] += reference.value == 0
            actual = frozenset(x.garment.garment_id for x in outfit.members)
            counts["same_reference_garments" if actual == known_garments.get(signature.key) else "seen_signature_different_garments"] += 1
        if not session.result.complete or session.result.candidate_count != sum(x["candidates"] for x in counters.values()):
            raise RuntimeError("Incomplete structural stream: no complete coverage result.")
        terminal = session.result.status
        exclusions = [asdict(x) for x in session.result.exclusions]
    elapsed = time.perf_counter() - start
    peak = tracemalloc.get_traced_memory()[1] if memory else None
    if memory:
        tracemalloc.stop()
    for s, counts in counters.items():
        counts["unique_complete_signatures"] = len(unique[s])
        counts["unique_covered_signatures"] = len(unique[s] & policy.approved.keys()) if policy.available else 0
        counts["unique_unseen_signatures"] = len(unique[s] - policy.approved.keys())
        counts["coverage_fraction"] = counts["covered"]/counts["candidates"] if counts["candidates"] else None
    total = sum(x["candidates"] for x in counters.values())
    covered = sum(x["covered"] for x in counters.values())
    return {"complete": True, "terminal_status": terminal, "exclusions": exclusions,
            "total_structural_candidates": total, "covered_candidates": covered,
            "coverage_fraction": covered/total if total else None,
            "hypothetical_whole_session_gate_permits": bool(total and covered == total),
            "gate_implemented": False, "by_structure": counters,
            "seconds": elapsed, "peak_python_traced_bytes": peak,
            "cached_garments": mapper.cache_size}


def baseline(rows):
    start = time.perf_counter()
    with RecommendationEngine(OfflineQuery(rows)).generate_homepage_candidates(rows[0].user_id) as session:
        count = sum(1 for _ in session)
        if not session.result.complete:
            raise RuntimeError("Incomplete baseline stream.")
    return count, time.perf_counter()-start


def run(dataset, sizes=(20, 50, 100, 200), memory=False, wardrobes=None):
    bundle = import_bundle(dataset)
    policy = CompatibilityReferencePolicy(bundle["policy"])
    results = []
    cases = []
    if wardrobes is not None:
        if set(wardrobes) != {"version", "kind", "wardrobes"} or wardrobes["kind"] != "captured_offline_wardrobes" or not isinstance(wardrobes["version"], str) or not wardrobes["version"]:
            raise ValueError("Versioned captured offline wardrobes required.")
        for item in wardrobes["wardrobes"]:
            if set(item) != {"session_id", "snapshots"} or not isinstance(item["session_id"], str) or not item["session_id"]:
                raise ValueError("Invalid captured wardrobe session.")
            cases.append((item["session_id"], tuple(ConfirmedGarmentSnapshot(**x) for x in item["snapshots"]), None))
        if len({x[0] for x in cases}) != len(cases):
            raise ValueError("Duplicate captured session ID.")
    else:
        for size in sizes:
            for varied in (False, True):
                rows, counts = synthetic_wardrobe(size, varied)
                cases.append((f"synthetic-{size}-{'varied' if varied else 'uniform'}", rows, counts))
        for varied in (False, True):
            rows, counts = synthetic_wardrobe(200, varied, True)
            cases.append((f"synthetic-200-outerwear-heavy-{'varied' if varied else 'uniform'}", rows, counts))
    for name, rows, counts in cases:
        n, base_seconds = baseline(rows)
        result = scan(rows, policy, dataset["records"])
        result.update(session_id=name, wardrobe_size=len(rows), role_counts=counts,
                      evidence_kind="captured_offline_wardrobe" if wardrobes is not None else "synthetic_probe",
                      wardrobe_hash=artifact_hash([asdict(x) for x in rows]),
                      structural_baseline_seconds=base_seconds,
                      observed_signature_audit_delta_seconds=result["seconds"]-base_seconds)
        if counts is not None:
            t,b,d,o = counts
            if n != (t*b+d)*(1+o):
                raise RuntimeError("Independent combination count mismatch.")
        if n != result["total_structural_candidates"]:
            raise RuntimeError("Audit changed candidate count.")
        if memory:
            traced = scan(rows, policy, dataset["records"], True)
            if traced["by_structure"] != result["by_structure"]:
                raise RuntimeError("Traced and ordinary coverage differ.")
            result["peak_python_traced_bytes"] = traced["peak_python_traced_bytes"]
            result["traced_seconds"] = traced["seconds"]
        results.append(result)
        print(json.dumps({k: result[k] for k in ("session_id", "total_structural_candidates", "coverage_fraction", "seconds", "peak_python_traced_bytes")}), flush=True)
    return {"schema_version": "coverage-readiness-1.0.0", "dataset_hash": bundle["dataset_hash"],
            "policy_hash": policy.hash, "approved_real_reference_count": len(policy.approved),
            "activation_approved": False, "python": platform.python_version(), "platform": platform.platform(),
            "method": "One structural baseline, one full signature/lookup pass, optional separate traced pass; no scoring, SQL, HTTP or candidate retention. Timing deltas are single-run observations, not causal optimized-production results. Signature-key sets grow with unique metadata; traced peak is not RSS.",
            "quality": quality_report(dataset), "sessions": results,
            "lookup_policy_available": policy.available,
            "hypothetical_gate_permitted_sessions": sum(x["hypothetical_whole_session_gate_permits"] for x in results),
            "limitations": ["Offline snapshots do not prove current confirmation or extraction quality.",
                            "No quality results can be inferred from synthetic coverage probes.",
                            "134820 candidates is one 200-garment shape, not a maximum."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--sizes", nargs="+", type=int, default=[20,50,100,200])
    parser.add_argument("--measure-memory", action="store_true")
    parser.add_argument("--wardrobes", type=Path, help="Optional captured offline wardrobes; otherwise explicitly synthetic probes")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(load_json(args.dataset), args.sizes, args.measure_memory,
                     load_json(args.wardrobes) if args.wardrobes else None)
        result["tool_sha256"] = {Path(p).name: __import__("hashlib").sha256(Path(p).read_bytes()).hexdigest() for p in (__file__, str(Path(__file__).with_name("compatibility_evidence_dataset.py")))}
        write_new(args.output, result, tuple(x for x in (args.dataset, args.wardrobes) if x))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
