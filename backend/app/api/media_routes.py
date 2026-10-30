from fastapi import APIRouter, Depends, Response, UploadFile
from fastapi.responses import FileResponse

from app.infrastructure.security import current_user_id
from app.infrastructure.media.protected_media_store import media_path_for_owner
from app.application.visualisation.personal_image_service import archive_person_image, register_person_image
from app.application.wardrobe.profile_service import active_profile_id
from app.infrastructure.media import protected_media_store as media_service

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{media_id}")
def get_media(media_id: str, user_id: str = Depends(current_user_id)) -> FileResponse:
    path, content_type = media_path_for_owner(media_id, user_id)
    return FileResponse(path, media_type=content_type)


@router.post("/person-images", status_code=201)
async def upload_person_image(file: UploadFile, user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)) -> dict:
    media_id = await media_service.store_image(file, user_id, "person_image")
    return register_person_image(media_id, user_id, file.filename or "Personal image", profile_id)


@router.delete("/person-images/{person_image_id}", status_code=204)
def remove_person_image(
    person_image_id: str,
    user_id: str = Depends(current_user_id),
    profile_id: str = Depends(active_profile_id),
) -> Response:
    archive_person_image(person_image_id, user_id, profile_id)
    return Response(status_code=204)
