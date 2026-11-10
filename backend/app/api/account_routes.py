from typing import Literal
from fastapi import APIRouter, Depends, Response, Header, HTTPException
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
def wardrobe_profiles(status: Literal['active','archived','all'] = 'active', user_id: str = Depends(current_user_id)) -> list[dict]:
    return profile_service.list_profiles(user_id,status)


@router.post("/wardrobe-profiles", status_code=201)
def create_wardrobe_profile(body: WardrobeProfileCreate, user_id: str = Depends(current_user_id)) -> dict:
    return profile_service.create_profile(user_id, body.name)


@router.delete("/wardrobe-profiles/{wardrobe_profile_id}")
def delete_wardrobe_profile(wardrobe_profile_id: str, user_id: str = Depends(current_user_id)) -> dict:
    return profile_service.delete_profile(user_id, wardrobe_profile_id)


@router.post("/wardrobe-profiles/{wardrobe_profile_id}/archive")
def archive_wardrobe_profile(wardrobe_profile_id: str, user_id: str = Depends(current_user_id)) -> dict:
    return profile_service.archive_profile(user_id,wardrobe_profile_id)


def _attribute_preferences_call(operation,*args):
    from app.domain.value_objects.attribute_preferences import PreferenceError
    try:return operation(*args)
    except PreferenceError as exc:raise HTTPException(exc.status,{'code':exc.code,'message':exc.reason}) from exc


@router.get('/attribute-preference-capabilities')
def attribute_preference_capabilities(user_id: str = Depends(current_user_id)) -> dict:
    from app.application.account.attribute_preference_service import capabilities
    return capabilities()


@router.get('/wardrobe-profiles/{wardrobe_profile_id}/attribute-preferences')
def attribute_preferences(wardrobe_profile_id: str,user_id: str = Depends(current_user_id),x_wardrobe_profile_id: str | None = Header(default=None)) -> dict:
    from app.application.account.attribute_preference_service import get
    return _attribute_preferences_call(get,user_id,wardrobe_profile_id,x_wardrobe_profile_id)


from app.api.attribute_preference_models import AttributePreferenceUpdate


@router.put('/wardrobe-profiles/{wardrobe_profile_id}/attribute-preferences')
def update_attribute_preferences(wardrobe_profile_id: str,body: AttributePreferenceUpdate,user_id: str = Depends(current_user_id),x_wardrobe_profile_id: str | None = Header(default=None)) -> dict:
    from app.application.account.attribute_preference_service import update
    return _attribute_preferences_call(update,user_id,wardrobe_profile_id,body.model_dump(),x_wardrobe_profile_id)


class WardrobeProfileDetailsUpdate(BaseModel):
    model_config = {"extra": "forbid", "strict": True}
    version: Literal['wearer-profile-details-1.0.0']
    expected_revision: str = Field(min_length=32,max_length=64)
    gender_identity: str | None = Field(max_length=60)


@router.get('/wardrobe-profiles/{wardrobe_profile_id}/category-eligibility')
def wearer_category_eligibility(wardrobe_profile_id: str,user_id: str = Depends(current_user_id),x_wardrobe_profile_id: str | None = Header(default=None)) -> dict:
    from app.application.wardrobe import wearer_category_service as categories
    if x_wardrobe_profile_id is not None and x_wardrobe_profile_id!=wardrobe_profile_id:
        raise HTTPException(409,{'code':'WearerMismatch','message':'Choose the same intended wearer.'})
    return categories.capabilities(user_id,wardrobe_profile_id)


@router.get('/wardrobe-profiles/{wardrobe_profile_id}/details')
def wardrobe_profile_details(wardrobe_profile_id: str,user_id: str = Depends(current_user_id),x_wardrobe_profile_id: str | None = Header(default=None)) -> dict:
    from app.application.wardrobe import profile_details_service
    return profile_details_service.get(user_id,wardrobe_profile_id,x_wardrobe_profile_id)


@router.put('/wardrobe-profiles/{wardrobe_profile_id}/details')
def update_wardrobe_profile_details(wardrobe_profile_id: str,body: WardrobeProfileDetailsUpdate,user_id: str = Depends(current_user_id),x_wardrobe_profile_id: str | None = Header(default=None)) -> dict:
    from app.application.wardrobe import profile_details_service
    return profile_details_service.update(user_id,wardrobe_profile_id,body.model_dump(),x_wardrobe_profile_id)
