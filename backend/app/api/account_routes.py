from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.application.account import account_service
from app.domain.value_objects.requests import PreferenceUpsert
from app.infrastructure.security import current_user_id

router = APIRouter(prefix="/account", tags=["account"])


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


@router.post("/register", status_code=201)
def register(body: RegisterRequest) -> dict:
    return account_service.register(body.email, body.password, body.display_name)


@router.post("/login")
def login(body: LoginRequest) -> dict:
    return account_service.login(body.email, body.password)


@router.get("/profile")
def profile(user_id: str = Depends(current_user_id)) -> dict:
    return account_service.get_profile(user_id)


@router.patch("/profile")
def update_profile(body: ProfileUpdate, user_id: str = Depends(current_user_id)) -> dict:
    return account_service.update_profile(user_id, body.display_name)


@router.get("/preferences")
def preferences(user_id: str = Depends(current_user_id)) -> list[dict]:
    return account_service.list_preferences(user_id)


@router.put("/preferences/{preference_type}")
def upsert_preference(preference_type: str, body: PreferenceUpsert, user_id: str = Depends(current_user_id)) -> dict:
    return account_service.upsert_preference(user_id, preference_type, body.preference_value, body.weight)
