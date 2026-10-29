"""Focused full-pipeline A/B/C profiling; cumulative times overlap, not wall time."""
import argparse
from dataclasses import asdict
import cProfile
import hashlib
import json
from pathlib import Path
import platform
import pstats
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.audit_compatibility_coverage import synthetic_wardrobe, OfflineQuery
from scripts.evaluate_rule_based_compatibility import Preferences
from scripts.benchmark_compatibility_pair_cache import fingerprint, workload_counts
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.recommendation_scorer import RecommendationScorer
from app.application.recommendation.cached_rule_based_recommendation_scorer import CachedRuleBasedRecommendationScorer
from app.application.recommendation.decision_recommendation_scorer import DecisionRecommendationScorer
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest


def execute(rows, arm):
    engine, prefs, request = RequestCandidateEngine(OfflineQuery(rows)), Preferences(), StructuredOutfitRequest()
    if arm == "A": return RecommendationScorer(engine,prefs).rank("synthetic-owner",request,"compatibility_deferred"),None
    if arm == "B": return CachedRuleBasedRecommendationScorer(engine,prefs).rank_with_cache_info("synthetic-owner",request,"rule_based_request_led")
    if arm == "C": return DecisionRecommendationScorer(engine,prefs).rank_with_cache_info("synthetic-owner",request)
    if arm == "D":
        from app.application.recommendation.prepared_decision_scorer import PreparedDecisionRecommendationScorer
        return PreparedDecisionRecommendationScorer(engine,prefs).rank_with_cache_info("synthetic-owner",request)
    raise ValueError("Unknown experiment arm")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size",type=int,default=100); parser.add_argument("--heavy",action="store_true")
    parser.add_argument("--arms",nargs="+",choices=list("ABCD"),default=list("ABC"))
    parser.add_argument("--output",type=Path,required=True); args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]; target=args.output.resolve()
    if target.exists() or not target.is_relative_to(root/"storage"): parser.error("New output inside storage required")
    rows,counts=synthetic_wardrobe(args.size,varied=True,heavy=args.heavy)
    result={"version":"1.0.0","synthetic":True,"size":args.size,"heavy":args.heavy,
            "expected":workload_counts(counts),"python":sys.version,"platform":platform.platform(),"arms":{}}
    for arm in args.arms:
        profiler=cProfile.Profile();start=time.perf_counter();profiler.enable()
        outcome,cache=execute(rows,arm)
        profiler.disable(); elapsed=time.perf_counter()-start
        if not outcome.complete: raise RuntimeError("Incomplete profile stream")
        entries=[]
        for (file,line,name),(primitive,calls,self_time,cumulative,callers) in pstats.Stats(profiler).stats.items():
            entries.append({"file":file,"line":line,"name":name,"primitive_calls":primitive,"calls":calls,
                            "self_seconds":self_time,"cumulative_seconds":cumulative})
        result["arms"][arm]={"profiled_wall_seconds":elapsed,"status":outcome.status,"scored":outcome.scored_count,
                              "fingerprint":fingerprint(outcome),"cache":asdict(cache) if cache else None,
                              "functions":sorted(entries,key=lambda x:x["cumulative_seconds"],reverse=True)}
        print(arm, "profiled wall", elapsed, "status",outcome.status,flush=True)
    result["source_hashes"]={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in (root/"backend/app").rglob("*.py")}
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("x",encoding="utf-8") as stream: json.dump(result,stream,indent=2)


if __name__=="__main__": main()
