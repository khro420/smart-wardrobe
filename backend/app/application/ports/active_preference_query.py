"""Caller supplies an authenticated user ID, never a client-selected owner."""
from abc import ABC,abstractmethod
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot


class ActivePreferenceQuery(ABC):
    @abstractmethod
    def get_active_preferences(self,user_id: str) -> tuple[PreferenceSnapshot, ...]:
        """Read active preferences for this authenticated user only."""
        raise NotImplementedError
