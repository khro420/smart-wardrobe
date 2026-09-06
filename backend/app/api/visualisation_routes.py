from fastapi import APIRouter, BackgroundTasks, Depends

from app.infrastructure.security import current_user_id
from app.domain.value_objects.requests import VisualisationCreate, VisualisationPrepare
from app.application.visualisation import outfit_visualisation_service as visualisation
from app.application.visualisation.personal_image_service import list_person_images
from app.application.visualisation.visualisation_result_service import get_visualisation

router = APIRouter(prefix="/visualisations", tags=["outfit visualisation"])


@router.get("/person-images")
def person_images(user_id: str = Depends(current_user_id)) -> list[dict]:
    return list_person_images(user_id)


@router.post("/prepare")
def prepare(body: VisualisationPrepare, user_id: str = Depends(current_user_id)) -> dict:
    return visualisation.prepare_visualisation(
        user_id=user_id,
        outfit_id=body.outfit_id,
        recommendation_id=body.recommendation_id,
    )


@router.post("", status_code=202)
def create(body: VisualisationCreate, background_tasks: BackgroundTasks, user_id: str = Depends(current_user_id)) -> dict:
    visualisation_id = visualisation.create_visualisation(
        user_id=user_id,
        person_image_id=body.person_image_id,
        outfit_id=body.outfit_id,
        recommendation_id=body.recommendation_id,
    )
    background_tasks.add_task(visualisation.run_visualisation, visualisation_id, user_id)
    return {"id": visualisation_id, "status": "queued"}


@router.get("/{visualisation_id}")
def get(visualisation_id: str, user_id: str = Depends(current_user_id)) -> dict:
    return get_visualisation(visualisation_id, user_id)


@router.post("/{visualisation_id}/cancel", status_code=204)
def cancel(visualisation_id: str, user_id: str = Depends(current_user_id)) -> None:
    visualisation.cancel_visualisation(visualisation_id, user_id)
