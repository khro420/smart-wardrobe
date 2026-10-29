from typing import Protocol
from app.application.ports.recommendation_repository import RecommendationRepository
from app.domain.value_objects.recommendation_persistence import RecommendationWrite


class AssistantRepository(RecommendationRepository, Protocol):
    def find_assistant_submission(self,user_id: str,key: str,request_text: str) -> dict | None: ...
    def persist_assistant(self,command: RecommendationWrite) -> tuple[dict,bool]: ...
