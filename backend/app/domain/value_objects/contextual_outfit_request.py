"""Versioned context is distinct from the user's five explicit request fields."""
from dataclasses import dataclass, asdict
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest


@dataclass(frozen=True)
class WeddingContext:
    role: str = 'unspecified'
    assumed_role: str | None = 'guest'
    dress_code: str | None = None
    version: str = 'contextual-nlp-1.0.0'

    def __post_init__(self):
        if (self.version != 'contextual-nlp-1.0.0'
                or self.role not in ('unspecified', 'guest', 'bride', 'groom', 'bridesmaid', 'groomsman')
                or self.assumed_role != ('guest' if self.role == 'unspecified' else None)
                or self.dress_code not in (None, 'casual', 'smart_casual', 'formal', 'black_tie')):
            raise ValueError('Invalid wedding context.')


@dataclass(frozen=True)
class ContextualOutfitRequest(StructuredOutfitRequest):
    context: WeddingContext | None = None

    def __post_init__(self):
        super().__post_init__()
        if (not isinstance(self.context, WeddingContext) or self.occasion != 'wedding'
                or self.formality != self.context.dress_code):
            raise ValueError('Context and explicit fields differ.')

    def minimum_request(self):
        return StructuredOutfitRequest(style=self.style, colours=self.colours,
                                       garment_categories=self.garment_categories)

    def to_dict(self):
        return {**super().to_dict(), 'context': asdict(self.context)}

