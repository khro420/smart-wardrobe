"""Read-only completed history. No generation, mutation or action routes."""
from fastapi import APIRouter,Depends,Query,Header,HTTPException
from typing import Literal
from fastapi.responses import JSONResponse
from app.application.ports.chat_history_runtime import chat_history_service
from app.infrastructure.security import current_user_id
from app.application.wardrobe.profile_service import selected_history_profile
from app.domain.value_objects.recommendation_refinement import canonical_uuid

router = APIRouter(prefix='/chats',tags=['Completed chat history'])


def response(operation):
    try: return operation()
    except LookupError:
        return JSONResponse(status_code=404,content={'status':'NotFound','detail':'Completed chat not found.'})
    except ValueError:
        return JSONResponse(status_code=422,content={'status':'InvalidInput','detail':'Invalid history query.'})
    except HTTPException:
        raise
    except Exception:
        return JSONResponse(status_code=503,content={'status':'HistoryUnavailable','detail':'History could not be retrieved.'})


def history_selection(user_id,view,wearer_profile_id,header):
    if wearer_profile_id is not None:canonical_uuid(wearer_profile_id)
    if view=='legacy_unrecorded':
        if wearer_profile_id is not None:raise ValueError('Legacy view cannot assert wearer.')
        return None
    if view=='historical':
        if wearer_profile_id is None:raise ValueError('Historical view requires a wearer.')
        return wearer_profile_id
    if wearer_profile_id is not None and header is not None and wearer_profile_id!=header:
        raise ValueError('Wearer mismatch.')
    return selected_history_profile(user_id,wearer_profile_id or header)['id']


@router.get('')
def search(search: str=Query(default='',max_length=500),limit: int=Query(default=50,ge=1,le=100),cursor: str | None=Query(default=None,max_length=4096),
           view: Literal['active','historical','legacy_unrecorded']='active',wearer_profile_id: str | None=None,
           x_wardrobe_profile_id: str | None=Header(default=None),user_id: str=Depends(current_user_id),service=Depends(chat_history_service)):
    return response(lambda:service.search(user_id,search,limit,cursor,history_selection(user_id,view,wearer_profile_id,x_wardrobe_profile_id),view))


@router.get('/{chat_id}')
def get(chat_id: str,view: Literal['active','historical','legacy_unrecorded']='active',wearer_profile_id: str | None=None,
        x_wardrobe_profile_id: str | None=Header(default=None),user_id: str=Depends(current_user_id),service=Depends(chat_history_service)):
    return response(lambda:service.get(user_id,chat_id,history_selection(user_id,view,wearer_profile_id,x_wardrobe_profile_id),view))
