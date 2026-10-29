"""Immutable minimum-policy evidence; no scores or aesthetic validity claim."""
from dataclasses import dataclass
from app.domain.value_objects.outfit_candidate import OutfitCandidate


@dataclass(frozen=True)
class AttributeEvidence:
    values: tuple[str, ...]
    state: str
    method: str

    def __post_init__(self):
        if self.state not in ("Known", "Missing", "Malformed", "Unrecognized") or not isinstance(self.method, str):
            raise ValueError("Invalid evidence metadata.")
        if not isinstance(self.values, (list, tuple)) or any(not isinstance(value, str) for value in self.values):
            raise ValueError("Invalid evidence values.")
        if self.state in ("Missing","Malformed") and self.values:
            raise ValueError("Missing/malformed evidence cannot contain positive values.")
        object.__setattr__(self, "values", tuple(dict.fromkeys(self.values)))


@dataclass(frozen=True)
class GarmentRequestEvidence:
    colour: AttributeEvidence
    style: AttributeEvidence

    def __post_init__(self):
        if not isinstance(self.colour, AttributeEvidence) or not isinstance(self.style, AttributeEvidence):
            raise ValueError("Invalid garment evidence.")


@dataclass(frozen=True)
class MandatoryCondition:
    field: str
    value: str
    state: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.field, str) or not isinstance(self.value, str) or self.state not in ("Pass", "Fail", "Unknown"):
            raise ValueError("Invalid mandatory condition.")
        if not isinstance(self.evidence_ids, (list, tuple)) or any(not isinstance(item, str) for item in self.evidence_ids):
            raise ValueError("Invalid evidence identifiers.")
        object.__setattr__(self, "evidence_ids", tuple(self.evidence_ids))


@dataclass(frozen=True)
class RequestEvaluation:
    conditions: tuple[MandatoryCondition, ...]

    def __post_init__(self):
        if not isinstance(self.conditions, (list, tuple)) or any(not isinstance(item, MandatoryCondition) for item in self.conditions):
            raise ValueError("Invalid conditions.")
        object.__setattr__(self, "conditions", tuple(self.conditions))

    @property
    def state(self):
        states = {item.state for item in self.conditions}
        return "Fail" if "Fail" in states else "Unknown" if "Unknown" in states else "Pass"


@dataclass(frozen=True)
class EvaluatedCandidate:
    candidate: OutfitCandidate
    evaluation: RequestEvaluation

    def __post_init__(self):
        if not isinstance(self.candidate, OutfitCandidate) or not isinstance(self.evaluation, RequestEvaluation) or self.evaluation.state != "Pass":
            raise ValueError("Only passing candidates may be emitted.")

    @property
    def validity(self):
        return "APPROVED_MINIMUM_REQUEST_CONDITIONS"


@dataclass(frozen=True)
class RequestGenerationResult:
    status: str = "Pending"
    complete: bool = False
    examined: int = 0
    passed: int = 0
    failed: int = 0
    unknown: int = 0
    reason: str | None = None

    def __post_init__(self):
        terminal_complete = {"MatchingCandidates", "NoMatchingCandidates", "InsufficientEvidence", "NoEligibleGarments", "InsufficientStructure", "NoStructuralCandidates"}
        if self.status not in terminal_complete | {"Pending", "Running", "PolicyUnavailable", "ProcessingFailure", "Interrupted"} or self.complete != (self.status in terminal_complete):
            raise ValueError("Invalid request stream completion.")
        if not isinstance(self.complete, bool) or any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (self.examined, self.passed, self.failed, self.unknown)):
            raise ValueError("Invalid stream counters.")
        if self.examined != self.passed+self.failed+self.unknown or (self.reason is not None and not isinstance(self.reason, str)):
            raise ValueError("Invalid stream accounting.")
