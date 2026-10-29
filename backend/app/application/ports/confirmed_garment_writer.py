from typing import Protocol


class ConfirmedGarmentWriter(Protocol):
    def save_confirmed_candidates(self, job_id: str, user_id: str, item_ids: list[str], save_mode: str, outfit_name: str | None, profile_id: str | None = None) -> dict: ...

    def save_automatically_processed_candidates(self, job_id: str, user_id: str, item_ids: list[str] | None = None, profile_id: str | None = None) -> dict: ...
