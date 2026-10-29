"""Saved-outfit integration: actual upload/review/confirm, disposable SQLite.

Synthetic detector and inference fixtures are NOT real-model validation.
"""
from contextlib import contextmanager, nullcontext
from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import threading
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.application.garment_processing import garment_processing_orchestrator as processing
from app.application.visualisation import outfit_identifier_validator as source
from app.application.visualisation import outfit_visualisation_service as jobs
from app.application.ports.visualisation_repository import runtime, configure_visualisation
from tests.test_garment_workflow import Detector, GeneratedVtoffStub, jpeg


@pytest.fixture
def saved(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DATABASE_PATH', tmp_path/'saved.db')
    monkeypatch.setattr(processing, 'get_garment_adapter', lambda: Detector())
    monkeypatch.setattr(processing, 'get_standardisation_adapter', lambda: GeneratedVtoffStub())
    with TestClient(app, headers={'X-User-Id':'saved-owner'}) as client:
        uploaded=client.post('/api/v1/processing/jobs', files={'file':('garments.jpg',jpeg(),'image/jpeg')})
        assert uploaded.status_code==202, uploaded.text
        job=client.get('/api/v1/processing/jobs/'+uploaded.json()['id']).json()
        item_ids=[i['id'] for i in job['items']]
        base='/api/v1/processing/jobs/'+job['id']
        assert client.post(base+'/review',json={'items':[{'item_id':i,'decision':'accepted'} for i in item_ids]}).status_code==200
        result=client.post(base+'/confirm',json={'save_mode':'outfit','outfit_name':'Normally confirmed','item_ids':item_ids[:2]})
        assert result.status_code==201, result.text
        first=result.json()
        # Confirm remaining item in a separate actual job (completed jobs cannot confirm twice).
        uploaded=client.post('/api/v1/processing/jobs',files={'file':('extra.jpg',jpeg(),'image/jpeg')})
        extra=client.get('/api/v1/processing/jobs/'+uploaded.json()['id']).json()
        e=extra['items'][0]['id']; base='/api/v1/processing/jobs/'+extra['id']
        assert client.post(base+'/review',json={'items':[{'item_id':e,'decision':'accepted'}]}).status_code==200
        result=client.post(base+'/confirm',json={'save_mode':'garments','item_ids':[e]})
        assert result.status_code==201
        manual=client.post('/api/v1/wardrobe/outfits',json={'name':'Manual confirmed outfit','garment_ids':first['garment_ids']})
        assert manual.status_code==201, manual.text
        person=client.post('/api/v1/media/person-images',files={'file':('person.jpg',jpeg(),'image/jpeg')})
        assert person.status_code==201, person.text
        yield {'client':client,'owner':'saved-owner','outfit':manual.json()['id'],
               'normal':first['outfit_id'],'ids':first['garment_ids'],'extra':result.json()['garment_ids'][0],
               'items':item_ids[:2],'job':job['id'],'person':person.json()['id'],'path':db.DATABASE_PATH}


def mutate(saved, condition):
    gid=saved['ids'][1]; item=saved['items'][1]; outfit=saved['outfit']
    with db.connection() as c:
        if condition in ('pending','accepted','rejected'):
            c.execute('UPDATE processing_items SET review_status=? WHERE id=?',(condition,item))
        elif condition in ('null','dangling'):
            c.execute('UPDATE garments SET processing_item_id=? WHERE id=?',(None if condition=='null' else 'absent',gid))
        elif condition=='missing_item': c.execute('DELETE FROM processing_items WHERE id=?',(item,))
        elif condition=='missing_job':
            # Explicitly simulate corrupt historical storage in this disposable DB.
            c.execute('PRAGMA foreign_keys=OFF')
            c.execute('DELETE FROM processing_jobs WHERE id=?',(saved['job'],))
        elif condition=='foreign_job': c.execute("UPDATE processing_jobs SET user_id='foreign' WHERE id=?",(saved['job'],))
        elif condition=='foreign_garment': c.execute("UPDATE garments SET user_id='foreign' WHERE id=?",(gid,))
        elif condition in ('archived','deleted'): c.execute('UPDATE garments SET status=? WHERE id=?',(condition,gid))
        elif condition=='missing_garment':
            # Deliberate legacy corruption, not an application-supported deletion.
            c.execute('PRAGMA foreign_keys=OFF')
            c.execute('DELETE FROM garments WHERE id=?',(gid,))
        elif condition=='media': c.execute('UPDATE garments SET preferred_media_id=(SELECT preferred_media_id FROM garments WHERE id=?) WHERE id=?',(saved['extra'],gid))
        elif condition=='category': c.execute("UPDATE garments SET category='skirt' WHERE id=?",(gid,))
        elif condition=='outerwear': c.execute("UPDATE garments SET category='long_sleeve_outwear' WHERE id=?",(gid,))
        elif condition=='role': c.execute("UPDATE outfit_items SET role='garment' WHERE outfit_id=? AND garment_id=?",(outfit,gid))
        elif condition=='unsupported_role': c.execute("UPDATE outfit_items SET role='unsupported' WHERE outfit_id=? AND garment_id=?",(outfit,gid))
        elif condition=='order': c.execute('UPDATE outfit_items SET item_order=3-item_order WHERE outfit_id=?',(outfit,))
        elif condition=='membership': c.execute('UPDATE outfit_items SET garment_id=? WHERE outfit_id=? AND garment_id=?',(saved['extra'],outfit,gid))
        elif condition=='count': c.execute('DELETE FROM outfit_items WHERE outfit_id=? AND garment_id=?',(outfit,gid))
        elif condition=='duplicate':
            c.execute('ALTER TABLE outfit_items RENAME TO original_outfit_items')
            c.execute('CREATE TABLE outfit_items AS SELECT * FROM original_outfit_items')
            c.execute('INSERT INTO outfit_items SELECT * FROM original_outfit_items WHERE outfit_id=? LIMIT 1',(outfit,))
        elif condition=='duplicate_order': c.execute('UPDATE outfit_items SET item_order=1 WHERE outfit_id=?',(outfit,))
        elif condition=='missing_media': c.execute("UPDATE media_assets SET status='deleted' WHERE id=(SELECT preferred_media_id FROM garments WHERE id=?)",(gid,))
        elif condition=='foreign_media': c.execute("UPDATE media_assets SET user_id='foreign' WHERE id=(SELECT preferred_media_id FROM garments WHERE id=?)",(gid,))
        elif condition=='foreign_outfit': c.execute("UPDATE outfits SET user_id='foreign' WHERE id=?",(outfit,))
        elif condition=='archived_outfit': c.execute("UPDATE outfits SET status='archived' WHERE id=?",(outfit,))
        else: raise AssertionError(condition)


def history(saved):
    with db.connection() as c:
        return {t:[tuple(r) for r in c.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in
                ('outfits','outfit_items','recommendations','recommendation_items')}


def test_read_only_confirmation_inventory(saved):
    # Inventory only SELECTs, before changing production validation. Fixtures are disposable.
    with db.connection() as c:
        rows=[dict(r) for r in c.execute('SELECT o.id AS outfit_id,o.creation_type,g.id AS garment_id,g.processing_item_id,p.review_status,j.user_id AS job_owner,g.user_id,g.status FROM outfits o JOIN outfit_items oi ON oi.outfit_id=o.id JOIN garments g ON g.id=oi.garment_id LEFT JOIN processing_items p ON p.id=g.processing_item_id LEFT JOIN processing_jobs j ON j.id=p.job_id ORDER BY o.id,oi.item_order')]
    eligible={g.garment_id for g in SqliteConfirmedGarmentQuery().get_confirmed_available_garments(saved['owner'])}
    assert len(rows)==4 and {r['creation_type'] for r in rows}=={'manual','image_upload'}
    assert all(r['review_status']=='confirmed' and r['job_owner']==r['user_id']==saved['owner'] and r['garment_id'] in eligible for r in rows)
    output=os.environ.get('SMART_WARDROBE_SAVED_INVENTORY')
    if output: Path(output).write_text(json.dumps({'scope':'Disposable actual API-confirmed test records only; no deployment database inspected','rows':rows},indent=2),encoding='utf-8')


def test_normal_manual_and_old_confirmed_sources(saved):
    before=history(saved)
    for oid in (saved['normal'],saved['outfit']):
        result=source.prepare_visualisation(saved['owner'],outfit_id=oid)
        assert [i['garment_id'] for i in result['items']]==saved['ids']
        assert [i['role'] for i in result['items']]==['top','bottom']
    with db.connection() as c: c.execute("UPDATE garments SET created_at='2001-01-01',updated_at='2001-01-01'")
    assert len(source.prepare_visualisation(saved['owner'],outfit_id=saved['outfit'])['items'])==2
    assert history(saved)==before


INVALID=('pending','accepted','rejected','null','dangling','missing_item','missing_job','foreign_job','foreign_garment','archived','deleted','missing_garment','outerwear','unsupported_role','duplicate','duplicate_order','missing_media','foreign_media','foreign_outfit','archived_outfit')


@pytest.mark.parametrize('condition',INVALID)
def test_second_invalid_member_rejected_no_partial_write_or_history_change(saved,condition):
    mutate(saved,condition); before=history(saved)
    with pytest.raises(HTTPException): source.prepare_visualisation(saved['owner'],outfit_id=saved['outfit'])
    with pytest.raises(HTTPException): jobs.create_visualisation(saved['owner'],saved['person'],outfit_id=saved['outfit'])
    with db.connection() as c:
        assert c.execute('SELECT count(*) FROM visualisations').fetchone()[0]==0
        assert c.execute('SELECT count(*) FROM visualisation_items').fetchone()[0]==0
    assert history(saved)==before


@pytest.mark.parametrize('condition',INVALID+('media','category','role','order','membership','count'))
def test_queued_source_revalidated_before_fake_inference(saved,condition,monkeypatch):
    identifier=jobs.create_visualisation(saved['owner'],saved['person'],outfit_id=saved['outfit'])
    mutate(saved,condition); before=history(saved)
    adapter=Mock(); monkeypatch.setattr(jobs,'get_vton_adapter',lambda:adapter)
    jobs.run_visualisation(identifier,saved['owner'])
    adapter.generate.assert_not_called()
    with db.connection() as c:
        result=c.execute('SELECT status,error_code FROM visualisations WHERE id=?',(identifier,)).fetchone()
        assert tuple(result)==('failed','unprocessable')
        assert c.execute('SELECT count(*) FROM visualisation_items WHERE visualisation_id=?',(identifier,)).fetchone()[0]==2
    assert history(saved)==before


def test_prepare_then_change_cannot_authorise_create(saved):
    source.prepare_visualisation(saved['owner'],outfit_id=saved['outfit'])
    mutate(saved,'accepted')
    with pytest.raises(HTTPException): jobs.create_visualisation(saved['owner'],saved['person'],outfit_id=saved['outfit'])


def test_multiple_tops_not_subject_to_recommendation_structure(saved):
    with db.connection() as c:
        c.execute('UPDATE outfit_items SET garment_id=?,role=? WHERE outfit_id=? AND garment_id=?',(saved['extra'],'top',saved['outfit'],saved['ids'][1]))
    assert source.prepare_visualisation(saved['owner'],outfit_id=saved['outfit'])['categories']==['upper','upper']


def test_item_insert_failure_rolls_back_entire_request(saved):
    with db.connection() as c:
        c.execute("CREATE TRIGGER fail_second BEFORE INSERT ON visualisation_items WHEN NEW.item_order=2 BEGIN SELECT RAISE(ABORT,'injected second item'); END")
    with pytest.raises(sqlite3.IntegrityError,match='injected second item'):
        jobs.create_visualisation(saved['owner'],saved['person'],outfit_id=saved['outfit'])
    with db.connection() as c:
        assert c.execute('SELECT count(*) FROM visualisations').fetchone()[0]==0
        assert c.execute('SELECT count(*) FROM visualisation_items').fetchone()[0]==0


@pytest.mark.parametrize('stage',['create','claim'])
def test_write_lock_and_no_transaction_during_gpu_wait_or_inference(saved,monkeypatch,stage):
    original=jobs.resolve_source; attempts=[]
    def checked(conn,*args,**kwargs):
        result=original(conn,*args,**kwargs)
        assert conn.in_transaction
        def competing():
            other=sqlite3.connect(saved['path'],timeout=.05)
            try:
                other.execute("UPDATE garments SET name=name"); other.commit(); attempts.append('committed')
            except sqlite3.OperationalError as e: attempts.append(str(e))
            finally: other.close()
        thread=threading.Thread(target=competing);thread.start();thread.join()
        return result
    if stage=='create': monkeypatch.setattr(jobs,'resolve_source',checked)
    identifier=jobs.create_visualisation(saved['owner'],saved['person'],outfit_id=saved['outfit'])
    if stage=='claim': monkeypatch.setattr(jobs,'resolve_source',checked)
    rt=runtime(); observations=[]
    def writable(label):
        with sqlite3.connect(saved['path'],timeout=.1) as c: c.execute('UPDATE garments SET name=name')
        observations.append(label)
    @contextmanager
    def slot():
        writable('gpu_wait'); yield
    def generate(plan,*args):
        writable('inference')
        with db.connection() as c:
            config=json.loads(c.execute('SELECT configuration_json FROM visualisations WHERE id=?',(identifier,)).fetchone()[0])
        assert plan.configuration.to_dict()==config
        assert len(plan.garments)==2
        return object()
    adapter=Mock();adapter.generate.side_effect=generate
    configure_visualisation(replace(rt,gpu_slot=slot,configuration=lambda:replace(rt.configuration(),seed=999)))
    monkeypatch.setattr(jobs,'get_vton_adapter',lambda:adapter)
    monkeypatch.setattr(jobs,'complete',lambda *args:observations.append('complete'))
    try: jobs.run_visualisation(identifier,saved['owner'])
    finally: configure_visualisation(rt)
    assert attempts and all('locked' in a for a in attempts)
    assert observations==['gpu_wait','inference','complete']
    adapter.generate.assert_called_once()


def test_concurrent_change_during_gpu_wait_is_revalidated(saved,monkeypatch):
    identifier=jobs.create_visualisation(saved['owner'],saved['person'],outfit_id=saved['outfit'])
    rt=runtime(); adapter=Mock(); changed=threading.Event()
    @contextmanager
    def slot():
        # Another real connection commits while the job waits for the GPU.
        worker=threading.Thread(target=lambda:(mutate(saved,'accepted'),changed.set()))
        worker.start();worker.join(timeout=5)
        assert changed.is_set()
        yield
    configure_visualisation(replace(rt,gpu_slot=slot))
    monkeypatch.setattr(jobs,'get_vton_adapter',lambda:adapter)
    try: jobs.run_visualisation(identifier,saved['owner'])
    finally: configure_visualisation(rt)
    adapter.generate.assert_not_called()
    with db.connection() as c:
        assert tuple(c.execute('SELECT status,error_code FROM visualisations WHERE id=?',(identifier,)).fetchone())==('failed','unprocessable')


def test_foreign_source_api_is_not_accessible(saved):
    response=saved['client'].post('/api/v1/visualisations/prepare',headers={'X-User-Id':'intruder'},json={'outfit_id':saved['outfit']})
    assert response.status_code==404


def test_read_only_unproven_fixture_inventory(saved):
    # Existing disposable NULL-link fixture is inventoried without repairing it.
    mutate(saved,'null')
    with db.connection() as c:
        c.execute('PRAGMA query_only=ON')
        rows=[dict(r) for r in c.execute('SELECT g.id,g.processing_item_id,p.review_status,j.user_id AS job_owner FROM garments g LEFT JOIN processing_items p ON p.id=g.processing_item_id LEFT JOIN processing_jobs j ON j.id=p.job_id WHERE g.id IN (?,?) ORDER BY g.id',saved['ids'])]
    assert sum(r['processing_item_id'] is None for r in rows)==1
    eligible={g.garment_id for g in SqliteConfirmedGarmentQuery().get_confirmed_available_garments(saved['owner'])}
    assert saved['ids'][0] in eligible and saved['ids'][1] not in eligible
