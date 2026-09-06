"""NLP chat and recommendation HTTP boundary from the report's application flow."""

from fastapi import APIRouter, Depends

from app.application.recommendation import recommendation_service as recommendations
from app.domain.value_objects.requests import RecommendationCreate, RecommendationSaveAsOutfit
from app.infrastructure.security import current_user_id

router = APIRouter(prefix="/recommendations", tags=["NLP outfit recommendations"])


@router.get("")
def list_all(user_id: str = Depends(current_user_id)) -> list[dict]:
    return recommendations.list_recommendations(user_id)


@router.post("", status_code=201)
def create(body: RecommendationCreate, user_id: str = Depends(current_user_id)) -> dict:
    return recommendations.create_recommendation(user_id, body.request_text)


@router.post("/{recommendation_id}/save-as-outfit", status_code=201)
def save_as_outfit(recommendation_id: str, body: RecommendationSaveAsOutfit, user_id: str = Depends(current_user_id)) -> dict:
    return recommendations.save_as_outfit(recommendation_id, user_id, body.name)
