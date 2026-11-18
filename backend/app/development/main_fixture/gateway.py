"""Authenticated normal-UI adapter for the closed synthetic source namespace."""
from pathlib import Path
import json,os,sqlite3
from fractions import Fraction
from .store import Store,FixtureError,PROFILE
from .core import VERSION,digest,encoded

KEY='phase2nd_fixture_selection'
ENV='SMART_WARDROBE_DEVELOPMENT_FIXTURE_PROFILE'
PIPELINE='synthetic_development_v1'

def verify_current_image(media_id,owner,path):
    from app.infrastructure.persistence.postgresql_repository import connection
    from fastapi import HTTPException
    with connection() as c:
        row=c.execute('select media_type from media_assets where id=? and user_id=?',(media_id,owner)).fetchone()
        if not row or row[0]!='synthetic_development_garment':return
        try:
            s=open_store();entry=next(e for e in s.catalog['garments'] if e['media']['id']==media_id)
            if s.image(entry,c).resolve()!=path.resolve():raise ValueError('Foreign fixture media path.')
        except (OSError,ValueError,StopIteration,sqlite3.Error):
            raise HTTPException(409,{'code':'FixtureMediaUnavailable','message':'Synthetic image or its source authority changed; the recorded image is not substituted.'}) from None

def open_store(*,enabled=False):
    from app.infrastructure.persistence.postgresql_repository import DATABASE_PATH
    from app.infrastructure.media.protected_media_store import MEDIA_DIR
    path=Path(os.getenv('SMART_WARDROBE_MAIN_FIXTURE_CONFIG',DATABASE_PATH.resolve().parent/'phase2nd/runtime.private.json')).resolve()
    cfg=json.loads(path.read_text(encoding='utf-8'))
    if Path(cfg['database']).resolve()!=DATABASE_PATH.resolve() or Path(cfg['media']).resolve()!=MEDIA_DIR.resolve():raise FixtureError('ForeignFixtureDatabase')
    cfg['profile']=PROFILE if os.getenv(ENV,'disabled')==PROFILE and not cfg.get('retired',False) else 'disabled'
    store=Store(cfg)
    if enabled:store.profile_on()
    return store

def capabilities(owner):
    result={'enabled':False,'profile':PROFILE,'scope':'fixture_only_explicit_v1','normal_garments_included':False,
        'description':'Explicit synthetic-only scope; original wardrobe remains available in normal mode.','count':30}
    try:
        s=open_store(enabled=True)
        with s.connection() as c:s.require_owner(c,owner)
        result.update(enabled=True,wearers=list(s.catalog['profiles']))
    except (OSError,ValueError,sqlite3.Error):pass
    return result

def mirror(c,s,row):
    p=json.loads(row['proof_json']);d=p['decision'];owner=row['owner_id'];pid=row['wearer_id'];rid=row['id'];now=row['created_at']
    from app.application.recommendation.decision_score_codec import score_from_json
    score=score_from_json(json.dumps(d['selected']['score']))
    c.execute("insert into nlp_chats (id,user_id,profile_id,request_text,interpreted_intent,extracted_entities_json,status,created_at,completed_at) values (?,?,?,?,?,?,'completed',?,?)",
        (rid,owner,pid,p['raw'],'outfit_recommendation',encoded(d['intent']['request']).decode(),now,now))
    vals=[None if x.summary.value is None else float(x.summary.value) for x in (score.request_match,score.compatibility,score.preference)]+[float(score.total)]
    c.execute("insert into recommendations (id,user_id,profile_id,chat_id,recommendation_type,status,created_at,expires_at,request_match_score,compatibility_score,preference_score,total_score) values (?,?,?,?,'assistant','available',?,NULL,?,?,?,?)",(rid,owner,pid,rid,now,*vals))
    for i,item in enumerate(d['items'],1):
        c.execute('insert into recommendation_items values (?,?,?,?,?)',(rid,item['garment_id'],item['role'],i,now))
        display={'name':item['name'],'category':item['attributes']['category'],'preferred_media_id':item['media_id']}
        c.execute('insert into recommendation_item_snapshots values (?,?,?)',(rid,item['garment_id'],encoded(display).decode()))
    c.execute('insert into recommendation_metadata values (?,?,?)',(rid,encoded({KEY:p}).decode(),encoded(d['selected']['score']).decode()))
    c.execute('insert into recommendation_submissions values (?,?,?,?,?)',(owner,'assistant',row['receipt'],row['fingerprint'],rid))

def record_from_conn(c,owner,identifier):
    s=open_store();s.require_owner(c,owner)
    row=c.execute('select * from phase2nd_proofs where id=? and owner_id=?',(identifier,owner)).fetchone()
    if not row:raise ValueError('Missing synthetic proof.')
    p=s.verify_record(c,row,owner);d=p['decision']
    record=c.execute('select * from recommendations where id=? and user_id=?',(identifier,owner)).fetchone()
    meta=c.execute('select * from recommendation_metadata where recommendation_id=?',(identifier,)).fetchone()
    chat=c.execute('select * from nlp_chats where id=? and user_id=?',(identifier,owner)).fetchone()
    receipt=c.execute("select * from recommendation_submissions where user_id=? and operation='assistant' and submission_key=?",(owner,p['receipt'])).fetchone()
    if not record or not meta or not chat or not receipt:raise ValueError('Incomplete synthetic atomic record.')
    if record['chat_id']!=identifier or record['profile_id']!=p['wearer_id'] or chat['profile_id']!=p['wearer_id'] or chat['request_text']!=p['raw'] or chat['status']!='completed':raise ValueError('Changed synthetic history association.')
    if json.loads(chat['extracted_entities_json'])!=d['intent']['request'] or receipt['recommendation_id']!=identifier or receipt['fingerprint']!=p['fingerprint']:raise ValueError('Changed synthetic receipt/interpretation.')
    if json.loads(meta['provenance_json'])!={KEY:p} or json.loads(meta['score_json'])!=d['selected']['score']:raise ValueError('Changed synthetic metadata.')
    from app.application.recommendation.decision_score_codec import score_from_json
    score=score_from_json(meta['score_json'])
    expected=[None if x.summary.value is None else float(x.summary.value) for x in (score.request_match,score.compatibility,score.preference)]+[float(score.total)]
    if [record[k] for k in ('request_match_score','compatibility_score','preference_score','total_score')]!=expected:raise ValueError('Changed synthetic numeric mirrors.')
    current_scope_valid=False
    try:s.profile_on();s.capture(c,owner,p['wearer_id']);current_scope_valid=True
    except (OSError,ValueError,sqlite3.Error):pass
    items=[]
    stored=c.execute('select i.*,s.display_json from recommendation_items i join recommendation_item_snapshots s using(recommendation_id,garment_id) where i.recommendation_id=? order by i.item_order',(identifier,)).fetchall()
    if len(stored)!=len(d['items']):raise ValueError('Incomplete synthetic item scope.')
    for index,(actual,wanted) in enumerate(zip(stored,d['items']),1):
        display={'name':wanted['name'],'category':wanted['attributes']['category'],'preferred_media_id':wanted['media_id']}
        if actual['garment_id']!=wanted['garment_id'] or actual['garment_role']!=wanted['role'] or actual['item_order']!=index or json.loads(actual['display_json'])!=display:raise ValueError('Changed synthetic immutable snapshot.')
        current=c.execute("select status from garments where id=? and user_id=?",(wanted['garment_id'],owner)).fetchone()
        items.append({'garment_id':wanted['garment_id'],'garment_role':wanted['role'],'item_order':index,**display,'snapshot_available':True,'currently_eligible':bool(current_scope_valid and current and current[0]=='available')})
    r=dict(record);r.update(request_text=p['raw'],items=items,provenance={KEY:p},score_metadata=d['selected']['score'],
        wearer_archived=False,wearer_association={'profile_id':p['wearer_id'],'name':p['catalog']['profiles'][p['wearer_id']]['row']['name'],'authority':'captured_synthetic_fixture_scope'},
        synthetic_fixture_display={'version':VERSION,'source':'synthetic_fixture_declaration','scope':'fixture_only_explicit_v1','normal_garments_included':False,'decision':d},
        input_normalization={'version':'compositional-input-display-1.0.0','grammar_version':d['intent']['grammar_version'],'normalized_text':d['intent']['normalization']['normalized_text'],
            'hard_conditions':d['intent']['hard_intent']['conditions'] if d['intent']['hard_intent'] else None,'original_hard_spans':d['intent']['original_hard_spans'],'original_optional_spans':d['intent']['original_optional_spans']})
    return r

def submit(owner,body,header):
    s=open_store(enabled=True)
    with s.connection() as c:s.require_owner(c,owner)
    if not body.wearer_profile_id:raise FixtureError('WearerSelectionRequired',422)
    if not body.submission_key or body.refinement is not None or any(getattr(body,k) is not None for k in ('attribute_conditions','preference_profile','compatibility_profile')):raise FixtureError('UnsupportedFixtureCombination',422)
    from app.application.recommendation.wearer_identity import resolve_wearer
    wearer=resolve_wearer(owner,body.wearer_profile_id,header)
    def export(c):
        row=c.execute('select * from phase2nd_proofs where owner_id=? and receipt=?',(owner,body.submission_key)).fetchone()
        mirror(c,s,row)
    with s.connection() as c:
        s.require_owner(c,owner,wearer.profile_id)
        other=c.execute("select recommendation_id from recommendation_submissions where user_id=? and operation='assistant' and submission_key=?",(owner,body.submission_key)).fetchone()
        if other and not c.execute('select 1 from phase2nd_proofs where id=?',(other[0],)).fetchone():raise FixtureError('IdempotencyConflict')
    from app.application.ports.assistant_runtime import assistant_service
    service=assistant_service();engine=getattr(service,'execution_engine','compact_exhaustive')
    # Selection object is a string in the approved service, not a client flag.
    if engine not in ('reference','compact_exhaustive'):engine='compact_exhaustive'
    answer=s.recommend(owner,wearer.profile_id,body.request_text,body.submission_key,engine,after_insert=export)
    if not answer.get('id'):return {'status':answer['decision']['status'],'outcome':answer['decision']['status'],'complete':True,'context_reason':'synthetic_fixture_scope','synthetic_fixture':True},200
    with s.connection() as c:r=record_from_conn(c,owner,answer['id'])
    return {**r,'status':'Selected','outcome':'Selected','recommendation_status':r['status'],'recommendation':r,'complete':True,'replayed':answer['replayed']},200 if answer['replayed'] else 201

def foreign_mode_receipt(owner,key):
    if not key:return False
    try:
        s=open_store()
        with s.connection() as c:return c.execute('select 1 from phase2nd_proofs where owner_id=? and receipt=?',(owner,key)).fetchone() is not None
    except (OSError,ValueError,sqlite3.Error):return False
