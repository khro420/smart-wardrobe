"""Persistence only: callers must finish mandatory validation/ranking first."""
from typing import Protocol
from app.domain.value_objects.recommendation_persistence import RecommendationWrite


class RecommendationRepository(Protocol):
    def persist(self, command: RecommendationWrite) -> dict: ...
    def get(self, user_id: str, recommendation_id: str) -> dict: ...
