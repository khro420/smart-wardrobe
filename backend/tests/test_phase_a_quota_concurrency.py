"""Complete shared-pool bound and concurrent account admissions, without clipping."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from dataclasses import replace
import uuid
import pytest
from tests.test_wardrobe_quota import quota,usage,seed,accepted_job
from tests.test_recommendation_refinement_integration import (
    refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,wardrobe,
)
from tests.test_phase_a_wearer_identity import request
from tests.test_phase_a_profile_archive import wearers
from tests.test_structural_candidates import garment,Query
from app.application.recommendation.recommendation_engine import RecommendationEngine
from app.infrastructure.persistence import postgresql_repository as db


def test_two_wearers_compete_for_one_account_slot(quota):
    client=quota
    a=client.get('/api/v1/account/wardrobe-profiles').json()[0]['id']
    b=client.post('/api/v1/account/wardrobe-profiles',json={'name':'Other'}).json()['id']
    jobs=[]
    for profile in (a,b):
        client.headers['X-Wardrobe-Profile-Id']=profile
        jobs.append(accepted_job(client))
    seed(99);barrier=Barrier(2)
    def run(pair):
        profile,job=pair;barrier.wait(timeout=10)
        return client.post('/api/v1/processing/jobs/'+job['id']+'/confirm',headers={'X-Wardrobe-Profile-Id':profile},json={'item_ids':[job['items'][0]['id']],'save_mode':'garments'})
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(run,zip((a,b),jobs)))
    assert sorted(r.status_code for r in results)==[201,409]
    assert usage(client)['used']==100
    for profile,job,result in zip((a,b),jobs,results):
        if result.status_code==201:
            assert client.post('/api/v1/processing/jobs/'+job['id']+'/confirm',headers={'X-Wardrobe-Profile-Id':profile},json={'item_ids':[job['items'][0]['id']],'save_mode':'garments'}).status_code==409
    assert usage(client)['used']==100


def test_structural_capacity_terminal_before_enumeration():
    rows=[garment(str(n),'vest_dress') for n in range(101)]
    engine=RecommendationEngine(Query(rows))
    result=engine.generate_homepage_candidates('owner')
    assert result.result.status=='WardrobeCapacityExceeded' and not result.result.complete
    assert tuple(result)==() and result.result.candidate_count==0


@pytest.mark.parametrize('engine',['compact_exhaustive','reference'])
def test_complete_overcapacity_pool_rejected_without_chat(refinement_api,engine,monkeypatch):
    from app.infrastructure.workflow_runtime import configure_local_workflow
    client,_=refinement_api;a,b=wearers(client);wardrobe(client)
    with db.connection() as conn:
        original=dict(conn.execute('SELECT * FROM garments LIMIT 1').fetchone())
        item=dict(conn.execute('SELECT * FROM processing_items WHERE id=?',(original['processing_item_id'],)).fetchone())
        count=conn.execute('SELECT COUNT(*) FROM garments').fetchone()[0]
        for _ in range(101-count):
            cloned_item={**item,'id':str(uuid.uuid4())}
            conn.execute('INSERT INTO processing_items('+','.join(cloned_item)+') VALUES('+','.join('?' for _ in cloned_item)+')',tuple(cloned_item.values()))
            cloned={**original,'id':str(uuid.uuid4()),'processing_item_id':cloned_item['id']}
            conn.execute('INSERT INTO garments('+','.join(cloned)+') VALUES('+','.join('?' for _ in cloned)+')',tuple(cloned.values()))
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE',engine);configure_local_workflow()
    response,result=request(client,a)
    assert response.status_code==409 and result['outcome']=='WardrobeCapacityExceeded' and not result['complete'],result
    with db.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM garments').fetchone()[0]==101
        assert conn.execute('SELECT COUNT(*) FROM nlp_chats').fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM recommendation_submissions').fetchone()[0]==0


def test_noneligible_excess_does_not_clip_valid_pool(refinement_api):
    client,_=refinement_api;a,b=wearers(client);wardrobe(client)
    with db.connection() as conn:
        uid=conn.execute('SELECT user_id FROM wardrobe_profiles WHERE id=?',(a,)).fetchone()[0]
    seed(101,uid,status='unavailable')
    response,result=request(client,a)
    assert response.status_code==201,result
    assert client.get('/api/v1/wardrobe/quota').json()['over_limit']
