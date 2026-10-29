"""Explicit cached Phase3A twin. Original uncached scorer remains the oracle."""
from fractions import Fraction
from itertools import combinations
from app.application.recommendation.rule_based_compatibility_policy import RuleBasedCompatibilityPolicy
from app.application.recommendation.compatibility_pair_cache import CompatibilityPairCache,MAX_PAIR_CAPACITY
from app.application.recommendation.rule_based_compatibility_evidence import RuleBasedCompatibilityEvidence
from app.application.recommendation.mandatory_rule_evaluator import MandatoryRuleEvaluator
from app.domain.value_objects.scored_candidate import VerifiedScoringInput
from app.domain.value_objects.recommendation_score import ComponentScore,ScoreEvidence


class CachedRuleBasedCompatibilityScorer:
    def __init__(self,policy=None,capacity=MAX_PAIR_CAPACITY):
        self.policy=policy or RuleBasedCompatibilityPolicy.load()
        if not isinstance(self.policy,RuleBasedCompatibilityPolicy):
            raise ValueError("Validated rule-based policy required.")
        self.evidence=RuleBasedCompatibilityEvidence()
        self.structure=MandatoryRuleEvaluator()
        self.pair_cache=CompatibilityPairCache(self.policy,capacity)
        self._context_id=None

    def score(self,verified):
        if not isinstance(verified,VerifiedScoringInput):
            raise ValueError("Independent gate-verified input required for scoring.")
        if self._context_id is None:
            self._context_id=verified.context_id
        elif self._context_id!=verified.context_id:
            raise ValueError("Compatibility cache cannot cross scoring sessions.")
        return self.evaluate(verified.candidate)

    def evaluate(self,candidate):
        """Offline intrinsic measurement only; not proof of current eligibility."""
        if not self.structure.is_structurally_valid(tuple(m.garment for m in candidate.members)):
            raise ValueError("Supported complete structural candidate required.")
        self.pair_cache.bind(candidate.members[0].garment.user_id,self.policy)
        prepared=tuple(self.evidence.classify(m.garment) for m in candidate.members)
        provenance=("policy_version:"+self.policy.version,"policy_hash:"+self.policy.hash)
        if len(prepared)==1:
            return ComponentScore(ScoreEvidence("compatibility",None,"Unknown",reasons=("no_pair_relationships",*provenance)),
                                  (ScoreEvidence("colour_coordination",None,"NotApplicable"),
                                   ScoreEvidence("style_consistency",None,"NotApplicable")))
        colours,styles=[],[]
        for a,b in combinations(prepared,2):
            pair=self.pair_cache.pair(a,b,candidate.members[0].garment.user_id,self.policy)
            colours.append(pair.colour)
            styles.append(pair.style)
        def mean(name,entries):
            observed=sum(x.observed for x in entries)
            value=sum((x.value for x in entries),Fraction(0))/len(entries) if observed==len(entries) else None
            return ScoreEvidence(name,value,"Available" if value is not None else "Unknown",observed,len(entries))
        c,s=mean("colour_coordination",colours),mean("style_consistency",styles)
        value=(c.value+s.value)/2 if c.value is not None and s.value is not None else None
        observed=c.observed+s.observed
        summary=ScoreEvidence("compatibility",value,"Available" if value is not None else "Unknown",observed,c.possible+s.possible,
                              provenance if value is not None else ("partial_evidence" if observed else "missing_evidence",*provenance))
        return ComponentScore(summary,(c,s,*colours,*styles))
