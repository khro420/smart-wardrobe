"""Loopback-only disposable integration/performance fixture; NEVER deploy this server.

Seeded descriptors and development AI are synthetic, not CV/VTON validation.
The /_test service timer deliberately bypasses HTTP authentication so it measures
the actual service separately; all normal API/browser trials use real login/JWT.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import platform
from time import perf_counter
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
temporary=tempfile.TemporaryDirectory(prefix='assistant-decision-test-')
os.environ.update(SMART_WARDROBE_DATA_DIR=temporary.name,
    SMART_WARDROBE_DATABASE=str(Path(temporary.name)/'test.db'),SMART_WARDROBE_AI_MODE='development',
    SMART_WARDROBE_VTOFF_ENABLED='off',SMART_WARDROBE_HOMEPAGE_ENABLED='true',
    SMART_WARDROBE_ASSISTANT_ENABLED='true',SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED='false',
    SMART_WARDROBE_ALLOW_DEV_IDENTITY='false',SMART_WARDROBE_TOKEN_SECRET='disposable-decision-browser-secret')
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.security import hash_password
from app.application.ports.assistant_runtime import assistant_service
from app.main import app
import uvicorn

workloads={}
db.initialise_database()
with db.connection() as c:
    for name,counts in [(str(n),(int(n*.4),int(n*.4),int(n*.1),n-2*int(n*.4)-int(n*.1))) for n in (20,50,100,200)]+[
        ('stress',(67,67,0,66)),('pair',(1,1,0,0)),('trio',(1,1,0,1)),('dress',(0,0,1,0)),
        ('dress_outer',(0,0,1,1)),('partial',(1,1,0,0)),('unknown',(1,1,0,0)),('zero',(1,1,0,0)),('empty',(0,0,0,0))]:
        owner='decision-'+name
        c.execute("INSERT INTO users VALUES(?,?,?,'Synthetic test','active','now','now')",(owner,owner+'@example.test',hash_password('Decision-test-password-123')))
        c.execute("INSERT INTO processing_jobs(id,user_id,source_media_id,status,created_at,updated_at) VALUES(?,?,'synthetic-media','completed','now','now')",(owner,owner))
        for category,amount in zip(('vest','trousers','vest_dress','long_sleeve_outwear'),counts):
            for i in range(amount):
                gid=f'{owner}-{category}-{i:04d}'
                colour='blue';styles=['vintage']
                if name=='zero' and category=='trousers': colour='red';styles=['sporty']
                if name in ('partial','unknown'): styles=None
                if name=='unknown': colour=None
                attrs=json.dumps({'style':styles})
                c.execute("INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES(?,?,?,1,'synthetic-media','synthetic-media',?,'confirmed','now')",(gid,owner,category,attrs))
                c.execute("INSERT INTO garments(id,user_id,processing_item_id,preferred_media_id,name,category,primary_colour,style_tags,attributes_json,additional_attributes,created_at,updated_at) VALUES(?,?,?,'synthetic-media',?,?,?,?,?,?,'now','now')",(gid,owner,gid,gid,category,colour,json.dumps(styles) if styles is not None else None,attrs,attrs))
        if name in ('20','50','100','200','stress'):
            c.execute("INSERT INTO user_preferences VALUES(?,?,'colours','{\"values\":[\"blue\"]}',1,'synthetic',1,'now','now')",(owner,owner))
        workloads[name]={'owner':owner,'eligible_by_category':dict(zip(('vest','trousers','vest_dress','long_sleeve_outwear'),counts)),
            'candidate_count':(counts[0]*counts[1]+counts[2])*(1+counts[3]),'preference_count':int(name in ('20','50','100','200','stress'))}


@app.middleware('http')
async def timing(request,call_next):
    start=perf_counter();response=await call_next(request)
    response.headers['X-Test-Backend-Seconds']=str(perf_counter()-start)
    return response


@app.get('/_test/workloads')
def metadata():
    from importlib.metadata import version
    return {'profile':os.getenv('SMART_WARDROBE_ASSISTANT_SCORING_PROFILE','compatibility_deferred'),'workloads':workloads,
        'environment':{'python':platform.python_version(),'os':platform.platform(),'cpu':platform.processor(),
            'packages':{name:version(name) for name in ('fastapi','uvicorn','pillow','numpy','python-multipart')}}}


@app.post('/_test/service/{name}')
def service_timing(name:str):
    start=perf_counter()
    r=assistant_service().recommend(workloads[name]['owner'],str(uuid4()),'Suggest an outfit with vintage style')
    return {'seconds':perf_counter()-start,'result':r}


@app.get('/_test/submission/{name}/{key}')
def settled_submission(name:str,key:str):
    # A proxy disconnect can leave a synchronous service call running. Read only;
    # never resubmit/rerank while waiting before the next timing trial.
    from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
    r=SqliteRecommendationRepository(db.DATABASE_PATH).find_assistant_submission(
        workloads[name]['owner'],key,'Suggest an outfit with vintage style')
    return {'complete':r is not None,'scored_count':r['provenance']['scored_count'] if r else None}


if __name__=='__main__':
    try: uvicorn.run(app,host='127.0.0.1',port=3201,access_log=False)
    finally: temporary.cleanup()
