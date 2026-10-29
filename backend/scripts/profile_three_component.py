"""Isolated diagnostic service profiles, not clean latency/NFR observations."""
import argparse,cProfile,json,pstats,sys,os,tracemalloc
from pathlib import Path
from time import perf_counter,process_time
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--allocation',action='store_true');p.add_argument('--facts-file',type=Path);args=p.parse_args()
if args.output.exists():raise SystemExit('Refusing to overwrite retained diagnostic output')
args.output.mkdir(parents=True)
from tests import assistant_decision_server as fixture
from app.application.nlp.nlp_interpreter import NLPInterpreter
from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.persistence.active_preference_query_adapter import SqliteActivePreferenceQuery
from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
from scripts.benchmark_compact_exhaustive import memory
if args.facts_file:
 import importlib.util
 import app.application.recommendation.compact_exhaustive_scorer as kernel_module
 spec=importlib.util.spec_from_file_location('frozen_compact_facts',args.facts_file)
 frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
 kernel_module.CompactScoringFacts=frozen.CompactScoringFacts
created=[];original=CompactExhaustiveScorer.__init__
def observed(self,*a,**kw):
    kw['diagnostics']=True;original(self,*a,**kw);created.append(self)
CompactExhaustiveScorer.__init__=observed
rows=[]
try:
 for size in (('50','200') if args.allocation else ('50','100','200')):
  for profile in (('experimental_compatibility_decision_v1',) if args.allocation else ('compatibility_deferred','experimental_compatibility_decision_v1')):
   name=size+'-'+profile;service=OutfitAssistantService(NLPInterpreter(),RequestCandidateEngine(SqliteConfirmedGarmentQuery()),SqliteActivePreferenceQuery(),SqliteRecommendationRepository(fixture.db.DATABASE_PATH),scoring_profile=profile,execution_engine='compact_exhaustive')
   profiler=cProfile.Profile();before=memory()
   if args.allocation:tracemalloc.start()
   wall,cpu=perf_counter(),process_time()
   if not args.allocation:profiler.enable()
   result=service.recommend(fixture.workloads[size]['owner'],str(uuid4()),'Suggest an outfit with vintage style')
   if not args.allocation:profiler.disable()
   row={'size':size,'profile':profile,'instrumented':True,'wall':perf_counter()-wall,'cpu':process_time()-cpu,'status':result['status'],'service_stages':result.get('timings'),'kernel_stages':created[-1].timings,'cache':created[-1].cache_statistics,'memory_before':before,'memory_after':memory(),'count':result.get('provenance',{}).get('scored_count')}
   if args.allocation:
    row['python_traced_current'],row['python_traced_peak']=tracemalloc.get_traced_memory();tracemalloc.stop()
   else:
    profiler.dump_stats(str(args.output/(name+'.prof')))
    stats=pstats.Stats(profiler);row['functions']=[{'file':key[0],'line':key[1],'function':key[2],'primitive_calls':v[0],'calls':v[1],'self_seconds':v[2],'cumulative_seconds':v[3]} for key,v in sorted(stats.stats.items(),key=lambda item:item[1][3],reverse=True)[:70]]
   rows.append(row);(args.output/'summary.json').write_text(json.dumps({'instrumented':True,'not_nfr':True,'metadata':fixture.metadata(),'rows':rows},indent=2));print(json.dumps({k:v for k,v in row.items() if k!='functions'}),flush=True)
   assert result['status']=='Selected' and row['count']==fixture.workloads[size]['candidate_count']
finally:fixture.temporary.cleanup()
