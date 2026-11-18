from fastapi import APIRouter, Depends

from app.application.visualisation.activity_service import list_activity
from app.application.wardrobe.profile_service import active_profile_id
from app.infrastructure.security import current_user_id

router = APIRouter(prefix='/activity', tags=['background activity'])


@router.get('')
def activity(user_id: str = Depends(current_user_id), profile_id: str = Depends(active_profile_id)):
    return {'jobs': list_activity(user_id, profile_id), 'queue_order': 'not_guaranteed'}
