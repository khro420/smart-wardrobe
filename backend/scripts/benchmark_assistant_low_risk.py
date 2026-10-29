"""Sequential isolated original/individual/combined full-service benchmarks.

Run without concurrent tests, builds or profiles. Synthetic confirmed SQLite;
fresh submission keys, real NLP, gate, scoring and atomic persistence.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import pstats
import statistics
import subprocess
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from tests.test_assistant_performance_equivalence import garment, preferences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sizes", nargs="+", type=int, default=[20, 50, 100, 200])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--skip-profiles", action="store_true")
    args = parser.parse_args()
    if args.repeats < 2 or min(args.sizes) < 10:
        parser.error("At least two trials and >=10 garments required")
    args.output.mkdir(parents=True, exist_ok=True)
    metadata = {"python": sys.version, "platform": platform.platform(),
        "dependencies": {name: importlib.metadata.version(name) for name in ("fastapi", "pillow", "numpy", "python-multipart")},
        "reference_sha256": hashlib.sha256((BACKEND / "tests/fixtures/performance_reference/app.zip").read_bytes()).hexdigest(),
        "production_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (BACKEND / "app/application/recommendation").glob("*.py")},
        "method": "Three measured trials by default, one excluded warmup per cell. Fresh disposable DB per variant/size/preferences. Full Assistant service, unique keys and real strict revalidation/commit. No HTTP/browser latency or NFR compliance claim. All raw samples retained. Profiles separately run after uninstrumented trials.",
        "records": [], "profiles": []}

    def save():
        (args.output / "results.json").write_text(json.dumps(metadata, indent=2) + "\n")

    worker = BACKEND / "tests/performance_worker.py"
    largest_fixtures = []
    for size in args.sizes:
        counts = {"top": int(size*.4), "bottom": int(size*.4), "dress": int(size*.1)}
        counts["outerwear"] = size-sum(counts.values())
        rows = []
        for role, category in (("top", "vest"), ("bottom", "trousers"), ("dress", "vest_dress"), ("outerwear", "long_sleeve_outwear")):
            rows.extend(garment(f"{role}-{i:06d}", category, primary_colour="blue", style_tags=["vintage"]) for i in range(counts[role]))
        expected = (counts["top"]*counts["bottom"]+counts["dress"])*(1+counts["outerwear"])
        for populated in (False, True):
            label = f"size-{size}-prefs-{int(populated)}"
            fixture = args.output / (label + "-input.json")
            fixture.write_text(json.dumps([dict(name=label, garments=rows, preferences=preferences() if populated else [], service=True)]))
            if size == max(args.sizes): largest_fixtures.append((label, fixture, expected))
            baseline = None
            for variant in ("original", "key", "preferences", "constants", "combined"):
                output = args.output / (label + "-" + variant + ".json")
                print(f"Starting {label}: {variant}", flush=True)
                subprocess.run([sys.executable, "-B", str(worker), "--variant", variant, "--fixtures", str(fixture),
                    "--output", str(output), "--repeats", str(args.repeats), "--warmups", "1"], check=True)
                value = json.loads(output.read_text())[0]
                if value["scored_count"] != expected: raise RuntimeError("Candidate set truncated")
                fingerprint = (value["winner"], value["score_metadata"])
                if baseline is None: baseline = fingerprint
                if fingerprint != baseline: raise RuntimeError("Winner/scoring metadata changed")
                samples = [item["wall"] for item in value["timings"]]
                record = {"size": size, "populated": populated, "variant": variant, "candidates": expected,
                    "median": statistics.median(samples), "min": min(samples), "max": max(samples),
                    "cpu_median": statistics.median(item["cpu"] for item in value["timings"]), "samples": value["timings"]}
                if len(samples) >= 20:
                    import math
                    record["p95"] = sorted(samples)[math.ceil(.95*len(samples))-1]
                metadata["records"].append(record)
                save()
                print(json.dumps({k:v for k,v in record.items() if k != "samples"}), flush=True)
    if not args.skip_profiles:
        for label, fixture, expected in largest_fixtures:
            for variant in ("original", "combined"):
                destination = args.output / (label + "-" + variant + ".prof")
                output = args.output / (label + "-" + variant + "-profile.json")
                print(f"Separate profile {label}: {variant}", flush=True)
                subprocess.run([sys.executable, "-B", "-m", "cProfile", "-o", str(destination), str(worker),
                    "--variant", variant, "--fixtures", str(fixture), "--output", str(output)], check=True)
                if json.loads(output.read_text())[0]["scored_count"] != expected: raise RuntimeError("Incomplete profile")
                stats = pstats.Stats(str(destination))
                metadata["profiles"].append({"label": label, "variant": variant, "total_calls": stats.total_calls,
                    "self_seconds": stats.total_tt, "functions": [{"file": key[0], "line": key[1], "function": key[2],
                    "calls": item[1], "self": item[2], "cumulative": item[3]} for key,item in stats.stats.items()]})
                save()
    save()


if __name__ == "__main__":
    main()
