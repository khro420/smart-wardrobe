"""The service validates canonical fields under the same write lock as CAS."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, model_validator
from app.domain.value_objects.attribute_preferences import UPDATE, validate_families, encode, uuid, HASH


class AttributePreferenceUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    contract: Literal['attribute-preferences-update-1.0.0']
    wearer_id: str
    expected_revision: str
    action_id: str
    families: dict

    @model_validator(mode='after')
    def validate_action(self):
        uuid(self.wearer_id);uuid(self.action_id)
        if not HASH.fullmatch(self.expected_revision): raise ValueError('Invalid preference revision.')
        validate_families(self.families)
        if len(encode(self.model_dump()))>32768: raise ValueError('Preference update exceeds encoding limit.')
        return self
