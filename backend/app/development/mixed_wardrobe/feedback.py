"""Explicit authenticated base-outfit feedback in existing preference storage."""
from datetime import datetime,timezone
from typing import Literal
import uuid
from fastapi import APIRouter,Depends,Header,HTTPException,Request
from pydantic import BaseModel,ConfigDict
from app.infrastructure.security import current_user_id
from app.application.recommendation.wearer_identity import resolve_wearer
from . import gateway
from .store import FixtureError
from .personalization import PROFILE,FEEDBACK_TYPE,read_feedback,base
from .core import encoded

router=APIRouter()

class FeedbackBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    wearer_profile_id:str
    verdict:Literal['like','dislike','clear']

def store_for(request,owner,wearer,header):
    if not request.client or not gateway.local(request.client.host):raise HTTPException(403,'Local development feedback only.')
    resolve_wearer(owner,wearer,header)
    s=gateway.open_store(enabled=True)
    if s.config.get('personalization_profile')!=PROFILE:raise HTTPException(422,'Explicit feedback profile disabled.')
    return s

def target(s,c,owner,wearer,rid):
    s.require_owner(c,owner,wearer)
    row=c.execute('select * from phase2nd_mixed_proofs where id=? and owner_id=? and wearer_id=?',(rid,owner,wearer)).fetchone() if c.execute("select 1 from sqlite_master where name='phase2nd_mixed_proofs'").fetchone() else None
    if not row:raise HTTPException(404,'Completed recommendation not found for this wearer.')
    p=s.verify_record(c,row,owner)
    # Verify the real completed receipt, immutable mirrors and history too.
    gateway._record_from_verified(c,s,owner,row,p)
    return [list(x) for x in base(p['decision']['selected']['key'])]

@router.get('/{recommendation_id}/feedback')
def get_feedback(recommendation_id:str,wearer_profile_id:str,request:Request,user_id:str=Depends(current_user_id),x_wardrobe_profile_id:str|None=Header(default=None)):
    try:
        s=store_for(request,user_id,wearer_profile_id,x_wardrobe_profile_id)
        with s.connection() as c:
            c.execute('BEGIN');key=target(s,c,user_id,wearer_profile_id,recommendation_id)
            entries=read_feedback(s,c,user_id,wearer_profile_id)
            verdict=next((e['verdict'] for e in entries if e['base']==key),None)
        return {'verdict':verdict,'scope':'exact_base_only'}
    except FixtureError as e:raise HTTPException(e.status,e.code) from e
    except ValueError as e:raise HTTPException(409,'Feedback verification failed; no data changed.') from e

@router.put('/{recommendation_id}/feedback')
def put_feedback(recommendation_id:str,body:FeedbackBody,request:Request,user_id:str=Depends(current_user_id),x_wardrobe_profile_id:str|None=Header(default=None)):
    try:
        wearer=body.wearer_profile_id;s=store_for(request,user_id,wearer,x_wardrobe_profile_id)
        with s.connection() as c:
            c.execute('BEGIN IMMEDIATE');key=target(s,c,user_id,wearer,recommendation_id)
            entries=read_feedback(s,c,user_id,wearer)
            existing=next((e for e in entries if e['base']==key),None)
            if (existing and existing['verdict']==body.verdict) or (existing is None and body.verdict=='clear'):
                return {'verdict':None if existing is None else existing['verdict'],'scope':'exact_base_only'}
            entries=[e for e in entries if e['base']!=key]
            now=datetime.now(timezone.utc).isoformat()
            if body.verdict!='clear':entries.insert(0,{'id':recommendation_id,'base':key,'verdict':body.verdict,'created_at':now})
            payload={'owner':user_id,'wearer':wearer,'entries':entries[:20]};payload['signature']=s.sign(payload)
            stored=c.execute('select id from user_preferences where user_id=? and profile_id=? and preference_type=?',(user_id,wearer,FEEDBACK_TYPE)).fetchone()
            wire=encoded(payload).decode()
            if stored:c.execute('update user_preferences set preference_value_json=?,updated_at=? where id=?',(wire,now,stored['id']))
            else:c.execute('insert into user_preferences (id,user_id,profile_id,preference_type,preference_value_json,weight,source,is_active,created_at,updated_at) values (?,?,?,?,?,0,?,0,?,?)',(str(uuid.uuid4()),user_id,wearer,FEEDBACK_TYPE,wire,FEEDBACK_TYPE,now,now))
        return {'verdict':None if body.verdict=='clear' else body.verdict,'scope':'exact_base_only'}
    except FixtureError as e:raise HTTPException(e.status,e.code) from e
    except ValueError as e:raise HTTPException(409,'Feedback verification failed; no data changed.') from e
