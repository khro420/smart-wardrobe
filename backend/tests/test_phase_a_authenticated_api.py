"""Authenticated Phase A ownership, exact intent and capacity boundaries."""
import uuid
import pytest
from tests.test_recommendation_refinement_integration import (
    refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,wardrobe,
)
from tests.test_phase_a_profile_archive import wearers,owner
from tests.test_phase_a_wearer_identity import request
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.security import issue_access_token


def test_foreign_account_wearer_parent_history_and_copied_logout(refinement_api):
    client,_=refinement_api;a,b=wearers(client);wardrobe(client)
    response,root=request(client,a);assert response.status_code==201,root
    original=client.headers['Authorization']
    client.post('/api/v1/account/register',json={'email':'foreign-phase-a@example.test','password':'Foreign-password-123','password_confirmation':'Foreign-password-123','display_name':'Other'})
    foreign=client.post('/api/v1/account/login',json={'email':'foreign-phase-a@example.test','password':'Foreign-password-123'}).json()['access_token']
    client.headers['Authorization']='Bearer '+foreign;client.headers.pop('X-Wardrobe-Profile-Id',None)
    assert request(client,a)[0].status_code==404
    assert client.post('/api/v1/account/wardrobe-profiles/'+a+'/archive').status_code==404
    assert client.get('/api/v1/chats/'+root['chat_id']+'?view=historical&wearer_profile_id='+a).status_code==404
    next_step=root['scoring_display']['refinement']['next_action']
    assert request(client,None,next_step['submission_key'],next_step['refinement'])[0].status_code==404
    client.headers['Authorization']=original;client.headers['X-Wardrobe-Profile-Id']=a
    assert client.post('/api/v1/account/logout').status_code==204
    assert request(client,a)[0].status_code==401
    assert client.get('/api/v1/chats/'+root['chat_id']+'?view=historical&wearer_profile_id='+a).status_code==401
    assert client.post('/api/v1/account/wardrobe-profiles/'+a+'/archive').status_code==401


@pytest.mark.parametrize('payload',[{'wearer_profile_id':None},{'wearer_profile_id':'wrong'},{'wearer_profile_id':'00000000-0000-4000-8000-00000000000A'},{'wearer_profile_id':15},{'owner':'forged'}])
def test_strict_wearer_shape(refinement_api,payload):
    client,_=refinement_api;wearers(client)
    response=client.post('/api/v1/recommendations?pipeline=integrated',json={'request_text':"I'm going shopping.",'submission_key':uuid.uuid4().hex,**payload})
    assert response.status_code==422


def test_same_fact_shared_order_and_independent_colour_totals(refinement_api):
    client,_=refinement_api;a,b=wearers(client);ids=wardrobe(client)
    _,first=request(client,a)
    client.headers['X-Wardrobe-Profile-Id']=b
    _,same=request(client,b)
    assert first['scoring_display']['total']==same['scoring_display']['total']=={'numerator':'4','denominator':'5'}
    assert [i['garment_id'] for i in first['items']]==[i['garment_id'] for i in same['items']]
    for profile,colour in ((a,'blue'),(b,'green')):
        client.headers['X-Wardrobe-Profile-Id']=profile
        assert client.put('/api/v1/account/preferences/colours',json={'preference_value':{'values':[colour]},'weight':1}).status_code==200
    client.headers['X-Wardrobe-Profile-Id']=a;response,blue=request(client,a);assert response.status_code==201,blue
    client.headers['X-Wardrobe-Profile-Id']=b;response,green=request(client,b);assert response.status_code==201,green
    assert [i['name'] for i in blue['items']]==['Blue T-shirt','Blue Jeans']
    assert blue['scoring_display']['total']=={'numerator':'1','denominator':'1'}
    # Both casual lowers have C=1/2 with this green upper and any-member P=1.
    # Their exact (T,R,C,P) keys tie; independently bind the final ID tie-break
    # to the fixture IDs rather than assuming a name ordering.
    lower=min(('Blue Jeans','Beige Shorts'),key=lambda name:ids[name])
    assert [i['name'] for i in green['items']]==['Green Sweatshirt',lower]
    assert green['scoring_display']['total']=={'numerator':'9','denominator':'10'}


def test_irrelevant_preference_change_does_not_invalidate_wearer(refinement_api,monkeypatch):
    client,_=refinement_api;a,b=wearers(client);wardrobe(client)
    from app.application.ports.assistant_runtime import assistant_service
    service=assistant_service();persist=service.repository.persist_assistant
    def change_other(command):
        with db.connection() as conn:
            conn.execute("INSERT INTO user_preferences(id,user_id,profile_id,preference_type,preference_value_json,weight,source,is_active,created_at,updated_at) VALUES(?,?,?,'colours','{\"values\":[\"green\"]}',1,'test',1,'now','now')",(str(uuid.uuid4()),command.user_id,b))
        return persist(command)
    monkeypatch.setattr(service.repository,'persist_assistant',change_other)
    response,result=request(client,a);assert response.status_code==201,result
