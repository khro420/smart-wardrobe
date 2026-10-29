from typing import Literal

from fastapi import APIRouter, Depends, Header, Query, Response

from app.infrastructure.security import current_user_id
from app.domain.value_objects.requests import GarmentUpdate, OutfitCreate, OutfitUpdate, ContextualSuitabilityReview
from app.application.wardrobe import wardrobe_service as wardrobe
from app.application.wardrobe.profile_service import active_profile_id

router = APIRouter(prefix="/wardrobe", tags=["digital wardrobe"])
WardrobeSort = Literal["updated_desc", "updated_asc", "name_asc", "name_desc", "favourites"]


@router.get("/quota")
def quota(response: Response, user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)) -> dict:
    response.headers["Cache-Control"] = "private, no-store"
    return wardrobe.get_wardrobe_quota(user_id, profile_id)


@router.get("/garments")
def garments(
    query: str = Query(default="", max_length=100),
    category: str | None = Query(default=None, max_length=50),
    favourite: bool | None = None,
    sort: WardrobeSort = "updated_desc",
    colour: str | None = Query(default=None, max_length=50),
    style: str | None = Query(default=None, max_length=100),
    availability: Literal["available", "unavailable", "archived", "all"] = "available",
    user_id: str = Depends(current_user_id),
    profile_id: str = Depends(active_profile_id),
) -> list[dict]:
    return wardrobe.list_garments(user_id, profile_id, query.strip(), category, favourite, sort, colour, style, availability)


@router.get("/garments/{garment_id}/dependencies")
def garment_dependencies(garment_id: str, user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)) -> dict:
    return wardrobe.get_garment_dependencies(garment_id, user_id, profile_id)


@router.patch("/garments/{garment_id}")
def update_garment(garment_id: str, body: GarmentUpdate, user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id), if_match: str | None = Header(default=None)) -> dict:
    return wardrobe.update_garment(garment_id, user_id, profile_id, body.model_dump(exclude_unset=True), expected_tag_revision=if_match)


@router.delete("/garments/{garment_id}", status_code=204)
def archive_garment(garment_id: str, user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)) -> Response:
    wardrobe.archive_garment(garment_id, user_id, profile_id)
    return Response(status_code=204)


@router.post('/garments/{garment_id}/contextual-suitability')
def contextual_suitability(garment_id: str, body: ContextualSuitabilityReview, user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)) -> dict:
    payload = body.model_dump(exclude_none=True)
    if body.appearance_review is not None:
        payload['appearance_review'] = body.appearance_review.model_dump(exclude_none=False)
    return wardrobe.review_contextual_suitability(garment_id, user_id, profile_id, payload)


@router.get("/outfits")
def outfits(
    query: str = Query(default="", max_length=100),
    category: str | None = Query(default=None, max_length=50),
    creation_type: Literal["image_upload", "manual", "recommendation"] | None = None,
    favourite: bool | None = None,
    sort: WardrobeSort = "updated_desc",
    user_id: str = Depends(current_user_id),
    profile_id: str = Depends(active_profile_id),
) -> list[dict]:
    return wardrobe.list_outfits(user_id, profile_id, query.strip(), category, creation_type, favourite, sort)


@router.get("/outfits/{outfit_id}/dependencies")
def outfit_dependencies(outfit_id: str, user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)) -> dict:
    return wardrobe.get_outfit_dependencies(outfit_id, user_id, profile_id)


@router.post("/outfits", status_code=201)
def create_outfit(body: OutfitCreate, user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)) -> dict:
    return wardrobe.create_outfit(user_id, profile_id, body.name, body.garment_ids, body.description)


@router.patch("/outfits/{outfit_id}")
def update_outfit(outfit_id: str, body: OutfitUpdate, user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)) -> dict:
    return wardrobe.update_outfit(outfit_id, user_id, profile_id, body.model_dump(exclude_unset=True))


@router.delete("/outfits/{outfit_id}", status_code=204)
def archive_outfit(outfit_id: str, user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)) -> Response:
    wardrobe.archive_outfit(outfit_id, user_id, profile_id)
    return Response(status_code=204)
