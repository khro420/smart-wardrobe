"""J8 isolated cProfile of actual service, never a clean latency result."""
import sys,os,json,argparse,cProfile,pstats,time
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():raise SystemExit('refusing overwrite')
a.output.mkdir(parents=True)
from tests import evidence_diversity_server as s
from app.application.nlp.nlp_interpreter import NLPInterpreter
from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.persistence.active_preference_query_adapter import SqliteActivePreferenceQuery
from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
created=[];init=CompactExhaustiveScorer.__init__
def observed(self,*args,**kwargs):kwargs['diagnostics']=True;init(self,*args,**kwargs);created.append(self)
CompactExhaustiveScorer.__init__=observed
rows=[]
try:
 for profile in ('compatibility_deferred','experimental_compatibility_decision_v1'):
  for fields,enabled in (('generic',False),('suitability',True),('generic',True),('suitability',False)):
   evaluator=SuitabilityRequestEvaluator if enabled else RequestConstraintEvaluator
   service=OutfitAssistantService(NLPInterpreter(),RequestCandidateEngine(SqliteConfirmedGarmentQuery(),evaluator_factory=evaluator),SqliteActivePreferenceQuery(),SqliteRecommendationRepository(s.fixture.db.DATABASE_PATH),scoring_profile=profile,execution_engine='compact_exhaustive')
   name=profile+'-'+fields+('-enabled' if enabled else '-disabled');prof=cProfile.Profile();start,cpu=time.perf_counter(),time.process_time();prior=len(created);prof.enable()
   r=service.recommend('j7-varied-200',str(uuid4()),s.PLAN['requests'][fields]);prof.disable();elapsed=time.perf_counter()-start
   row=dict(name=name,profile=profile,fields=fields,suitability=enabled,status=r['status'],wall=elapsed,cpu=time.process_time()-cpu,stages=r.get('timings'),scored=(r.get('provenance') or {}).get('scored_count'),instrumented=True)
   if len(created)>prior:row.update(kernel=created[-1].timings,cache=created[-1].cache_statistics)
   prof.dump_stats(str(a.output/(name+'.prof')))
   stats=pstats.Stats(prof);row['functions']=[dict(file=k[0],line=k[1],function=k[2],primitive_calls=v[0],calls=v[1],self_seconds=v[2],cumulative_seconds=v[3]) for k,v in sorted(stats.stats.items(),key=lambda x:x[1][3],reverse=True)[:120]]
   rows.append(row);(a.output/'summary.json').write_text(json.dumps(rows,indent=2));print(name,r['status'],round(elapsed,3),flush=True)
finally:s.fixture.temporary.cleanup()
