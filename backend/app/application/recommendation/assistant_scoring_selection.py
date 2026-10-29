"""Server-only, versioned allowlist. Experimental selection is never the default."""
from dataclasses import dataclass
from fractions import Fraction
from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
from app.application.recommendation.rule_based_compatibility_policy import digest, RuleBasedCompatibilityPolicy
from app.application.recommendation.decision_score_codec import score_to_json
from app.domain.value_objects.compatibility_decision import DecisionCompatibilityComponent

DEFERRED = "compatibility_deferred"
DECISION = "experimental_compatibility_decision_v1"
ENVIRONMENT_KEY = "SMART_WARDROBE_ASSISTANT_SCORING_PROFILE"


@dataclass(frozen=True)
class AssistantScoringSelection:
    profile: str = DEFERRED
    version: str = "assistant-scoring-selection-1.0.0"
    context_ranking: str = 'disabled'

    def __post_init__(self):
        if self.profile not in (DEFERRED, DECISION) or self.version != "assistant-scoring-selection-1.0.0":
            raise ValueError("Unknown Assistant scoring configuration.")
        if self.context_ranking not in ('disabled','context_relevance_decision_v1') or self.context_ranking!='disabled' and self.profile!=DECISION:
            raise ValueError('Relative ranking requires the accepted decision baseline.')

    @property
    def hash(self):
        return digest({"version":self.version,"profile":self.profile})

    def scorer(self,engine,preferences,factory):
        from app.application.recommendation.recommendation_scorer import RecommendationScorer
        if self.profile == DECISION and factory is RecommendationScorer:
            from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
            factory = AggregatedDecisionRecommendationScorer
            if self.context_ranking!='disabled':return factory(engine,preferences,context_ranking=True)
        return factory(engine,preferences)

    def rank(self,scorer,user,request,refinement_plan=None):
        if refinement_plan is not None:
            if self.profile!=DECISION or self.context_ranking=='disabled':raise ValueError('Refinement requires relative decision scoring.')
            return scorer.rank(user,request,refinement_plan=refinement_plan)
        return scorer.rank(user,request) if self.profile == DECISION else scorer.rank(user,request,self.profile)

    def validate(self,score):
        if score.profile_name=='context_relevance_decision_v1' and self.context_ranking!='disabled':
            score_to_json(score)
            return
        if score.profile_name != self.profile:
            raise ValueError("Selected scoring profile mismatch.")
        if self.profile == DEFERRED:
            if score.compatibility.summary.state != "Unavailable" or score.weights != (Fraction(7,10),Fraction(0),Fraction(3,10)):
                raise ValueError("Deferred profile invariant mismatch.")
        else:
            policy = CompatibilityDecisionPolicy.load()
            if (not isinstance(score.compatibility,DecisionCompatibilityComponent)
                    or (score.policy_version,score.weights) != (policy.version,policy.weights)
                    or score.compatibility.decision.policy_hash != policy.hash):
                raise ValueError("Decision profile invariant mismatch.")
            raw_policy = RuleBasedCompatibilityPolicy.load()
            if "policy_hash:"+raw_policy.hash not in score.compatibility.summary.reasons:
                raise ValueError("Raw compatibility rule provenance mismatch.")
            score_to_json(score)  # Original exact decoder/validators certify replay.
