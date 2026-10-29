"""Read-only algorithm diagnosis on disposable synthetic SQLite wardrobes.

Never patches production methods. CPU profiles and tracemalloc runs are separate
from uninstrumented latency runs. Does not measure HTTP/browser response time.
"""
import argparse
import cProfile
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import pstats
import statistics
import sys
import tempfile
import time
import tracemalloc

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sizes", nargs="+", type=int, default=[20, 50, 100, 200])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--preference-repeats", type=int, default=3)
    parser.add_argument("--baseline-only", action="store_true", help="Skip CPU and allocation instrumentation.")
    parser.add_argument("--finalization-only", action="store_true", help="Measure terminal next/close after draining the request stream, without ranking.")
    args = parser.parse_args()
    if min(args.sizes) < 10 or min(args.repeats, args.preference_repeats) < 2:
        parser.error("Use sizes >=10 and at least two measured trials.")
    args.output.mkdir(parents=True, exist_ok=True)
    source_paths = sorted((BACKEND / "app").rglob("*.py"))
    hashes = {str(p.relative_to(BACKEND)): digest(p) for p in source_paths}
    result = {
        "python": sys.version, "platform": platform.platform(),
        "processor": platform.processor(), "logical_cpu_count": os.cpu_count(),
        "dependencies": {name: importlib.metadata.version(name) for name in ("fastapi", "pillow", "numpy", "python-multipart")},
        "source_sha256": hashes, "script_sha256": digest(Path(__file__)),
        "method": "Synthetic strict-confirmed SQLite. One excluded warmup per size/scenario; fresh submission keys, real NLP/ranking/revalidation/persistence. Sequential trials, no concurrent browser/build. Profiles use process_time CPU clock; wall/CPU overhead must not be used for NFR acceptance. Allocation snapshots show surviving allocations, not all allocation events. No production algorithm patches.",
        "baselines": [], "profiles": [], "allocations": [], "finalizations": [],
    }

    def save():
        (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="assistant-diagnosis-") as directory:
        os.environ.update(SMART_WARDROBE_DATA_DIR=directory,
                          SMART_WARDROBE_DATABASE=str(Path(directory) / "initial.db"),
                          SMART_WARDROBE_VTOFF_ENABLED="off")
        from benchmark_homepage_recommendation import seed
        from app.infrastructure.persistence import postgresql_repository as db
        from app.infrastructure.persistence import active_preference_query_adapter as prefs
        from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
        from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
        from app.application.nlp.nlp_interpreter import NLPInterpreter
        from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
        from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
        from app.domain.value_objects.preference_snapshot import PreferenceSnapshot

        class Preferences:
            def __init__(self, enabled):
                self.enabled = enabled

            def get_active_preferences(self, user_id):
                if not self.enabled:
                    return ()
                definitions = [("colours", ["blue", "black"]),
                               ("styles", ["vintage", "classic"]),
                               ("garment_categories", [{"kind": "group", "value": "top"}]),
                               ("formality", ["casual"])]
                return tuple(PreferenceSnapshot(str(i), user_id, kind,
                             json.dumps({"values": values}), "0.5")
                             for i, (kind, values) in enumerate(definitions))

        for size in args.sizes:
            db.DATABASE_PATH = prefs.DATABASE_PATH = Path(directory) / f"{size}.db"
            db.initialise_database()
            counts = seed(size)
            with db.connection() as conn:
                conn.execute("UPDATE garments SET primary_colour='blue',style_tags='[\"vintage\"]'")
            expected = (counts["top"] * counts["bottom"] + counts["dress"]) * (1 + counts["outerwear"])
            serial = 0

            if args.finalization_only:
                request = NLPInterpreter().interpret("Suggest an outfit with vintage style").structured_request
                session = RequestCandidateEngine(SqliteConfirmedGarmentQuery()).generate_candidates("benchmark", request)
                for _ in range(expected):
                    next(session)
                start = time.perf_counter()
                try:
                    next(session)
                except StopIteration:
                    terminal_seconds = time.perf_counter() - start
                else:
                    raise RuntimeError("Unexpected extra candidate.")
                start = time.perf_counter()
                session.close()
                close_seconds = time.perf_counter() - start
                if not session.result.complete or session.result.passed != expected:
                    raise RuntimeError("Finalization failed.")
                row = {"size": size, "candidates": expected, "terminal_next_seconds": terminal_seconds,
                       "close_seconds": close_seconds, "status": session.result.status}
                result["finalizations"].append(row)
                print(json.dumps(row), flush=True)
                save()
                continue

            def execute(with_preferences):
                nonlocal serial
                serial += 1
                service = OutfitAssistantService(NLPInterpreter(), RequestCandidateEngine(SqliteConfirmedGarmentQuery()),
                    Preferences(with_preferences), SqliteRecommendationRepository(db.DATABASE_PATH))
                wall, cpu = time.perf_counter(), time.process_time()
                outcome = service.recommend("benchmark", f"size-{size}-submission-{serial}", "Suggest an outfit with vintage style")
                timing = {"wall_seconds": time.perf_counter() - wall, "cpu_seconds": time.process_time() - cpu}
                if outcome["status"] != "Selected" or not outcome["complete"] or outcome["provenance"]["scored_count"] != expected or outcome["replayed"]:
                    raise RuntimeError(f"Incomplete or replayed diagnosis: {outcome}")
                return {**timing, "stages": outcome["timings"], "recommendation_id": outcome["id"],
                        "winner_items": [(item["garment_id"], item["garment_role"], item["item_order"]) for item in outcome["items"]]}

            for scenario in (False, True):
                execute(scenario)  # Excluded warm-up; never an idempotency replay.
                trials = []
                for trial in range(args.preference_repeats if scenario else args.repeats):
                    trials.append(execute(scenario))
                    print(json.dumps({"size": size, "preferences": scenario, "trial": trial, **trials[-1]}), flush=True)
                values = sorted(item["wall_seconds"] for item in trials)
                result["baselines"].append({"size": size, "role_counts": counts, "candidates": expected,
                    "preferences": scenario, "trials": trials, "median_seconds": statistics.median(values),
                    "empirical_p95_seconds": values[math.ceil(.95 * len(values)) - 1],
                    "range_seconds": [min(values), max(values)]})
                save()

            if args.baseline_only:
                continue
            for scenario in ([False, True] if size == max(args.sizes) else [False]):
                print(f"CPU profile starting: size={size}, preferences={scenario}", flush=True)
                profiler = cProfile.Profile(timer=time.process_time)
                profiler.enable()
                trial = execute(scenario)
                profiler.disable()
                name = f"size-{size}-prefs-{int(scenario)}"
                profiler.dump_stats(str(args.output / f"{name}.prof"))
                stats = pstats.Stats(profiler)
                entries = []
                for (filename, line, function), (primitive, calls, own, cumulative, callers) in stats.stats.items():
                    entries.append({"file": filename, "line": line, "function": function,
                        "primitive_calls": primitive, "calls": calls, "self_cpu_seconds": own,
                        "cumulative_cpu_seconds": cumulative})
                entries.sort(key=lambda item: item["cumulative_cpu_seconds"], reverse=True)
                result["profiles"].append({"size": size, "preferences": scenario, "timing": trial,
                    "total_calls": stats.total_calls, "total_self_cpu_seconds": stats.total_tt, "functions": entries})
                print(f"CPU profile complete: {name}, {trial['wall_seconds']:.3f}s wall", flush=True)
                save()

            if size in (20, 50):
                tracemalloc.start(10)
                trial = execute(True)
                current, peak = tracemalloc.get_traced_memory()
                snapshot = tracemalloc.take_snapshot()
                tracemalloc.stop()
                result["allocations"].append({"size": size, "timing": trial, "current_bytes": current,
                    "peak_bytes": peak, "surviving_top_lines": [str(item) for item in snapshot.statistics("lineno")[:25]]})
                print(f"Allocation run complete: size={size}, peak={peak}", flush=True)
                save()
    if hashes != {str(p.relative_to(BACKEND)): digest(p) for p in source_paths}:
        raise RuntimeError("Application source changed during diagnosis.")
    result["application_sources_unchanged"] = True
    save()


if __name__ == "__main__":
    main()
