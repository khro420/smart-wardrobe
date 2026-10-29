"""Approved colour/style proxies only; zero is not a proven fashion clash."""
from fractions import Fraction
from itertools import combinations
from app.application.recommendation.rule_based_compatibility_policy import RuleBasedCompatibilityPolicy
from app.application.recommendation.rule_based_compatibility_evidence import RuleBasedCompatibilityEvidence
from app.application.recommendation.mandatory_rule_evaluator import MandatoryRuleEvaluator
from app.domain.value_objects.scored_candidate import VerifiedScoringInput
from app.domain.value_objects.recommendation_score import ComponentScore,ScoreEvidence


class RuleBasedCompatibilityScorer:
    def __init__(self,policy=None):
        self.policy=policy or RuleBasedCompatibilityPolicy.load()
        if not isinstance(self.policy,RuleBasedCompatibilityPolicy):
            raise ValueError("Validated rule-based policy required.")
        self.evidence=RuleBasedCompatibilityEvidence()
        self.structure=MandatoryRuleEvaluator()

    def score(self,verified):
        if not isinstance(verified,VerifiedScoringInput):
            raise ValueError("Independent gate-verified input required for scoring.")
        return self.evaluate(verified.candidate)

    def evaluate(self,candidate):
        """Offline intrinsic measurement only; not proof of current eligibility."""
        if not self.structure.is_structurally_valid(tuple(m.garment for m in candidate.members)):
            raise ValueError("Supported complete structural candidate required.")
        prepared=tuple(self.evidence.classify(m.garment) for m in candidate.members)
        provenance=("policy_version:"+self.policy.version,"policy_hash:"+self.policy.hash)
        if len(prepared)==1:
            return ComponentScore(ScoreEvidence("compatibility",None,"Unknown",reasons=("no_pair_relationships",*provenance)),
                                  (ScoreEvidence("colour_coordination",None,"NotApplicable"),
                                   ScoreEvidence("style_consistency",None,"NotApplicable")))
        colours,styles=[],[]
        for a,b in combinations(prepared,2):
            key=a.garment_id+":"+b.garment_id
            reasons=tuple(a.garment_id+":"+r for r in a.reasons)+tuple(b.garment_id+":"+r for r in b.reasons)
            colour=(Fraction(int(a.colour==b.colour or a.colour in self.policy.achromatic or b.colour in self.policy.achromatic))
                    if a.colour_state==b.colour_state=="Known" else None)
            style=(Fraction(2*len(a.styles & b.styles),len(a.styles)+len(b.styles))
                   if a.style_state==b.style_state=="Known" else None)
            colours.append(ScoreEvidence("colour:"+key,colour,"Available" if colour is not None else "Unknown",int(colour is not None),1,reasons))
            styles.append(ScoreEvidence("style:"+key,style,"Available" if style is not None else "Unknown",int(style is not None),1,reasons))
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
