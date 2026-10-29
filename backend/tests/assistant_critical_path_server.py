"""Disposable loopback diagnostic server; NEVER deploy. Reuses exact 3B seeds.

Stage instrumentation is explicit and disabled in uninstrumented timing runs.
All spans are inclusive; nested spans must not be added to elapsed wall time.
"""
from contextvars import ContextVar
from functools import wraps
import inspect
import os
from time import perf_counter,process_time
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests import assistant_decision_server as fixture
from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
app=fixture.app
ACTIVE=ContextVar('diagnostic_request',default=None)
TX=ContextVar('diagnostic_transaction',default=False)
GATE=ContextVar('diagnostic_gate',default=False)
jobs={}
enabled=os.getenv('SMART_WARDROBE_CRITICAL_PATH_DIAGNOSTICS','false')=='true'


@app.middleware('http')
async def request_context(request,call_next):
    if request.method!='POST' or request.url.path!='/api/v1/recommendations':return await call_next(request)
    row={'spans':{}};token=ACTIVE.set(row);start=perf_counter()
    try:return await call_next(request)
    finally:
        row['backend_request_seconds']=perf_counter()-start
        ACTIVE.reset(token)


def add(label,elapsed):
    current=ACTIVE.get()
    if current is not None:
        row=current['spans'].setdefault(label,{'calls':0,'inclusive_seconds':0})
        row['calls']+=1;row['inclusive_seconds']+=elapsed


def instrument(cls,name,label,flag=None):
    original=getattr(cls,name)
    @wraps(original)
    def wrapped(*args,**kwargs):
        start=perf_counter();token=flag.set(True) if flag else None
        if flag is TX and ACTIVE.get() is not None:ACTIVE.get()['transaction_tick']=start
        try:return original(*args,**kwargs)
        finally:
            add(label() if callable(label) else label,perf_counter()-start)
            if flag:flag.reset(token)
    setattr(cls,name,wrapped)


original_recommend=OutfitAssistantService.recommend
original_repository_init=SqliteRecommendationRepository.__init__
def repository_init(self,database_path=fixture.db.DATABASE_PATH,checkpoint=None):
    def checked(stage,connection):
        row=ACTIVE.get()
        if row is not None:
            now=perf_counter()
            last=row.get('transaction_tick',now)
            if enabled:add('transaction_checkpoint:'+stage,now-last)
            row['transaction_tick']=now
            if (os.getenv('SMART_WARDROBE_CRITICAL_PATH_ALLOW_FAILURE')=='true'
                    and row['submission_key'].startswith('late-failure-') and stage=='metadata'):
                raise RuntimeError('Synthetic late failure; test database only.')
        if checkpoint:checkpoint(stage,connection)
    original_repository_init(self,database_path,checked)
SqliteRecommendationRepository.__init__=repository_init
@wraps(original_recommend)
def track(self,user,key,text):
    row=ACTIVE.get()
    if row is None:row={'spans':{}}
    row.update(owner=user,submission_key=key)
    token=ACTIVE.set(row);start,cpu=perf_counter(),process_time()
    try:
        r=original_recommend(self,user,key,text)
        row.update(done=True,status=r['status'],candidate_count=(r.get('provenance') or {}).get('scored_count'),
            id=r.get('id'),chat_id=r.get('chat_id'),score=r.get('score_metadata'),provenance=r.get('provenance'),
            items=[(i['garment_id'],i['garment_role'],i['item_order']) for i in r.get('items',[])],stages=r.get('timings'))
        return r
    finally:
        row.update(service_seconds=perf_counter()-start,cpu_seconds=process_time()-cpu)
        jobs[key]=row;ACTIVE.reset(token)
OutfitAssistantService.recommend=track


if enabled:
    from app.application.nlp.nlp_interpreter import NLPInterpreter
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
    from app.application.recommendation.garment_retrieval_service import GarmentRetrievalService
    from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
    from app.application.recommendation.rule_based_compatibility_evidence import RuleBasedCompatibilityEvidence
    from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
    from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
    from app.application.recommendation.request_match_scorer import RequestMatchScorer
    from app.application.recommendation.preference_scorer import PreferenceScorer
    from app.application.recommendation.cached_rule_based_compatibility_scorer import CachedRuleBasedCompatibilityScorer
    from app.application.recommendation.prepared_decision_policy import PreparedDecisionPolicy
    from app.application.recommendation.candidate_ranker import CandidateRanker
    from app.domain.value_objects.recommendation_score import RecommendationScore
    from app.application.recommendation.candidate_generator import CandidateGenerator
    from app.infrastructure.security import current_user_id
    from fastapi import Request
    from fastapi._compat.v2 import ModelField
    from starlette.responses import JSONResponse
    instrument(ModelField,'validate','http_field_validation')
    for cls,name,label in [(NLPInterpreter,'interpret','nlp'),(SqliteConfirmedGarmentQuery,'get_confirmed_available_garments',lambda:'transaction_query' if TX.get() else 'confirmed_query_and_projection'),
        (ConfirmedGarmentSnapshot,'__post_init__','snapshot_validation'),(GarmentRetrievalService,'retrieve','structural_retrieval_preparation'),
        (GarmentEvidenceMapper,'classify','request_garment_evidence'),(RuleBasedCompatibilityEvidence,'classify','compatibility_garment_evidence'),
        (RequestConstraintEvaluator,'evaluate',lambda:'independent_mandatory_recheck' if GATE.get() else 'mandatory_filter'),
        (RequestMatchScorer,'score','request_score'),(PreferenceScorer,'score','preference_score'),
        (CachedRuleBasedCompatibilityScorer,'score','raw_compatibility'),(PreparedDecisionPolicy,'apply','compatibility_decision'),
        (RecommendationScore,'__post_init__','exact_total_validation'),(CandidateRanker,'better','winner_comparison')]:
        instrument(cls,name,label)
    instrument(ScoringEligibilityGate,'verify','independent_gate',GATE)
    instrument(SqliteRecommendationRepository,'persist_assistant','transaction_revalidation_writes_commit',TX)
    original_enumerate=CandidateGenerator.enumerate
    def enumeration(self,*args,**kwargs):
        stream=original_enumerate(self,*args,**kwargs)
        try:
            while True:
                start=perf_counter()
                try:item=next(stream)
                except StopIteration:return
                finally:add('candidate_generation_next',perf_counter()-start)
                yield item
        finally:stream.close()
    CandidateGenerator.enumerate=enumeration
    original_auth=current_user_id
    @wraps(original_auth)
    async def auth(*args,**kwargs):
        start=perf_counter()
        try:return await original_auth(*args,**kwargs)
        finally:
            add('authentication',perf_counter()-start)
            # Auth precedes service-context creation: report independently.
            jobs['last_auth']={'seconds':perf_counter()-start}
    app.dependency_overrides[original_auth]=auth
    original_render=JSONResponse.render
    def render(self,content):
        start=perf_counter()
        try:return original_render(self,content)
        finally:
            add('api_json_serialization',perf_counter()-start)
            if isinstance(content,dict) and 'submission_key' not in content and content.get('outcome')=='Selected':
                jobs['last_serialization']={'seconds':perf_counter()-start}
    JSONResponse.render=render


@app.get('/_test/job/{key}')
def job(key:str):return jobs.get(key,{'done':False})


@app.get('/_test/diagnostics')
def diagnostics():return {'enabled':enabled,'auth':jobs.get('last_auth'),'serialization':jobs.get('last_serialization')}


@app.get('/_test/counts/{name}')
def counts(name:str):
    owner=fixture.workloads[name]['owner']
    with fixture.db.connection() as c:
        return {table:c.execute('SELECT count(*) FROM '+table+' WHERE user_id=?',(owner,)).fetchone()[0]
            for table in ('nlp_chats','recommendations')}


@app.post('/_test/select/{profile}/{arm}')
def select(profile:str,arm:str):
    # Test harness control plane only; no production request selector is added.
    from app.application.recommendation.assistant_scoring_selection import AssistantScoringSelection,DECISION
    from app.application.recommendation.recommendation_scorer import RecommendationScorer
    from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
    from app.application.recommendation.prepared_decision_scorer import PreparedDecisionRecommendationScorer
    AssistantScoringSelection(profile)
    if arm not in ('reference','trial'):raise ValueError('Unknown test arm')
    service=fixture.assistant_service()
    service.scoring_profile=profile
    service.scorer_factory=(AggregatedDecisionRecommendationScorer if arm=='trial' else PreparedDecisionRecommendationScorer) if profile==DECISION else RecommendationScorer
    return {'profile':profile,'arm':arm}


if __name__=='__main__':
    try:fixture.uvicorn.run(app,host='127.0.0.1',port=3201,access_log=False)
    finally:fixture.temporary.cleanup()
