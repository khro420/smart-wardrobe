"""Read-only completed-interaction boundary, independent from generation."""
from typing import Protocol


class ChatHistoryQuery(Protocol):
    def search(self,user_id: str,search: str='',limit: int=50,cursor: str | None=None) -> dict: ...
    def get(self,user_id: str,chat_id: str) -> dict: ...
