"""Synthetic numeric-cache allocation observation; not end-to-end process RSS."""
import argparse
import json
from pathlib import Path
import sys
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.application.recommendation.prepared_compatibility_aggregation import PreparedCompatibilityAggregation


def measure(capacity):
    scorer = PreparedCompatibilityAggregation(aggregation_capacity=capacity)
    tracemalloc.start()
    for i in range(1, 1025):
        # Synthetic validated fractions, not garment/fashion reference labels.
        scorer._aggregate((((i, 1024), 1),), ((((1024-i), 1024), 1),))
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"capacity": capacity, "current_traced_bytes": current,
            "peak_traced_bytes": peak, "cache_info": scorer.aggregation_cache_info._asdict()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new output path")
    data = {"method": "1,024 synthetic distinct numeric vectors after scorer initialization. Python tracemalloc includes entry churn; excludes initialization, whole candidate pipeline, native allocations and process RSS. Never use these instrumented runs as latency evidence.",
            "observations": [measure(n) for n in (0, 256)]}
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data))
