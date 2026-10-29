"""Immutable semantic observations; unspecified context is never invented."""
from dataclasses import dataclass, asdict
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest

STATES = ('Known', 'Unspecified', 'Ambiguous', 'Conflicting', 'Unsupported')


@dataclass(frozen=True)
class Situation:
    identifier: str
    label: str
    phrases: tuple[str, ...]
    activity: str | None
    venue: str | None
    projection_occasion: str


@dataclass(frozen=True)
class SourceSpan:
    start: int
    end: int
    text: str

    def __post_init__(self):
        if type(self.start) is not int or type(self.end) is not int or not 0 <= self.start < self.end or not isinstance(self.text, str) or len(self.text) != self.end-self.start:
            raise ValueError('Invalid original source span.')


@dataclass(frozen=True)
class ContextSlot:
    state: str = 'Unspecified'
    values: tuple[str, ...] = ()
    spans: tuple[SourceSpan, ...] = ()

    def __post_init__(self):
        if (self.state not in STATES or type(self.values) is not tuple or type(self.spans) is not tuple
                or any(not isinstance(v, str) or not v for v in self.values)
                or any(type(s) is not SourceSpan for s in self.spans)
                or self.state == 'Unspecified' and (self.values or self.spans)
                or self.state == 'Known' and not self.values):
            raise ValueError('Invalid semantic slot.')

    @property
    def value(self):
        return self.values[0] if self.state == 'Known' and len(self.values) == 1 else None


@dataclass(frozen=True)
class GeneralContext:
    original_text: str
    situation: ContextSlot = ContextSlot()
    activity: ContextSlot = ContextSlot()
    role: ContextSlot = ContextSlot()
    venue: ContextSlot = ContextSlot()
    environment: ContextSlot = ContextSlot()
    dress_code: ContextSlot = ContextSlot()
    formality: ContextSlot = ContextSlot()
    style: ContextSlot = ContextSlot()
    colours: ContextSlot = ContextSlot()
    categories: ContextSlot = ContextSlot()
    soft_preferences: ContextSlot = ContextSlot()
    goals: ContextSlot = ContextSlot()
    temporal: ContextSlot = ContextSlot()
    companions: ContextSlot = ContextSlot()
    unhandled: ContextSlot = ContextSlot()
    facets: ContextSlot = ContextSlot()
    grammar_sha256: str = ''
    taxonomy_sha256: str = ''
    version: str = 'general-context-1.0.0'
    bundle_id: str = 'legacy_8_v1'

    def __post_init__(self):
        if ((self.version,self.bundle_id) not in (('general-context-1.0.0','legacy_8_v1'),('general-context-1.1.0','context_18_v1')) or not isinstance(self.original_text, str)):
            raise ValueError('Invalid context schema.')
        if (self.facets.state not in ('Unspecified','Known') or len(self.facets.values)>2
                or len(set(self.facets.values))!=len(self.facets.values)
                or any(v not in ('meal:dinner','celebration:birthday','transport:train','transport:bus','transport:flight') for v in self.facets.values)
                or sum(v.startswith('transport:') for v in self.facets.values)>1
                or self.bundle_id=='legacy_8_v1' and self.facets.state!='Unspecified'):
            raise ValueError('Invalid bounded context facets.')
        for name in ('situation', 'activity', 'role', 'venue', 'environment', 'dress_code', 'formality', 'style', 'colours', 'categories', 'soft_preferences', 'goals', 'temporal', 'companions', 'unhandled', 'facets'):
            slot = getattr(self, name)
            if type(slot) is not ContextSlot or any(self.original_text[s.start:s.end] != s.text for s in slot.spans):
                raise ValueError('Context spans do not match original text.')
            if slot.state == 'Known' and (not slot.spans or name not in ('colours', 'categories', 'soft_preferences', 'goals','facets') and len(slot.values) != 1):
                raise ValueError('Incomplete or non-scalar semantic observation.')


@dataclass(frozen=True)
class GeneralContextRequest(StructuredOutfitRequest):
    context: GeneralContext | None = None

    def __post_init__(self):
        super().__post_init__()
        if type(self.context) is not GeneralContext or self.context.situation.state != 'Known':
            raise ValueError('A recognised context frame is required.')

    def minimum_request(self):
        return StructuredOutfitRequest(style=self.style, colours=self.colours, garment_categories=self.garment_categories)

    def to_dict(self):
        return {**super().to_dict(), 'context': asdict(self.context)}
