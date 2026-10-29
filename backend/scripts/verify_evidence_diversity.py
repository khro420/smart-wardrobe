"""Offline J7 observer: instrumentation excluded from clean transport timings."""
import sys,json,hashlib,argparse,time,tracemalloc
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests import evidence_diversity_server as server
from app.application.recommendation import compact_exhaustive_scorer as kernel
from app.application.recommendation.compact_scoring_facts import CompactScoringFacts
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.persistence.active_preference_query_adapter import SqliteActivePreferenceQuery
from app.application.nlp.nlp_interpreter import NLPInterpreter
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
if args.output.exists():raise SystemExit('Refusing overwrite')
args.output.mkdir(parents=True)
observed=[]
class Observer(CompactScoringFacts):
 def __init__(self,*a,**kw):
  super().__init__(*a,**kw);seen=set();original=self._score
  def score(*args):seen.add(args);return original(*args)
  object.__setattr__(self,'_score',score);object.__setattr__(self,'observed_keys',seen);object.__setattr__(self,'original_score',original);observed.append(self)
 # preserve normal cache diagnostics while recording exact keys in this isolated observer only
 @property
 def cache_info(self):
  return dict(pairs=len(self.pairs),capacity=self.pair_capacity,hits=self.hits,misses=self.misses,evictions=self.evictions,aggregations=tuple(fn.cache_info()._asdict() for fn in (self._request,self._preference,self._decision,self.original_score)))
kernel.CompactScoringFacts=Observer
rows=[]
try:
 cells=list(dict.fromkeys((s['workload'],s['request'],s['profile']) for s in server.PLAN['schedule']))
 for name,request,profile in cells:
  interpreted=NLPInterpreter().interpret(server.PLAN['requests'][request])
  if interpreted.status!='Supported':rows.append(dict(workload=name,request=request,profile=profile,status=interpreted.status));continue
  counts={}; ledger=hashlib.sha256()
  def checkpoint(stage,*data):
   if stage=='closed':counts.update(structural=data[0],scored=data[1])
  evaluator=SuitabilityRequestEvaluator if request=='suitability' else RequestConstraintEvaluator
  k=kernel.CompactExhaustiveScorer(SqliteConfirmedGarmentQuery(),SqliteActivePreferenceQuery(),profile,evaluator_type=evaluator,checkpoint=checkpoint,diagnostics=True)
  tick=time.perf_counter();cpu=time.process_time();r=k.rank('j7-'+name,interpreted.structured_request)
  elapsed=time.perf_counter()-tick
  f=observed.pop();cache=k.cache_statistics;total=cache['aggregations'][-1];miss=total['misses'];hit=total['hits']
  row=dict(workload=name,request=request,profile=profile,status=r.status,complete=r.complete,counts=counts,unique_certificates=len(f.observed_keys),validation_calls=miss,certificate_hits=hit,certificate_misses=miss,certificate_evictions=max(0,miss-total['currsize']),reuse_rate=hit/(hit+miss) if hit+miss else 0,cache=cache,wall=elapsed,cpu=time.process_time()-cpu,stages=k.timings,diagnostics=r.diagnostics,winner_id=r.winner.verified.candidate.candidate_id if r.winner else None)
  rows.append(row);(args.output/'summary.json').write_text(json.dumps(rows,indent=2,default=str));print(name,request,profile,r.status,counts,'unique',row['unique_certificates'],'miss',miss,flush=True)
  del f,k
 (args.output/'summary.json').write_text(json.dumps(rows,indent=2,default=str))
finally:server.fixture.temporary.cleanup()

