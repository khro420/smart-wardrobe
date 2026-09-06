from typing import Protocol


class VisualisationGateway(Protocol):
    """Contract through which recommendation results can request visualisation."""
    def create_from_outfit(self, user_id: str, outfit_id: str, person_image_id: str) -> str: ...
    def create_from_recommendation(self, user_id: str, recommendation_id: str, person_image_id: str) -> str: ...
