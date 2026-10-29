"""Immutable declarations; no assertion of independently verified suitability."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SuitabilityDeclaration:
    field: str
    value: str
    decision: str

    def __post_init__(self):
        if self.field not in ("occasion","formality") or not isinstance(self.value,str) or not self.value or self.decision not in ("allow","deny"):
            raise ValueError("Invalid suitability declaration.")


@dataclass(frozen=True)
class GarmentSuitabilityEvidence:
    declarations: tuple[SuitabilityDeclaration, ...] = ()
    malformed_fields: tuple[str, ...] = ()
    source_state: str = "Missing"
    policy_version: str = "owner-declarations-1.0.0"

    def __post_init__(self):
        if self.source_state not in ("Missing","Empty","Parsed","Malformed") or not isinstance(self.policy_version,str) or not self.policy_version:
            raise ValueError("Invalid suitability evidence metadata.")
        if not isinstance(self.declarations,(tuple,list)) or any(not isinstance(x,SuitabilityDeclaration) for x in self.declarations):
            raise ValueError("Invalid suitability declarations.")
        if not isinstance(self.malformed_fields,(tuple,list)) or any(x not in ("occasion","formality") for x in self.malformed_fields):
            raise ValueError("Invalid malformed fields.")
        if self.source_state != "Parsed" and self.declarations:
            raise ValueError("Unavailable collection cannot carry declarations.")
        object.__setattr__(self,"declarations",tuple(dict.fromkeys(self.declarations)))
        object.__setattr__(self,"malformed_fields",tuple(sorted(set(self.malformed_fields))))

    def state_for(self,field,value):
        if field not in ("occasion","formality"):
            raise ValueError("Unsupported suitability field.")
        if self.source_state in ("Missing","Empty","Malformed") or field in self.malformed_fields:
            return "Unknown"
        decisions = {item.decision for item in self.declarations if item.field == field and item.value == value}
        return "Pass" if decisions == {"allow"} else "Fail" if decisions == {"deny"} else "Unknown"
