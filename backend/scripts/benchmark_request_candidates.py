"""Compare category short-circuit evaluation with exhaustive minimum filtering."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import tracemalloc

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
from scripts.benchmark_structural_candidates import SyntheticQuery
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest,GarmentCategoryConstraint


def benchmark(sizes):
    results = []
    request = StructuredOutfitRequest(colours=("blue",),style="vintage",garment_categories=(GarmentCategoryConstraint("category","trousers"),))
    for size in sizes:
        counts = {"top":int(size*0.4),"bottom":int(size*0.4),"dress":int(size*0.1)}
        counts["outerwear"] = size-sum(counts.values())
        query = SyntheticQuery(counts)
        query.rows = tuple(replace(item,primary_colour="blue" if index % 2 == 0 else "black",style_tags=("vintage",) if index % 3 == 0 else None) for index,item in enumerate(query.rows))
        records = []
        for optimized in (False,True):
            engine = RequestCandidateEngine(query,optimized=optimized)
            started = time.perf_counter()
            session = engine.generate_candidates("benchmark",request)
            digest = hashlib.sha256()
            for item in session:
                digest.update(json.dumps(item.candidate.key,separators=(",",":")).encode())
            elapsed = time.perf_counter()-started
            tracemalloc.start()
            traced = engine.generate_candidates("benchmark",request)
            for _ in traced:
                pass
            _,peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            if not session.result.complete or traced.result != session.result:
                raise RuntimeError("Incomplete or inconsistent benchmark.")
            records.append({"optimized":optimized,"seconds":elapsed,"peak_traced_working_bytes":peak,
                            "examined":session.result.examined,"passed":session.result.passed,"failed":session.result.failed,"unknown":session.result.unknown,
                            "evidence_cache_size":session.evidence_cache_size,"complete":session.result.complete,"accepted_keys_sha256":digest.hexdigest()})
        if records[0]["accepted_keys_sha256"] != records[1]["accepted_keys_sha256"] or any(records[0][key] != records[1][key] for key in ("examined","passed","failed","unknown")):
            raise RuntimeError("Optimized and exhaustive results differ.")
        result = {"size":size,"role_counts":counts,"runs":records}
        results.append(result)
        print(json.dumps(result),flush=True)
    return {"python":platform.python_version(),"platform":platform.platform(),"method":"Synthetic prebuilt snapshots; includes policy initialization, retrieval and exhaustive structure/request evaluation. Timing without tracemalloc; separate full traced pass for Python allocations, not RSS. No SQL/scoring/frontend. One run per setting; warmed allocator affects memory.","request":request.to_dict(),"results":results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes",nargs="+",type=int,default=[20,50,100,200])
    parser.add_argument("--output",type=Path)
    args = parser.parse_args()
    if any(size < 10 for size in args.sizes):
        parser.error("Sizes must be at least ten.")
    result = benchmark(args.sizes)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
