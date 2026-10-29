"""Explicit TEST-ONLY prepared-context/provenance bridge; never live wiring.

The original service consumes a captured session only to identify its evaluator.
This bridge supplies that metadata carrier after the compact ledger completes;
it does not pretend the unconsumed public stream was exhausted. The returned
RankingOutcome and original winning public models certify completion instead.
"""
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer


class CompactAssistantAdapter:
    def __init__(self,captured_engine,preferences,profile,**options):
        self.captured_engine,self.preferences,self.profile,self.options=captured_engine,preferences,profile,options
        self.kernel=None

    def rank(self,user_id,request,profile_name=None):
        if profile_name is not None and profile_name!=self.profile:raise ValueError('Test profile mismatch.')
        engine=self.captured_engine.engine
        self.kernel=CompactExhaustiveScorer(engine.structural_engine.retrieval.query,self.preferences,self.profile,
            evaluator_type=type(engine.evaluator_factory()),**self.options)
        result=self.kernel.rank(user_id,request)
        self.captured_engine.session=self.kernel.public_session
        return result


def factory(profile,**options):
    return lambda engine,preferences:CompactAssistantAdapter(engine,preferences,profile,**options)
