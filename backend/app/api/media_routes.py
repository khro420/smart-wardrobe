from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse

from app.infrastructure.security import current_user_id
from app.infrastructure.media.protected_media_store import media_path_for_owner
from app.application.visualisation.personal_image_service import register_person_image
from app.infrastructure.media import protected_media_store as media_service

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{media_id}")
def get_media(media_id: str, user_id: str = Depends(current_user_id)) -> FileResponse:
    path, content_type = media_path_for_owner(media_id, user_id)
    return FileResponse(path, media_type=content_type)


@router.post("/person-images", status_code=201)
async def upload_person_image(file: UploadFile, user_id: str = Depends(current_user_id)) -> dict:
    media_id = await media_service.store_image(file, user_id, "person_image")
    return register_person_image(media_id, user_id, file.filename or "Personal image")
