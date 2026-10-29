"""J12 disposable loopback fixture. No profile/evaluator selection endpoints."""
import hashlib
from datetime import datetime,timezone
from contextvars import ContextVar
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from time import perf_counter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
temporary=tempfile.TemporaryDirectory(prefix='wardrobe-j12-')
os.environ.update(SMART_WARDROBE_DATA_DIR=temporary.name,SMART_WARDROBE_DATABASE=str(Path(temporary.name)/'release.db'),
                  SMART_WARDROBE_AI_MODE='development',SMART_WARDROBE_VTOFF_ENABLED='off',
                  SMART_WARDROBE_ALLOW_DEV_IDENTITY='false',SMART_WARDROBE_TOKEN_SECRET='disposable-j12-test-secret')
from PIL import Image
from app.main import app
from app.infrastructure.persistence.postgresql_repository import initialise_database,connection
from app.infrastructure.security import hash_password
from app.infrastructure.media.protected_media_store import store_media_bytes
from app.application.ports.assistant_runtime import assistant_service
from app.application.recommendation.compact_assistant_scorer import CompactAssistantScorer
from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
import uvicorn

PLAN_PATH=Path(__file__).parent/'fixtures/capacity_100.v1.json'
PLAN=json.loads(PLAN_PATH.read_text()); jobs={}; active=ContextVar('release_observation',default=None)
initialise_database()
owners=['quota-owner','browser-owner','browser-other']+['j10-'+name for name in PLAN['mixes']]
with connection() as c:
    for owner in owners:
        c.execute("INSERT INTO users VALUES(?,?,?,'J12 test','active','now','now')",(owner,('quota@example.test' if owner=='quota-owner' else owner+'@example.test'),hash_password('Quota-test-password-123' if owner=='quota-owner' else 'Browser-test-password-123' if owner.startswith('browser') else 'Decision-test-password-123')))
image=BytesIO();Image.new('RGB',(256,256),'navy').save(image,'PNG')
media={owner:store_media_bytes(image.getvalue(),owner,'garment_crop') for owner in owners}
with connection() as c:
    for name,rows in PLAN['mixes'].items():
        owner='j10-'+name;m=media[owner]
        c.execute("INSERT INTO processing_jobs(id,user_id,source_media_id,status,created_at,updated_at) VALUES(?,?,?,'completed','now','now')",(owner,owner,m))
        for r in rows:
            attrs=json.dumps({'style':r['style'],'custom_tags':r['custom_tags'],'pattern':r['pattern']});gid=r['id']
            c.execute("INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES(?,?,?,1,?,?,?,'confirmed','now')",(gid,owner,r['category'],m,m,attrs))
            c.execute("INSERT INTO garments(id,user_id,processing_item_id,preferred_media_id,name,category,primary_colour,style_tags,custom_tags,attributes_json,additional_attributes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,'now','now')",(gid,owner,gid,m,gid,r['category'],r['primary_colour'],json.dumps(r['style']) if r['style'] is not None else None,json.dumps(r['custom_tags']),attrs,attrs))
        for index,p in enumerate(PLAN['preferences']):
            c.execute('INSERT INTO user_preferences VALUES(?,?,?,?,1,?,1,?,?)',(owner+str(index),owner,p['type'],json.dumps({'values':p['values']}),'synthetic','now','now'))


@app.get('/_test/release')
def release():
    service=assistant_service()
    return {'engine':service.execution_engine,'profile':service.scoring_profile,
            'evaluator':service.engine.evaluator_factory.__name__,
            'flags':{name:os.getenv(name) for name in ['SMART_WARDROBE_ASSISTANT_ENABLED','SMART_WARDROBE_HOMEPAGE_ENABLED','SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE','SMART_WARDROBE_ASSISTANT_SCORING_PROFILE','SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED']},
            'plan_sha256':hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest(),'plan':PLAN}


@app.post('/_test/quota/setup/{used}')
def setup(used:int):
    assert 0<=used<=101
    with connection() as c:
        c.execute("DELETE FROM outfit_items WHERE outfit_id IN (SELECT id FROM outfits WHERE user_id='quota-owner')")
        for table in ['outfits','garments']:c.execute('DELETE FROM '+table+" WHERE user_id='quota-owner'")
        c.execute("DELETE FROM processing_items WHERE job_id IN (SELECT id FROM processing_jobs WHERE user_id='quota-owner')")
        c.execute("DELETE FROM processing_jobs WHERE user_id='quota-owner'")
        for n in range(used):
            gid='quota-existing-'+str(n)
            c.execute("INSERT INTO garments(id,user_id,preferred_media_id,name,category,attributes_json,created_at,updated_at) VALUES(?,'quota-owner',?,?,'vest','{}','now','now')",(gid,media['quota-owner'],'Existing '+gid))
        c.execute("INSERT INTO processing_jobs(id,user_id,source_media_id,status,created_at,updated_at) VALUES('quota-job','quota-owner',?,'review_required','now','now')",(media['quota-owner'],))
        for n in range(2):c.execute("INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES(?,'quota-job','vest',1,?,?,'{}','accepted','now')",('quota-new-'+str(n),media['quota-owner'],media['quota-owner']))
    return {'used':used}


@app.post('/_test/quota/fill')
def fill():
    with connection() as c:c.execute("INSERT INTO garments(id,user_id,preferred_media_id,name,category,attributes_json,created_at,updated_at) VALUES('quota-other-tab','quota-owner',?,'Other tab','vest','{}','now','now')",(media['quota-owner'],))
    return {'ok':True}


@app.get('/_test/resources')
def resources():
    command="$m=Get-CimInstance Win32_OperatingSystem;$c=Get-CimInstance Win32_Processor|Select-Object -First 1;@{free_physical_kib=$m.FreePhysicalMemory;total_physical_kib=$m.TotalVisibleMemorySize;cpu_name=$c.Name;cpu_load_percent=$c.LoadPercentage;logical_processors=$c.NumberOfLogicalProcessors}|ConvertTo-Json -Compress"
    result=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True,timeout=20)
    return {'at':datetime.now(timezone.utc).isoformat(),'available':result.returncode==0,'system':json.loads(result.stdout) if result.returncode==0 else None}


@app.get('/_test/job/{key}')
def job(key:str):return jobs.get(key,{'done':False})


rank=CompactAssistantScorer.rank
def observe_rank(self,*args,**kwargs):
    result=rank(self,*args,**kwargs);row=active.get()
    if row is not None and self.kernel:row['cache']=self.kernel.cache_statistics
    return result
CompactAssistantScorer.rank=observe_rank
recommend=OutfitAssistantService.recommend
def observe_recommend(self,user,key,text):
    row={};token=active.set(row);start=perf_counter()
    try:
        result=recommend(self,user,key,text)
        row.update(done=True,status=result['status'],id=result.get('id'),chat_id=result.get('chat_id'),
                   score=result.get('score_metadata'),provenance=result.get('provenance'),
                   items=[(i['garment_id'],i['garment_role'],i['item_order']) for i in result.get('items',[])])
        return result
    finally:row['service_seconds']=perf_counter()-start;jobs[key]=row;active.reset(token)
OutfitAssistantService.recommend=observe_recommend

if __name__=='__main__':
    try:uvicorn.run(app,host='127.0.0.1',port=3101,access_log=False)
    finally:temporary.cleanup()
