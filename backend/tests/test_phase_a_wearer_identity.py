"""Intended wearer, account-wide receipts and isolated tastes via authenticated API."""
import uuid
import pytest
from tests.test_recommendation_refinement_integration import (
    refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,wardrobe,
)
from tests.test_phase_a_profile_archive import wearers,owner
from app.infrastructure.persistence import postgresql_repository as db
from app.application.ports.assistant_runtime import assistant_service


def request(client,wearer,key=None,action=None,text="I'm going shopping."):
    body={'request_text':text,'submission_key':key or uuid.uuid4().hex}
    if wearer is not None:body['wearer_profile_id']=wearer
    if action is not None:body['refinement']=action
    response=client.post('/api/v1/recommendations?pipeline=integrated',json=body)
    return response,response.json()


def test_explicit_wearer_and_account_first_receipt(refinement_api,monkeypatch):
    client,_=refinement_api;a,b=wearers(client);wardrobe(client)
    assert request(client,None)[0].status_code==422
    assert request(client,b)[0].status_code==409  # header is A
    key=uuid.uuid4().hex
    response,root=request(client,a,key);assert response.status_code==201,root
    assert root['intended_wearer']['profile_id']==a
    assert root['provenance']['refinement']['version']=='recommendation-refinement-evidence-1.1.0'
    assert root['provenance']['refinement']['request_fingerprint_version']==3
    client.headers['X-Wardrobe-Profile-Id']=b
    response,result=request(client,b,key);assert response.status_code==409,result
    client.headers['X-Wardrobe-Profile-Id']=a
    assert client.post('/api/v1/account/wardrobe-profiles/'+a+'/archive').status_code==200
    service=assistant_service();service.refinement_profile='disabled';service.context_ranking_profile='disabled'
    monkeypatch.setattr(service.interpreter,'interpret',lambda _:pytest.fail('Replay reinterpreted'))
    response,replay=request(client,a,key);assert response.status_code==200,replay
    assert replay['id']==root['id'] and replay['intended_wearer']==root['intended_wearer']
    assert replay['scoring_display']==root['scoring_display']
    assert request(client,a)[0].status_code==409


def test_empty_preferences_do_not_permit_cross_wearer_chain(refinement_api):
    client,_=refinement_api;a,b=wearers(client);wardrobe(client)
    response,root=request(client,a);assert response.status_code==201,root
    next_step=root['scoring_display']['refinement']['next_action']
    client.headers['X-Wardrobe-Profile-Id']=b
    response,result=request(client,b,next_step['submission_key'],next_step['refinement'])
    assert response.status_code==409,result
    client.headers['X-Wardrobe-Profile-Id']=a
    response,child=request(client,a,next_step['submission_key'],next_step['refinement'])
    assert response.status_code==201,child
    assert child['provenance']['refinement']['root_R']==root['provenance']['refinement']['root_R']
    response,replay=request(client,a,next_step['submission_key'],next_step['refinement'])
    assert response.status_code==200 and replay['id']==child['id']


def test_preferences_are_explicit_and_do_not_borrow(refinement_api):
    from app.application.recommendation.wearer_identity import resolve_wearer
    from app.infrastructure.persistence.active_preference_query_adapter import SqliteActivePreferenceQuery
    client,_=refinement_api;a,b=wearers(client);wardrobe(client);uid=owner(a)
    assert client.put('/api/v1/account/preferences/colours',json={'preference_value':{'values':['blue']},'weight':1}).status_code==200
    query=SqliteActivePreferenceQuery()
    with pytest.raises(ValueError):query.get_active_preferences(uid)
    assert len(query.get_active_preferences(uid,resolve_wearer(uid,a)))==1
    assert query.get_active_preferences(uid,resolve_wearer(uid,b))==()
    client.headers['X-Wardrobe-Profile-Id']=b
    assert client.put('/api/v1/account/preferences/colours',json={'preference_value':{'values':['green']},'weight':1}).status_code==200
    a_rows=query.get_active_preferences(uid,resolve_wearer(uid,a));b_rows=query.get_active_preferences(uid,resolve_wearer(uid,b))
    assert 'blue' in a_rows[0].value_json and 'green' in b_rows[0].value_json
    client.headers['X-Wardrobe-Profile-Id']=a
    response,aroot=request(client,a);assert response.status_code==201,aroot
    client.headers['X-Wardrobe-Profile-Id']=b
    response,broot=request(client,b);assert response.status_code==201,broot
    assert aroot['intended_wearer']['profile_id']==a and broot['intended_wearer']['profile_id']==b


def test_archive_racing_recommendation_commit_is_atomic(refinement_api,monkeypatch):
    from app.application.wardrobe.profile_service import archive_profile
    client,_=refinement_api;a,b=wearers(client);wardrobe(client);uid=owner(a)
    service=assistant_service();persist=service.repository.persist_assistant
    def racing(command):
        archive_profile(uid,a)
        return persist(command)
    monkeypatch.setattr(service.repository,'persist_assistant',racing)
    response,result=request(client,a);assert response.status_code==409,result
    with db.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM recommendations').fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM recommendation_submissions').fetchone()[0]==0
