"""Summarize retained measurements without dropping failed transport trials."""
import argparse
import json
from pathlib import Path
from statistics import median


def stats(values):
    values = list(values)
    return {"count": len(values), "median": median(values) if values else None,
            "maximum": max(values) if values else None}


def summarize(data):
    groups = {}
    for row in data["records"]:
        key = (row["name"], row["profile"], row["layer"], row["arm"])
        groups.setdefault(key, []).append(row)
    output = []
    for key, rows in groups.items():
        output.append(dict(zip(("name", "profile", "layer", "arm"), key),
            trials=len(rows), errors=sum(r["error"] is not None for r in rows),
            transport_all=stats(r["seconds"] for r in rows),
            transport_success_only=stats(r["seconds"] for r in rows if r["error"] is None),
            backend_service_all=stats(r["job"]["service_seconds"] for r in rows),
            backend_request_header=stats(r["backend_seconds"] for r in rows if r.get("backend_seconds") is not None),
            browser_response_arrival=stats(r["http_seconds"] for r in rows if r.get("http_seconds") is not None),
            proxy_network_browser_residual=stats(r["http_seconds"]-r["backend_seconds"] for r in rows if r.get("http_seconds") is not None and r.get("backend_seconds") is not None),
            cpu_all=stats(r["job"]["cpu_seconds"] for r in rows),
            completed_jobs=sum(r["job"].get("done", False) for r in rows),
            fingerprints=sorted(set(r["fingerprint"] for r in rows)),
            statuses=[r.get("http_status") for r in rows],
            candidate_counts=sorted(set(r["job"]["candidate_count"] for r in rows))))
    pairs = []
    for name, profile, layer in dict.fromkeys(key[:3] for key in groups):
        rows = [r for r in data["records"] if (r["name"], r["profile"], r["layer"]) == (name, profile, layer)]
        for pair in sorted(set(r["pair"] for r in rows)):
            arms = {r["arm"]: r for r in rows if r["pair"] == pair}
            if set(arms) != {"reference", "trial"}:
                raise ValueError("Incomplete matched pair")
            a, b = arms["reference"], arms["trial"]
            if a["fingerprint"] != b["fingerprint"]:
                raise ValueError("Differential fingerprint mismatch")
            pairs.append({"name": name, "profile": profile, "layer": layer, "pair": pair,
                "service_gain_percent": 100 * (a["job"]["service_seconds"] - b["job"]["service_seconds"]) / a["job"]["service_seconds"],
                "transport_gain_percent": None if a["error"] or b["error"] else 100 * (a["seconds"] - b["seconds"]) / a["seconds"],
                "reference_error": a["error"], "trial_error": b["error"]})
    return {"method": "All trials retained; maxima are observed tails, not inferred population percentiles. Failed proxy elapsed time is not successful response latency. CPU spans are process-wide, not additive under concurrency.",
            "trial_count": len(data["records"]), "errors": sum(r["error"] is not None for r in data["records"]),
            "metadata": data["metadata"], "groups": output, "pairs": pairs}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = summarize(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"trials": result["trial_count"], "errors": result["errors"]}))
