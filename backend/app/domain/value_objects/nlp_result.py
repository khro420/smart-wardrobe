"""Controlled NLP outcomes and immutable, internal interpretation evidence."""
from dataclasses import dataclass
from typing import Literal
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest


@dataclass(frozen=True)
class ExtractionMatch:
    field: str
    canonical_value: str
    phrase: str
    start: int
    end: int
    kind: str | None = None

    def __post_init__(self):
        if any(not isinstance(value, str) for value in (self.field, self.canonical_value, self.phrase)) or (self.kind is not None and not isinstance(self.kind, str)):
            raise ValueError("Extraction metadata must be immutable text.")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (self.start, self.end)) or not 0 <= self.start < self.end:
            raise ValueError("Invalid normalized-text evidence span.")


@dataclass(frozen=True)
class NLPOutcome:
    status: Literal["Supported", "InvalidInput", "UnsupportedRequest", "ProcessingError"]
    reason: str
    message: str
    original_text: str | None
    structured_request: StructuredOutfitRequest | None = None
    evidence: tuple[ExtractionMatch, ...] = ()

    def __post_init__(self):
        if self.status not in ("Supported", "InvalidInput", "UnsupportedRequest", "ProcessingError"):
            raise ValueError("Invalid NLP outcome status.")
        if not all(isinstance(value, str) for value in (self.reason, self.message)) or (self.original_text is not None and not isinstance(self.original_text, str)):
            raise ValueError("Outcome metadata must be text.")
        if (self.status == "Supported") != isinstance(self.structured_request, StructuredOutfitRequest):
            raise ValueError("Only supported outcomes contain structured requests.")
        if not isinstance(self.evidence, (tuple, list)) or any(not isinstance(item, ExtractionMatch) for item in self.evidence):
            raise ValueError("Invalid extraction evidence.")
        object.__setattr__(self, "evidence", tuple(self.evidence))
