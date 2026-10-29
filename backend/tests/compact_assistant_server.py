"""Loopback-only isolated bridge. No production composition/selector changes."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['SMART_WARDROBE_CRITICAL_PATH_DIAGNOSTICS']=os.getenv('SMART_WARDROBE_COMPACT_DIAGNOSTICS','false')
os.environ['SMART_WARDROBE_CRITICAL_PATH_ALLOW_FAILURE']=os.getenv('SMART_WARDROBE_COMPACT_ALLOW_FAILURE','false')
from tests import assistant_critical_path_server as diagnostic
from tests.compact_service_adapter import CompactAssistantAdapter
from app.application.recommendation.assistant_scoring_selection import AssistantScoringSelection,DECISION
from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
from app.application.recommendation.recommendation_scorer import RecommendationScorer
from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
from scripts.benchmark_compact_exhaustive import memory

fixture=diagnostic.fixture
app=diagnostic.app
if diagnostic.enabled:
    # The retained aggregated coordinator overrides the older raw-score method.
    # Observe its actual implementation only in the separate diagnostic run.
    from app.application.recommendation.prepared_compatibility_aggregation import PreparedCompatibilityAggregation
    from app.application.recommendation.exact_score_reuse import ExactScoreReuse
    diagnostic.instrument(PreparedCompatibilityAggregation,'score','aggregated_raw_compatibility')
    original_reuse_init=ExactScoreReuse.__init__
    def observed_reuse_init(self):
        original_reuse_init(self)
        weighted=self.weighted
        def observed_weighted(*args):
            from time import perf_counter
            start=perf_counter()
            try:return weighted(*args)
            finally:diagnostic.add('weighted_arithmetic',perf_counter()-start)
        self.weighted=observed_weighted
    ExactScoreReuse.__init__=observed_reuse_init
if os.getenv('SMART_WARDROBE_COMPACT_MULTI')=='true':
    import json
    owner=fixture.workloads['100']['owner']
    with fixture.db.connection() as c:
        for kind,values in (('styles',['vintage']),('garment_categories',[{'kind':'group','value':'top'}])):
            c.execute('INSERT INTO user_preferences VALUES(?,?,?,?,1,?,1,?,?)',(owner+kind,owner,kind,json.dumps({'values':values}),'synthetic','now','now'))
    fixture.workloads['100']['preference_count']=3


@app.post('/_test/compact/{profile}/{arm}')
def select(profile:str,arm:str):
    AssistantScoringSelection(profile)
    if arm not in ('reference','compact'):raise ValueError('Unknown experimental test arm.')
    svc=fixture.assistant_service();svc.scoring_profile=profile
    if arm=='compact':
        class ObservedAdapter(CompactAssistantAdapter):
            def rank(self,*args,**kwargs):
                result=super().rank(*args,**kwargs)
                row=diagnostic.ACTIVE.get()
                if row is not None and self.kernel:row.update(kernel_stages=self.kernel.timings,cache=self.kernel.cache_statistics)
                return result
        def selected(engine,preferences):
            return ObservedAdapter(engine,preferences,profile,diagnostics=diagnostic.enabled)
        svc.scorer_factory=selected
    else:svc.scorer_factory=AggregatedDecisionRecommendationScorer if profile==DECISION else RecommendationScorer
    return {'profile':profile,'arm':arm,'test_only':True}


original=OutfitAssistantService.recommend
def observe_memory(self,*args,**kwargs):
    result=original(self,*args,**kwargs)
    row=diagnostic.ACTIVE.get()
    if row is not None:row['memory']=memory()
    return result
OutfitAssistantService.recommend=observe_memory


if __name__=='__main__':
    try:fixture.uvicorn.run(app,host='127.0.0.1',port=3201,access_log=False)
    finally:fixture.temporary.cleanup()
