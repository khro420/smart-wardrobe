"""Frozen J-15 combined dataset through authenticated app.main API and real SQLite."""
from dataclasses import asdict
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path

import pytest
from PIL import Image
from app.application.ports.assistant_runtime import assistant_service
from app.infrastructure import security
from app.infrastructure.config import MEDIA_DIR
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from tests.test_release_configuration import release, lifecycle
from tests.final_evaluation_auditor import audit, encoded

BACKEND=Path(__file__).resolve().parents[1]
ROOT=BACKEND.parent
FIXTURE=BACKEND/'tests/fixtures/final_recommendation_evaluation.v1.json'
PLAN=json.loads(FIXTURE.read_text())
CONTROLS=BACKEND/'tests/fixtures/final_recommendation_controls.v1.json'
CASES=[*PLAN['cases'],*json.loads(CONTROLS.read_text())['cases']]
TABLES=('recommendations','nlp_chats','recommendation_items','recommendation_metadata','recommendation_submissions','recommendation_item_snapshots')

def counts():
    with db.connection() as c:return {t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in TABLES}
def wardrobe():
    with db.connection() as c:
        return [dict(r) for r in c.execute('SELECT g.*,p.id AS evidence_item_id,p.review_status AS evidence_review_status,j.user_id AS evidence_job_owner FROM garments g LEFT JOIN processing_items p ON p.id=g.processing_item_id LEFT JOIN processing_jobs j ON j.id=p.job_id ORDER BY g.id')]
def seed(case,owner):
    with db.connection() as c:
        for descriptor in case['garments']:
            gid='j15-'+case['id']+'-'+descriptor['name'];job=gid+'-job';item=gid+'-item';media=gid+'-media' if descriptor['media'] else ''
            user=owner if descriptor['owner']=='self' else 'style-owner'
            job_owner=owner if descriptor['job_owner']=='self' else 'style-owner'
            attributes={'style':descriptor['styles'],'custom_tags':descriptor['tags']}
            key='j15/'+gid+'.png';image=MEDIA_DIR/key;image.parent.mkdir(parents=True,exist_ok=True)
            Image.new('RGB',(128,128),'blue').save(image)
            c.execute("INSERT INTO media_assets(id,user_id,media_type,storage_key,content_type,size_bytes,status,created_at,width,height) VALUES(?,?,'garment_crop',?,'image/png',?,'available','j15',128,128)",(gid+'-media',user,key,image.stat().st_size))
            c.execute("INSERT INTO processing_jobs(id,user_id,source_media_id,status,created_at,updated_at) VALUES(?,?,?,'completed','j15','j15')",(job,job_owner,gid+'-media'))
            c.execute('INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES(?,?,?,1,?,?,?,?,\'j15\')',
                      (item,job,descriptor['category'],gid+'-media',media,json.dumps(attributes),descriptor['review_status']))
            link=None if descriptor['linked'] is False else gid+'-absent' if descriptor['linked']=='dangling' else item
            c.execute("INSERT INTO garments(id,user_id,processing_item_id,preferred_media_id,name,category,primary_colour,attributes_json,status,created_at,updated_at,style_tags,custom_tags) VALUES(?,?,?,?,?,?,?,?,?,'j15','j15',?,?)",
                      (gid,user,link,media,descriptor['name'],descriptor['category'],descriptor['colour'],json.dumps(attributes),descriptor['status'],
                       json.dumps(descriptor['styles']) if descriptor['styles'] is not None else None,json.dumps(descriptor['tags'])))
        for i,p in enumerate(case['preferences']):
            c.execute("INSERT INTO user_preferences(id,user_id,preference_type,preference_value_json,weight,source,is_active,created_at,updated_at) VALUES(?,?,?,?,?,'frozen synthetic fixture',1,'j15','j15')",
                      (case['id']+'-pref'+str(i),owner,p['type'],json.dumps({'values':p['values']}),float(Fraction(p['weight']))))

def persisted(identifier):
    with db.connection() as c:
        recommendation=dict(c.execute('SELECT * FROM recommendations WHERE id=?',(identifier,)).fetchone())
        return {'recommendation':recommendation,
                'chat':dict(c.execute('SELECT * FROM nlp_chats WHERE id=?',(recommendation['chat_id'],)).fetchone()),
                'metadata':dict(c.execute('SELECT * FROM recommendation_metadata WHERE recommendation_id=?',(identifier,)).fetchone()),
                'receipt':dict(c.execute('SELECT * FROM recommendation_submissions WHERE recommendation_id=?',(identifier,)).fetchone()),
                'items':[dict(r) for r in c.execute('SELECT * FROM recommendation_items WHERE recommendation_id=? ORDER BY item_order',(identifier,))],
                'snapshots':[dict(r) for r in c.execute('SELECT s.* FROM recommendation_item_snapshots s JOIN recommendation_items i USING(recommendation_id,garment_id) WHERE s.recommendation_id=? ORDER BY i.item_order',(identifier,))]}

@pytest.mark.skipif(not os.getenv('SMART_WARDROBE_FINAL_EVALUATION'),reason='Explicit frozen evaluation collection only; do not silently repeat 152 acceptance cases in ordinary regressions')
@pytest.mark.parametrize('case',CASES,ids=lambda case:case['id'])
def test_frozen_combined_evaluation(release,monkeypatch,case):
    for path,digest in json.loads((ROOT/'storage/verification/phase5f2e3j15/frozen-inputs.json').read_text()).items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    for path,digest in json.loads((ROOT/'storage/verification/phase5f2e3j15/frozen-controls.json').read_text()).items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    client,_=release
    monkeypatch.setattr(security,'ALLOW_DEVELOPMENT_IDENTITY',False)
    registered=client.post('/api/v1/account/register',json={'email':case['id'].lower()+'@j15.example.test','password':'J15-disposable-password-123','display_name':case['id']})
    assert registered.status_code==201,registered.text
    auth=registered.json();owner=auth['profile']['id'];client.headers['Authorization']='Bearer '+auth['access_token']
    seed(case,owner)
    before=wardrobe();before_counts=counts();quota=client.get('/api/v1/wardrobe/quota').json()
    service=assistant_service()
    assert service.execution_engine=='compact_exhaustive' and service.scoring_profile=='experimental_compatibility_decision_v1'
    assert type(service.engine.evaluator_factory()).__name__=='SuitabilityRequestEvaluator'
    observed={};query_observations=[]
    interpret=service.interpreter.interpret
    def observe(text):
        result=interpret(text)
        observed.update(intent=result.status,fields=json.loads(json.dumps(asdict(result.structured_request))) if result.structured_request else None,reason=result.reason)
        return result
    monkeypatch.setattr(service.interpreter,'interpret',observe)
    query=service.engine.structural_engine.retrieval.query
    original_query=query.get_confirmed_available_garments
    def observe_query(user_id):
        result=original_query(user_id)
        query_observations.append([asdict(g) for g in result]);return result
    monkeypatch.setattr(query,'get_confirmed_available_garments',observe_query)
    fault_events=[]
    if case.get('fault')=='archive_before_persistence':
        original=service.repository.persist_assistant
        def race(command):
            with db.connection() as c:
                c.execute("UPDATE garments SET status='archived' WHERE id=?",(command.candidate.members[0].garment.garment_id,))
            fault_events.append('Selected fixture garment archived after ranking and before transaction revalidation')
            return original(command)
        monkeypatch.setattr(service.repository,'persist_assistant',race)
    if case.get('fault')=='metadata_failure':
        def fail(stage,connection):
            if stage=='metadata':
                fault_events.append('Injected failure after score metadata INSERT, before commit')
                raise RuntimeError('J15 controlled persistence fault')
        monkeypatch.setattr(service.repository,'checkpoint',fail)
    response=client.post('/api/v1/recommendations?pipeline=integrated',json={'request_text':case['text'],'submission_key':'j15-'+case['id']})
    result=response.json();outcome=result.get('outcome',result.get('status','InvalidInput'))
    actual_intent=observed.get('intent','InvalidInput' if response.status_code==422 and 'detail' in result else 'NotObserved')
    record={'case':case,'fixture_sha256':hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),'owner':owner,
            'actual_intent':actual_intent,'actual_fields':observed.get('fields'),'nlp_reason':observed.get('reason'),
            'http':response.status_code,'outcome':outcome,'result':result,'wardrobe_before':before,'wardrobe_after':wardrobe(),
            'query_observations':query_observations,'counts_before':before_counts,'counts_after':counts(),
            'quota_before':quota,'quota_after':client.get('/api/v1/wardrobe/quota').json(),'fault_events':fault_events,
            'persisted':persisted(result['id']) if outcome=='Selected' else None}
    record['audit']=audit(record)
    output=os.getenv('SMART_WARDROBE_FINAL_EVALUATION')
    if output:
        directory=Path(output);directory.mkdir(parents=True,exist_ok=True);target=directory/(case['id']+'.json')
        assert not target.exists(),'Refuse to overwrite an evaluated case'
        target.write_text(json.dumps(record,indent=2,default=encoded)+'\n',encoding='utf-8')
    assert record['audit']['pass'],record['audit']['errors']
    if case.get('expected_used') is not None:assert quota['used']==case['expected_used']
    if case.get('fault'):assert fault_events
