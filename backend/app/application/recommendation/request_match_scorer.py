from app.application.recommendation.exact_score_reuse import ExactScoreReuse
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.domain.value_objects.scored_candidate import VerifiedScoringInput
from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore


class RequestMatchScorer:
    @staticmethod
    def relative_component(verified,prepared):
        """Explicit new-profile entry; score() retains historical semantics."""
        return prepared.component(verified)

    def __init__(self,mapper=None):
        self.mapper = mapper or GarmentEvidenceMapper()
        self._reuse = ExactScoreReuse()
        self._request = None
        self._details = ()
        self._style_facts = {}
        self.fact_hits = self.fact_misses = 0

    def _prepare(self, request):
        if self._request is not request:
            self._request = request
            self._style_facts.clear()
            self._details = tuple((field, None if field == "style" else
                self._reuse.evidence(field,self._reuse.fraction(1),"Available",1,1))
                for field in ("garment_categories","colours","style","occasion","formality")
                if getattr(request,field) is not None)

    def _style(self, garment):
        cached = self._style_facts.get(garment.garment_id)
        if cached is not None:
            if cached[0] != garment:
                raise ValueError("Conflicting garment evidence in one session.")
            self.fact_hits += 1
            return cached[1]
        evidence = self.mapper.classify(garment).style
        fact = (self._request.style in evidence.values, evidence.state == "Known",
                evidence.state.lower()+":"+garment.garment_id)
        self._style_facts[garment.garment_id] = (garment,fact)
        self.fact_misses += 1
        return fact

    def score(self,verified):
        if not isinstance(verified,VerifiedScoringInput):
            raise ValueError("Verified scoring input required.")
        request = verified.request
        self._prepare(request)
        details = []
        for field, prepared in self._details:
            if field == "style":
                base = [member for member in verified.candidate.members if member.role != "outerwear"]
                facts = [self._style(member.garment) for member in base]
                matched = sum(item[0] for item in facts)
                known = sum(item[1] for item in facts)
                reasons = tuple(item[2] for item in facts)
                details.append(self._reuse.evidence(field,self._reuse.fraction(matched,len(base)),"Available" if known == len(base) else "Partial",known,len(base),reasons))
            else:
                details.append(prepared)
        if not details:
            return self._reuse.component(self._reuse.evidence("request_match",None,"NotApplicable"))
        return self._reuse.component(self._reuse.evidence("request_match",self._reuse.mean(tuple(x.value for x in details)),"Partial" if any(x.state == "Partial" for x in details) else "Available",sum(x.observed for x in details),sum(x.possible for x in details)),tuple(details))
