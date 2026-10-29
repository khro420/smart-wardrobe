"""J-7 disposable loopback fixture. Never deploy; synthetic owner declarations."""
import sys,json,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests import compact_integrated_server as base
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
fixture,app=base.fixture,base.app
PLAN=json.loads((Path(__file__).parent/'fixtures/evidence_diversity.v1.json').read_text())
with fixture.db.connection() as c:
 for name,rows in list(PLAN['mixes'].items())+[('terminal',[])]:
  owner='j7-'+name
  c.execute("INSERT INTO users VALUES(?,?,?,'Synthetic J7','active','now','now')",(owner,owner+'@example.test',fixture.hash_password('Decision-test-password-123')))
  c.execute("INSERT INTO processing_jobs(id,user_id,source_media_id,status,created_at,updated_at) VALUES(?,?,'synthetic-media','completed','now','now')",(owner,owner))
  for r in rows:
   gid=r['id'];attrs=json.dumps({'style':r['style'],'custom_tags':r['custom_tags'],'pattern':r['pattern']})
   c.execute("INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES(?,?,?,1,'synthetic-media','synthetic-media',?,'confirmed','now')",(gid,owner,r['category'],attrs))
   c.execute("INSERT INTO garments(id,user_id,processing_item_id,preferred_media_id,name,category,primary_colour,style_tags,custom_tags,attributes_json,additional_attributes,created_at,updated_at) VALUES(?,?,?,'synthetic-media',?,?,?,?,?,?,?,'now','now')",(gid,owner,gid,gid,r['category'],r['primary_colour'],json.dumps(r['style']) if r['style'] is not None else None,json.dumps(r['custom_tags']),attrs,attrs))
  for n,p in enumerate(PLAN['preferences']):
   c.execute('INSERT INTO user_preferences VALUES(?,?,?,?,1,?,1,?,?)',(owner+str(n),owner,p['type'],json.dumps({'values':p['values']}),'synthetic','now','now'))
  fixture.workloads[name]={'owner':owner,'candidate_count':17710 if name.endswith('100') else 134820 if rows else 0}
@app.get('/_test/j7-plan')
def plan():return PLAN
@app.post('/_test/j7-select/{profile}/{suitability}')
def select(profile:str,suitability:str):
 result=base.select(profile,'compact')
 fixture.assistant_service().engine.evaluator_factory=SuitabilityRequestEvaluator if suitability=='enabled' else RequestConstraintEvaluator
 return result
if __name__=='__main__':
 try:fixture.uvicorn.run(app,host='127.0.0.1',port=3201,access_log=False)
 finally:fixture.temporary.cleanup()
