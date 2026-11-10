"""P2 roots and every child bind captured settings independently of the old R floor."""
import json,uuid
import pytest
from tests.test_p2_preference_integration import p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,submit_p2,save,pattern,wardrobe,qualify
from app.application.ports.assistant_runtime import assistant_service
from app.infrastructure.persistence import postgresql_repository as db
from app.domain.value_objects.attribute_preferences import PROFILE


@pytest.mark.parametrize('typed_mode',[False,True])
@pytest.mark.parametrize('engine',['compact_exhaustive','reference'])
def test_P2_chain_exact_replay_no_NLP_same_scope_and_original_floor(p2_api,monkeypatch,engine,typed_mode):
    client,a=p2_api;ids=wardrobe(client);assistant_service().execution_engine=engine
    if typed_mode:
        for name in ('Blue T-shirt','Green Sweatshirt'):qualify(client,ids[name],pattern='plain',material=['cotton'],neckline='v-neck')
    save(client,a,pattern())
    text="I'm going shopping and want a plain cotton v-neck top." if typed_mode else "I'm going shopping."
    response,root=submit_p2(client,a,text);assert response.status_code==201,root
    assert root['provenance']['refinement']['request_fingerprint_version']==5
    step=root['scoring_display']['refinement']['next_action']
    monkeypatch.setattr(assistant_service().attribute_pipeline,'interpret',lambda *args:pytest.fail('Alternative invoked NLP'))
    response,child=submit_p2(client,a,text,step['submission_key'],step['refinement'])
    assert response.status_code==201,child
    assert child['scoring_display']['kind']=='AttributePreference',child['scoring_display']
    assert child['provenance']['attribute_preference']['snapshot']==root['provenance']['attribute_preference']['snapshot']
    assert child['provenance']['refinement']['root_R']==root['provenance']['refinement']['root_R']
    assert tuple(i['garment_id'] for i in child['items'] if i['garment_role']!='outerwear')!=tuple(i['garment_id'] for i in root['items'] if i['garment_role']!='outerwear')
    response,replay=submit_p2(client,a,text,step['submission_key'],step['refinement'])
    assert response.status_code==200 and replay['id']==child['id'],replay
    history=client.get('/api/v1/chats/'+child['chat_id']);assert history.status_code==200,history.text
    assert history.json()['recommendation']['scoring_display']==child['scoring_display']


def test_changed_preferences_require_new_root_completed_replay_retains_snapshot(p2_api):
    client,a=p2_api;wardrobe(client);save(client,a,pattern());key=uuid.uuid4().hex
    _,root=submit_p2(client,a,key=key);step=root['scoring_display']['refinement']['next_action']
    save(client,a,pattern('stripe'))
    response,result=submit_p2(client,a,root['request_text'],step['submission_key'],step['refinement'])
    assert response.status_code==409 and result['outcome']=='RefinementScopeChanged',result
    response,replay=submit_p2(client,a,key=key)
    assert response.status_code==200 and replay['score_metadata']==root['score_metadata'] and replay['provenance']['attribute_preference']==root['provenance']['attribute_preference']


def test_P1_P2_parent_modes_and_cross_wearer_never_mix(p2_api,monkeypatch):
    client,a=p2_api;wardrobe(client);b=client.post('/api/v1/account/wardrobe-profiles',json={'name':'B'}).json()['id']
    _,root=submit_p2(client,a);step=root['scoring_display']['refinement']['next_action']
    monkeypatch.setattr(assistant_service().attribute_pipeline,'interpret',lambda *args:pytest.fail('Mismatched lineage interpreted'))
    assert submit_p2(client,a,root['request_text'],step['submission_key'],step['refinement'],profile=None)[0].status_code==409
    assert submit_p2(client,b,root['request_text'],step['submission_key'],step['refinement'])[0].status_code==409


@pytest.mark.parametrize('stage',['preference_revalidated','revalidated','chat','recommendation','item','snapshot','metadata','submission','before_commit'])
def test_P2_write_faults_rollback_every_stage(p2_api,monkeypatch,stage):
    client,a=p2_api;wardrobe(client);save(client,a,pattern())
    def fail(actual,conn):
        if actual==stage:raise RuntimeError('Synthetic P2 transaction fault')
    monkeypatch.setattr(assistant_service().repository,'checkpoint',fail)
    response,result=submit_p2(client,a)
    assert response.status_code==503 and result['outcome']=='PersistenceFailure',result
    with db.connection() as conn:
        for table in ('recommendations','nlp_chats','recommendation_items','recommendation_item_snapshots','recommendation_metadata','recommendation_submissions'):
            assert conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0


def test_concurrent_same_parent_commits_one_P2_child(p2_api,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app.application.recommendation.wearer_identity import resolve_wearer
    client,a=p2_api;wardrobe(client);save(client,a,pattern());_,root=submit_p2(client,a)
    service=assistant_service();original=service.repository.persist_assistant;barrier=Barrier(2)
    def simultaneous(command):barrier.wait(timeout=20);return original(command)
    monkeypatch.setattr(service.repository,'persist_assistant',simultaneous)
    step=root['scoring_display']['refinement']['next_action'];wearer=resolve_wearer(root['user_id'],a)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(service.recommend,root['user_id'],step['submission_key'],root['request_text'],step['refinement'],wearer=wearer,preference_profile=PROFILE) for _ in range(2)]
        results=[f.result(timeout=30) for f in futures]
    assert all(r['status']=='Selected' for r in results),results
    assert {r['replayed'] for r in results}=={False,True}
    assert results[0]['id']==results[1]['id']
    with db.connection() as conn:assert conn.execute('SELECT COUNT(*) FROM recommendations').fetchone()[0]==2


def test_explicit_initial_exclusions_bind_P2_request_and_children(p2_api):
    client,a=p2_api;wardrobe(client)
    initial={'version':'assistant-refinement-request-1.0.0','kind':'initial','excluded_categories':['trousers']}
    response,root=submit_p2(client,a,refinement=initial);assert response.status_code==201,root
    assert all(i['category']!='trousers' for i in root['items'])
    step=root['scoring_display']['refinement']['next_action']
    response,child=submit_p2(client,a,root['request_text'],step['submission_key'],step['refinement'])
    assert response.status_code==201,child
    assert all(i['category']!='trousers' for i in child['items'])


def test_archive_and_current_loader_shutdown_preserve_P2_history(p2_api,monkeypatch):
    from app.application.recommendation.attribute_preference_policy import AttributePreferencePolicy
    from app.application.recommendation.preference_normalizer import PreferenceNormalizer
    from app.application.wardrobe.description_policy import DescriptionPolicy
    client,a=p2_api;wardrobe(client);save(client,a,pattern());key=uuid.uuid4().hex;_,root=submit_p2(client,a,key=key)
    assert client.post('/api/v1/account/wardrobe-profiles',json={'name':'Second'}).status_code==201
    assert client.post('/api/v1/account/wardrobe-profiles/'+a+'/archive').status_code==200
    def unavailable(*args,**kwargs):pytest.fail('Historical read invoked active preference/description loader')
    monkeypatch.setattr(AttributePreferencePolicy,'load',unavailable)
    monkeypatch.setattr(PreferenceNormalizer,'normalize',unavailable)
    monkeypatch.setattr(DescriptionPolicy,'load',unavailable)
    assistant_service().preference_policy=None
    response,replay=submit_p2(client,a,key=key)
    assert response.status_code==200 and replay['score_metadata']==root['score_metadata'],replay
    history=client.get('/api/v1/chats/'+root['chat_id']+'?view=historical&wearer_profile_id='+a)
    assert history.status_code==200,history.text
    assert history.json()['recommendation']['scoring_display']['kind']=='AttributePreference'
    assert submit_p2(client,a)[0].status_code==409
