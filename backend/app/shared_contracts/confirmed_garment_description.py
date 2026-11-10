"""Parallel description projection; never extends the legacy hashed dataclass."""
from dataclasses import dataclass
from typing import Protocol

from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
from app.domain.value_objects.garment_description_evidence import GarmentDescriptionEvidence


@dataclass(frozen=True)
class ConfirmedGarmentDescription:
    snapshot: ConfirmedGarmentSnapshot
    description: GarmentDescriptionEvidence

    def __post_init__(self):
        if type(self.snapshot) is not ConfirmedGarmentSnapshot or type(self.description) is not GarmentDescriptionEvidence:
            raise ValueError('Description collection members must be immutable.')
        subject = self.description.to_dict()['subject']
        if subject['account_id'] != self.snapshot.user_id or subject['garment_id'] != self.snapshot.garment_id:
            raise ValueError('Description subject does not match the strict snapshot.')


class ConfirmedGarmentDescriptionQuery(Protocol):
    def get_confirmed_garment_descriptions(self, user_id: str, policy) -> tuple[ConfirmedGarmentDescription, ...]: ...
