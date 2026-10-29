"""Quota acceptance through real routes and independent SQLite connections.

All rows/media are disposable test fixtures; no capacity benchmark or inference.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import sqlite3
from threading import Barrier
from types import SimpleNamespace
import uuid

import pytest
from fastapi.testclient import TestClient
from tests.test_garment_workflow import Detector, GeneratedVtoffStub, jpeg
from app.main import app
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure import security
from app.application.garment_processing import garment_processing_orchestrator as processing
from app.domain.value_objects.garment_attributes import GarmentAttributes
from app.application.wardrobe.wardrobe_service import confirm_candidates
from fastapi import HTTPException

BASE = '/api/v1'


@pytest.fixture
def quota(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DATABASE_PATH', tmp_path/'quota.db')
    monkeypatch.setattr(security, 'ALLOW_DEVELOPMENT_IDENTITY', True)
    monkeypatch.setattr(processing, 'get_garment_adapter', lambda: Detector())
    monkeypatch.setattr(processing, 'get_standardisation_adapter', lambda: GeneratedVtoffStub())
    monkeypatch.setattr(processing, 'get_attribute_adapter', lambda: SimpleNamespace(extract=lambda _: GarmentAttributes({})))
    with TestClient(app, headers={'X-User-Id': 'quota-owner'}) as client:
        yield client


def usage(client):
    response = client.get(BASE+'/wardrobe/quota')
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'private, no-store'
    return response.json()


def seed(count, owner='quota-owner', status='available'):
    # Intentionally unlinked entries still consume slots, independently of eligibility.
    with db.connection() as c:
        c.executemany("INSERT INTO garments(id,user_id,preferred_media_id,name,category,attributes_json,status,created_at,updated_at) VALUES(?,?,'fixture-media','Existing','vest','{}',?,'now','now')",
                      [(str(uuid.uuid4()), owner, status) for _ in range(count)])


def accepted_job(client):
    result = client.post(BASE+'/processing/jobs', files={'file': ('garments.jpg', jpeg(), 'image/jpeg')})
    assert result.status_code == 202, result.text
    job = client.get(BASE+'/processing/jobs/'+result.json()['id']).json()
    result = client.post(BASE+'/processing/jobs/'+job['id']+'/review', json={'items': [
        {'item_id': item['id'], 'decision': 'accepted'} for item in job['items']]})
    assert result.status_code == 200, result.text
    return result.json()


def confirm(client, job, n=1, mode='garments', ids=None):
    return client.post(BASE+'/processing/jobs/'+job['id']+'/confirm', json={
        'item_ids': ids if ids is not None else [i['id'] for i in job['items'][:n]],
        'save_mode': mode, 'outfit_name': 'Quota outfit'})


def unchanged_job(client, job):
    current = client.get(BASE+'/processing/jobs/'+job['id']).json()
    assert current['status'] == 'review_required'
    assert [i['review_status'] for i in current['items']] == ['accepted']*3
    with db.connection() as c:
        assert c.execute('SELECT COUNT(*) FROM garments WHERE processing_item_id IN (SELECT id FROM processing_items WHERE job_id=?)', (job['id'],)).fetchone()[0] == 0


@pytest.mark.parametrize('start,n,expected', [(99,1,201),(98,2,201),(99,2,409),(100,1,409),(101,1,409)])
@pytest.mark.parametrize('mode', ['garments','outfit'])
def test_boundaries_atomic_batches_and_existing_over_limit(quota, start, n, expected, mode):
    job = accepted_job(quota); seed(start)
    before = usage(quota)
    response = confirm(quota, job, n, mode)
    assert response.status_code == expected, response.text
    after = usage(quota)
    if expected == 201:
        assert after['used'] == 100
        assert len(response.json()['garment_ids']) == n
        assert confirm(quota, job, n, mode).status_code == 409
        assert usage(quota) == after
    else:
        detail = response.json()['detail']
        assert detail['code'] == 'WardrobeQuotaExceeded' and detail['stage'] == 'confirmation'
        assert (detail['used'],detail['requested'],detail['remaining']) == (start,n,max(0,100-start))
        assert after == before
        unchanged_job(quota,job)
        with db.connection() as c: assert c.execute('SELECT COUNT(*) FROM outfits').fetchone()[0] == 0
    assert after['over_limit'] == (after['used'] > 100)
    # No truncation or retroactive removal of existing rows.
    assert len(quota.get(BASE+'/wardrobe/garments').json()) == after['used']


@pytest.mark.parametrize('ids', [[], ['same','same'], [str(i) for i in range(101)]])
def test_existing_request_validation_unchanged(quota, ids):
    job = accepted_job(quota)
    response = confirm(quota,job,ids=ids)
    assert response.status_code == 422 and isinstance(response.json()['detail'],list)
    assert usage(quota)['used'] == 0


def test_valid_hundred_item_batch(quota):
    job = accepted_job(quota)
    with db.connection() as c:
        original = dict(c.execute('SELECT * FROM processing_items WHERE id=?',(job['items'][0]['id'],)).fetchone())
        ids=[]
        for _ in range(100):
            row={**original,'id':str(uuid.uuid4())}; ids.append(row['id'])
            c.execute('INSERT INTO processing_items('+','.join(row)+') VALUES('+','.join('?' for _ in row)+')',tuple(row.values()))
    assert confirm(quota,job,ids=ids).status_code == 201
    assert usage(quota)['used'] == 100


@pytest.mark.parametrize('start,n', [(99,1),(98,2)])
def test_different_jobs_compete_on_independent_connections(quota, start, n):
    jobs=[accepted_job(quota),accepted_job(quota)]; seed(start)
    barrier=Barrier(2)
    def race(job):
        barrier.wait(timeout=10)
        response=confirm(quota,job,n)
        return {'job':job['id'],'http':response.status_code,'body':response.json()}
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(race,jobs))
    assert sorted(r['http'] for r in results)==[201,409]
    assert usage(quota)['used']==100
    loser=next(job for job in jobs if job['id']==next(r['job'] for r in results if r['http']==409))
    unchanged_job(quota,loser)
    evidence=os.getenv('SMART_WARDROBE_QUOTA_EVIDENCE')
    if evidence:
        with open(evidence,'a',encoding='utf-8') as stream:
            stream.write(json.dumps({'start':start,'batch':n,'results':results,'final':usage(quota),'independent_connections':True})+'\n')


def test_same_job_concurrent_and_completed_retry(quota):
    job=accepted_job(quota); seed(99); barrier=Barrier(2)
    def race(_):
        barrier.wait(timeout=10)
        return confirm(quota,job).status_code
    with ThreadPoolExecutor(max_workers=2) as pool: assert sorted(pool.map(race,range(2)))==[201,409]
    assert confirm(quota,job,2,'outfit').status_code==409
    assert usage(quota)['used']==100


def test_write_fault_rolls_back_and_retries_once(quota):
    job=accepted_job(quota); seed(98)
    with db.connection() as c:
        c.execute("CREATE TRIGGER fail_quota_outfit BEFORE INSERT ON outfit_items BEGIN SELECT RAISE(ABORT,'injected quota rollback'); END")
    with pytest.raises(sqlite3.IntegrityError,match='injected quota rollback'): confirm(quota,job,2,'outfit')
    assert usage(quota)['used']==98
    unchanged_job(quota,job)
    with db.connection() as c:
        assert c.execute('SELECT COUNT(*) FROM outfits').fetchone()[0]==0
        c.execute('DROP TRIGGER fail_quota_outfit')
    assert confirm(quota,job,2,'outfit').status_code==201
    assert usage(quota)['used']==100


def test_archive_release_blocked_archive_and_retry(quota):
    waiting=accepted_job(quota); saved=accepted_job(quota)
    result=confirm(quota,saved,1,'outfit'); assert result.status_code==201
    blocked=result.json()['garment_ids'][0]; seed(99)
    assert quota.delete(BASE+'/wardrobe/garments/'+blocked).status_code==409
    assert usage(quota)['used']==100
    assert confirm(quota,waiting).status_code==409
    gid=next(g['id'] for g in quota.get(BASE+'/wardrobe/garments').json() if g['id']!=blocked)
    assert quota.delete(BASE+'/wardrobe/garments/'+gid).status_code==204
    assert usage(quota)['used']==99
    assert confirm(quota,waiting).status_code==201
    with db.connection() as c:
        assert c.execute('SELECT COUNT(*) FROM garments').fetchone()[0]==101
        assert c.execute('SELECT status FROM garments WHERE id=?',(gid,)).fetchone()[0]=='archived'


def test_usage_scope_owner_privacy_and_no_reservations(quota,monkeypatch):
    accepted_job(quota); seed(95); seed(3,status='unavailable'); seed(4,status='archived'); seed(101,owner='another-owner')
    with db.connection() as c:
        c.execute("UPDATE garments SET deleted_at='now' WHERE id=(SELECT id FROM garments WHERE user_id='quota-owner' AND status='available' LIMIT 1)")
    result=usage(quota)
    assert (result['used'],result['remaining'],result['pending_reserved'])==(98,2,0)
    assert quota.get(BASE+'/wardrobe/quota?user_id=another-owner').json()==result
    assert quota.get(BASE+'/wardrobe/quota',headers={'X-User-Id':'another-owner'}).json()['used']==101
    monkeypatch.setattr(security,'ALLOW_DEVELOPMENT_IDENTITY',False)
    assert quota.get(BASE+'/wardrobe/quota').status_code==401


def test_full_upload_rejected_before_media_job_and_dispatch(quota,monkeypatch):
    seed(100)
    with db.connection() as c:
        before=[c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ['media_assets','processing_jobs','processing_items']]
    def forbidden(*args,**kwargs): raise AssertionError('Full upload reached durable media storage')
    monkeypatch.setattr('app.api.garment_processing_routes.upload_validator.validate_and_store_wardrobe_image',forbidden)
    response=quota.post(BASE+'/processing/jobs',files={'file':('outfit.jpg',jpeg(),'image/jpeg')})
    assert response.status_code==409,response.text
    assert response.json()['detail']['stage']=='upload' and response.json()['detail']['requested'] is None
    with db.connection() as c:
        assert before==[c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ['media_assets','processing_jobs','processing_items']]


def test_direct_application_writer_cannot_bypass_quota(quota):
    job=accepted_job(quota); seed(100)
    with pytest.raises(HTTPException) as error:
        confirm_candidates(job['id'],'quota-owner',[job['items'][0]['id']],'garments',None)
    assert error.value.status_code==409 and error.value.detail['code']=='WardrobeQuotaExceeded'
    unchanged_job(quota,job)


@pytest.mark.parametrize('fault', ['second_garment','job_completion'])
def test_fault_after_partial_work_rolls_back_all_selected_items(quota,fault):
    job=accepted_job(quota); seed(98)
    trigger=("BEFORE INSERT ON garments WHEN (SELECT COUNT(*) FROM garments)=99" if fault=='second_garment'
             else "BEFORE UPDATE OF status ON processing_jobs WHEN NEW.status='completed'")
    with db.connection() as c:
        c.execute("CREATE TRIGGER fail_quota_partial "+trigger+" BEGIN SELECT RAISE(ABORT,'injected partial rollback'); END")
    with pytest.raises(sqlite3.IntegrityError,match='injected partial rollback'): confirm(quota,job,2)
    assert usage(quota)['used']==98
    unchanged_job(quota,job)
    with db.connection() as c: c.execute('DROP TRIGGER fail_quota_partial')
    assert confirm(quota,job,2).status_code==201


def test_archive_and_confirmation_race_respects_commit_order(quota):
    job=accepted_job(quota); seed(100)
    with db.connection() as c: gid=c.execute('SELECT id FROM garments LIMIT 1').fetchone()[0]
    barrier=Barrier(2)
    def action(archive):
        barrier.wait(timeout=10)
        return (quota.delete(BASE+'/wardrobe/garments/'+gid) if archive else confirm(quota,job)).status_code
    with ThreadPoolExecutor(max_workers=2) as pool: statuses=list(pool.map(action,[True,False]))
    assert statuses[0]==204 and statuses[1] in (201,409)
    assert usage(quota)['used']==(100 if statuses[1]==201 else 99)
    if statuses[1]==409: assert confirm(quota,job).status_code==201
    assert usage(quota)['used']==100
