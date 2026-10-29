"""J9 disposable loopback verification fixture. NEVER deploy its test controls."""
import hashlib
import json
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests import compact_integrated_server as base
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from PIL import Image

fixture, app = base.fixture, base.app
PLAN_PATH = Path(__file__).parent / 'fixtures/capacity_150.v1.json'
PLAN = json.loads(PLAN_PATH.read_text())
PLAN_HASH = hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest()
with fixture.db.connection() as c:
    for name, rows in PLAN['mixes'].items():
        owner = 'j9-' + name
        c.execute("INSERT INTO users VALUES(?,?,?,'Synthetic J9','active','now','now')",
                  (owner, owner+'@example.test', fixture.hash_password('Decision-test-password-123')))
        # A deterministic, authorised synthetic thumbnail, not a real garment image.
        image = BytesIO()
        Image.new('RGB', (256, 256), 'navy').save(image, format='PNG')
        # Use this same transaction for metadata; bytes live in the temporary fixture directory.
        media = owner + '-media'
        (Path(fixture.temporary.name)/'media'/(media+'.png')).write_bytes(image.getvalue())
        c.execute("INSERT INTO media_assets(id,user_id,media_type,storage_key,content_type,size_bytes,status,created_at,width,height) VALUES(?,?,'garment_crop',?,'image/png',?,'available','now',256,256)",
                  (media,owner,media+'.png',len(image.getvalue())))
        c.execute("INSERT INTO processing_jobs(id,user_id,source_media_id,status,created_at,updated_at) VALUES(?,?,?,'completed','now','now')",(owner,owner,media))
        for r in rows:
            gid=r['id']; attrs=json.dumps({'style':r['style'],'custom_tags':r['custom_tags'],'pattern':r['pattern']})
            c.execute("INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES(?,?,?,1,?,?,?,'confirmed','now')",(gid,owner,r['category'],media,media,attrs))
            c.execute("INSERT INTO garments(id,user_id,processing_item_id,preferred_media_id,name,category,primary_colour,style_tags,custom_tags,attributes_json,additional_attributes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,'now','now')",(gid,owner,gid,media,gid,r['category'],r['primary_colour'],json.dumps(r['style']) if r['style'] is not None else None,json.dumps(r['custom_tags']),attrs,attrs))
        for n,p in enumerate(PLAN['preferences']):
            c.execute('INSERT INTO user_preferences VALUES(?,?,?,?,1,?,1,?,?)',(owner+str(n),owner,p['type'],json.dumps({'values':p['values']}),'synthetic','now','now'))
        fixture.workloads[name]={'owner':owner,'candidate_count':PLAN['expected_structural'][name],'preference_count':len(PLAN['preferences'])}


@app.get('/_test/j9-plan')
def plan():
    return {'plan':PLAN,'sha256':PLAN_HASH}


@app.post('/_test/j9-select/{profile}/{suitability}')
def select(profile:str,suitability:str):
    if suitability not in ('enabled','disabled'):
        raise ValueError('Invalid test-only evaluator selection')
    result=base.select(profile,'compact')
    fixture.assistant_service().engine.evaluator_factory=SuitabilityRequestEvaluator if suitability=='enabled' else RequestConstraintEvaluator
    return {**result,'suitability':suitability}


if __name__=='__main__':
    try: fixture.uvicorn.run(app,host='127.0.0.1',port=3201,access_log=False)
    finally: fixture.temporary.cleanup()
