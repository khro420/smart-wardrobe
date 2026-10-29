"""Matched interleaved full-pipeline experiment; uncached Phase3A is untouched.

Peak RSS comes from separate fresh-process complete passes, not tracemalloc.
No external packages, model, HTTP, database or candidate limits are introduced.
"""
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
from scripts.audit_compatibility_coverage import synthetic_wardrobe,OfflineQuery
from scripts.evaluate_rule_based_compatibility import Preferences
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.rule_based_recommendation_scorer import RuleBasedRecommendationScorer
from app.application.recommendation.cached_rule_based_recommendation_scorer import CachedRuleBasedRecommendationScorer
from app.infrastructure.persistence.recommendation_repository_adapter import encode
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.application.recommendation.rule_based_compatibility_policy import RULES,PROFILES


def peak_rss():
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD)]+[(x,ctypes.c_size_t) for x in
                      ("PeakWorkingSetSize","WorkingSetSize","QuotaPeakPagedPoolUsage","QuotaPagedPoolUsage",
                       "QuotaPeakNonPagedPoolUsage","QuotaNonPagedPoolUsage","PagefileUsage","PeakPagefileUsage")]
        kernel=ctypes.WinDLL("kernel32",use_last_error=True);psapi=ctypes.WinDLL("psapi",use_last_error=True)
        kernel.GetCurrentProcess.restype=wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes=(wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD)
        psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
        data=Counters();data.cb=ctypes.sizeof(data)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(data),data.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return data.PeakWorkingSetSize
    import resource
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform=="darwin" else value*1024)


def fingerprint(result):
    winner=result.winner
    payload={"status":result.status,"complete":result.complete,"count":result.scored_count,"diagnostics":result.diagnostics,
             "candidate":winner.verified.candidate.key if winner else None,"score":winner.score if winner else None}
    return hashlib.sha256(encode(payload).encode()).hexdigest()


def execute(rows,cached):
    query=OfflineQuery(rows);engine=RequestCandidateEngine(query);request=StructuredOutfitRequest()
    if cached:
        result,info=CachedRuleBasedRecommendationScorer(engine,Preferences()).rank_with_cache_info("synthetic-owner",request,"rule_based_request_led")
    else:
        result=RuleBasedRecommendationScorer(engine,Preferences()).rank("synthetic-owner",request,"rule_based_request_led");info=None
    if not result.complete:raise RuntimeError("Incomplete experiment stream.")
    return result,info


def workload_counts(counts):
    t,b,d,o=counts
    return {"candidates":(t*b+d)*(1+o),"pair_visits":t*b+3*t*b*o+d*o,"unique_pairs":t*b+(t+b+d)*o}


def memory_worker(size,heavy,cached):
    startup=peak_rss();rows,counts=synthetic_wardrobe(size,varied=True,heavy=heavy)
    input_peak=peak_rss();result,info=execute(rows,cached)
    return {"startup_peak_rss_bytes":startup,"input_peak_rss_bytes":input_peak,"peak_rss_bytes":peak_rss(),
            "fingerprint":fingerprint(result),"complete":result.complete,"status":result.status,
            "cache":asdict(info) if info else None,"counts":workload_counts(counts)}


def benchmark(size,heavy,repeats,memory):
    rows,counts=synthetic_wardrobe(size,varied=True,heavy=heavy);expected=workload_counts(counts)
    runs=[];expected_hash=None
    for pair in range(repeats):
        order=(False,True) if pair%2==0 else (True,False)
        measured={}
        for cached in order:
            gc.collect()
            start=time.perf_counter();result,info=execute(rows,cached);seconds=time.perf_counter()-start
            trace=fingerprint(result)
            if expected_hash is None:expected_hash=trace
            if trace!=expected_hash:raise RuntimeError("Cached/uncached full-result mismatch.")
            if info:
                assert info.visits==expected["pair_visits"] and info.misses==expected["unique_pairs"] and info.evictions==0
                assert int(dict(result.diagnostics)["accepted_examined"])==expected["candidates"]
            else:assert int(dict(result.diagnostics)["accepted_examined"])==expected["candidates"]
            record={"seconds":seconds,"fingerprint":trace,"status":result.status,"scored":result.scored_count,
                    "cache":asdict(info) if info else None}
            measured["cached" if cached else "uncached"]=record
            print(f"size={size} heavy={heavy} pair={pair+1} arm={'cached' if cached else 'uncached'} seconds={seconds:.6f}",flush=True)
        runs.append({"order":["cached" if x else "uncached" for x in order],**measured})
    rss={}
    if memory:
        for cached in (False,True):
            command=[sys.executable,"-B",str(Path(__file__).resolve()),"--memory-worker",str(size),"--arm","cached" if cached else "uncached"]
            if heavy:command.append("--heavy")
            worker=json.loads(subprocess.run(command,check=True,capture_output=True,text=True,encoding="utf-8").stdout)
            if worker["fingerprint"]!=expected_hash:raise RuntimeError("Memory worker result mismatch.")
            rss["cached" if cached else "uncached"]=worker
            print(f"size={size} heavy={heavy} memory arm={'cached' if cached else 'uncached'} peak_rss={worker['peak_rss_bytes']}",flush=True)
    old=[r["uncached"]["seconds"] for r in runs];new=[r["cached"]["seconds"] for r in runs]
    differences=[(a-b)/a*100 for a,b in zip(old,new)]
    return {"size":size,"heavy":heavy,"structural_counts":counts,"expected":expected,"runs":runs,"memory":rss,
            "summary":{"uncached_median_seconds":statistics.median(old),"cached_median_seconds":statistics.median(new),
                       "uncached_range_seconds":[min(old),max(old)],"cached_range_seconds":[min(new),max(new)],
                       "paired_improvements_percent":differences,"paired_improvement_median_percent":statistics.median(differences),
                       "median_ratio_speedup":statistics.median(old)/statistics.median(new)}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes",type=int,nargs="*",default=[20,50,100,200]);parser.add_argument("--heavy",action="store_true")
    parser.add_argument("--pairs",type=int,default=6);parser.add_argument("--memory",action="store_true")
    parser.add_argument("--output",type=Path);parser.add_argument("--memory-worker",type=int)
    parser.add_argument("--arm",choices=("cached","uncached"),default="cached");args=parser.parse_args()
    if args.memory_worker:
        print(json.dumps(memory_worker(args.memory_worker,args.heavy,args.arm=="cached")));return
    if args.output is None or args.pairs<1 or any(size<10 for size in args.sizes):parser.error("new output, sizes>=10 and positive pair count required")
    repository=Path(__file__).resolve().parents[2];target=args.output.resolve()
    if target.exists() or not target.is_relative_to(repository/'storage'):parser.error("new output inside repository storage required")
    report={"version":"1.0.0","kind":"interleaved_full_pipeline_pair_cache_experiment","complete":False,
            "synthetic":True,"python":sys.version,"platform":platform.platform(),"capacity":19900,"pairs":args.pairs,
            "gc_enabled":gc.isenabled(),"python_hash_seed":os.getenv("PYTHONHASHSEED"),"memory_method":"fresh-process peak RSS; includes interpreter and input, not tracemalloc",
            "profile":"rule_based_request_led","request":"no optional fields","preferences":[],"workloads":[],
            "source_hashes":{p.relative_to(repository).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in (Path(__file__),RULES,PROFILES,*((repository/'backend/app/application/recommendation').glob('*pair_cache*.py')),
                                       *((repository/'backend/app/application/recommendation').glob('cached_rule_based*.py')))}}
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
    for size,heavy in [(x,False) for x in args.sizes]+([(200,True)] if args.heavy else []):
        report["workloads"].append(benchmark(size,heavy,args.pairs,args.memory))
        target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    report["complete"]=True;target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print("Complete report:",target,flush=True)


if __name__=="__main__":main()
