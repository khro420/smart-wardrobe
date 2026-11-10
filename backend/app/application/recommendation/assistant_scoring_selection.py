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
    preference_profile: str | None=None
    compatibility_profile: str | None=None

    def __post_init__(self):
        if self.profile not in (DEFERRED, DECISION) or self.version != "assistant-scoring-selection-1.0.0":
            raise ValueError("Unknown Assistant scoring configuration.")
        if self.context_ranking not in ('disabled','context_relevance_decision_v1') or self.context_ranking!='disabled' and self.profile!=DECISION:
            raise ValueError('Relative ranking requires the accepted decision baseline.')
        if self.preference_profile is not None:
            from app.domain.value_objects.attribute_preferences import PROFILE
            if self.preference_profile!=PROFILE or self.profile!=DECISION:raise ValueError('P2 requires its explicit version and accepted60/20/20 profile.')

        if self.compatibility_profile is not None:
            from app.domain.value_objects.palette_compatibility import PROFILE
            if self.compatibility_profile!=PROFILE or self.profile!=DECISION:raise ValueError('C2 requires its explicit profile and accepted outer weights.')

    @property
    def hash(self):
        value={"version":self.version,"profile":self.profile}
        if self.preference_profile is not None:value['preference_profile']=self.preference_profile
        if self.compatibility_profile is not None:value['compatibility_profile']=self.compatibility_profile
        return digest(value)

    def scorer(self,engine,preferences,factory,*,preference_context=None,compatibility_context=None):
        from app.application.recommendation.recommendation_scorer import RecommendationScorer
        if compatibility_context is not None:
            from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
            if factory not in (RecommendationScorer,AggregatedDecisionRecommendationScorer):raise ValueError('C2 requires an approved scoring implementation.')
            return AggregatedDecisionRecommendationScorer(engine,preferences,context_ranking=self.context_ranking!='disabled',preference_context=preference_context,compatibility_context=compatibility_context)
        if preference_context is not None:
            if self.profile!=DECISION:raise ValueError('P2 requires the accepted60/20/20 decision profile.')
            from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
            if factory not in (RecommendationScorer,AggregatedDecisionRecommendationScorer):raise ValueError('P2 requires an approved scoring implementation.')
            return AggregatedDecisionRecommendationScorer(engine,preferences,context_ranking=self.context_ranking!='disabled',preference_context=preference_context)
        if self.profile == DECISION and factory is RecommendationScorer:
            from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
            factory = AggregatedDecisionRecommendationScorer
            if self.context_ranking!='disabled':return factory(engine,preferences,context_ranking=True)
        return factory(engine,preferences)

    def rank(self,scorer,user,request,refinement_plan=None):
        if refinement_plan is not None:
            from app.application.recommendation.garment_only_refinement_selection import is_garment
            if self.profile!=DECISION or self.context_ranking=='disabled' and not is_garment(refinement_plan):raise ValueError('Refinement requires approved decision scoring.')
            return scorer.rank(user,request,refinement_plan=refinement_plan)
        return scorer.rank(user,request) if self.profile == DECISION else scorer.rank(user,request,self.profile)

    def validate(self,score):
        from app.domain.value_objects.palette_compatibility import PROFILES,PROFILE,DECISION as C2_VERSION,WEIGHTS
        if score.profile_name in PROFILES.values():
            from app.domain.value_objects.palette_compatibility import PaletteCompatibilityComponent
            from app.application.recommendation.palette_compatibility_policy import RESOURCE_SHA256
            p2,relative=next(k for k,v in PROFILES.items() if v==score.profile_name)
            if self.compatibility_profile!=PROFILE or p2!=(self.preference_profile is not None) or relative and self.context_ranking=='disabled' or score.policy_version!=C2_VERSION or score.weights!=WEIGHTS or type(score.compatibility) is not PaletteCompatibilityComponent or score.compatibility.decision.policy_hash!=RESOURCE_SHA256:raise ValueError('Unselected C2 score or changed outer contract.')
            score_to_json(score);return
        if self.compatibility_profile is not None:raise ValueError('Selected C2 returned a legacy score.')
        from app.domain.value_objects.attribute_preferences import PROFILE as P2
        if score.profile_name==P2:
            if self.preference_profile!=P2 or self.profile!=DECISION:raise ValueError('Unselected P2 score.')
            policy=CompatibilityDecisionPolicy.load()
            if not isinstance(score.compatibility,DecisionCompatibilityComponent) or score.weights!=policy.weights or score.compatibility.decision.policy_hash!=policy.hash:
                raise ValueError('P2 changed the accepted C decision or outer coefficients.')
            score_to_json(score)
            return
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
