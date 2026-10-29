"""Synthetic exhaustive Phase 3A benchmark; no scoring or end-to-end claim."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import tracemalloc

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
from app.application.recommendation.recommendation_engine import RecommendationEngine
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot


class SyntheticQuery:
    """Prebuilt contract fixtures, not a database-confirmation benchmark."""
    def __init__(self, counts):
        self.rows = []
        for role,category in (("top","vest"),("bottom","trousers"),("dress","vest_dress"),("outerwear","long_sleeve_outwear")):
            structural,layer = GARMENT_STRUCTURE[category]
            for index in range(counts[role]):
                identifier = f"{role}-{index:06d}"
                self.rows.append(ConfirmedGarmentSnapshot(identifier,"benchmark","available",category,identifier,"media",False,"time",structural_role=structural,layering_index=layer))
        self.rows = tuple(self.rows)
    def get_confirmed_available_garments(self,user_id):
        assert user_id == "benchmark"
        return self.rows


def run(sizes):
    records = []
    engine_warmup = RecommendationEngine(SyntheticQuery({"top":1,"bottom":1,"dress":0,"outerwear":0}))
    list(engine_warmup.generate_homepage_candidates("benchmark"))
    for size in sizes:
        counts = {"top":int(size*0.4),"bottom":int(size*0.4),"dress":int(size*0.1)}
        counts["outerwear"] = size-sum(counts.values())
        query = SyntheticQuery(counts)
        engine = RecommendationEngine(query)
        expected = (counts["top"]*counts["bottom"]+counts["dress"])*(1+counts["outerwear"])
        tracemalloc.start()
        start = time.perf_counter()
        session = engine.generate_homepage_candidates("benchmark")
        count = 0
        for candidate in session:
            count += 1
        elapsed = time.perf_counter()-start
        _,peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        if count != expected or not session.result.complete or session.result.status != "StructuralCandidates":
            raise RuntimeError("Incomplete or incorrect enumeration; benchmark not successful.")
        # Tracemalloc has significant per-allocation overhead. Measure a second
        # complete pass without it rather than reporting profiling time as API
        # latency. Both passes must enumerate the same exhaustive count.
        plain_start = time.perf_counter()
        plain_session = engine.generate_homepage_candidates("benchmark")
        plain_count = sum(1 for _ in plain_session)
        plain_elapsed = time.perf_counter()-plain_start
        if plain_count != expected or not plain_session.result.complete:
            raise RuntimeError("Uninstrumented pass did not complete.")
        record = {"wardrobe_size":size,"role_counts":counts,"expected_candidates":expected,"actual_candidates":count,
                  "elapsed_seconds":elapsed,"uninstrumented_seconds":plain_elapsed,"peak_working_memory_bytes":peak,"complete":session.result.complete,"status":session.result.status}
        records.append(record)
        print(json.dumps(record),flush=True)
    paths = sorted((BACKEND/"app/application/recommendation").glob("*.py")) + [BACKEND/"app/application/recommendation/config/structure.v1.json",BACKEND/"app/domain/value_objects/outfit_candidate.py",BACKEND/"app/domain/value_objects/candidate_generation_result.py",Path(__file__)]
    return {"measured_at":datetime.now(timezone.utc).isoformat(),"python":platform.python_version(),"os":platform.platform(),
            "processor":platform.processor(),"logical_cpu_count":os.cpu_count(),"policy_version":"1.0.0",
            "source_sha256":{str(path.relative_to(BACKEND)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
            "method":"One traced-memory pass and one uninstrumented timing pass per size; fixture construction/policy loading excluded; retrieval, validation and full streaming enumeration included; candidates not retained. Peak is Python traced working allocations, not RSS. Allocator reuse/warmup can make peaks nonmonotonic. No SQL, scoring, persistence, random selection or browser latency.","records":records}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes",nargs="+",type=int,default=[20,50,100,200])
    parser.add_argument("--output",type=Path)
    args = parser.parse_args()
    if any(size < 10 for size in args.sizes):
        parser.error("Use sizes at least ten so both base slots are populated.")
    result = run(args.sizes)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
