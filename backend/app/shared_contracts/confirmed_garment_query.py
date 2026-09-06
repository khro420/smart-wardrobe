from typing import Protocol


class ConfirmedGarmentQuery(Protocol):
    """Minimal read-only boundary exposed to recommendation/NLP modules.

    Only opaque identifiers cross this contract. Descriptive wardrobe records,
    media paths and unconfirmed/deleted garments remain inside the wardrobe
    subsystem.
    """
    def list_available_garment_ids(self, user_id: str) -> list[str]: ...
