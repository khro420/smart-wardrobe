from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from app.application.account import account_service
from app.domain.value_objects.requests import PreferenceUpsert
from app.infrastructure.security import current_user_id, logout_bearer, VerifiedBearer
from app.application.wardrobe import profile_service
from app.application.wardrobe.profile_service import active_profile_id

router = APIRouter(prefix="/account", tags=["account"])


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=256)
    password_confirmation: str = Field(min_length=12, max_length=256)
    display_name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class WardrobeProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)


@router.post("/register", status_code=201)
def register(body: RegisterRequest) -> dict:
    return account_service.register(body.email, body.password, body.display_name, body.password_confirmation)


@router.post("/login")
def login(body: LoginRequest) -> dict:
    return account_service.login(body.email, body.password)


@router.get("/profile")
def profile(user_id: str = Depends(current_user_id)) -> dict:
    return account_service.get_profile(user_id)


@router.post("/logout", status_code=204)
def logout(claims: VerifiedBearer = Depends(logout_bearer)) -> Response:
    account_service.logout(claims)
    return Response(status_code=204)


@router.patch("/profile")
def update_profile(body: ProfileUpdate, user_id: str = Depends(current_user_id)) -> dict:
    return account_service.update_profile(user_id, body.display_name)


@router.get("/preferences")
def preferences(user_id: str = Depends(current_user_id), wardrobe_profile_id: str = Depends(active_profile_id)) -> list[dict]:
    return account_service.list_preferences(user_id, wardrobe_profile_id)


@router.get("/preference-options")
def preference_options(user_id: str = Depends(current_user_id)) -> dict:
    return account_service.preference_options()


@router.put("/preferences/{preference_type}")
def upsert_preference(preference_type: str, body: PreferenceUpsert, user_id: str = Depends(current_user_id), wardrobe_profile_id: str = Depends(active_profile_id)) -> dict:
    return account_service.upsert_preference(user_id, preference_type, body.preference_value, body.weight, wardrobe_profile_id)


@router.get("/wardrobe-profiles")
def wardrobe_profiles(user_id: str = Depends(current_user_id)) -> list[dict]:
    return profile_service.list_profiles(user_id)


@router.post("/wardrobe-profiles", status_code=201)
def create_wardrobe_profile(body: WardrobeProfileCreate, user_id: str = Depends(current_user_id)) -> dict:
    return profile_service.create_profile(user_id, body.name)


@router.delete("/wardrobe-profiles/{wardrobe_profile_id}")
def delete_wardrobe_profile(wardrobe_profile_id: str, user_id: str = Depends(current_user_id)) -> dict:
    return profile_service.delete_profile(user_id, wardrobe_profile_id)
