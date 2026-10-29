from typing import Protocol
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot


class ConfirmedGarmentQuery(Protocol):
    """Read-only Digital Wardrobe boundary.

    The legacy ID operation checks ownership/availability only. The snapshot
    operation additionally requires linked confirmed processing provenance.
    Neither operation exposes storage paths or temporary processing records.
    """
    def list_available_garment_ids(self, user_id: str) -> list[str]: ...

    def get_confirmed_available_garments(self, user_id: str) -> tuple[ConfirmedGarmentSnapshot, ...]: ...
