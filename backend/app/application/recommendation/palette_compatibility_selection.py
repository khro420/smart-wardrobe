"""C2 composition before selection; original mandatory, R/P and Seen machinery."""
from collections import OrderedDict
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace
from app.domain.value_objects.palette_compatibility import PaletteCompatibilityComponent,PROFILES,DECISION,WEIGHTS
from app.domain.value_objects.compact_recommendation import CompactScore,validate_total
from app.application.recommendation.context_relevance_scorer import RelativeTracker
from app.application.recommendation.attribute_preference_relative_facts import P2RelativeTracker
from app.application.recommendation.palette_compatibility_policy import encode,decode

def profile_score(score,*,p2=None,relative=None):
    if type(score.compatibility) is not PaletteCompatibilityComponent:return score
    if p2 is None:p2=score.profile_name=='attribute_preference_decision_v2' or score.profile_name in (PROFILES[True,False],PROFILES[True,True])
    if relative is None:relative=score.request_match.summary.name=='relative_style_alignment'
    return replace(score,profile_name=PROFILES[bool(p2),bool(relative)],policy_version=DECISION)

def legacy_score(score):
    from app.domain.value_objects.attribute_preferences import DECISION as P2_VERSION
    if score.profile_name not in PROFILES.values():return score
    p2,relative=next(key for key,value in PROFILES.items() if value==score.profile_name)
    if p2:name,version='attribute_preference_decision_v2',P2_VERSION
    elif relative:
        from app.application.recommendation.context_relevance_policy import POLICY_VERSION
        name,version='context_relevance_decision_v1',POLICY_VERSION
    else:name,version='experimental_compatibility_decision_v1','compatibility-decision-1.0.0'
    return replace(score,profile_name=name,policy_version=version)

def wrap_proof(data,score):
    data=dict(data)
    data.update(base_version=data['version'],base_explanation_version=data['explanation_version'],
        base_actual_profile=data['actual_profile'],version='context-relevance-evidence-3.0.0',
        explanation_version='context-relevance-explanation-3.0.0',actual_profile=score.profile_name,
        compatibility_profile='recorded_palette_compatibility_v1',compatibility_policy_sha256=score.compatibility.decision.policy_hash)
    return data

class PaletteTracker(RelativeTracker):
    def proof(self,winner):
        proxy=replace(winner,score=legacy_score(winner.score))
        return encode(wrap_proof(decode(super().proof(proxy),307200),winner.score)).decode()

class PaletteP2Tracker(P2RelativeTracker):
    def proof(self,winner):
        proxy=replace(winner,score=legacy_score(winner.score))
        return encode(wrap_proof(decode(super().proof(proxy),307200),winner.score)).decode()

class PaletteFacts:
    """Replace only C after the original R/P producer, before all comparisons."""
    def __init__(self,original,prepared,garments):
        self.original,self.prepared,self.garments=original,prepared,tuple(garments);self.cache=OrderedDict()
    def score(self,roles,indexes):
        original=self.original.score(roles,indexes)
        c=self.prepared.compact(self.garments,roles,indexes)
        key=(roles,original,c)
        if key not in self.cache:
            total=WEIGHTS[0]*original.request.contribution+WEIGHTS[1]*c.value+WEIGHTS[2]*original.preference.contribution
            result=CompactScore(original.request,c,original.preference,total,original.request_details,original.preference_details)
            validate_total(result,WEIGHTS);self.cache[key]=result
            if len(self.cache)>256:self.cache.popitem(last=False)
        return self.cache[key]
    @property
    def cache_info(self):return {**self.original.cache_info,'palette_pairs':len(self.prepared._pairs),'palette_aggregates':len(self.prepared._aggregates),'palette_scores':len(self.cache)}

def reference_rank(engine,query,user,request,prepared,*,preference_context=None,context_ranking=False,refinement_plan=None,audit=None):
    """Independent public candidate loop; never invokes compact numeric facts."""
    from app.application.recommendation.garment_retrieval_service import GarmentRetrievalService
    from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
    from app.application.recommendation.compact_exhaustive_scorer import SnapshotQuery
    from app.application.recommendation.preference_normalizer import PreferenceNormalizer
    from app.application.recommendation.preference_scorer import PreferenceScorer
    from app.application.recommendation.request_match_scorer import RequestMatchScorer
    from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
    from app.application.recommendation.context_relevance_scorer import applies,PreparedRelativeFacts
    from app.application.recommendation.attribute_preference_relative_facts import P2RelativeFacts,public_score,measure
    from app.application.recommendation.candidate_ranker import CandidateRanker
    from app.domain.value_objects.recommendation_score import RecommendationScore
    from app.domain.value_objects.scored_candidate import ScoredCandidate
    from app.domain.value_objects.ranking_outcome import RankingOutcome
    session=None
    try:
        actual=engine.engine if hasattr(engine,'engine') else engine
        garments=GarmentRetrievalService(actual.structural_engine.retrieval.query).retrieve(user).garments
        if prepared.user!=user or any(g.garment_id not in prepared.by_id or prepared.by_id[g.garment_id].snapshot!=g for g in garments):raise ValueError('C2 capture mismatch.')
        rows=tuple(query.get_active_preferences(user))
        preferences=PreferenceNormalizer().normalize(user,rows) if preference_context is None else preference_context.composed.legacy
        if preference_context is not None:
            if rows!=preference_context.snapshot.legacy_rows():raise ValueError('C2/P2 capture mismatch.')
            preference_context.bind_request(request)
        if refinement_plan is not None:
            from app.application.recommendation.refinement_selector import filter_snapshot,check_category_conflicts
            from app.application.nlp.vocabulary import Vocabulary
            check_category_conflicts(request,refinement_plan.exclusions,Vocabulary.load())
            filtered=filter_snapshot(garments,refinement_plan.exclusions);garments=filtered.garments
        replay=RequestCandidateEngine(SnapshotQuery(user,garments),evaluator_factory=actual.evaluator_factory,
            attribute_context=getattr(actual,'attribute_context',None),attribute_verifier=getattr(actual,'attribute_verifier',None))
        replay.attribute_seen=getattr(actual,'attribute_seen',())
        replay.attribute_counter_guard=getattr(actual,'attribute_counter_guard',None)
        session=replay.generate_candidates(user,request)
        if hasattr(engine,'session'):engine.session=session
        if session.result.status in ('PolicyUnavailable','ProcessingFailure','Interrupted'):return RankingOutcome(session.result.status)
        tracker=None
        if context_ranking and applies(request):
            tracker=(PaletteTracker(PreparedRelativeFacts(garments,request,preferences),refinement_plan) if preference_context is None else
                PaletteP2Tracker(P2RelativeFacts(garments,request,preferences,preference_context),refinement_plan))
        from app.application.recommendation.garment_only_refinement_selection import is_garment,GarmentTracker
        if is_garment(refinement_plan):tracker=GarmentTracker(garments,refinement_plan)
        if refinement_plan is not None and tracker is None:return RankingOutcome('RefinementUnavailable')
        gate=ScoringEligibilityGate(session,user,request);rscorer=RequestMatchScorer();pscorer=PreferenceScorer();ranker=CandidateRanker()
        best=None;winners={};scored=0
        for item in session:
            verified=gate.verify(item);roles=tuple(m.role for m in verified.candidate.members)
            c=prepared.public(verified);r=rscorer.score(verified);p=pscorer.score(verified,preferences)
            original=RecommendationScore(r,c,p,WEIGHTS[0]*r.contribution+WEIGHTS[1]*c.contribution+WEIGHTS[2]*p.contribution,
                PROFILES[False,False],DECISION,WEIGHTS)
            value=profile_score(public_score(original,preference_context.public(verified).score),p2=True) if preference_context else original
            base=ScoredCandidate(verified,value);chosen=base;scored+=1
            if tracker is not None:
                indexes=tuple(tracker.facts.by_id[m.garment.garment_id] for m in verified.candidate.members)
                scalar=SimpleNamespace(total=value.total,contributions=(r.contribution,c.contribution,value.preference.contribution),
                    preference=measure(value.preference.summary),preference_details=tuple(measure(d) for d in value.preference.details),
                    compatibility=SimpleNamespace(value=c.contribution),original_preference_score=SimpleNamespace(preference=measure(p.summary),preference_details=tuple(measure(d) for d in p.details)))
                point,_=tracker.consider(roles,indexes,None,scalar,verified.candidate.key)
                if point is not None and not is_garment(refinement_plan):chosen=ScoredCandidate(verified,profile_score(tracker.facts.public(verified,original),p2=preference_context is not None))
                if point is not None and not is_garment(refinement_plan) and (chosen.score.total,chosen.score.request_match.contribution,chosen.score.preference.contribution)!=(point.total,point.request.contribution,point.preference.contribution):raise ValueError('C2 independent scalar/public mismatch.')
                if tracker.best_point and tracker.best_point[2]==indexes:winners['point']=chosen
                if tracker.best_legacy and tracker.best_legacy[2]==indexes:winners['legacy']=base
            elif ranker.better(chosen,best):best=chosen
            if audit is not None:audit(chosen)
        result=session.result
        if not result.complete:return RankingOutcome('ProcessingFailure')
        session.close();session=None
        if tracker is not None:best=winners['point' if tracker.relative else 'legacy'] if tracker.selected is not None else None
        status='Selected' if best else (tracker.empty_refinement_status if tracker is not None else None) or result.status
        if status=='MatchingCandidates':status='NoMatchingCandidates'
        summary=None
        if refinement_plan is not None:
            from app.application.recommendation.refinement_selector import outcome_summary
            summary=outcome_summary(refinement_plan,filtered,tracker,result.failed,result.unknown,status)
        return RankingOutcome(status,best,True,tracker.points if tracker is not None and (tracker.relative or is_garment(refinement_plan)) else scored,
            diagnostics=preferences.diagnostics,ranking_evidence=tracker.proof(best) if tracker is not None and best else None,refinement_summary=summary)
    finally:
        if session is not None:session.close()
