"""New profile through real disposable API/storage, not private manual data."""
import json
import uuid
from fractions import Fraction as F
import pytest
from tests.test_automatic_garment_finalization import automatic_api,upload,garments
from tests.test_everyday_context import everyday_api
from tests.test_release_configuration import release,submit
from tests.test_forward_style_semantics import lifecycle
from tests.test_automatic_admission_integration import legacy
from tests.test_context_relevance_ranking import FACTS,TEXTS
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.ports.assistant_runtime import assistant_service
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
from app.application.recommendation.decision_score_codec import score_from_json,score_to_json


@pytest.fixture
def relative_api(automatic_api,monkeypatch):
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_RANKING_PROFILE','context_relevance_decision_v1')
    configure_local_workflow()
    return automatic_api


def wardrobe(client):
    ids={}
    for _,name,category,colour,style in FACTS:
        gid=legacy(client,style,category)
        assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'name':name,'primary_colour':colour}).status_code==200
        ids[name]=gid
    return ids


def test_five_api_requests_exact_display_no_review_and_immutable_replay(relative_api,monkeypatch):
    client,_=relative_api;ids=wardrobe(client)
    before=garments(client)
    caps=client.get('/api/v1/recommendations/capabilities').json()
    assert caps['context_ranking']['version']=='context-ranking-capabilities-1.0.0'
    assert len(caps['context_ranking']['objectives'])==5
    first=None
    for index,text in enumerate(TEXTS):
        key=uuid.uuid4().hex
        response,result=submit(client,text,key)
        assert response.status_code==201,result
        names=[i['name'] for i in result['items']]
        assert names==(['Blue T-shirt','Blue Jeans'] if index<3 else ['Navy Dress','Grey Jacket'])
        score=score_from_json(json.dumps(result['score_metadata']))
        assert score_from_json(score_to_json(score))==score
        assert (score.request_match.contribution,score.compatibility.contribution,score.preference.contribution,score.total)==(F(1),F(1),F(0),F(4,5))
        view=result['scoring_display']
        assert view['version']=='assistant-scoring-display-2.0.0'
        assert view['total']=={'numerator':'4','denominator':'5'}
        assert [c['name'] for c in view['components']]==['R','C','P']
        assert view['coverage']['global_optimum_certified']
        assert result['provenance']['context_relevance']['selected_members'][0]['origin']=='unknown'
        if first is None:first=(key,text,result)
    assert garments(client)==before
    # Old-key lookup precedes selection/interpretation, even after mode changes.
    assistant_service().context_ranking_profile='disabled'
    key,text,original=first
    response,replay=submit(client,text,key)
    assert response.status_code==200 and replay['replayed']
    assert replay['id']==original['id'] and replay['score_metadata']==original['score_metadata']
    assert replay['provenance']==original['provenance'] and replay['scoring_display']==original['scoring_display']
    historical=client.get('/api/v1/chats/'+original['chat_id']).json()['recommendation']
    assert historical['score_metadata']==original['score_metadata']
    assert historical['scoring_display']==original['scoring_display']


def test_automatic_add_normal_workflow_and_disclosed_no_objective_fallback(relative_api):
    client,_=relative_api
    job=upload(client)
    assert job['status']=='completed' and len(garments(client))==1
    assert not garments(client)[0]['contextual_edit']['review_current']
    response,result=submit(client,"I'm going shopping.")
    assert response.status_code==201,result
    assert result['scoring_display']['selection_mode']=='best_evidenced_with_coverage_v1'
    response,result=submit(client,"I'm going shopping; the dress code is casual.")
    assert response.status_code==201,result
    assert result['scoring_display']['selection_mode']=='baseline_disclosed_v1'
    assert result['scoring_display']['fallback_reason']=='objective_unavailable'
    assert result['provenance']['context_relevance']['relative_R'] is None
    assert result['score_metadata']['profile_name']=='experimental_compatibility_decision_v1'


def test_explicit_style_preference_deny_and_unsupported_code(relative_api):
    client,_=relative_api;ids=wardrobe(client)
    _,result=submit(client,'Suggest an outfit for dinner with casual style')
    assert [i['name'] for i in result['items']]==['Blue T-shirt','Blue Jeans']
    assert result['scoring_display']['objective']['authority']=='explicit_user_style'
    assert client.put('/api/v1/account/preferences/colours',json={'preference_value':{'values':['green']},'weight':1}).status_code==200
    _,result=submit(client,TEXTS[0])
    expected_lower=min(('Blue Jeans','Beige Shorts'),key=lambda name:ids[name])
    assert [i['name'] for i in result['items']]==['Green Sweatshirt',expected_lower]
    assert result['scoring_display']['total']=={'numerator':'9','denominator':'10'}
    response,result=submit(client,"I'm going shopping; the dress code is formal.")
    assert response.status_code==422 and result['outcome']=='PolicyUnavailable'


@pytest.mark.parametrize('stage',['chat','recommendation','item','snapshot','metadata','submission','before_commit'])
def test_relative_atomic_write_failures_leave_no_partial_chat_or_score(relative_api,monkeypatch,stage):
    client,_=relative_api;upload(client)
    def fail(where,conn):
        if where==stage:raise RuntimeError('synthetic write failure')
    monkeypatch.setattr(assistant_service().repository,'checkpoint',fail)
    response,result=submit(client,TEXTS[0])
    assert response.status_code==503 and result['outcome']=='PersistenceFailure'
    with db.connection() as conn:
        for table in ('recommendations','nlp_chats','recommendation_submissions','recommendation_items','recommendation_metadata'):
            assert conn.execute('SELECT count(*) FROM '+table).fetchone()[0]==0


def test_selected_snapshot_change_rejected_and_same_key_can_retry(relative_api,monkeypatch):
    client,_=relative_api;upload(client);gid=garments(client)[0]['id']
    repository=assistant_service().repository;original=repository.persist_assistant
    def changed(command):
        assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'name':'Changed synthetic name'}).status_code==200
        return original(command)
    key=uuid.uuid4().hex
    with monkeypatch.context() as local:
        local.setattr(repository,'persist_assistant',changed)
        response,result=submit(client,TEXTS[0],key)
        assert response.status_code==409 and result['outcome']=='WardrobeChanged'
    assert submit(client,TEXTS[0],key)[0].status_code==201


def test_forged_new_proof_rejected_before_private_write_and_replay_ignores_live_catalogue(relative_api,monkeypatch):
    from dataclasses import replace
    from app.application.recommendation.context_relevance_policy import ContextRelevancePolicy
    client,_=relative_api;upload(client)
    repository=assistant_service().repository;original=repository.persist_assistant
    def forged(command):
        provenance=json.loads(command.provenance_json)
        provenance['context_relevance']['policy_sha256']='0'*64
        return original(replace(command,provenance_json=json.dumps(provenance)))
    with monkeypatch.context() as local:
        local.setattr(repository,'persist_assistant',forged)
        assert submit(client,TEXTS[0])[1]['outcome']=='PersistenceFailure'
    with db.connection() as conn:assert conn.execute('SELECT count(*) FROM nlp_chats').fetchone()[0]==0
    key=uuid.uuid4().hex
    _,saved=submit(client,TEXTS[0],key)
    def unavailable(*args,**kwargs):raise AssertionError('Replay must not consult current catalogue')
    monkeypatch.setattr(ContextRelevancePolicy,'load',unavailable)
    _,replayed=submit(client,TEXTS[0],key)
    assert replayed['replayed'] and replayed['score_metadata']==saved['score_metadata']
    assert client.get('/api/v1/chats/'+saved['chat_id']).json()['recommendation']['score_metadata']==saved['score_metadata']


@pytest.mark.parametrize('sql',[
    "UPDATE processing_jobs SET status='failed'",
    "UPDATE processing_items SET review_status='pending'",
    "UPDATE processing_jobs SET user_id='foreign-synthetic-owner'",
    "UPDATE garments SET status='archived'",
    "UPDATE garments SET status='unavailable'",
])
def test_strict_current_eligibility_not_weakened_by_relative_profile(relative_api,sql):
    client,_=relative_api;upload(client)
    with db.connection() as conn:
        if 'foreign-synthetic-owner' in sql:
            db.ensure_user('foreign-synthetic-owner')
        conn.execute(sql)
    _,result=submit(client,TEXTS[0])
    assert result['outcome']=='NoEligibleGarments'
