from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile

from app.infrastructure.security import current_user_id
from app.domain.value_objects.requests import ConfirmRequest, ReviewRequest
from app.application.garment_processing import garment_processing_orchestrator as processing
from app.application.garment_processing import processing_job_service, review_service, upload_validator

router = APIRouter(prefix="/processing/jobs", tags=["garment processing"])


@router.post("", status_code=202)
async def submit_image(file: UploadFile, background_tasks: BackgroundTasks, user_id: str = Depends(current_user_id)) -> dict:
    media_id = await upload_validator.validate_and_store_wardrobe_image(file, user_id)
    job_id = processing_job_service.create_job(media_id, user_id)
    background_tasks.add_task(processing.run_job, job_id, user_id)
    return {"id": job_id, "status": "queued"}


@router.get("/{job_id}")
def get_job(job_id: str, user_id: str = Depends(current_user_id)) -> dict:
    return processing_job_service.get_job(job_id, user_id)


@router.post("/{job_id}/review")
def review(job_id: str, body: ReviewRequest, user_id: str = Depends(current_user_id)) -> dict:
    return review_service.review_job(job_id, user_id, [item.model_dump(exclude_unset=True) for item in body.items])


@router.post("/{job_id}/confirm", status_code=201)
def confirm(job_id: str, body: ConfirmRequest, user_id: str = Depends(current_user_id)) -> dict:
    return review_service.confirm_reviewed_candidates(job_id, user_id, body.item_ids, body.save_mode, body.outfit_name)


@router.post("/{job_id}/cancel", status_code=204)
def cancel(job_id: str, user_id: str = Depends(current_user_id)) -> None:
    processing_job_service.cancel_job(job_id, user_id)
