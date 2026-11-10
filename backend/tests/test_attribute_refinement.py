"""Full inherited condition identity through authenticated disposable lineages."""
import json
import uuid
import pytest
from tests.test_attribute_persistence import attribute_api,qualify,submit,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,wardrobe
from tests.test_phase_a_profile_archive import wearers
from app.application.ports.assistant_runtime import assistant_service
from app.infrastructure.persistence import postgresql_repository as db


def qualifying_wardrobe(client):
    ids=wardrobe(client)
    for name in ('Blue T-shirt','Green Sweatshirt'):
        qualify(client,ids[name],pattern='plain',material=['cotton'],neckline='v-neck')
    return ids


def test_alternative_inherits_conditions_without_reinterpreting(attribute_api,monkeypatch):
    client,_=attribute_api;qualifying_wardrobe(client)
    response,root=submit(client);assert response.status_code==201,root
    step=root['scoring_display']['refinement']['next_action'];pipeline=assistant_service().attribute_pipeline
    monkeypatch.setattr(pipeline,'interpret',lambda *a,**k:pytest.fail('Alternative invoked NLP'))
    response,child=submit(client,root['request_text'],step['submission_key'],action=step['refinement'])
    assert response.status_code==201,child
    assert child['scoring_display']['refinement']['ordinal']==1
    assert child['scoring_display']['refinement']['root_R']==root['scoring_display']['refinement']['root_R']
    assert child['provenance']['attribute_selection']['intent']==root['provenance']['attribute_selection']['intent']
    assert child['provenance']['refinement']['attribute_scope_sha256']==root['provenance']['refinement']['attribute_scope_sha256']
    root_base=tuple(i['garment_id'] for i in root['items'] if i['garment_role']!='outerwear')
    child_base=tuple(i['garment_id'] for i in child['items'] if i['garment_role']!='outerwear')
    assert root_base!=child_base
    response,replay=submit(client,root['request_text'],step['submission_key'],action=step['refinement'])
    assert response.status_code==200 and replay['id']==child['id'] and replay['replayed']


def test_cross_wearer_parent_and_submission_reject_before_interpretation(attribute_api,monkeypatch):
    client,_=attribute_api;a,b=wearers(client);qualifying_wardrobe(client)
    key=uuid.uuid4().hex;response,root=submit(client,key=key,wearer=a);assert response.status_code==201,root
    pipeline=assistant_service().attribute_pipeline
    monkeypatch.setattr(pipeline,'interpret',lambda *a,**k:pytest.fail('Cross-wearer action interpreted'))
    client.headers['X-Wardrobe-Profile-Id']=b
    assert submit(client,key=key,wearer=b)[0].status_code==409
    step=root['scoring_display']['refinement']['next_action']
    response,result=submit(client,root['request_text'],step['submission_key'],action=step['refinement'],wearer=b)
    assert response.status_code==409 and result['outcome']=='IdempotencyConflict',result


def test_changed_description_requires_new_root_but_receipt_stays_immutable(attribute_api):
    client,_=attribute_api;ids=qualifying_wardrobe(client)
    key=uuid.uuid4().hex;response,root=submit(client,key=key);assert response.status_code==201,root
    qualify(client,ids['Green Sweatshirt'],material=['linen'])
    step=root['scoring_display']['refinement']['next_action']
    response,result=submit(client,root['request_text'],step['submission_key'],action=step['refinement'])
    assert response.status_code==409 and result['outcome']=='RefinementScopeChanged',result
    response,replay=submit(client,key=key)
    assert response.status_code==200 and replay['id']==root['id'] and replay['attribute_display']==root['attribute_display']


def test_archive_preserves_completed_b1_history_and_blocks_new_actions(attribute_api):
    client,_=attribute_api;a,b=wearers(client);qualifying_wardrobe(client)
    key=uuid.uuid4().hex;response,root=submit(client,key=key,wearer=a);assert response.status_code==201,root
    assert client.post('/api/v1/account/wardrobe-profiles/'+a+'/archive').status_code==200
    response,replay=submit(client,key=key,wearer=a)
    assert response.status_code==200 and replay['id']==root['id'] and replay['intended_wearer']==root['intended_wearer']
    assert submit(client,wearer=a)[0].status_code==409
    history=client.get('/api/v1/chats/'+root['chat_id']+'?view=historical&wearer_profile_id='+a)
    assert history.status_code==200,history.text
    assert history.json()['recommendation']['attribute_display']==root['attribute_display']


@pytest.mark.parametrize('stage',['attribute_revalidated','revalidated','chat','recommendation','item','snapshot','metadata','submission','before_commit'])
def test_attribute_persistence_fault_is_atomic(attribute_api,monkeypatch,stage):
    client,_=attribute_api;qualifying_wardrobe(client)
    with db.connection() as conn:
        before={table:conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('recommendations','nlp_chats','recommendation_items','recommendation_item_snapshots','recommendation_metadata','recommendation_submissions')}
    def fail(actual,conn):
        if actual==stage:raise RuntimeError('synthetic B1 transaction fault')
    monkeypatch.setattr(assistant_service().repository,'checkpoint',fail)
    response,result=submit(client)
    assert response.status_code==503 and result['outcome']=='PersistenceFailure',result
    with db.connection() as conn:
        after={table:conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in before}
    assert after==before


def test_stored_corruption_is_visible_and_never_replaced(attribute_api,monkeypatch):
    client,_=attribute_api;qualifying_wardrobe(client)
    key=uuid.uuid4().hex;response,root=submit(client,key=key);assert response.status_code==201,root
    with db.connection() as conn:
        original=conn.execute('SELECT provenance_json FROM recommendation_metadata WHERE recommendation_id=?',(root['id'],)).fetchone()[0]
        data=json.loads(original);data['attribute_selection']['intent']['conditions']['groups'][0]['conditions'][0]['values']=['floral']
        bad=json.dumps(data);conn.execute('UPDATE recommendation_metadata SET provenance_json=? WHERE recommendation_id=?',(bad,root['id']))
        count=conn.execute('SELECT COUNT(*) FROM recommendations').fetchone()[0]
    monkeypatch.setattr(assistant_service().attribute_pipeline,'interpret',lambda *a,**k:pytest.fail('Corrupt receipt reranked'))
    response,result=submit(client,key=key)
    assert response.status_code==503 and result['outcome']=='PersistenceFailure',result
    with db.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM recommendations').fetchone()[0]==count
        assert conn.execute('SELECT provenance_json FROM recommendation_metadata WHERE recommendation_id=?',(root['id'],)).fetchone()[0]==bad


def test_typed_alternative_inherits_exact_input_and_changed_input_conflicts(attribute_api):
    from tests.test_attribute_conditions import request
    client,_=attribute_api;qualifying_wardrobe(client);typed=request()
    text="I'm going shopping.";response,root=submit(client,text,typed=typed);assert response.status_code==201,root
    step=root['scoring_display']['refinement']['next_action']
    response,wrong=submit(client,text,step['submission_key'],typed=request(values=['linen']),action=step['refinement'])
    assert response.status_code==409 and wrong['outcome']=='IdempotencyConflict',wrong
    response,child=submit(client,text,step['submission_key'],typed=typed,action=step['refinement'])
    assert response.status_code==201 and child['provenance']['attribute_selection']['intent']['typed_input']==typed,child
    assert child['scoring_display']['refinement']['root_R']==root['scoring_display']['refinement']['root_R']


def test_concurrent_b1_same_parent_writes_one_child_and_replays(attribute_api,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app.application.recommendation.wearer_identity import resolve_wearer
    client,_=attribute_api;qualifying_wardrobe(client);_,root=submit(client)
    service=assistant_service();repository=service.repository;original=repository.persist_assistant
    barrier=Barrier(2)
    def simultaneous(command):barrier.wait(timeout=20);return original(command)
    step=root['scoring_display']['refinement']['next_action'];wearer=resolve_wearer(root['user_id'],root['profile_id'])
    monkeypatch.setattr(repository,'persist_assistant',simultaneous)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(service.recommend,root['user_id'],step['submission_key'],root['request_text'],step['refinement'],wearer=wearer) for _ in range(2)]
        results=[f.result(timeout=30) for f in futures]
    assert all(r['status']=='Selected' for r in results),results
    assert {r['replayed'] for r in results}=={False,True}
    assert results[0]['id']==results[1]['id']
    with db.connection() as conn:assert conn.execute('SELECT COUNT(*) FROM recommendations').fetchone()[0]==2


@pytest.mark.parametrize('name',['Blue T-shirt','Navy Dress'])
def test_locked_paired_collection_detects_selected_or_competitor_description_race(attribute_api,monkeypatch,name):
    client,_=attribute_api;ids=qualifying_wardrobe(client)
    repository=assistant_service().repository;original=repository.persist_assistant
    def changed(command):
        qualify(client,ids[name],material=['linen'])
        return original(command)
    monkeypatch.setattr(repository,'persist_assistant',changed)
    response,result=submit(client)
    assert response.status_code==409 and result['outcome'] in ('WardrobeChanged','RefinementScopeChanged'),result
    with db.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM recommendations').fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM recommendation_submissions').fetchone()[0]==0


def test_shared_b1_conditions_preserve_independent_wearer_preference_arithmetic(attribute_api):
    client,_=attribute_api;a,b=wearers(client);ids=qualifying_wardrobe(client)
    assert client.patch('/api/v1/wardrobe/garments/'+ids['Beige Shorts'],json={'primary_colour':'green'}).status_code==200
    for profile,colour in ((a,'blue'),(b,'green')):
        client.headers['X-Wardrobe-Profile-Id']=profile
        assert client.put('/api/v1/account/preferences/colours',json={'preference_value':{'values':[colour]},'weight':1}).status_code==200
    results=[]
    for profile in (a,b):
        client.headers['X-Wardrobe-Profile-Id']=profile
        response,result=submit(client,wearer=profile);assert response.status_code==201,result
        assert result['scoring_display']['total']=={'numerator':'1','denominator':'1'}
        results.append(result)
    assert [i['name'] for i in results[0]['items']]==['Blue T-shirt','Blue Jeans']
    assert [i['name'] for i in results[1]['items']]==['Green Sweatshirt','Beige Shorts']
    assert results[0]['provenance']['attribute_selection']['strict_snapshot_sha256']==results[1]['provenance']['attribute_selection']['strict_snapshot_sha256']


def test_original_style_history_privacy_and_rollback_assertions_with_captured_wearer(lifecycle,monkeypatch):
    """Run the unchanged historical assertions under the required Phase A context.

    The old direct fixture omits wearer at its visualisation call and already
    fails on the frozen Phase A+B0 baseline. Its source/expectations stay intact.
    """
    from tests.test_forward_style_semantics import test_history_unchanged_owner_isolation_and_atomic_rollback as original_assertions
    from app.application.recommendation.wearer_identity import resolve_wearer
    from app.application.wardrobe.profile_service import profile_scope
    from app.application.visualisation import outfit_visualisation_service as visualisation
    response=lifecycle[0].get('/api/v1/account/wardrobe-profiles')
    assert response.status_code==200
    wearer=resolve_wearer('style-owner',response.json()[0]['id'])
    original_create=visualisation.create_visualisation;calls=[]
    def captured_create(owner,*args,**kwargs):
        assert owner=='style-owner' and 'profile_id' not in kwargs
        calls.append(wearer.profile_id)
        return original_create(owner,*args,profile_id=wearer.profile_id,**kwargs)
    monkeypatch.setattr(visualisation,'create_visualisation',captured_create)
    with profile_scope(wearer.profile_id):original_assertions(lifecycle)
    assert calls==[wearer.profile_id]
