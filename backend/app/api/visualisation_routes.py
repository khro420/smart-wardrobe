from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, model_validator

from app.infrastructure.security import current_user_id
from app.application.wardrobe.profile_service import active_profile_id
from app.domain.value_objects.requests import VisualisationCreate, VisualisationPrepare
from app.application.visualisation import outfit_visualisation_service as visualisation
from app.application.visualisation.personal_image_service import list_person_images
from app.application.visualisation.visualisation_result_service import get_visualisation

router = APIRouter(prefix="/visualisations", tags=["outfit visualisation"])


@router.get('/history')
def history(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=10000), user_id: str = Depends(current_user_id)):
    from app.application.visualisation.activity_service import list_history
    return list_history(user_id, limit, offset)


@router.delete('/history/{kind}/{identifier}', status_code=204)
def remove_history(kind: str, identifier: str, user_id: str = Depends(current_user_id)):
    from app.application.visualisation.activity_service import remove_history as remove
    remove(user_id, kind, identifier)


class GroupDetect(BaseModel):
    person_image_id: str


class GroupAssignment(BaseModel):
    person_index: int
    outfit_id: str | None = None
    recommendation_id: str | None = None

    @model_validator(mode='after')
    def one_source(self):
        if bool(self.outfit_id) == bool(self.recommendation_id):
            raise ValueError('Choose exactly one outfit or recommendation.')
        return self


class GroupSubmit(BaseModel):
    assignments: list[GroupAssignment]


@router.post('/groups/detect')
def detect_group(body: GroupDetect, user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)):
    from app.application.visualisation import group_visualisation_service as group
    return group.detect(user_id, profile_id, body.person_image_id)


@router.post('/groups/{identifier}', status_code=202)
def create_group(identifier: str, body: GroupSubmit, background_tasks: BackgroundTasks, user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)):
    from app.application.visualisation import group_visualisation_service as group
    group.submit(user_id, profile_id, identifier, body.assignments)
    background_tasks.add_task(group.run, user_id, identifier)
    return {'id': identifier, 'status': 'queued'}


@router.get('/groups/{identifier}')
def get_group(identifier: str, user_id: str = Depends(current_user_id)):
    from app.application.visualisation import group_visualisation_service as group
    return group.get(user_id, identifier)


@router.post('/groups/{identifier}/cancel', status_code=204)
def cancel_group(identifier: str, user_id: str = Depends(current_user_id)):
    from app.application.visualisation import group_visualisation_service as group
    group.cancel(user_id, identifier)


@router.get("/person-images")
def person_images(user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)) -> list[dict]:
    return list_person_images(user_id, profile_id)


@router.post("/prepare")
def prepare(body: VisualisationPrepare, user_id: str = Depends(current_user_id)) -> dict:
    return visualisation.prepare_visualisation(
        user_id=user_id,
        outfit_id=body.outfit_id,
        recommendation_id=body.recommendation_id,
    )


@router.post("", status_code=202)
def create(body: VisualisationCreate, background_tasks: BackgroundTasks, user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)) -> dict:
    visualisation_id = visualisation.create_visualisation(
        user_id=user_id,
        person_image_id=body.person_image_id,
        outfit_id=body.outfit_id,
        recommendation_id=body.recommendation_id,
        profile_id=profile_id,
    )
    background_tasks.add_task(visualisation.run_visualisation, visualisation_id, user_id)
    return {"id": visualisation_id, "status": "queued"}


@router.get("/{visualisation_id}")
def get(visualisation_id: str, user_id: str = Depends(current_user_id)) -> dict:
    return get_visualisation(visualisation_id, user_id)


@router.post("/{visualisation_id}/cancel", status_code=204)
def cancel(visualisation_id: str, user_id: str = Depends(current_user_id)) -> None:
    visualisation.cancel_visualisation(visualisation_id, user_id)
