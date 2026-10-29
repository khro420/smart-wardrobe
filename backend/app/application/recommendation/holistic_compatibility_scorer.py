"""Explicit experimental reviewed-reference policy; no inferred harmony."""
from fractions import Fraction
from app.application.recommendation.compatibility_scorer import CompatibilityScorer
from app.application.recommendation.compatibility_evidence_mapper import CompatibilityEvidenceMapper
from app.domain.value_objects.scored_candidate import VerifiedScoringInput
from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore


class HolisticCompatibilityScorer(CompatibilityScorer):
    def __init__(self,policy,mapper=None):
        super().__init__(mapper)
        self.policy = policy
        self.evidence = CompatibilityEvidenceMapper(policy,self.mapper)

    def score(self,verified,profile):
        if not isinstance(verified,VerifiedScoringInput) or profile.compatibility != "reviewed_holistic":
            raise ValueError("Verified input and explicit holistic profile required.")
        provenance = ("policy_version:"+self.policy.version,"policy_hash:"+self.policy.hash)
        if not self.policy.available:
            return ComponentScore(ScoreEvidence("compatibility",None,"Unavailable",reasons=("policy_unavailable",*provenance)))
        signature,observed,possible,reasons = self.evidence.signature(verified.candidate)
        detail = ScoreEvidence("descriptor_coverage",Fraction(observed,possible),"Available" if observed == possible else "Partial",observed,possible,reasons)
        if signature is None:
            return ComponentScore(ScoreEvidence("compatibility",None,"Unknown",observed,possible,("incomplete_or_malformed_evidence",*provenance)),(detail,))
        reference = self.policy.approved.get(signature.key)
        if reference is None:
            return ComponentScore(ScoreEvidence("compatibility",None,"Unknown",observed,possible,("missing_approved_reference",*provenance)),(detail,))
        return ComponentScore(ScoreEvidence("compatibility",reference.value,"Available",observed,possible,("reference:"+reference.reference_id,*provenance)),(detail,))
