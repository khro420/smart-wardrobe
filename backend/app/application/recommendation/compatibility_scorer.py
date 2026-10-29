"""Experimental shared annotation measure, not validated fashion harmony."""
from fractions import Fraction
from itertools import combinations
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.domain.value_objects.scored_candidate import VerifiedScoringInput
from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore


class ProfileUnavailable(ValueError):
    pass


class CompatibilityScorer:
    def __init__(self,mapper=None):
        self.mapper = mapper or GarmentEvidenceMapper()
        self._unavailable = ComponentScore(ScoreEvidence("compatibility",None,"Unavailable"))

    def score(self,verified,profile):
        if not isinstance(verified,VerifiedScoringInput):
            raise ValueError("Verified scoring input required.")
        if profile.compatibility == "disabled":
            return self._unavailable
        members = verified.candidate.members
        if len(members) == 1:
            # Reject entire session: do not penalise singleton outfits or switch
            # weights only for this candidate. Caller can explicitly rerun deferred.
            raise ProfileUnavailable("Shared-style profile cannot compare an unpaired candidate.")
        details = []
        for a,b in combinations(members,2):
            first,second = self.mapper.classify(a.garment).style,self.mapper.classify(b.garment).style
            if first.state != "Known" or second.state != "Known" or not first.values or not second.values:
                details.append(ScoreEvidence(a.garment.garment_id+":"+b.garment.garment_id,None,"Unknown",0,1,tuple((value.state.lower() if value.values or value.state != "Known" else "empty")+":"+item.garment.garment_id for item,value in ((a,first),(b,second)))))
            else:
                x,y = set(first.values),set(second.values)
                details.append(ScoreEvidence(a.garment.garment_id+":"+b.garment.garment_id,Fraction(len(x&y),len(x|y)),"Available",1,1))
        observed = sum(x.observed for x in details)
        if observed == 0:
            summary = ScoreEvidence("compatibility",None,"Unknown",0,len(details))
        else:
            summary = ScoreEvidence("compatibility",sum((x.value or Fraction(0)) for x in details)/len(details),"Available" if observed == len(details) else "Partial",observed,len(details))
        return ComponentScore(summary,tuple(details))
