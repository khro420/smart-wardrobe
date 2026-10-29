"""Additive homepage retry lookup; Phase 5A persistence interface is unchanged."""
from typing import Protocol
from app.application.ports.recommendation_repository import RecommendationRepository
from app.domain.value_objects.recommendation_persistence import RecommendationWrite


class HomepageRepository(RecommendationRepository, Protocol):
    def find_homepage_submission(self, user_id: str, submission_key: str) -> dict | None: ...
    def persist_homepage(self, command: RecommendationWrite) -> tuple[dict, bool]: ...
