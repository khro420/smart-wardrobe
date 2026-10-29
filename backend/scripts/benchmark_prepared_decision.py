"""Six alternating full-pipeline A/B/C/D passes; C/D must be exactly equivalent."""
import argparse
from dataclasses import asdict
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.audit_compatibility_coverage import synthetic_wardrobe
from scripts.profile_decision_performance import execute
from scripts.benchmark_compatibility_pair_cache import fingerprint,workload_counts
from scripts.benchmark_compatibility_decision import peak_rss
from app.infrastructure.persistence.recommendation_repository_adapter import encode

LABELS={"A":"live_compatibility_deferred","B":"cached_Phase3A","C":"original_Phase3C2","D":"prepared_Phase3C2"}


def record(outcome,cache):
    return {"fingerprint":fingerprint(outcome),"status":outcome.status,"complete":outcome.complete,
            "scored":outcome.scored_count,"diagnostics":outcome.diagnostics,
            "winner":outcome.winner.verified.candidate.key if outcome.winner else None,
            "winner_score":json.loads(encode(outcome.winner.score)) if outcome.winner else None,
            "cache":asdict(cache) if cache else None}


def memory_worker(size,heavy,arm):
    startup=peak_rss();rows,counts=synthetic_wardrobe(size,varied=True,heavy=heavy)
    input_peak=peak_rss();outcome,cache=execute(rows,arm)
    if not outcome.complete:raise RuntimeError("Incomplete memory stream")
    return {**record(outcome,cache),"startup_peak_rss_bytes":startup,"input_peak_rss_bytes":input_peak,
            "peak_rss_bytes":peak_rss(),"expected":workload_counts(counts)}


def benchmark(size,heavy,pairs,memory):
    rows,counts=synthetic_wardrobe(size,varied=True,heavy=heavy);expected=workload_counts(counts)
    reference={};runs=[]
    for pair in range(pairs):
        order=list("ABCD" if pair%2==0 else "DCBA");run={"order":order,"arms":{}}
        for arm in order:
            gc.collect();start=time.perf_counter();outcome,cache=execute(rows,arm);elapsed=time.perf_counter()-start
            result=record(outcome,cache)
            if not outcome.complete:raise RuntimeError("Incomplete timing stream")
            if arm in reference and result!=reference[arm]:raise RuntimeError("Per-policy nondeterminism")
            reference[arm]=result
            if arm!="A":
                assert cache.visits==expected["pair_visits"] and cache.misses==expected["unique_pairs"] and cache.evictions==0
                assert int(dict(outcome.diagnostics)["accepted_examined"])==expected["candidates"]
            if arm!="B":assert outcome.scored_count==expected["candidates"]
            run["arms"][arm]={**result,"seconds":elapsed}
            print(f"size={size} heavy={heavy} pair={pair+1}/{pairs} arm={arm} seconds={elapsed:.6f}",flush=True)
        if reference["C"]!=reference["D"]:raise RuntimeError("Original/prepared full-result mismatch")
        runs.append(run)
    rss={}
    if memory:
        for arm in "ABCD":
            cmd=[sys.executable,"-B",str(Path(__file__).resolve()),"--memory-worker",str(size),"--arm",arm]
            if heavy:cmd.append("--heavy")
            result=json.loads(subprocess.run(cmd,check=True,capture_output=True,text=True,encoding="utf-8").stdout)
            if result["fingerprint"]!=reference[arm]["fingerprint"]:raise RuntimeError("Memory fingerprint mismatch")
            rss[arm]=result
            print(f"size={size} heavy={heavy} memory arm={arm} peak_rss={result['peak_rss_bytes']}",flush=True)
    times={arm:[r["arms"][arm]["seconds"] for r in runs] for arm in "ABCD"}
    improvements=[100*(a-b)/a for a,b in zip(times["C"],times["D"])]
    return {"size":size,"heavy":heavy,"structures":counts,"expected":expected,"runs":runs,"memory":rss,
            "summary":{"arms":{a:{"median_seconds":statistics.median(v),"min_seconds":min(v),"max_seconds":max(v)} for a,v in times.items()},
                       "C_to_D_paired_improvements_percent":improvements,
                       "C_to_D_median_paired_improvement_percent":statistics.median(improvements),
                       "B_to_D_paired_overhead_percent":[100*(d-b)/b for b,d in zip(times["B"],times["D"])]}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes",nargs="*",type=int,default=[20,50,100,200]);parser.add_argument("--heavy",action="store_true")
    parser.add_argument("--pairs",type=int,default=6);parser.add_argument("--memory",action="store_true")
    parser.add_argument("--output",type=Path);parser.add_argument("--memory-worker",type=int)
    parser.add_argument("--arm",choices=list("ABCD"));args=parser.parse_args()
    if args.memory_worker:
        print(json.dumps(memory_worker(args.memory_worker,args.heavy,args.arm)));return
    root=Path(__file__).resolve().parents[2]
    if args.output is None or args.pairs<1 or any(n<10 for n in args.sizes):parser.error("New output, sizes>=10 and positive pairs required")
    target=args.output.resolve()
    if target.exists() or not target.is_relative_to(root/"storage"):parser.error("New storage output required")
    sources=[Path(__file__),Path(__file__).with_name("profile_decision_performance.py"),*(root/"backend/app").rglob("*.py"),*(root/"backend/app").rglob("*.json")]
    report={"version":"1.0.0","complete":False,"synthetic":True,"arms":LABELS,"pairs":args.pairs,
            "python":sys.version,"platform":platform.platform(),"hash_seed":os.getenv("PYTHONHASHSEED"),"gc_enabled":gc.isenabled(),
            "request":"no optional fields","preferences":[],"memory_method":"fresh-process peak working-set RSS, including interpreter/input",
            "source_hashes":{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},"workloads":[]}
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2)
    for size,heavy in [(x,False) for x in args.sizes]+([(200,True)] if args.heavy else []):
        report["workloads"].append(benchmark(size,heavy,args.pairs,args.memory))
        target.write_text(json.dumps(report,indent=2),encoding="utf-8")
    report["complete"]=True;target.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("Completed:",target,flush=True)


if __name__=="__main__":main()
