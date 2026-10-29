"""Real disposable authenticated auto-add, correction and transaction checks."""
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import pytest
from app.infrastructure.persistence import postgresql_repository as db
from app.application.garment_processing import garment_processing_orchestrator as processing
from app.application.wardrobe.wardrobe_service import finalize_automatic_candidates
from app.domain.value_objects.detected_garment import DetectedGarment
from app.domain.value_objects.saved_attribute_evidence import KEY as SOURCE_KEY
from app.application.garment_processing.automatic_garment_finalization import MODE, KEY, projection
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from tests.test_everyday_context import everyday_api
from tests.test_release_configuration import release,submit
from tests.test_forward_style_semantics import lifecycle
from tests.test_garment_workflow import jpeg,png


class SyntheticDetector:
    def __init__(self,rows=None):self.rows=rows or [('vest_dress','casual')]
    def analyse(self,path):
        return [DetectedGarment(category,.9,{'style':None if style is None else [style],'style_source':'synthetic','source':'synthetic test fixture','primary_colour':'blue','requires_review':True},crop_png=png('blue')) for category,style in self.rows]


@pytest.fixture
def automatic_api(everyday_api,monkeypatch):
    monkeypatch.setattr(processing,'get_garment_adapter',lambda:SyntheticDetector())
    return everyday_api


def upload(client,mode=MODE):
    response=client.post('/api/v1/processing/jobs'+('' if mode is None else '?admission_mode='+mode),files={'file':('synthetic.jpg',jpeg(),'image/jpeg')})
    assert response.status_code==202,response.text
    if mode:assert response.json()['admission_mode']==mode
    job=client.get('/api/v1/processing/jobs/'+response.json()['id']);assert job.status_code==200
    return job.json()


def garments(client):return client.get('/api/v1/wardrobe/garments').json()


def retry(client,job,ids=None):
    return client.post('/api/v1/processing/jobs/'+job['id']+'/confirm',json={'item_ids':ids or [i['id'] for i in job['items']],'save_mode':'garments','admission_mode':MODE})


def test_automatic_success_has_no_human_review_and_replay_is_idempotent(automatic_api):
    client,_=automatic_api;job=upload(client)
    assert job['status']=='completed' and job['admission']['state']=='saved'
    assert len(garments(client))==1
    g=garments(client)[0]
    assert g['contextual_edit']['review_current'] is False
    assert 'owner_style_confirmation_v1' not in g['attributes'] and 'contextual_suitability_v1' not in g['attributes']
    assert g['attributes'][SOURCE_KEY]['style']['origin']=='synthetic'
    assert g['attributes'][SOURCE_KEY]==g['additional_attributes'][SOURCE_KEY]
    assert g['attributes']['requires_review'] is True
    r=retry(client,job);assert r.status_code==201 and r.json()['replayed']
    assert r.json()['garment_ids']==[g['id']] and len(garments(client))==1
    assert submit(client,"I'm going shopping")[1]['outcome']=='Selected'


@pytest.mark.parametrize('rows,expected',[([('Unclassified garment',None)],'incomplete'),([('trousers','casual'),('Unclassified garment','casual')],'incomplete'),([('vest_dress',None)],'saved')])
def test_missing_structure_vs_missing_style(automatic_api,monkeypatch,rows,expected):
    client,_=automatic_api;monkeypatch.setattr(processing,'get_garment_adapter',lambda:SyntheticDetector(rows));job=upload(client)
    assert job['admission']['state']==expected
    assert len(garments(client))==(len(rows) if expected=='saved' else 0)
    if expected=='saved':assert submit(client,"I'm going shopping")[1]['outcome']=='InsufficientEvidence'
    else:assert job['status']=='review_required'


def test_one_correction_save_completes_without_style_attestation(automatic_api,monkeypatch):
    client,_=automatic_api;monkeypatch.setattr(processing,'get_garment_adapter',lambda:SyntheticDetector([('Unclassified garment','casual')]))
    job=upload(client);item=job['items'][0]
    response=client.post('/api/v1/processing/jobs/'+job['id']+'/review',json={'items':[{'item_id':item['id'],'decision':'accepted','category':'vest_dress'}]})
    assert response.status_code==200,response.text
    assert response.json()['status']=='completed' and len(garments(client))==1
    assert not garments(client)[0]['contextual_edit']['review_current']
    assert submit(client,"I'm going to class")[1]['outcome']=='Selected'


def test_legacy_upload_protocol_still_requires_accept_and_confirm(automatic_api):
    client,_=automatic_api;job=upload(client,None)
    assert job['status']=='review_required' and job['admission']['mode']=='manual_review_v1'
    assert garments(client)==[]
    assert retry(client,job).status_code==409


@pytest.mark.parametrize('failure',['exception','empty'])
def test_processing_failure_does_not_create_garments(automatic_api,monkeypatch,failure):
    def analyse(path):
        if failure=='exception':raise RuntimeError('Synthetic detector failure')
        return []
    monkeypatch.setattr(processing,'get_garment_adapter',lambda:SimpleNamespace(analyse=analyse))
    client,_=automatic_api;job=upload(client)
    assert job['status']=='failed' and not job['items'] and garments(client)==[]


def test_batch_fault_rolls_back_and_retry_returns_stable_ids(automatic_api,monkeypatch):
    client,_=automatic_api;monkeypatch.setattr(processing,'get_garment_adapter',lambda:SyntheticDetector([('long_sleeve_top','casual'),('trousers','casual')]))
    with db.connection() as conn:conn.execute("CREATE TRIGGER auto_abort BEFORE INSERT ON garments WHEN (SELECT count(*) FROM garments)>0 BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
    job=upload(client);assert job['status']=='review_required' and garments(client)==[]
    assert all(i['review_status']=='pending' for i in job['items'])
    with db.connection() as conn:conn.execute('DROP TRIGGER auto_abort')
    r=retry(client,job);assert r.status_code==201,r.text
    ids=r.json()['garment_ids'];assert len(ids)==len(set(ids))==2
    assert retry(client,job).json()['garment_ids']==ids
    assert retry(client,job,ids=[job['items'][0]['id']]).status_code==409
    assert len(garments(client))==2


def test_completed_job_is_required_even_for_a_forged_confirmed_link(automatic_api):
    client,_=automatic_api;job=upload(client)
    with db.connection() as conn:conn.execute("UPDATE processing_jobs SET status='failed' WHERE id=?",(job['id'],))
    assert SqliteConfirmedGarmentQuery().get_confirmed_available_garments('style-owner')==()
    assert submit(client,"I'm going shopping")[1]['outcome']=='NoEligibleGarments'


def test_cancellation_wins_and_new_namespaces_are_protected(automatic_api,monkeypatch):
    client,_=automatic_api
    original=processing.runtime().confirmed_writer.save_automatically_processed_candidates
    def cancel_first(job,user,item_ids=None):
        from app.application.garment_processing.processing_job_service import cancel_job
        cancel_job(job,user)
        return original(job,user,item_ids)
    monkeypatch.setattr(processing.runtime().confirmed_writer,'save_automatically_processed_candidates',cancel_first)
    job=upload(client);assert job['status']=='cancelled' and garments(client)==[]
    monkeypatch.setattr(processing.runtime().confirmed_writer,'save_automatically_processed_candidates',original)
    legacy=upload(client,None)
    for key in (SOURCE_KEY,KEY,'owner_style_confirmation_v1'):
        r=client.post('/api/v1/processing/jobs/'+legacy['id']+'/review',json={'items':[{'item_id':legacy['items'][0]['id'],'decision':'accepted','attributes':{key:{}}}]})
        assert r.status_code==422


def test_automatic_batch_cannot_downgrade_to_partial_legacy_confirmation(automatic_api,monkeypatch):
    from tests.test_automatic_admission_integration import stage
    client,_=automatic_api
    job=stage(client,monkeypatch,[('vest_dress','casual'),('Unclassified garment',None)])
    item=job['items'][0]
    assert client.post('/api/v1/processing/jobs/'+job['id']+'/review',json={'items':[{'item_id':item['id'],'decision':'accepted'}]}).status_code==200
    response=client.post('/api/v1/processing/jobs/'+job['id']+'/confirm',json={'item_ids':[item['id']],'save_mode':'garments'})
    assert response.status_code==409 and garments(client)==[]


def test_two_automatic_jobs_compete_atomically_for_last_quota_space(automatic_api,monkeypatch):
    from tests.test_automatic_admission_integration import stage
    client,_=automatic_api
    monkeypatch.setattr(processing,'get_garment_adapter',lambda:SyntheticDetector([('vest_dress',None)]*99))
    assert upload(client)['status']=='completed'
    first=stage(client,monkeypatch,[('vest_dress','casual')])
    second=stage(client,monkeypatch,[('vest_dress','casual')])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda job:finalize_automatic_candidates(job['id'],'style-owner'),[first,second]))
    assert sorted(r['admission']['state'] for r in results)==['blocked','saved']
    assert len(garments(client))==100
    for job,result in zip([first,second],results):
        if result['admission']['state']=='saved':
            assert finalize_automatic_candidates(job['id'],'style-owner')['garment_ids']==result['garment_ids']
        else:
            assert result['admission']['reason']=='WardrobeQuotaExceeded'
    assert len(garments(client))==100


def test_automatic_job_is_not_acquired_or_finalised_by_another_owner(automatic_api):
    from fastapi import HTTPException
    client,_=automatic_api
    job=upload(client)
    with pytest.raises(HTTPException) as error:
        finalize_automatic_candidates(job['id'],'foreign-owner')
    assert error.value.status_code==404 and len(garments(client))==1
