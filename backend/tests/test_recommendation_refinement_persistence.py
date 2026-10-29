"""New-mode lock, rollback, scope races, indexed lineage and immutable receipts."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import json,uuid
import pytest
from tests.test_recommendation_refinement_integration import refinement_api,submit,next_action,initial
from tests.test_context_expansion_integration import expanded_api
from tests.test_context_relevance_integration import relative_api,automatic_api,everyday_api,release,lifecycle,wardrobe
from app.application.ports.assistant_runtime import assistant_service
from app.infrastructure.persistence import postgresql_repository as db


@pytest.mark.parametrize('stage',['revalidated','chat','recommendation','item','snapshot','metadata','submission','before_commit'])
def test_child_fault_rolls_back_every_insert_and_slot(refinement_api,monkeypatch,stage):
    client,_=refinement_api;wardrobe(client);_,root=submit(client)
    repository=assistant_service().repository
    with db.connection() as conn:
        before={t:conn.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('nlp_chats','recommendations','recommendation_items','recommendation_item_snapshots','recommendation_metadata','recommendation_submissions')}
    with monkeypatch.context() as local:
        def fail(where,conn):
            if where==stage:raise RuntimeError('Disposable refinement fault')
        local.setattr(repository,'checkpoint',fail)
        assert next_action(client,root)[0].status_code==503
    with db.connection() as conn:
        assert before=={t:conn.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in before}
    response,child=next_action(client,root);assert response.status_code==201,child
    assert next_action(client,root)[1]['id']==child['id']


@pytest.mark.parametrize('change',['selected','competitor','preference'])
def test_locked_scope_rejects_rank_to_commit_changes(refinement_api,monkeypatch,change):
    client,_=refinement_api;ids=wardrobe(client);_,root=submit(client)
    repository=assistant_service().repository;original=repository.persist_assistant
    def altered(command):
        with db.connection() as conn:
            if change=='preference':
                conn.execute("INSERT INTO user_preferences (id,user_id,preference_type,preference_value_json,weight,source,is_active,created_at,updated_at) VALUES (?,?,?,? ,1,'test',1,'now','now')",(str(uuid.uuid4()),command.user_id,'colours','{"values":["green"]}'))
            else:
                gid=command.candidate.members[0].garment.garment_id if change=='selected' else ids['Navy Dress']
                conn.execute("UPDATE garments SET updated_at='changed-during-rank' WHERE id=?",(gid,))
        return original(command)
    with monkeypatch.context() as local:
        local.setattr(repository,'persist_assistant',altered)
        response,result=next_action(client,root)
        assert response.status_code==409 and result['outcome']=='RefinementScopeChanged',result
    with db.connection() as conn:assert conn.execute('SELECT count(*) FROM recommendations').fetchone()[0]==1


def test_concurrent_same_parent_has_one_child_and_one_replay(refinement_api,monkeypatch):
    client,_=refinement_api;wardrobe(client);_,root=submit(client)
    service=assistant_service();repository=service.repository;original=repository.persist_assistant
    barrier=Barrier(2)
    def simultaneous(command):barrier.wait(timeout=20);return original(command)
    descriptor=root['scoring_display']['refinement']['next_action']
    with monkeypatch.context() as local:
        local.setattr(repository,'persist_assistant',simultaneous)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(service.recommend,root['user_id'],descriptor['submission_key'],root['request_text'],descriptor['refinement']) for _ in range(2)]
            results=[f.result(timeout=30) for f in futures]
    assert all(r['status']=='Selected' for r in results),results
    assert {r['replayed'] for r in results}=={False,True}
    assert results[0]['id']==results[1]['id']
    with db.connection() as conn:assert conn.execute('SELECT count(*) FROM recommendations').fetchone()[0]==2


def test_archive_replay_does_not_load_active_policy_or_preferences(refinement_api,monkeypatch):
    client,_=refinement_api;wardrobe(client);_,root=submit(client);_,child=next_action(client,root)
    from app.application.recommendation.context_bundle import ContextBundle
    from app.application.recommendation.refinement_policy import RefinementPolicy
    def forbidden(*args,**kwargs):raise AssertionError('Archived replay read current ranking configuration')
    monkeypatch.setattr(ContextBundle,'load',forbidden);monkeypatch.setattr(RefinementPolicy,'load',forbidden)
    monkeypatch.setattr(assistant_service().preference_query,'get_active_preferences',forbidden)
    response,replay=next_action(client,root)
    assert response.status_code==200 and replay['scoring_display']==child['scoring_display'],replay
    assert client.get('/api/v1/chats/'+child['chat_id']).json()['recommendation']['score_metadata']==child['score_metadata']



def test_sqlite_busy_is_technical_and_same_key_recovers(refinement_api,monkeypatch):
    client,_=refinement_api;wardrobe(client);_,root=submit(client)
    repository=assistant_service().repository;original=repository._connect
    with db.connection() as blocker:
        blocker.execute('BEGIN IMMEDIATE')
        def immediate():
            conn=original();conn.execute('PRAGMA busy_timeout=0');return conn
        with monkeypatch.context() as local:
            local.setattr(repository,'_connect',immediate)
            response,result=next_action(client,root)
            assert response.status_code==503,result
        blocker.rollback()
    response,child=next_action(client,root)
    assert response.status_code==201 and child['scoring_display']['refinement']['ordinal']==1


def test_new_mode_uses_one_snapshot_pair_and_one_locked_validation_pair(refinement_api,monkeypatch):
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    from app.infrastructure.persistence import active_preference_query_adapter as preferences
    client,_=refinement_api;wardrobe(client);service=assistant_service();counts={'strict':0,'preferences':0}
    strict=SqliteConfirmedGarmentQuery.get_confirmed_available_garments;pref=preferences.read_active_preference_rows
    def query(self,*args,**kwargs):counts['strict']+=1;return strict(self,*args,**kwargs)
    def read(conn,*args,**kwargs):counts['preferences']+=1;return pref(conn,*args,**kwargs)
    monkeypatch.setattr(SqliteConfirmedGarmentQuery,'get_confirmed_available_garments',query)
    monkeypatch.setattr(preferences,'read_active_preference_rows',read)
    response,root=submit(client)
    assert response.status_code==201 and counts=={'strict':2,'preferences':2},(root,counts)
    counts.update(strict=0,preferences=0)
    response,child=next_action(client,root)
    assert response.status_code==201 and counts=={'strict':2,'preferences':2},(child,counts)



def test_disposable_rank_commit_and_lineage_read_observation(refinement_api,tmp_path):
    import time,tracemalloc
    from app.infrastructure.persistence.refinement_lineage_query import read_chain
    from app.application.recommendation.refinement_lineage_service import validate_chain
    client,_=refinement_api;wardrobe(client);results=[]
    response,root=submit(client);assert response.status_code==201;result=root
    for index in range(4):
        results.append({'ordinal':index,'timings':result['timings']})
        if index<3:
            response,result=next_action(client,result);assert response.status_code==201
    with db.connection() as conn:
        queries=[];conn.set_trace_callback(queries.append);tracemalloc.start();started=time.perf_counter()
        parent,chain=read_chain(conn,root['user_id'],result['id']);validate_chain(root['user_id'],chain)
        elapsed=time.perf_counter()-started;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    assert len(chain)==4 and len(queries)==3
    (tmp_path/'transaction-observation.json').write_text(json.dumps({'steps':results,'chain_records':len(chain),'chain_selects':len(queries),'chain_read_validate_seconds':elapsed,'chain_peak_bytes':peak},indent=2))
