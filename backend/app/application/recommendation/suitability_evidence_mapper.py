"""Parse exact reserved tags once per garment/session; no persistence reads."""
from app.application.recommendation.suitability_policy import SuitabilityPolicy
from app.domain.value_objects.garment_suitability_evidence import GarmentSuitabilityEvidence,SuitabilityDeclaration


class SuitabilityEvidenceParser:
    def __init__(self,policy=None):
        self.policy = policy or SuitabilityPolicy.load()
        self._cache = {}

    @property
    def cache_size(self):
        return len(self._cache)

    def parse(self,garment):
        cached = self._cache.get(garment.garment_id)
        if cached is not None:
            if cached[0] != garment:
                raise ValueError("Conflicting suitability snapshots in one session.")
            return cached[1]
        tags = garment.custom_tags
        declarations,malformed = [],set()
        if "custom_tags" in garment.invalid_attributes:
            source = "Malformed"
        elif tags is None:
            source = "Missing"
        elif not tags:
            source = "Empty"
        else:
            source = "Parsed"
            for tag in tags:
                # Ordinary tags have no reserved meaning, including bare 'formal'.
                # Case/version/grammar errors in the reserved namespace abstain.
                if not tag.casefold().startswith("rec:"):
                    continue
                parts = tag.split(":")
                field = parts[2] if len(parts) > 2 else None
                affected = {field} if field in ("occasion","formality") else {"occasion","formality"}
                valid = len(parts) == 5 and ":".join(parts[:2]) == self.policy.reserved_prefix and field in ("occasion","formality")
                if valid:
                    valid = parts[3] in self.policy.values(field) and parts[4] in ("allow","deny")
                if not valid:
                    malformed.update(affected)
                else:
                    declarations.append(SuitabilityDeclaration(field,parts[3],parts[4]))
        evidence = GarmentSuitabilityEvidence(tuple(sorted(set(declarations),key=lambda item:(item.field,item.value,item.decision))),tuple(sorted(malformed)),source,self.policy.version)
        self._cache[garment.garment_id] = (garment,evidence)
        return evidence
