"""Disposable actual-service diagnosis; instrumentation is never installed in app code.

Cumulative profiler/timer spans overlap. Uninstrumented trials are separate.
Synthetic confirmed garments and one real stored blue preference match Phase 3B.
"""
import argparse
import cProfile
import functools
import hashlib
import json
import os
from pathlib import Path
import platform
import pstats
import statistics
import sys
import tempfile
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
sys.path.insert(0,str(ROOT/'backend/scripts'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--size',type=int,default=100)
    p.add_argument('--repeats',type=int,default=2)
    p.add_argument('--profile',action='store_true')
    p.add_argument('--diverse',action='store_true',help='Separate synthetic cache-diversity check; not the matched transport workload')
    p.add_argument('--trial',action='store_true',help='Paired original versus aggregation-prepared service; no runtime wiring changes.')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.size<10 or args.repeats<1: p.error('Positive trials and at least ten garments required')
    output=args.output.resolve()
    if not output.is_relative_to(ROOT/'storage') or output.exists():p.error('New output under storage required')
    output.parent.mkdir(parents=True,exist_ok=True)
    result={'size':args.size,'python':sys.version,'platform':platform.platform(),'runs':[],'profiles':[],
        'method':'Actual service, strict SQLite query, stored preference, complete enumeration and atomic persistence. Profile cumulative spans overlap and instrumentation affects elapsed time; never use profiled runs for NFR acceptance.'}
    def save():output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='integrated-assistant-diagnosis-') as directory:
        os.environ.update(SMART_WARDROBE_DATA_DIR=directory,SMART_WARDROBE_DATABASE=str(Path(directory)/'test.db'),
            SMART_WARDROBE_AI_MODE='development',SMART_WARDROBE_VTOFF_ENABLED='off')
        from benchmark_homepage_recommendation import seed
        from app.infrastructure.persistence import postgresql_repository as db
        from app.infrastructure.persistence.active_preference_query_adapter import SqliteActivePreferenceQuery
        from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
        from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
        from app.application.nlp.nlp_interpreter import NLPInterpreter
        from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
        from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
        from app.application.recommendation.assistant_scoring_selection import DEFERRED,DECISION
        db.initialise_database();counts=seed(args.size)
        with db.connection() as c:
            c.execute("UPDATE garments SET primary_colour='blue',style_tags='[\"vintage\"]'")
            if args.diverse:
                colours=('red','blue','white','black','navy','green')
                styles=(('classic',),('vintage',),('sporty',),('classic','vintage'),())
                for i,row in enumerate(c.execute('SELECT id FROM garments ORDER BY id').fetchall()):
                    c.execute('UPDATE garments SET primary_colour=?,style_tags=? WHERE id=?',
                        (colours[i%len(colours)],json.dumps(styles[(i//len(colours))%len(styles)]),row['id']))
            c.execute("INSERT INTO user_preferences VALUES('pref','benchmark','colours','{\"values\":[\"blue\"]}',1,'synthetic',1,'now','now')")
        request_text='Suggest an outfit' if args.diverse else 'Suggest an outfit with vintage style'
        result['request_text']=request_text
        result['diverse_synthetic_evidence']=args.diverse
        result['category_counts']=counts
        expected=(counts['top']*counts['bottom']+counts['dress'])*(counts['outerwear']+1)
        result['expected_candidates']=expected
        services={name:OutfitAssistantService(NLPInterpreter(),RequestCandidateEngine(SqliteConfirmedGarmentQuery()),
            SqliteActivePreferenceQuery(),SqliteRecommendationRepository(),scoring_profile=name) for name in (DEFERRED,DECISION)}
        from app.application.recommendation.prepared_decision_scorer import PreparedDecisionRecommendationScorer
        services[DECISION].scorer_factory=PreparedDecisionRecommendationScorer
        if args.trial:
            from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
            services={'reference':services[DECISION], 'trial':OutfitAssistantService(NLPInterpreter(),RequestCandidateEngine(SqliteConfirmedGarmentQuery()),
                SqliteActivePreferenceQuery(),SqliteRecommendationRepository(),scoring_profile=DECISION,scorer_factory=AggregatedDecisionRecommendationScorer)}
        def execute(name):
            start,cpu=time.perf_counter(),time.process_time()
            r=services[name].recommend('benchmark',str(uuid4()),request_text)
            elapsed,processor=time.perf_counter()-start,time.process_time()-cpu
            assert r['status']=='Selected' and r['complete'] and r['provenance']['scored_count']==expected,r.get('status')
            identity={'items':[(i['garment_id'],i['garment_role'],i['item_order']) for i in r['items']],
                'score':r['score_metadata'],'provenance':r['provenance']}
            return {'profile':name,'seconds':elapsed,'cpu_seconds':processor,'stages':r['timings'],
                'fingerprint':hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                'candidate_count':expected,'score':r['score_metadata']}
        for trial in range(args.repeats):
            order=tuple(services) if trial%2==0 else tuple(reversed(services))
            for name in order:
                row=execute(name);result['runs'].append(row);print(json.dumps({k:v for k,v in row.items() if k!='score'}),flush=True);save()
        if args.profile:
            for name in services:
                profiler=cProfile.Profile();profiler.enable();row=execute(name);profiler.disable()
                entries=[]
                for (file,line,function),(primitive,calls,self_time,cumulative,_) in pstats.Stats(profiler).stats.items():
                    entries.append({'file':file,'line':line,'function':function,'primitive_calls':primitive,'calls':calls,'self_seconds':self_time,'cumulative_seconds':cumulative})
                result['profiles'].append({**row,'functions':sorted(entries,key=lambda x:x['cumulative_seconds'],reverse=True)})
                print('Profile complete',name,row['seconds'],flush=True);save()
        result['sources']={f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/'backend/app').rglob('*.py')}
        save()


if __name__=='__main__':main()
