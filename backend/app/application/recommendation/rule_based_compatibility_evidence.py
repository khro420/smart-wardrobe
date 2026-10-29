"""One cache per evaluation session; primary colour only, no approximations."""
import re
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.domain.value_objects.rule_based_compatibility import PreparedCompatibilityEvidence


class RuleBasedCompatibilityEvidence:
    def __init__(self):
        self.mapper=GarmentEvidenceMapper()  # Never accept an approximate classifier.
        self._cache={}

    @property
    def cache_size(self):
        return len(self._cache)

    def classify(self,garment):
        cached=self._cache.get(garment.garment_id)
        if cached is not None:
            if cached[0]!=garment:
                raise ValueError("Conflicting garment snapshot within compatibility session.")
            return cached[1]
        raw=self.mapper.classify(garment)
        colour_state="Malformed" if "primary_colour" in garment.invalid_attributes else raw.colour.state
        colour=raw.colour.values[0] if colour_state=="Known" and raw.colour.values else None
        style_state=raw.style.state
        if style_state=="Known" and not raw.style.values:
            style_state="Empty"
        reasons=["colour:"+colour_state.lower(),"colour_method:"+raw.colour.method,
                 "style:"+style_state.lower()]
        for tag in garment.style_tags or ():
            normalized=re.sub(r"\s+"," ",tag.strip().casefold())
            if normalized not in self.mapper.style_aliases:
                reasons.append("unsupported_style:"+tag)
        reasons.extend("upstream_invalid:"+name for name in garment.invalid_attributes)
        result=PreparedCompatibilityEvidence(garment.garment_id,colour,colour_state,
                                             frozenset(raw.style.values),style_state,tuple(reasons))
        self._cache[garment.garment_id]=(garment,result)
        return result
