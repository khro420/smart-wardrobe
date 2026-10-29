"""Read-only completed history. No generation, mutation or action routes."""
from fastapi import APIRouter,Depends,Query
from fastapi.responses import JSONResponse
from app.application.ports.chat_history_runtime import chat_history_service
from app.infrastructure.security import current_user_id
from app.application.wardrobe.profile_service import active_profile_id

router = APIRouter(prefix='/chats',tags=['Completed chat history'])


def response(operation):
    try: return operation()
    except LookupError:
        return JSONResponse(status_code=404,content={'status':'NotFound','detail':'Completed chat not found.'})
    except ValueError:
        return JSONResponse(status_code=422,content={'status':'InvalidInput','detail':'Invalid history query.'})
    except Exception:
        return JSONResponse(status_code=503,content={'status':'HistoryUnavailable','detail':'History could not be retrieved.'})


@router.get('')
def search(search: str=Query(default='',max_length=500),limit: int=Query(default=50,ge=1,le=100),cursor: str | None=Query(default=None,max_length=4096),
           user_id: str=Depends(current_user_id),profile_id: str=Depends(active_profile_id),service=Depends(chat_history_service)):
    return response(lambda:service.search(user_id,search,limit,cursor,profile_id))


@router.get('/{chat_id}')
def get(chat_id: str,user_id: str=Depends(current_user_id),profile_id: str=Depends(active_profile_id),service=Depends(chat_history_service)):
    return response(lambda:service.get(user_id,chat_id,profile_id))
