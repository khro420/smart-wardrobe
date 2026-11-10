"""Immutable parallel evidence. Legacy numerical snapshots retain their exact format."""
from dataclasses import dataclass
from app.domain.value_objects.verified_garment_subtype import encode,decode,SOURCE_VERSION
@dataclass(frozen=True)
class ConfirmedGarmentSubtype:
    garment_id:str
    payload:str
    def __post_init__(self):
        value=decode(self.payload,262144)
        from app.domain.value_objects.verified_garment_subtype import validate_source
        validate_source(value)
        if value.get('version')!=SOURCE_VERSION or value.get('subject_id')!=self.garment_id:raise ValueError('Invalid captured subtype source.')
        object.__setattr__(self,'payload',encode(value))
    def to_dict(self):return decode(self.payload,262144)
