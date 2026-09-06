from dataclasses import dataclass


@dataclass(frozen=True)
class StandardisationResult:
    preferred_media_id: str
    used_fallback: bool
    vtoff_media_id: str | None = None
    notice: str | None = None
    metadata: dict[str, object] | None = None
