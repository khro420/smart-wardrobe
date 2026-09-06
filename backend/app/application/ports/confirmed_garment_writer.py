from typing import Protocol


class ConfirmedGarmentWriter(Protocol):
    def save_confirmed_candidates(self, job_id: str, user_id: str, item_ids: list[str], save_mode: str, outfit_name: str | None) -> dict: ...
