"""Disposable actual-service pairs. Instrumentation/memory runs are labelled."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
from time import perf_counter,process_time
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))


def memory():
    if os.name!='nt':return {'available':False}
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(n,ctypes.c_size_t) for n in ('peak_working_set','working_set','quota_peak_paged','quota_paged','quota_peak_nonpaged','quota_nonpaged','pagefile','peak_pagefile')]
    c=Counters();c.cb=ctypes.sizeof(c)
    ctypes.windll.kernel32.GetCurrentProcess.restype=wintypes.HANDLE
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    if not ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(c),c.cb):return {'available':False}
    return {'available':True,'working_set_bytes':c.working_set,'process_lifetime_peak_bytes':c.peak_working_set}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sizes',default='20,50,100,200,stress')
    p.add_argument('--repeats',type=int,default=0,help='0: six pairs at 100/200, two elsewhere')
    p.add_argument('--multi',action='store_true');p.add_argument('--diagnostic',action='store_true')
    p.add_argument('--allocations',action='store_true',help='Separate tracemalloc observation; never latency acceptance')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'storage'):p.error('New output under storage required')
    from tests import assistant_decision_server as fixture
    from app.application.nlp.nlp_interpreter import NLPInterpreter
    from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
    from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
    from app.application.recommendation.recommendation_scorer import RecommendationScorer
    from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
    from app.application.recommendation.compact_exhaustive_scorer import DEFERRED,EXPERIMENTAL
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    from app.infrastructure.persistence.active_preference_query_adapter import SqliteActivePreferenceQuery
    from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
    from tests.compact_service_adapter import factory
    if args.multi:
        with fixture.db.connection() as c:
            for name in args.sizes.split(','):
                owner=fixture.workloads[name]['owner']
                for kind,values in (('styles',['vintage']),('garment_categories',[{'kind':'group','value':'top'}])):
                    c.execute('INSERT INTO user_preferences VALUES(?,?,?,?,1,?,1,?,?)',(owner+kind,owner,kind,json.dumps({'values':values}),'synthetic','now','now'))
                fixture.workloads[name]['preference_count']=3
    result={'metadata':fixture.metadata(),'instrumented':args.diagnostic or args.allocations,'runs':[],
        'memory_method':'Windows working set and process-lifetime high-water mark; includes interpreter, seed and earlier trials, not per-request allocation peak.'}
    fingerprints={}
    def save():output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for name in args.sizes.split(','):
        for profile in (DEFERRED,EXPERIMENTAL):
            for pair in range(args.repeats or (6 if name in ('100','200') else 2)):
                for arm in (('reference','compact') if pair%2==0 else ('compact','reference')):
                    created=[]
                    def compact_factory(engine,preferences):
                        adapter=factory(profile,diagnostics=args.diagnostic)(engine,preferences);created.append(adapter);return adapter
                    scorer=compact_factory if arm=='compact' else AggregatedDecisionRecommendationScorer if profile==EXPERIMENTAL else RecommendationScorer
                    service=OutfitAssistantService(NLPInterpreter(),RequestCandidateEngine(SqliteConfirmedGarmentQuery()),SqliteActivePreferenceQuery(),SqliteRecommendationRepository(fixture.db.DATABASE_PATH),scorer_factory=scorer,scoring_profile=profile)
                    if args.allocations:
                        import tracemalloc
                        tracemalloc.start()
                    start,cpu=perf_counter(),process_time()
                    response=service.recommend(fixture.workloads[name]['owner'],str(uuid4()),'Suggest an outfit with vintage style')
                    row={'name':name,'profile':profile,'pair':pair,'arm':arm,'seconds':perf_counter()-start,'cpu_seconds':process_time()-cpu,
                        'status':response['status'],'complete':response.get('complete'),'stages':response.get('timings'),'memory':memory()}
                    if args.allocations:
                        row['python_traced_current_bytes'],row['python_traced_peak_bytes']=tracemalloc.get_traced_memory()
                        tracemalloc.stop()
                    if created and created[0].kernel:
                        row.update(kernel_stages=created[0].kernel.timings,cache=created[0].kernel.cache_statistics)
                    if response['status']=='Selected':
                        identity={'items':[(i['garment_id'],i['garment_role'],i['item_order']) for i in response['items']],
                            'score':response['score_metadata'],'provenance':response['provenance']}
                        row['fingerprint']=hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                        row['candidate_count']=response['provenance']['scored_count']
                        k=(name,profile)
                        if k in fingerprints:assert fingerprints[k]==row['fingerprint']
                        fingerprints[k]=row['fingerprint']
                    result['runs'].append(row);save();print(json.dumps(row),flush=True)
                    assert response['status']=='Selected',response
                    assert row['candidate_count']==fixture.workloads[name]['candidate_count']
    fixture.temporary.cleanup()


if __name__=='__main__':main()
