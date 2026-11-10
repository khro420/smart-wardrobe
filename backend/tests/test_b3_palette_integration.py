"""Actual authenticated disposable API: explicit C2, exact replay and history."""
import uuid,json
import pytest
from tests.test_p2_preference_integration import p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,wardrobe,save
from tests.test_attribute_persistence import qualify
from app.application.ports.assistant_runtime import assistant_service
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.infrastructure.persistence import postgresql_repository as db
from app.application.recommendation.palette_compatibility_policy import ENVIRONMENT_KEY
from app.domain.value_objects.palette_compatibility import PROFILE,PROFILES

@pytest.fixture
def palette_api(p2_api,monkeypatch):
    monkeypatch.setenv(ENVIRONMENT_KEY,PROFILE);configure_local_workflow()
    return p2_api

def submit(client,wearer,text="I'm going shopping.",key=None,p2=False,refinement=None,typed=None,profile=PROFILE):
    body={'request_text':text,'submission_key':key or uuid.uuid4().hex,'wearer_profile_id':wearer}
    if profile is not None:body['compatibility_profile']=profile
    if p2:body['preference_profile']='attribute_preference_decision_v2'
    if refinement is not None:body['refinement']=refinement
    if typed is not None:body['attribute_conditions']=typed
    reply=client.post('/api/v1/recommendations?pipeline=integrated',json=body)
    return reply,reply.json()

def populate(client):
    ids=wardrobe(client)
    for name,gid in ids.items():
        colour='#ff0000' if name=='Green Sweatshirt' else '#0000ff'
        qualify(client,gid,colour_palette=[{'hex':colour,'coverage':'1'}])
    return ids

@pytest.mark.parametrize('engine',['compact_exhaustive','reference'])
@pytest.mark.parametrize('p2',[False,True])
@pytest.mark.parametrize('text',["I'm going shopping.",'Recommend an outfit.'])
def test_complete_API_score_mode_and_exact_replay(palette_api,engine,p2,text,monkeypatch):
    client,wearer=palette_api;populate(client);service=assistant_service();service.execution_engine=engine
    key=uuid.uuid4().hex;reply,value=submit(client,wearer,text,key,p2)
    assert reply.status_code==201,value
    assert value['score_metadata']['profile_name']==PROFILES[p2,text!="Recommend an outfit."]
    assert value['scoring_display']['kind']=='PaletteCompatibility'
    assert value['provenance']['palette_compatibility']['wearer_id']==wearer
    assert value['scoring_display']['palette']['contribution']=={'numerator':'1','denominator':'1'}
    service.compatibility_policy=None;service.attribute_pipeline=None
    monkeypatch.setattr(service.interpreter,'interpret',lambda *a:pytest.fail('Completed C2 replay reinterpreted'))
    reply,replay=submit(client,wearer,text,key,p2)
    assert reply.status_code==200 and replay['id']==value['id'] and replay['score_metadata']==value['score_metadata'],replay
    assert submit(client,wearer,text,key,p2,profile=None)[0].status_code==409

@pytest.mark.parametrize('engine',['compact_exhaustive','reference'])
@pytest.mark.parametrize('p2',[False,True])
def test_alternative_has_bound_C2_mode_Seen_and_historical_read(palette_api,engine,p2):
    client,wearer=palette_api;populate(client);assistant_service().execution_engine=engine
    reply,root=submit(client,wearer,p2=p2);assert reply.status_code==201,root
    action=root['scoring_display']['refinement']['next_action'];assert action['compatibility_profile']==PROFILE
    reply,child=submit(client,wearer,root['request_text'],action['submission_key'],p2,action['refinement'])
    assert reply.status_code==201,child
    assert child['items']!=root['items'] and child['provenance']['refinement']['request_fingerprint_version']==6
    reply,replay=submit(client,wearer,root['request_text'],action['submission_key'],p2,action['refinement'])
    assert reply.status_code==200 and replay['id']==child['id'],replay
    historical=client.get('/api/v1/chats/'+child['chat_id']);assert historical.status_code==200,historical.text
    assert historical.json()['recommendation']['scoring_display']==child['scoring_display']

def test_default_C1_and_disabled_C2_are_explicit(palette_api):
    client,wearer=palette_api;populate(client)
    capability=client.get('/api/v1/recommendations/capabilities').json()['palette_compatibility']
    assert capability['enabled'] and capability['default']=='c1'
    reply,old=submit(client,wearer,profile=None);assert reply.status_code==201,old
    assert 'palette_compatibility' not in old['provenance']
    assistant_service().compatibility_policy=None
    reply,value=submit(client,wearer);assert reply.status_code==422 and value['outcome']=='CompatibilityUnavailable',value
    body={'request_text':"I'm going shopping.",'submission_key':uuid.uuid4().hex,'wearer_profile_id':wearer,'compatibility_profile':None}
    assert client.post('/api/v1/recommendations',json=body).status_code==422
