from typing import Literal

from fastapi import APIRouter, Depends, Query, Response

from app.infrastructure.security import current_user_id
from app.domain.value_objects.requests import GarmentUpdate, OutfitCreate, OutfitUpdate
from app.application.wardrobe import wardrobe_service as wardrobe

router = APIRouter(prefix="/wardrobe", tags=["digital wardrobe"])
WardrobeSort = Literal["updated_desc", "updated_asc", "name_asc", "name_desc", "favourites"]


@router.get("/garments")
def garments(
    query: str = Query(default="", max_length=100),
    category: str | None = Query(default=None, max_length=50),
    favourite: bool | None = None,
    sort: WardrobeSort = "updated_desc",
    user_id: str = Depends(current_user_id),
) -> list[dict]:
    return wardrobe.list_garments(user_id, query.strip(), category, favourite, sort)


@router.get("/garments/{garment_id}/dependencies")
def garment_dependencies(garment_id: str, user_id: str = Depends(current_user_id)) -> dict:
    return wardrobe.get_garment_dependencies(garment_id, user_id)


@router.patch("/garments/{garment_id}")
def update_garment(garment_id: str, body: GarmentUpdate, user_id: str = Depends(current_user_id)) -> dict:
    return wardrobe.update_garment(garment_id, user_id, body.model_dump(exclude_unset=True))


@router.delete("/garments/{garment_id}", status_code=204)
def archive_garment(garment_id: str, user_id: str = Depends(current_user_id)) -> Response:
    wardrobe.archive_garment(garment_id, user_id)
    return Response(status_code=204)


@router.get("/outfits")
def outfits(
    query: str = Query(default="", max_length=100),
    category: str | None = Query(default=None, max_length=50),
    creation_type: Literal["image_upload", "manual", "recommendation"] | None = None,
    favourite: bool | None = None,
    sort: WardrobeSort = "updated_desc",
    user_id: str = Depends(current_user_id),
) -> list[dict]:
    return wardrobe.list_outfits(user_id, query.strip(), category, creation_type, favourite, sort)


@router.get("/outfits/{outfit_id}/dependencies")
def outfit_dependencies(outfit_id: str, user_id: str = Depends(current_user_id)) -> dict:
    return wardrobe.get_outfit_dependencies(outfit_id, user_id)


@router.post("/outfits", status_code=201)
def create_outfit(body: OutfitCreate, user_id: str = Depends(current_user_id)) -> dict:
    return wardrobe.create_outfit(user_id, body.name, body.garment_ids, body.description)


@router.patch("/outfits/{outfit_id}")
def update_outfit(outfit_id: str, body: OutfitUpdate, user_id: str = Depends(current_user_id)) -> dict:
    return wardrobe.update_outfit(outfit_id, user_id, body.model_dump(exclude_unset=True))


@router.delete("/outfits/{outfit_id}", status_code=204)
def archive_outfit(outfit_id: str, user_id: str = Depends(current_user_id)) -> Response:
    wardrobe.archive_outfit(outfit_id, user_id)
    return Response(status_code=204)
