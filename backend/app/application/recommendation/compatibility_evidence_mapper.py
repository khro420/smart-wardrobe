"""Cached current evidence only: no pair creation or dress duplication."""
import re
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.domain.value_objects.compatibility_signature import CompatibilityDescriptor,GarmentCompatibilityEvidence,CompatibilitySignature,STRUCTURES


class CompatibilityEvidenceMapper:
    def __init__(self,policy,mapper=None):
        self.policy = policy
        self.mapper = mapper or GarmentEvidenceMapper()
        self._cache = {}

    @property
    def cache_size(self):
        return len(self._cache)

    def classify(self,garment):
        cached = self._cache.get(garment.garment_id)
        if cached is not None:
            if cached[0] != garment:
                raise ValueError("Conflicting compatibility evidence in one session.")
            return cached[1]
        evidence = self.mapper.classify(garment)
        reasons,observed = [],0
        for field,item in (("style",evidence.style),("colour",evidence.colour)):
            if item.state == "Known" and item.values:
                observed += 1
            else:
                reasons.append(field+":"+("empty" if item.state == "Known" else item.state.lower()))
        pattern = garment.pattern
        if "pattern" in garment.invalid_attributes:
            reasons.append("pattern:malformed")
        elif pattern is None or not pattern.strip():
            reasons.append("pattern:missing")
        else:
            pattern = re.sub(r"\s+"," ",pattern.strip().casefold())
            if pattern in self.policy.patterns:
                observed += 1
            else:
                reasons.append("pattern:unrecognized")
        descriptor = CompatibilityDescriptor(evidence.style.values,evidence.colour.values[0],pattern) if observed == 3 else None
        result = GarmentCompatibilityEvidence(descriptor,observed,tuple(reasons))
        self._cache[garment.garment_id] = (garment,result)
        return result

    def signature(self,candidate):
        evidence = tuple((item.role,self.classify(item.garment)) for item in candidate.members)
        observed = sum(item.observed for _,item in evidence)
        reasons = tuple(role+":"+reason for role,item in evidence for reason in item.reasons)
        roles = tuple(item.role for item in candidate.members)
        structure = next(name for name,expected in STRUCTURES.items() if roles == expected)
        signature = CompatibilitySignature(structure,tuple((role,item.descriptor) for role,item in evidence)) if all(item.descriptor is not None for _,item in evidence) else None
        return signature,observed,len(evidence)*3,reasons
