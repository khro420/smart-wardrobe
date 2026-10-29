"""Instrumented full Assistant backend on synthetic strict-confirmed SQLite data."""
import argparse
import functools
import hashlib
import json
from pathlib import Path
import platform
import sys
import tempfile
from time import perf_counter

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
from benchmark_homepage_recommendation import seed
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.persistence import active_preference_query_adapter as prefs
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
from app.application.nlp.nlp_interpreter import NLPInterpreter
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.recommendation.request_match_scorer import RequestMatchScorer
from app.application.recommendation.preference_scorer import PreferenceScorer
from app.application.recommendation.compatibility_scorer import CompatibilityScorer
from app.application.recommendation.candidate_generator import CandidateGenerator


def run(sizes):
    records, originals, totals = [], [], {}
    def instrument(cls,name,label):
        original = getattr(cls,name)
        @functools.wraps(original)
        def timed(*args,**kwargs):
            start = perf_counter()
            try: return original(*args,**kwargs)
            finally: totals[label] = totals.get(label,0)+perf_counter()-start
        originals.append((cls,name,original))
        setattr(cls,name,timed)
    for cls,name,label in [(RequestConstraintEvaluator,'evaluate','mandatory_evaluation_including_gate_recheck_seconds'),
        (RequestMatchScorer,'score','request_scoring_seconds'),(PreferenceScorer,'score','preference_scoring_seconds'),
        (CompatibilityScorer,'score','deferred_compatibility_overhead_seconds')]:
        instrument(cls,name,label)
    original_enumerate = CandidateGenerator.enumerate
    def enumerate_timed(self,*args,**kwargs):
        stream = original_enumerate(self,*args,**kwargs)
        while True:
            start = perf_counter()
            try: item = next(stream)
            except StopIteration: return
            finally: totals['candidate_construction_seconds'] = totals.get('candidate_construction_seconds',0)+perf_counter()-start
            yield item
    originals.append((CandidateGenerator,'enumerate',original_enumerate))
    CandidateGenerator.enumerate = enumerate_timed
    old_database, old_preferences = db.DATABASE_PATH,prefs.DATABASE_PATH
    try:
        with tempfile.TemporaryDirectory(prefix='assistant-benchmark-') as directory:
            for size in sizes:
                db.DATABASE_PATH = prefs.DATABASE_PATH = Path(directory)/f'{size}.db'
                db.initialise_database()
                counts = seed(size)
                with db.connection() as c:
                    c.execute("UPDATE garments SET primary_colour='blue',style_tags='[\"vintage\"]'")
                totals.clear()
                class Query:
                    def get_confirmed_available_garments(self,user_id):
                        start = perf_counter()
                        try: return SqliteConfirmedGarmentQuery().get_confirmed_available_garments(user_id)
                        finally: totals['retrieval_seconds'] = perf_counter()-start
                def checkpoint(stage,conn):
                    if stage == 'revalidated': totals['lock_revalidation_seconds'] = perf_counter()-totals['write_start']
                class Repository(SqliteRecommendationRepository):
                    def persist_assistant(self,command):
                        totals['write_start'] = perf_counter()
                        result = super().persist_assistant(command)
                        totals['write_readback_commit_seconds'] = perf_counter()-totals['write_start']-totals['lock_revalidation_seconds']
                        return result
                service = OutfitAssistantService(NLPInterpreter(),RequestCandidateEngine(Query()),prefs.SqliteActivePreferenceQuery(),Repository(db.DATABASE_PATH,checkpoint))
                start = perf_counter()
                result = service.recommend('benchmark',f'size-{size}','Suggest an outfit with vintage style')
                elapsed = perf_counter()-start
                expected = (counts['top']*counts['bottom']+counts['dress'])*(1+counts['outerwear'])
                if result['status']!='Selected' or result['provenance']['scored_count']!=expected:
                    raise RuntimeError(f'Incomplete/incorrect benchmark: {result["status"]}')
                record = {'garments':size,'role_counts':counts,'candidates_scored':expected,'total_seconds':elapsed,
                    **result['timings'],**{k:v for k,v in totals.items() if k!='write_start'}}
                records.append(record)
                print(json.dumps(record),flush=True)
    finally:
        db.DATABASE_PATH,prefs.DATABASE_PATH = old_database,old_preferences
        for cls,name,original in originals: setattr(cls,name,original)
    sources = [Path(__file__),BACKEND/'app/application/recommendation/outfit_assistant_service.py',BACKEND/'app/application/recommendation/recommendation_scorer.py']
    return {'python':platform.python_version(),'platform':platform.platform(),'processor':platform.processor(),
        'method':'One instrumented trial per synthetic SQLite size. Actual NLP, mandatory evaluation and independent gate recheck, exact scoring/ranking and atomic persistence. No stored preferences; all garments annotated vintage. Fixture creation/migration and HTTP/browser/CV excluded. Timers add overhead; ranking includes mandatory/gate/scoring/construction costs, so do not sum overlapping metrics. No candidate materialization/truncation or browser/NFR compliance claim.',
        'source_sha256':{str(p.relative_to(BACKEND)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'records':records}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes',type=int,nargs='+',default=[20,50,100,200])
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    if min(args.sizes)<10 or len(set(args.sizes))!=len(args.sizes): parser.error('Use unique sizes >=10.')
    result = run(args.sizes)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
