"""Exact base/floor filtering before comparison; original scalar/public scores retained."""
from types import SimpleNamespace
from fractions import Fraction
from app.domain.value_objects.garment_only_refinement import GarmentRefinementPlan

def is_garment(plan):return type(plan) is GarmentRefinementPlan

class GarmentTracker:
    relative=False
    best_point=None
    def __init__(self,garments,plan):
        if not is_garment(plan):raise ValueError('Typed garment plan required.')
        self.plan=plan;self.best_legacy=None;self.points=self.passed=self.unresolved=0
        self.skipped={'already_seen':0,'below_floor_points':0,'unresolved_below_floor':0}
        self.facts=SimpleNamespace(by_id={g.garment_id:i for i,g in enumerate(garments)},objective=None,bounds=lambda roles,indexes:(Fraction(0),Fraction(0),None,None))
    def consider(self,roles,indexes,conditions,score,key):
        self.passed+=1
        if score.contributions[0]!=0:raise ValueError('Pure B1 cannot earn request-match points.')
        signature=tuple(pair for pair in key if pair[0]!='outerwear')
        if signature in self.plan.seen:self.skipped['already_seen']+=1;return None,None
        if self.plan.root_R is not None and score.contributions[0]<self.plan.root_R:self.skipped['below_floor_points']+=1;return None,None
        self.points+=1;value=(score.total,*score.contributions)
        if self.best_legacy is None or value>self.best_legacy[0] or value==self.best_legacy[0] and key<self.best_legacy[5]:
            self.best_legacy=(value,roles,indexes,conditions,score,key)
        return score,None
    @property
    def selected(self):return self.best_legacy
    @property
    def empty_refinement_status(self):return 'RefinementExhausted'
    def proof(self,winner):return None

def reference_rank(scorer,user,request,plan):
    """P1/C1 public loop; P2/C2 retain their original public coordinators."""
    from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
    from app.application.recommendation.preference_normalizer import PreferenceNormalizer
    from app.application.recommendation.request_match_scorer import RequestMatchScorer
    from app.application.recommendation.preference_scorer import PreferenceScorer
    from app.application.recommendation.rule_based_compatibility_scorer import RuleBasedCompatibilityScorer
    from app.application.recommendation.rule_based_compatibility_policy import RuleBasedCompatibilityPolicy
    from app.application.recommendation.prepared_decision_policy import PreparedDecisionPolicy
    from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
    from app.application.recommendation.candidate_ranker import CandidateRanker
    from app.domain.value_objects.recommendation_score import RecommendationScore
    from app.domain.value_objects.scored_candidate import ScoredCandidate
    from app.domain.value_objects.ranking_outcome import RankingOutcome
    from app.domain.value_objects.compatibility_signature import STRUCTURES
    from app.application.recommendation.refinement_selector import base_signature
    preferences=PreferenceNormalizer().normalize(user,tuple(scorer.preference_query.get_active_preferences(user)))
    session=scorer.candidate_engine.generate_candidates(user,request);best=None;count=0
    try:
        gate=ScoringEligibilityGate(session,user,request);decision=PreparedDecisionPolicy(CompatibilityDecisionPolicy.load())
        raw=RuleBasedCompatibilityScorer(RuleBasedCompatibilityPolicy.load());roles_to_structure={v:k for k,v in STRUCTURES.items()}
        for item in session:
            verified=gate.verify(item);candidate=verified.candidate
            if base_signature(candidate) in plan.seen or any(m.garment.category in plan.exclusions for m in candidate.members):continue
            r=RequestMatchScorer().score(verified);p=PreferenceScorer().score(verified,preferences)
            c=decision.apply(raw.score(verified),roles_to_structure[tuple(m.role for m in candidate.members)])
            if r.summary.state!='NotApplicable' or r.summary.value is not None or r.contribution!=0:raise ValueError('Invalid pure-B1 R.')
            score=RecommendationScore(r,c,p,Fraction(3,5)*r.contribution+Fraction(1,5)*c.contribution+Fraction(1,5)*p.contribution,decision.name,decision.version,decision.weights)
            chosen=ScoredCandidate(verified,score);count+=1
            if CandidateRanker().better(chosen,best):best=chosen
        result=session.result
        if not result.complete:return RankingOutcome('ProcessingFailure')
        unknown=getattr(session,'attribute_ledger',None)
        if best is None:return RankingOutcome('RefinementInsufficientEvidence' if unknown and unknown.unseen_unknown or result.unknown else 'RefinementExhausted',complete=True)
        return RankingOutcome('Selected',best,True,count,diagnostics=preferences.diagnostics)
    finally:session.close()
