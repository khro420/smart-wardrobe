"""Local authenticated mixed-source dispatch; no caller supplies source facts or winners."""
from pathlib import Path
import os,json,sqlite3
from .store import Store,PROFILE,FixtureError
from .core import VERSION,ORIGIN,digest,encoded
KEY='phase2nd_mixed_selection'
ENV='SMART_WARDROBE_DEVELOPMENT_MIXED_PROFILE'

def open_store(*,enabled=False):
    from app.development.main_fixture.gateway import open_store as fixture_store
    base=fixture_store();cfg=dict(base.config)
    cfg['profile']=PROFILE if os.getenv(ENV,'disabled')==PROFILE and not cfg.get('retired',False) else 'disabled'
    from .context_contract import ENV as CONTEXT_ENV,PROFILE as CONTEXT_PROFILE
    cfg['context_profile']=CONTEXT_PROFILE if os.getenv(CONTEXT_ENV,'disabled')==CONTEXT_PROFILE else 'disabled'
    from .context_language_contract import ENV as LANGUAGE_ENV,PROFILE as LANGUAGE_PROFILE
    cfg['language_profile']=LANGUAGE_PROFILE if cfg['context_profile']==CONTEXT_PROFILE and os.getenv(LANGUAGE_ENV,'disabled')==LANGUAGE_PROFILE else 'disabled'
    from .interview_default_contract import ENV as DEFAULT_ENV,PROFILE as DEFAULT_PROFILE
    cfg['interview_default_profile']=DEFAULT_PROFILE if cfg['language_profile']==LANGUAGE_PROFILE and os.getenv(DEFAULT_ENV,'disabled')==DEFAULT_PROFILE else 'disabled'
    from .semantic_frame_contract import ENV as FRAME_ENV,PROFILE as FRAME_PROFILE
    from .semantic_reliability_contract import PROFILE as SCOPED_PROFILE
    from .semantic_structured_contract import PROFILE as TYPED_PROFILE
    semantic_requested=os.getenv(FRAME_ENV,'disabled')
    cfg['semantic_frame_profile']=semantic_requested if semantic_requested in (FRAME_PROFILE,SCOPED_PROFILE,TYPED_PROFILE) else 'disabled'
    if semantic_requested not in ('disabled',FRAME_PROFILE,SCOPED_PROFILE,TYPED_PROFILE) or semantic_requested in (FRAME_PROFILE,SCOPED_PROFILE,TYPED_PROFILE) and cfg['interview_default_profile']!=DEFAULT_PROFILE:
        cfg['semantic_error']='SemanticProfileUnavailable'
    from .fashion_contract import ENV as FASHION_ENV,PROFILE as FASHION_PROFILE
    cfg['fashion_profile']=FASHION_PROFILE if cfg['profile']==PROFILE and os.getenv(FASHION_ENV,'disabled')==FASHION_PROFILE else 'disabled'
    from .personalization import ENV as PERSONAL_ENV,PROFILE as PERSONAL_PROFILE
    cfg['personalization_profile']=PERSONAL_PROFILE if cfg['fashion_profile']==FASHION_PROFILE and os.getenv(PERSONAL_ENV,'disabled')==PERSONAL_PROFILE else 'disabled'
    s=Store(cfg)
    if enabled:s.profile_on()
    return s

def local(host):return host in ('127.0.0.1','::1')

def capabilities(owner,host):
    result={'enabled':False,'profile':PROFILE,'scope':'mixed_original_and_synthetic_v1'}
    if not local(host):return result
    from app.application.ports.assistant_runtime import assistant_service
    if assistant_service() is None:return result
    result['grammar_version']='conversational-compositional-grammar-1.9.0'
    try:
        s=open_store(enabled=True)
        with s.connection() as c:s.require_owner(c,owner)
        result.update(enabled=True,wearers=list(s.catalog['profiles']))
        from .fashion_contract import PROFILE as FASHION_PROFILE
        result['compatibility']={'enabled':s.config.get('fashion_profile')==FASHION_PROFILE,'profile':FASHION_PROFILE,'weights':['3/5','1/5','1/5'],'human_quality_validation':'NOT_EVALUATED'}
        from .personalization import PROFILE as PERSONAL_PROFILE
        result['personalization']={'enabled':s.config.get('personalization_profile')==PERSONAL_PROFILE,'profile':PERSONAL_PROFILE,'scope':'exact_score_ties_only','feedback':'explicit_base_only'}
        from .context_contract import PROFILE as CONTEXT_PROFILE,VERSION as CONTEXT_VERSION
        result['contextual']={'enabled':s.config.get('context_profile')==CONTEXT_PROFILE,'profile':CONTEXT_PROFILE,'proof_version':CONTEXT_VERSION,'bundle':'context_18_v1'}
        from .context_language_contract import PROFILE as LANGUAGE_PROFILE,VERSION as LANGUAGE_VERSION
        result['contextual']['language_expansion']={'enabled':s.config.get('language_profile')==LANGUAGE_PROFILE,'profile':LANGUAGE_PROFILE,'proof_version':LANGUAGE_VERSION}
        from .semantic_frame_contract import PROFILE as FRAME_PROFILE
        from .semantic_constraint_contract import VERSION as FRAME_VERSION
        from .semantic_reliability_contract import PROFILE as SCOPED_PROFILE,VERSION as SCOPED_VERSION
        from .semantic_structured_contract import PROFILE as TYPED_PROFILE,VERSION as TYPED_VERSION
        selected_profile=s.config.get('semantic_frame_profile')
        semantic_on=selected_profile in (FRAME_PROFILE,SCOPED_PROFILE,TYPED_PROFILE)
        result['contextual']['semantic_interpreter']={'enabled':semantic_on,'profile':selected_profile if semantic_on else FRAME_PROFILE,'proof_version':TYPED_VERSION if selected_profile==TYPED_PROFILE else SCOPED_VERSION if selected_profile==SCOPED_PROFILE else FRAME_VERSION,'implementation':'local_nli_dependency_hybrid_v1','model_required':True,'unavailable_behavior':'explicit_refusal_no_fallback'}
        if semantic_on and not s.config.get('semantic_error'):
            if selected_profile==TYPED_PROFILE:
                from .semantic_structured_contract import GRAMMAR
            elif selected_profile==SCOPED_PROFILE:
                from .semantic_reliability_contract import GRAMMAR
            else:
                from .semantic_constraint_contract import GRAMMAR
            from .semantic_model import ready,identity,ModelUnavailable
            result['grammar_version']=GRAMMAR
            try:ready();result['contextual']['semantic_interpreter'].update(ready=True,models=identity())
            except ModelUnavailable:result['contextual']['semantic_interpreter'].update(ready=False,reason='SemanticInterpreterUnavailable')
        if s.config.get('semantic_error'):result['contextual']['semantic_interpreter'].update(ready=False,reason=s.config['semantic_error'])
        from .interview_default_contract import PROFILE as DEFAULT_PROFILE
        result['contextual']['interview_default']={'enabled':s.config.get('interview_default_profile')==DEFAULT_PROFILE,'profile':DEFAULT_PROFILE,'value':'smart_casual','origin':'inferred_policy_default'}
    except (OSError,ValueError,sqlite3.Error):pass
    return result

def counts(catalog):
    from .core import rows_from_catalog,OriginalRow
    pid=catalog['original']['wearer']['profile_id'];rows=rows_from_catalog(catalog,catalog['fixture']['profiles'][pid]['gender'])
    n=catalog['original']['eligibility']['account_count'];m=len(catalog['fixture']['garments'])
    return {'available_inventory':len(catalog['available_ids']),'original_confirmed':n,'synthetic_declared':m,'eligible_original':sum(isinstance(r,OriginalRow) for r in rows),'eligible_synthetic':sum(not isinstance(r,OriginalRow) for r in rows),'excluded_unconfirmed':len(catalog['available_ids'])-n-m}

def continuation(s,row,p):
    action=s.action(row['id'],p)
    return {'version':'mixed-development-continuation-1.0.0','ordinal':p['ordinal'],'excluded_categories':[],'limit_reached':action is None,'next_action':None if action is None else {'submission_key':action['action_key'],'refinement':{'version':'assistant-refinement-request-1.0.0','kind':'alternative','parent_recommendation_id':row['id']}}}

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
    row=c.execute('select * from phase2nd_mixed_proofs where id=? and owner_id=?',(identifier,owner)).fetchone()
    if not row:raise ValueError('Missing synthetic proof.')
    p=s.verify_record(c,row,owner)
    return _record_from_verified(c,s,owner,row,p)

def _record_from_verified(c,s,owner,row,p):
    identifier=row['id'];d=p['decision']
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
    try:s.profile_on();current_scope_valid=s.capture(c,owner,p['wearer_id'])==p['catalog']
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
        wearer_archived=not bool(c.execute("select 1 from wardrobe_profiles where id=? and user_id=? and status='active'",(p['wearer_id'],owner)).fetchone()),wearer_association={'profile_id':p['wearer_id'],'name':p['catalog']['fixture']['profiles'][p['wearer_id']]['row']['name'],'authority':'captured_mixed_source_scope'},
        mixed_wardrobe_display={'version':p['version'],'scope':'mixed_original_and_synthetic_v1','source_counts':counts(p['catalog']),'contains_synthetic':any(x['source']==ORIGIN for x in d['items']),'items':[{'garment_id':x['garment_id'],'source':x['source']} for x in d['items']],'decision':d},
        development_continuation=continuation(s,row,p),
        input_normalization={'version':'compositional-input-display-1.0.0','grammar_version':d['intent']['grammar_version'],'normalized_text':d['intent']['normalization']['normalized_text'],
            'hard_conditions':d['intent']['hard_intent']['conditions'] if d['intent']['hard_intent'] else None,'original_hard_spans':d['intent']['original_hard_spans'],'original_optional_spans':d['intent']['original_optional_spans']})
    return r

def owns_parent(owner,parent):
    from app.infrastructure.persistence.postgresql_repository import connection
    with connection() as c:
        row=c.execute('select m.provenance_json from recommendation_metadata m join recommendations r on r.id=m.recommendation_id where r.id=? and r.user_id=?',(parent,owner)).fetchone()
        return bool(row and KEY in json.loads(row[0]))

def prior_mode_conflict(c,owner,key):
    r=c.execute("select recommendation_id from recommendation_submissions where user_id=? and operation='assistant' and submission_key=?",(owner,key)).fetchone()
    if not r:return False
    if not c.execute("select 1 from sqlite_master where name='phase2nd_mixed_proofs'").fetchone():return True
    return not c.execute('select 1 from phase2nd_mixed_proofs where id=?',(r[0],)).fetchone()

def submit(owner,body,header,host):
    if not local(host):raise FixtureError('LocalDevelopmentOnly',403)
    s=open_store(enabled=True)
    with s.connection() as c:s.require_owner(c,owner)
    if not body.wearer_profile_id:raise FixtureError('WearerSelectionRequired',422)
    if not body.submission_key or any(getattr(body,k) is not None for k in ('attribute_conditions','preference_profile','compatibility_profile')):raise FixtureError('UnsupportedMixedProfile',422)
    from app.application.recommendation.wearer_identity import resolve_wearer
    wearer=resolve_wearer(owner,body.wearer_profile_id,header)
    parent=None;action_key=None
    with s.connection() as c:
        s.require_owner(c,owner,wearer.profile_id)
        if prior_mode_conflict(c,owner,body.submission_key):raise FixtureError('IdempotencyConflict')
        if body.refinement is not None:
            if body.refinement.kind!='alternative':raise FixtureError('UnsupportedMixedRefinement',422)
            parent=body.refinement.parent_recommendation_id
            r=c.execute('select * from phase2nd_mixed_proofs where id=? and owner_id=?',(parent,owner)).fetchone() if c.execute("select 1 from sqlite_master where name='phase2nd_mixed_proofs'").fetchone() else None
            if not r:raise FixtureError('RecommendationNotFound',404)
            p=s.verify_record(c,r,owner);action=s.action(parent,p)
            if not action:raise FixtureError('RefinementUnavailable',422)
            action_key=action['action_key']
            if body.submission_key!=action_key:raise FixtureError('InvalidContinuationBinding')
    def export(c,locked_proof):
        # Immutable bytes were minted from the independent selection while this
        # same connection holds BEGIN IMMEDIATE; no first-pass result is reused.
        if not c.in_transaction:raise ValueError('Missing mixed write lock.')
        row=s.lookup(c,owner,body.submission_key)
        if row is None or row['proof_json'].encode()!=locked_proof:raise ValueError('Changed locked proof.')
        p=json.loads(locked_proof)
        mirror(c,s,row)
        if s.capture(c,owner,wearer.profile_id)!=p['catalog']:raise ValueError('Source changed during mixed write.')
        _record_from_verified(c,s,owner,row,p)

    from app.application.ports.assistant_runtime import assistant_service
    if assistant_service() is None:raise FixtureError('IntegrationDisabled',503)
    engine=getattr(assistant_service(),'execution_engine','compact_exhaustive')
    if engine not in ('reference','compact_exhaustive'):raise FixtureError('UnsupportedMixedEngine',422)
    answer=s.recommend(owner,wearer.profile_id,body.request_text,body.submission_key,engine,parent,action_key,after_insert=export)
    if not answer.get('id'):return {'status':answer['decision']['status'],'outcome':answer['decision']['status'],'complete':True,'development_scope':'mixed_original_and_synthetic_v1'},200
    with s.connection() as c:r=record_from_conn(c,owner,answer['id'])
    return {**r,'status':'Selected','outcome':'Selected','recommendation_status':r['status'],'recommendation':r,'complete':True,'replayed':answer['replayed']},200 if answer['replayed'] else 201


def wardrobe_annotations(owner,wearer,rows):
    try:
        s=open_store()
        with s.connection() as c:
            s.require_owner(c,owner)
            reason=None;allowed=set()
            try:
                s.profile_on();catalog=s.capture(c,owner,wearer)
                from .core import rows_from_catalog
                allowed={r.snapshot.garment_id for r in rows_from_catalog(catalog,catalog['fixture']['profiles'][wearer]['gender'])}
            except ValueError as e:reason=getattr(e,'code','UnqualifiedMixedSource')
        ids={e['row']['id'] for e in s.catalog['garments']}
        return [{**r,'development_evidence':{'version':'mixed-development-garment-1.0.0','source':ORIGIN,'profile_id':wearer,'eligible':r['id'] in allowed,'reason':reason or (None if r['id'] in allowed else 'WearerCategoryNotPermitted')}} if r['id'] in ids else r for r in rows]
    except (OSError,ValueError,sqlite3.Error):return rows


def owns_receipt(owner,key):
    if not key:return False
    from app.infrastructure.persistence.postgresql_repository import connection
    with connection() as c:
        row=c.execute("select m.provenance_json from recommendation_metadata m join recommendation_submissions s on s.recommendation_id=m.recommendation_id where s.user_id=? and s.operation='assistant' and s.submission_key=?",(owner,key)).fetchone()
        return bool(row and KEY in json.loads(row[0]))


def receipt_namespace(owner,key):
    if not key:return None
    from app.infrastructure.persistence.postgresql_repository import connection
    with connection() as c:
        row=c.execute("select m.provenance_json from recommendation_submissions s left join recommendation_metadata m on m.recommendation_id=s.recommendation_id where s.user_id=? and s.operation='assistant' and s.submission_key=?",(owner,key)).fetchone()
        if not row:return None
        p=json.loads(row[0]) if row[0] else {}
        return 'mixed' if KEY in p else 'fixture' if 'phase2nd_fixture_selection' in p else 'normal'
