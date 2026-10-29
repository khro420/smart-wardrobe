"""Read-only retrieval diagnostics and explicit stream completion metadata."""
from dataclasses import dataclass
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot


@dataclass(frozen=True)
class GarmentExclusion:
    garment_id: str | None
    reason: str

    def __post_init__(self):
        if (self.garment_id is not None and not isinstance(self.garment_id, str)) or not isinstance(self.reason, str):
            raise ValueError("Exclusion metadata must be immutable text.")


@dataclass(frozen=True)
class RetrievalResult:
    garments: tuple[ConfirmedGarmentSnapshot, ...]
    exclusions: tuple[GarmentExclusion, ...] = ()

    def __post_init__(self):
        for field, item_type in (("garments", ConfirmedGarmentSnapshot), ("exclusions", GarmentExclusion)):
            items = getattr(self, field)
            if not isinstance(items, (tuple, list)) or any(not isinstance(item, item_type) for item in items):
                raise ValueError("Invalid retrieval result.")
            object.__setattr__(self, field, tuple(items))


@dataclass(frozen=True)
class CandidateGenerationResult:
    status: str
    complete: bool
    candidate_count: int = 0
    reason: str | None = None
    exclusions: tuple[GarmentExclusion, ...] = ()
    validity: str = "STRUCTURAL_ONLY"

    def __post_init__(self):
        if self.status not in {"Pending", "Running", "StructuralCandidates", "NoEligibleGarments", "InsufficientStructure", "NoStructuralCandidates", "ProcessingFailure", "Interrupted", "PolicyUnavailable"}:
            raise ValueError("Invalid generation status.")
        if not isinstance(self.complete, bool) or isinstance(self.candidate_count, bool) or not isinstance(self.candidate_count, int) or self.candidate_count < 0:
            raise ValueError("Invalid completion metadata.")
        expected_complete = self.status in {"StructuralCandidates", "NoEligibleGarments", "InsufficientStructure", "NoStructuralCandidates"}
        if self.complete != expected_complete or self.validity != "STRUCTURAL_ONLY":
            raise ValueError("Invalid completion or validity claim.")
        if self.reason is not None and not isinstance(self.reason, str):
            raise ValueError("Invalid reason.")
        if not isinstance(self.exclusions, (list, tuple)) or any(not isinstance(item, GarmentExclusion) for item in self.exclusions):
            raise ValueError("Invalid exclusion diagnostics.")
        object.__setattr__(self, "exclusions", tuple(self.exclusions))
