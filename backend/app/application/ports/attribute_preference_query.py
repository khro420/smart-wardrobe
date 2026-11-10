"""P2 preferences require the captured account and intended wearer explicitly."""
from typing import Protocol
from app.domain.value_objects.attribute_preferences import AttributePreferenceSnapshot


class AttributePreferenceQuery(Protocol):
    def capture(self, account_id: str, wearer) -> AttributePreferenceSnapshot: ...
    def capture_locked(self, conn, account_id: str, wearer) -> AttributePreferenceSnapshot: ...
