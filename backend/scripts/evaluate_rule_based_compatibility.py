"""Reproducible synthetic rule/coverage/weight/performance evaluation, not fashion validation.

Run from backend. No database, HTTP, frontend or model calls. No candidate truncation.
Memory is a separate complete tracemalloc pass, not RSS or the uninstrumented timing.
"""
import argparse
from dataclasses import asdict,replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import tracemalloc
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.audit_compatibility_coverage import synthetic_wardrobe,OfflineQuery
from app.application.recommendation.rule_based_compatibility_scorer import RuleBasedCompatibilityScorer
from app.application.recommendation.rule_based_recommendation_scorer import RuleBasedRecommendationScorer
from app.application.recommendation.rule_based_compatibility_policy import RuleBasedCompatibilityPolicy,RuleBasedScoringProfile,RULES,PROFILES,digest
from app.application.recommendation.recommendation_scorer import RecommendationScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
from app.domain.value_objects.compatibility_signature import STRUCTURES


class Preferences:
    def __init__(self,rows=()):self.rows=rows
    def get_active_preferences(self,user_id):return self.rows


def fraction(value):
    return None if value is None else {"numerator":value.numerator,"denominator":value.denominator}


def result_json(result):
    winner=result.winner
    return {"status":result.status,"complete":result.complete,"scored":result.scored_count,
            "diagnostics":result.diagnostics,"winner":list(winner.verified.candidate.key) if winner else None,
            "components":{k:fraction(getattr(winner.score,k).summary.value) for k in ("request_match","compatibility","preference")} if winner else None,
            "total":fraction(winner.score.total) if winner else None}


def run(rows,experimental=True,profile="rule_based_request_led",preferences=()):
    engine=RequestCandidateEngine(OfflineQuery(rows))
    scorer=(RuleBasedRecommendationScorer if experimental else RecommendationScorer)(engine,Preferences(preferences))
    return scorer.rank(rows[0].user_id if rows else "synthetic-owner",StructuredOutfitRequest(),profile if experimental else "compatibility_deferred")


def labelled_examples():
    rows,_=synthetic_wardrobe(10)
    base={r.category:r for r in rows}
    def row(cat,id,colour="blue",style=("classic",)):
        return replace(base[cat],garment_id=id,primary_colour=colour,style_tags=style)
    t=row("vest","top");b=row("trousers","bottom");d=row("vest_dress","dress");o=row("long_sleeve_outwear","outerwear")
    return [("complete_two_piece",[t,b]),("complete_three_piece",[t,b,o]),("single_dress",[d]),
            ("dress_outerwear",[d,o]),("computed_zero",[t,replace(b,primary_colour="red",style_tags=("sporty",))]),
            ("missing_style",[t,replace(b,style_tags=None)]),("empty_style",[t,replace(b,style_tags=())]),
            ("unsupported_style",[t,replace(b,style_tags=("classic","not-approved"))]),
            ("malformed_style",[t,replace(b,style_tags=None,invalid_attributes=("style_tags",))]),
            ("unrecognized_hex",[t,replace(b,primary_colour="#234567")]),
            ("mixed_available_unknown",[t,b,d,o]),
            ("repeated_colour_different_style",[t,replace(b,style_tags=("sporty",))])]


def coverage_examples():
    report=[];structures={roles:name for name,roles in STRUCTURES.items()}
    totals={name:{"candidates":0,"available":0,"unknown":0,"no_pairs":0,"partial":0} for name in STRUCTURES}
    blocked=0;missing={"colour":0,"style":0};garment_count=0
    for label,rows in labelled_examples():
        scorer=RuleBasedCompatibilityScorer();entries=[]
        request=StructuredOutfitRequest()
        session=RequestCandidateEngine(OfflineQuery(rows)).generate_candidates("synthetic-owner",request)
        gate=ScoringEligibilityGate(session,"synthetic-owner",request)
        for item in session:
            verified=gate.verify(item);c=scorer.score(verified)
            structure=structures[tuple(x.role for x in verified.candidate.members)]
            bucket=totals[structure];bucket["candidates"]+=1
            bucket["available" if c.summary.value is not None else "unknown"]+=1
            bucket["no_pairs"]+=int("no_pair_relationships" in c.summary.reasons)
            bucket["partial"]+=int(0<c.summary.observed<c.summary.possible)
            entries.append({"structure":structure,"key":verified.candidate.key,"C":fraction(c.summary.value),
                            "state":c.summary.state,"observed":c.summary.observed,"possible":c.summary.possible,
                            "rules":[{"name":x.name,"value":fraction(x.value),"state":x.state,"reasons":x.reasons} for x in c.details]})
        assert session.result.complete
        session.close()
        for row in rows:
            prepared=scorer.evidence.classify(row);garment_count+=1
            missing["colour"]+=int(prepared.colour_state!="Known")
            missing["style"]+=int(prepared.style_state!="Known")
        outcomes={name:result_json(run(rows,profile=name)) for name in ("rule_based_request_led","rule_based_balanced")}
        is_blocked=outcomes["rule_based_request_led"]["status"]=="InsufficientEvidence"
        blocked+=is_blocked
        report.append({"label":label,"synthetic":True,"snapshots_sha256":digest([asdict(x) for x in rows]),
                       "candidates":entries,"profiles":outcomes,"compatibility_gate_blocked":is_blocked})
    for bucket in totals.values():
        bucket["coverage"]=bucket["available"]/bucket["candidates"] if bucket["candidates"] else None
    return {"sessions":report,"coverage_by_structure":totals,"blocked_sessions":blocked,"total_sessions":len(report),
            "blocked_session_percentage":100*blocked/len(report),"garment_observations":garment_count,
            "missing_or_unusable":missing,"missing_or_unusable_rates":{k:v/garment_count for k,v in missing.items()}}


def weight_sensitivity():
    rows,_=synthetic_wardrobe(10);base={r.category:r for r in rows}
    rows=[replace(base["vest"],garment_id="top",primary_colour="blue",style_tags=("vintage",)),
          replace(base["trousers"],garment_id="red-bottom",primary_colour="red",style_tags=("vintage",)),
          replace(base["trousers"],garment_id="black-bottom",primary_colour="black",style_tags=("vintage",))]
    prefs=[PreferenceSnapshot("red","synthetic-owner","colours",'{"values":["red"]}',"0.6",None,True),
           PreferenceSnapshot("classic","synthetic-owner","styles",'{"values":["classic"]}',"0.4",None,True)]
    return {name:result_json(run(rows,profile=name,preferences=prefs)) for name in ("rule_based_request_led","rule_based_balanced")}


def benchmark(size,heavy,memory,repeats):
    rows,counts=synthetic_wardrobe(size,varied=True,heavy=heavy)
    expected=(counts[0]*counts[1]+counts[2])*(1+counts[3]);arms={}
    for experimental,name in ((False,"deferred_baseline"),(True,"rule_based")):
        times=[];result=None
        for _ in range(repeats):
            start=time.perf_counter();result=run(rows,experimental);times.append(time.perf_counter()-start)
            assert result.complete
            examined=int(dict(result.diagnostics)["accepted_examined"]) if experimental else result.scored_count
            assert examined==expected
        peak=None
        if memory:
            tracemalloc.start()
            measured=run(rows,experimental)
            _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            assert measured.complete and measured.status==result.status
        arms[name]={"seconds":times,"tracemalloc_peak_bytes":peak,"result":result_json(result)}
        print(f"benchmark size={size} heavy={heavy} arm={name} candidates={expected} seconds={times} peak={peak}",flush=True)
    return {"size":size,"heavy":heavy,"counts":counts,"candidates":expected,"synthetic":True,
            "input_sha256":digest([asdict(x) for x in rows]),"arms":arms,
            "wall_delta_seconds":arms["rule_based"]["seconds"][0]-arms["deferred_baseline"]["seconds"][0],
            "peak_delta_bytes":arms["rule_based"]["tracemalloc_peak_bytes"]-arms["deferred_baseline"]["tracemalloc_peak_bytes"] if memory else None}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes",nargs="*",type=int,default=[20,50,100,200]);parser.add_argument("--heavy",action="store_true")
    parser.add_argument("--measure-memory",action="store_true");parser.add_argument("--repeats",type=int,default=1)
    parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    if args.repeats<1 or any(x<10 for x in args.sizes):parser.error("positive repeats and sizes >=10 required")
    target=args.output.resolve();backend=Path(__file__).resolve().parents[1];repository=backend.parent
    if target.exists() or not target.is_relative_to(repository/'storage'):
        parser.error("Use a new report path inside repository storage; source and existing artifacts are protected.")
    policy=RuleBasedCompatibilityPolicy.load()
    report={"kind":"synthetic_rule_based_compatibility_evaluation","version":"1.0.0","human_validated":False,
            "fashion_accuracy":None,"nfr02_achieved":False,"python":sys.version,"platform":platform.platform(),
            "policy_version":policy.version,"policy_hash":policy.hash,"profiles_hash":hashlib.sha256(PROFILES.read_bytes()).hexdigest(),
            "coverage":coverage_examples(),"weight_sensitivity":weight_sensitivity(),"benchmarks":[],
            "methodology":"Uninstrumented backend passes; separate full tracemalloc passes, not RSS. Synthetic varied annotations. No HTTP/browser/model acceptance or statistical latency claim."}
    target.parent.mkdir(parents=True,exist_ok=True)
    for size in args.sizes:
        report["benchmarks"].append(benchmark(size,False,args.measure_memory,args.repeats))
    if args.heavy:report["benchmarks"].append(benchmark(200,True,args.measure_memory,args.repeats))
    report["script_sha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with target.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
    print("Report:",target,flush=True)


if __name__=="__main__":main()
