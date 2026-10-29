"""Only disposable authenticated app.main data; owner manual runtime is never used."""
from dataclasses import replace
from fractions import Fraction as F
import json,uuid
import pytest
from tests.test_context_relevance_integration import relative_api,automatic_api,everyday_api,release,lifecycle,wardrobe
from tests.test_automatic_garment_finalization import upload,garments
from tests.test_release_configuration import submit
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.ports.assistant_runtime import assistant_service
from app.application.recommendation.context_bundle import ARCHIVES,ACTIVE_WAVE
from app.infrastructure.persistence import postgresql_repository as db
from tests.test_context_expansion_equivalence import TEXTS

@pytest.fixture
def expanded_api(relative_api,monkeypatch):
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_BUNDLE','context_18_v1')
    configure_local_workflow()
    return relative_api

def test_active_contexts_and_exact_persisted_outcomes(expanded_api):
    client,_=expanded_api;wardrobe(client);before=garments(client)
    caps=client.get('/api/v1/recommendations/capabilities').json()
    assert len([s for s in caps['context_support']['situations'] if s['policy_available']])==len(ARCHIVES[ACTIVE_WAVE]['scopes'])
    assert caps['context_ranking']['version']=='context-ranking-capabilities-1.1.0'
    requests={**TEXTS,
        'everyday.shopping':"I'm going shopping.",
        'everyday.academic_attendance':"I'm going to class.",
        'everyday.casual_outing':"I'm going out with friends.",
        'social.date':"I'm going on a date tonight.",
        'social.meal':"I'm meeting friends for dinner."}
    for sid,text in requests.items():
        if sid not in ARCHIVES[ACTIVE_WAVE]['targets']:continue
        response,result=submit(client,text)
        assert response.status_code==201,result
        target=ARCHIVES[ACTIVE_WAVE]['targets'][sid]
        assert [item['name'] for item in result['items']]==(['Blue T-shirt','Blue Jeans'] if target=='casual' else ['Navy Dress','Grey Jacket'])
        display=result['scoring_display']
        assert display['version']=='assistant-scoring-display-2.1.0' and display['objective']['target']==target
        assert display['total']==dict(numerator='4',denominator='5')
        assert [c['name'] for c in display['components']]==['R','C','P']
        assert result['provenance']['general_context']['situation']==sid
        assert client.get('/api/v1/chats/'+result['chat_id']).json()['recommendation']['scoring_display']==display
    assert garments(client)==before

def test_normal_add_requires_no_confirmation_then_all_new_contexts(expanded_api):
    client,_=expanded_api;job=upload(client)
    assert job['status']=='completed' and len(garments(client))==1
    assert not garments(client)[0]['contextual_edit']['review_current']
    for sid,text in TEXTS.items():
        if sid not in ARCHIVES[ACTIVE_WAVE]['targets']:continue
        response,result=submit(client,text);assert response.status_code==201,result
        assert result['scoring_display']['objective']['situation']==sid

@pytest.mark.parametrize('stage',['chat','recommendation','item','snapshot','metadata','submission','before_commit'])
def test_atomic_fault_rollback_and_same_key_recovery(expanded_api,monkeypatch,stage):
    client,_=expanded_api;upload(client);repository=assistant_service().repository;key=uuid.uuid4().hex
    with monkeypatch.context() as local:
        def fail(where,conn):
            if where==stage:raise RuntimeError('Synthetic scoped write fault')
        local.setattr(repository,'checkpoint',fail)
        assert submit(client,TEXTS['academic.library_study'],key)[0].status_code==503
    with db.connection() as conn:
        for table in ('nlp_chats','recommendations','recommendation_items','recommendation_metadata','recommendation_submissions'):assert conn.execute('SELECT count(*) FROM '+table).fetchone()[0]==0
    assert submit(client,TEXTS['academic.library_study'],key)[0].status_code==201
    assert submit(client,TEXTS['academic.library_study'],key)[1]['replayed']

@pytest.mark.parametrize('sql',["UPDATE processing_jobs SET status='failed'","UPDATE processing_items SET review_status='pending'","UPDATE garments SET status='archived'","UPDATE garments SET status='unavailable'"])
def test_strict_joins(expanded_api,sql):
    client,_=expanded_api;upload(client)
    with db.connection() as conn:conn.execute(sql)
    assert submit(client,TEXTS['academic.library_study'])[1]['outcome']=='NoEligibleGarments'

def test_new_clarification_has_specific_reason(expanded_api):
    client,_=expanded_api
    response,result=submit(client,'I have a meeting.')
    assert response.status_code==422 and result['context_reason']=='context_clarification_required'

def test_generic_request_retains_legacy_scoring_in_expanded_bundle(expanded_api):
    client,_=expanded_api;upload(client)
    response,result=submit(client,'Suggest an outfit')
    assert response.status_code==201,result
    assert result['score_metadata']['profile_name']=='experimental_compatibility_decision_v1'
    assert result['scoring_display']['version']=='assistant-scoring-display-1.0.0'
    assert 'context_relevance' not in result['provenance']

def test_expanded_selected_snapshot_change_rejects_then_same_key_recovers(expanded_api,monkeypatch):
    client,_=expanded_api;upload(client);gid=garments(client)[0]['id']
    repository=assistant_service().repository;original=repository.persist_assistant
    key=uuid.uuid4().hex;text=TEXTS['academic.library_study']
    def changed(command):
        response=client.patch('/api/v1/wardrobe/garments/'+gid,json={'name':'Changed disposable snapshot'})
        assert response.status_code==200
        return original(command)
    with monkeypatch.context() as local:
        local.setattr(repository,'persist_assistant',changed)
        response,result=submit(client,text,key)
        assert response.status_code==409 and result['outcome']=='WardrobeChanged'
    with db.connection() as conn:
        for table in ('nlp_chats','recommendations','recommendation_submissions'):assert conn.execute('SELECT count(*) FROM '+table).fetchone()[0]==0
    assert submit(client,text,key)[0].status_code==201
