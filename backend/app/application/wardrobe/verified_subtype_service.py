"""Auditable owner review; no automatic inference or changes to extracted attributes."""
import uuid
from fastapi import HTTPException
from app.application.ports.workflow_runtime import runtime,connection,utcnow
from app.application.wardrobe.profile_service import require_active_profile
from app.domain.value_objects import verified_garment_subtype as types
def enabled():
    try:return getattr(runtime(),'subtype_store',None) is not None
    except RuntimeError:return False
def store():
    if not enabled():raise HTTPException(404,'Verified garment types are unavailable.')
    return runtime().subtype_store
def source(conn,owner,row,kind=None):
    row=dict(row);kind=kind or ('garment' if 'category' in row else 'processing_item')
    return types.project(row,owner,store().events(conn,owner,kind,row['id']))
def projection(conn,owner,row,kind=None):
    value=source(conn,owner,row,kind);value['registry']=types.registry();return value
def _subject(conn,owner,kind,subject):
    if kind=='garment':row=conn.execute('SELECT * FROM garments WHERE id=? AND user_id=?',(subject,owner)).fetchone()
    else:row=conn.execute('SELECT p.* FROM processing_items p JOIN processing_jobs j ON j.id=p.job_id WHERE p.id=? AND j.user_id=?',(subject,owner)).fetchone()
    if not row:raise HTTPException(404,'Garment review was not found.')
    return dict(row)
def review(conn,owner,profile_id,row,update,kind=None):
    row=dict(row);kind=kind or ('garment' if 'category' in row else 'processing_item')
    _subject(conn,owner,kind,row['id']);require_active_profile(conn,owner,profile_id)
    expected={'action_id','expected_revision','state','value','review_basis','reason'}
    if type(update) is not dict or set(update)!=expected:raise HTTPException(422,'Unexpected garment type review fields.')
    try:uuid.UUID(update['action_id'])
    except (ValueError,TypeError,AttributeError):raise HTTPException(422,'A review action identifier is required.')
    prior_action=store().find_action(conn,owner,update['action_id'])
    if prior_action is not None and (prior_action['subject_id']!=row['id'] or prior_action['subject_kind']!=kind or prior_action['wearer_profile_id']!=profile_id):raise HTTPException(409,'Review action belongs to a different subject or wearer.')
    events=store().events(conn,owner,kind,row['id']);before=types.project(row,owner,events)
    for old in events:
        if old['action_id']==update['action_id']:
            if (old['state'],old['subtype'],old['prior_revision'],old['review_basis'],old['reason'])!=(update['state'],update['value'],update['expected_revision'],update['review_basis'],update['reason']):raise HTTPException(409,'Review action conflicts with its original input.')
            return before
    if before['revision']!=update['expected_revision']:raise HTTPException(409,'Garment type changed. Reload before reviewing.')
    from app.application.wardrobe.wearer_category_service import require_profile,fail
    _,_,gender=require_profile(owner,profile_id,conn)
    previous_blouse=any(e['subtype']=='blouse' or e['unresolved_restriction']=='blouse' for e in events)
    resolved=bool(events and events[-1]['event_kind'] in ('owner_correction','owner_category_resolution') and events[-1]['unresolved_restriction'] is None)
    if gender=='male' and (before['value']=='blouse' or previous_blouse and not resolved):fail('WearerSubtypeNotPermitted','This garment has a retained blouse review. Choose a wearer who can use it for an explicit correction.')
    category=before['category'];value=update['value'];state=update['state']
    if gender=='male' and state=='Known' and value=='blouse':fail('WearerSubtypeNotPermitted','Blouses are not permitted for the selected male wearer.')
    if update['review_basis'] not in ('owner_review','synthetic_fixture_declaration'):raise HTTPException(422,'Unknown review source.')
    correction=bool(events)
    event=dict(contract=types.EVENT_VERSION,event_id=str(uuid.uuid4()),owner_id=owner,subject_kind=kind,subject_id=row['id'],wearer_profile_id=profile_id,action_id=update['action_id'],ordinal=len(events)+1,prior_revision=before['revision'],event_kind='owner_category_resolution' if state=='Inapplicable' else 'owner_correction' if correction else 'owner_confirm' if state=='Known' else 'owner_unspecified',state=state,subtype=value,category=category,media_id=row['preferred_media_id'],source_binding_sha256=types.binding(row,owner),registry_version=types.VERSION,registry_sha256=types.RESOURCE_SHA256,origin='owner_selected',contributor=owner,recorded_at=utcnow(),review_basis=update['review_basis'],reason=update['reason'],transfer_source=None,unresolved_restriction='blouse' if value=='blouse' else None)
    event['revision']=types.digest(event)
    try:types.validate_event(event)
    except (ValueError,TypeError,KeyError) as e:raise HTTPException(422,str(e)) from e
    store().append(conn,event);return types.project(row,owner,events+[event])
def current(conn,owner,profile_id,subject):
    require_active_profile(conn,owner,profile_id);return projection(conn,owner,_subject(conn,owner,'garment',subject))
def update(owner,profile_id,subject,payload):
    with connection() as conn:
        conn.execute('BEGIN IMMEDIATE');row=_subject(conn,owner,'garment',subject)
        review(conn,owner,profile_id,row,payload)
        return projection(conn,owner,row)
def transfer(conn,owner,profile_id,item,garment_id):
    if not enabled():return
    original=source(conn,owner,item,'processing_item')
    if original['state'] not in ('Known','Unspecified'):return
    row=_subject(conn,owner,'garment',garment_id)
    if store().events(conn,owner,'garment',garment_id):return
    head=original['events'][-1]
    event={**head,'event_id':str(uuid.uuid4()),'subject_kind':'garment','subject_id':garment_id,'action_id':str(uuid.uuid5(uuid.NAMESPACE_URL,head['action_id']+':'+garment_id)), 'ordinal':1,'prior_revision':None,'event_kind':'system_transfer','source_binding_sha256':types.binding(row,owner),'recorded_at':utcnow(),'transfer_source':{'event_id':head['event_id'],'revision':head['revision'],'subject_id':item['id']}}
    event.pop('revision');event['revision']=types.digest(event);store().append(conn,event)
