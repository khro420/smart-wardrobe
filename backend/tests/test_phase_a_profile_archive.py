"""Frozen Phase A archival/ownership mechanics on disposable application data."""
import uuid
import pytest
from fastapi import HTTPException
from tests.test_recommendation_refinement_integration import (
    refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,
    wardrobe,submit as legacy_submit,
)
from app.infrastructure.persistence import postgresql_repository as db
from app.application.wardrobe import profile_service
from app.application.garment_processing import processing_job_service
from app.application.visualisation import personal_image_service,outfit_visualisation_service

def submit(client):
    import uuid
    response=client.post('/api/v1/recommendations?pipeline=integrated',json={
        'request_text':"I'm going shopping.",'submission_key':uuid.uuid4().hex,
        'wearer_profile_id':client.headers['X-Wardrobe-Profile-Id']})
    return response,response.json()



def wearers(client):
    a=client.get('/api/v1/account/wardrobe-profiles').json()[0]['id']
    b=client.post('/api/v1/account/wardrobe-profiles',json={'name':'B'}).json()['id']
    client.headers['X-Wardrobe-Profile-Id']=a
    return a,b


def owner(profile):
    with db.connection() as conn:
        return conn.execute('SELECT user_id FROM wardrobe_profiles WHERE id=?',(profile,)).fetchone()[0]


def test_archive_retains_history_inventory_and_origin(refinement_api):
    client,_=refinement_api;a,b=wearers(client);wardrobe(client)
    response,root=submit(client);assert response.status_code==201,root
    assert client.put('/api/v1/account/preferences/colours',json={'preference_value':{'values':['blue']},'weight':1}).status_code==200
    from tests.test_garment_workflow import jpeg
    image=client.post('/api/v1/media/person-images',files={'file':('synthetic-person.jpg',jpeg(),'image/jpeg')})
    assert image.status_code==201,image.text
    person=image.json();uid=owner(a)
    with db.connection() as conn:
        conn.execute("INSERT INTO visualisations(id,user_id,profile_id,recommendation_id,source_type,person_image_id,person_media_id,output_media_id,status,created_at,updated_at,completed_at) VALUES('retained-visual',?,?,?,'recommendation',?,?,?,'completed','now','now','now')",(uid,a,root['id'],person['id'],person['media_id'],person['media_id']))
        conn.execute("INSERT INTO visualisation_items(visualisation_id,garment_id,source_media_id,role,item_order) VALUES('retained-visual',?,?,?,1)",(root['items'][0]['garment_id'],root['items'][0]['preferred_media_id'],root['items'][0]['garment_role']))
    tables=['garments','outfits','processing_jobs','processing_items','recommendations','nlp_chats',
            'recommendation_item_snapshots','recommendation_items','recommendation_metadata',
            'recommendation_submissions','user_preferences','person_images','visualisations','media_assets']
    with db.connection() as conn:
        before={table:[tuple(row) for row in conn.execute('SELECT * FROM '+table)] for table in tables}
    assert client.delete('/api/v1/account/wardrobe-profiles/'+a).status_code==409
    response=client.post('/api/v1/account/wardrobe-profiles/'+a+'/archive')
    assert response.status_code==200,response.text
    assert response.json()['next_profile_id']==b
    with db.connection() as conn:
        assert {table:[tuple(row) for row in conn.execute('SELECT * FROM '+table)] for table in tables}==before
        assert conn.execute('SELECT status,is_default FROM wardrobe_profiles WHERE id=?',(a,)).fetchone()[:]==('archived',0)
    assert [p['id'] for p in client.get('/api/v1/account/wardrobe-profiles').json()]==[b]
    assert [p['id'] for p in client.get('/api/v1/account/wardrobe-profiles?status=archived').json()]==[a]
    assert client.post('/api/v1/account/wardrobe-profiles/'+a+'/archive').status_code==409
    assert client.post('/api/v1/account/wardrobe-profiles/'+b+'/archive').status_code==409
    assert client.get('/api/v1/account/preferences').status_code==409
    assert client.delete('/api/v1/account/wardrobe-profiles/'+str(uuid.uuid4())).status_code==404
    assert client.get('/api/v1/visualisations/retained-visual').status_code==200


@pytest.mark.parametrize('state',['queued','processing','review_required'])
def test_pending_job_blocks_archive_without_changes(refinement_api,state):
    client,_=refinement_api;a,b=wearers(client);wardrobe(client)
    with db.connection() as conn:
        jid=conn.execute('SELECT id FROM processing_jobs WHERE profile_id=? LIMIT 1',(a,)).fetchone()[0]
        conn.execute('UPDATE processing_jobs SET status=? WHERE id=?',(state,jid))
    response=client.post('/api/v1/account/wardrobe-profiles/'+a+'/archive')
    assert response.status_code==409 and response.json()['detail']['code']=='ProfileBusy'
    assert {p['id'] for p in client.get('/api/v1/account/wardrobe-profiles').json()}=={a,b}


def test_history_owner_scope_and_inactive_new_work(refinement_api):
    client,_=refinement_api;a,b=wearers(client);wardrobe(client);uid=owner(a)
    with db.connection() as conn:
        row=conn.execute('SELECT id,source_media_id FROM processing_jobs WHERE profile_id=? LIMIT 1',(a,)).fetchone()
        jid,media=row
    assert client.get('/api/v1/processing/jobs/capabilities').json()['admission_modes']==['manual_review_v1','automatic_structural_v1']
    assert client.post('/api/v1/account/wardrobe-profiles/'+a+'/archive').status_code==200
    historical=client.get('/api/v1/processing/jobs/'+jid+'/history')
    assert historical.status_code==200 and historical.json()['read_only']
    assert any(j['id']==jid for j in client.get('/api/v1/processing/jobs/history?wearer_profile_id='+a).json())
    assert client.get('/api/v1/processing/jobs/'+jid).status_code==409
    with pytest.raises(HTTPException) as error:
        processing_job_service.create_job(media,uid,a)
    assert error.value.status_code==409
    with pytest.raises(HTTPException) as error:
        personal_image_service.register_person_image(media,uid,'Retained',a)
    assert error.value.status_code==409
    with pytest.raises(HTTPException) as error:
        outfit_visualisation_service.create_visualisation(uid,'missing',profile_id=a)
    assert error.value.status_code==409
    with pytest.raises(HTTPException) as error:
        processing_job_service.historical_job(jid,'foreign-owner')
    assert error.value.status_code==404
    assert client.get('/api/v1/processing/jobs/history?limit=101').status_code==422


@pytest.mark.parametrize('state',['queued','processing'])
def test_pending_visual_blocks_archive(refinement_api,state):
    client,_=refinement_api;a,b=wearers(client);wardrobe(client)
    response,root=submit(client);assert response.status_code==201,root
    with db.connection() as conn:
        conn.execute("INSERT INTO visualisations(id,user_id,profile_id,recommendation_id,source_type,person_image_id,status,created_at,updated_at) VALUES('busy-visual',?,?,?,'recommendation','fixture-person',?,'now','now')",(owner(a),a,root['id'],state))
    response=client.post('/api/v1/account/wardrobe-profiles/'+a+'/archive')
    assert response.status_code==409 and response.json()['detail']['code']=='ProfileBusy'


def test_concurrent_job_creation_and_archive_serialize(refinement_api):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    client,_=refinement_api;a,b=wearers(client);wardrobe(client);uid=owner(a)
    with db.connection() as conn:
        media=conn.execute('SELECT source_media_id FROM processing_jobs WHERE user_id=? LIMIT 1',(uid,)).fetchone()[0]
        before=conn.execute('SELECT COUNT(*) FROM processing_jobs WHERE user_id=?',(uid,)).fetchone()[0]
    barrier=Barrier(2)
    def run(kind):
        barrier.wait(timeout=10)
        try:
            value=processing_job_service.create_job(media,uid,a) if kind=='job' else profile_service.archive_profile(uid,a)
            return kind,True,value
        except HTTPException as error:
            return kind,False,error.status_code
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(run,['job','archive']))
    assert sum(success for _,success,_ in results)==1,results
    assert next(value for _,success,value in results if not success)==409
    with db.connection() as conn:
        status=conn.execute('SELECT status FROM wardrobe_profiles WHERE id=?',(a,)).fetchone()[0]
        count=conn.execute('SELECT COUNT(*) FROM processing_jobs WHERE user_id=?',(uid,)).fetchone()[0]
    assert (status,count) in [('archived',before),('active',before+1)]
