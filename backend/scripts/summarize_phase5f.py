"""Recompute descriptive statistics from raw trials; no latency samples altered."""
import argparse
import json
import math
from pathlib import Path
import statistics

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("artifact",type=Path)
args=parser.parse_args()
data=json.loads(args.artifact.read_text(encoding="utf-8-sig"))
expected={(size,flow,layer) for size in (20,50,100,200) for layer,flows in (
    ("real HTTP API",("homepage","assistant","history","authenticated_capabilities")),
    ("production Chromium",("homepage","assistant","history"))) for flow in flows}
actual={(r["size"],r["flow"],r["layer"].split(";")[0]) for r in data["records"]}
if actual != expected or len(data["records"]) != len(expected):
    raise ValueError("Incomplete or duplicate workload records; no full-run summary certified.")
def summarize(record):
    values=record["samples"]
    if not values or any(not isinstance(x,(int,float)) or not math.isfinite(x) or x<0 for x in values):
        raise ValueError("Invalid raw timing observations.")
    record.update(median=statistics.median(values),min=min(values),max=max(values))
    if len(values)>=20: record["p95"]=sorted(values)[math.ceil(.95*len(values))-1]
    else: record.pop("p95",None)
for record in data["records"]:
    if len(record["samples"]) != (20 if record["layer"].startswith("real HTTP") else 5):
        raise ValueError("Incomplete measured trials.")
    summarize(record)
    if "response_to_visible" in record: summarize(record["response_to_visible"])
    print(f"{record['size']} {record['flow']} {record['layer']}: median={record['median']:.4f}s p95={record.get('p95','not estimated')} range=[{record['min']:.4f},{record['max']:.4f}]")
data["statistics_method"]="Conventional median (mean of middle two for even n); empirical nearest-rank p95 for n>=20 only; warm-up excluded; samples unchanged."
args.artifact.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
