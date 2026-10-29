"""Real SQLite/service/API checks; garment descriptors are synthetic test data."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from fractions import Fraction
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.application.recommendation.assistant_scoring_selection import DEFERRED, DECISION, ENVIRONMENT_KEY, AssistantScoringSelection
from app.application.recommendation.decision_score_codec import score_from_json
from app.application.recommendation.scoring_display import display_for_record
from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
from app.application.chat_history.chat_history_service import ChatHistoryService
from app.infrastructure.persistence.chat_history_query_adapter import SqliteChatHistoryQuery
from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
from app.infrastructure.security import issue_access_token
from tests.test_recommendation_persistence import store, connect
from tests.test_outfit_assistant import assistant_store, service, add_garment, count


def selected(store, profile=DECISION, repo=None):
    s=service(store,repo=repo)
    s.execution_engine='reference'  # Retain coverage of the reference decision factory.
    s.scoring_profile=profile
    return s


@pytest.mark.parametrize('profile',[DEFERRED,DECISION])
@pytest.mark.parametrize('structure',['pair','trio','dress','dress_outer'])
def test_real_persistence_all_structures_and_exact_history(assistant_store,profile,structure):
    if structure in ('pair','trio'):
        with connect(assistant_store[0]) as c: c.execute("UPDATE garments SET status='archived'")
        add_garment(assistant_store,'top','vest')
        add_garment(assistant_store,'bottom','trousers')
    if structure in ('trio','dress_outer'): add_garment(assistant_store,'outer','long_sleeve_outwear')
    text='Suggest an outfit'+(' including outerwear' if structure in ('trio','dress_outer') else '')
    result=selected(assistant_store,profile).recommend('owner','real',text)
    assert result['status']=='Selected' and result['complete']
    assert result['provenance']['scoring_profile']==profile
    assert len(result['items'])=={'pair':2,'trio':3,'dress':1,'dress_outer':2}[structure]
    view=result['scoring_display']
    assert view['kind']==('Deferred' if profile==DEFERRED else 'Decision')
    if profile==DECISION:
        score=score_from_json(json.dumps(result['score_metadata']))
        assert score.total==sum((w*x.contribution for w,x in zip(score.weights,(score.request_match,score.compatibility,score.preference))),Fraction())
        assert score.weights==(Fraction(3,5),Fraction(1,5),Fraction(1,5))
        assert view['basis']==('NoPairReference' if structure=='dress' else 'Computed')
    with connect(assistant_store[0]) as c:
        before=tuple(c.execute('SELECT * FROM recommendation_metadata').fetchone())
        c.execute("UPDATE garments SET status='archived'")
    replay=selected(assistant_store,DEFERRED if profile==DECISION else DECISION).recommend('owner','real',text)
    assert replay['replayed'] and replay['score_metadata']==result['score_metadata'] and replay['scoring_display']==view
    history=ChatHistoryService(SqliteChatHistoryQuery(assistant_store[0],cursor_secret='test')).get('owner',result['chat_id'])
    assert history['recommendation']['scoring_display']==view
    assert not history['recommendation']['items'][0]['currently_eligible']
    with connect(assistant_store[0]) as c: assert tuple(c.execute('SELECT * FROM recommendation_metadata').fetchone())==before


@pytest.mark.parametrize('colour,styles,basis,raw',[
    ('red','["sporty"]','Computed',0),
    (None,None,'FullyConventional',None),
    ('blue',None,'PartiallyConventional',None),
])
def test_zero_and_missing_evidence_are_persisted_distinctly(assistant_store,colour,styles,basis,raw):
    with connect(assistant_store[0]) as c: c.execute("UPDATE garments SET status='archived'")
    add_garment(assistant_store,'top','vest','blue','["classic"]')
    add_garment(assistant_store,'bottom','trousers',colour,styles)
    r=selected(assistant_store).recommend('owner','evidence','Suggest an outfit')
    assert r['status']=='Selected'
    assert r['compatibility_score']==raw
    assert r['scoring_display']['basis']==basis
    with connect(assistant_store[0]) as c:
        assert c.execute('SELECT compatibility_score FROM recommendations').fetchone()[0]==raw
    if raw==0: assert r['scoring_display']['raw_value']=={'numerator':0,'denominator':1}
    else: assert r['scoring_display']['raw_value'] is None


@pytest.mark.parametrize('profile',[DEFERRED,DECISION])
@pytest.mark.parametrize('text,status',[
    ('Suggest an outfit with red colours','NoMatchingCandidates'),
    ('Suggest an outfit for campus','PolicyUnavailable'),
    ('Tell me a joke','UnsupportedRequest'),
])
def test_mandatory_and_unsupported_conditions_never_write(assistant_store,profile,text,status):
    assert selected(assistant_store,profile).recommend('owner','invalid',text)['status']==status
    assert count(assistant_store)==(0,0,0)


@pytest.mark.parametrize('profile',[DEFERRED,DECISION])
def test_unknown_mandatory_colour_and_strict_eligibility(assistant_store,profile):
    with connect(assistant_store[0]) as c: c.execute("UPDATE garments SET primary_colour='#182a46'")
    s=selected(assistant_store,profile)
    assert s.recommend('owner','unknown','Suggest an outfit with blue colours')['status']=='InsufficientEvidence'
    with connect(assistant_store[0]) as c: c.execute("UPDATE processing_items SET review_status='accepted'")
    assert s.recommend('owner','ineligible','Suggest an outfit')['status']=='NoEligibleGarments'
    assert count(assistant_store)==(0,0,0)


@pytest.mark.parametrize('stage',['revalidated','recommendation','chat','item','snapshot','metadata','submission','before_commit'])
def test_atomic_rollback(assistant_store,stage):
    seen=[]
    def fail(actual,connection):
        seen.append(actual)
        if actual==stage: raise RuntimeError('synthetic injected write failure')
    r=selected(assistant_store,repo=SqliteRecommendationRepository(assistant_store[0],fail)).recommend('owner','rollback','Suggest an outfit')
    assert stage in seen
    assert r['status']=='PersistenceFailure' and count(assistant_store)==(0,0,0)


def test_concurrent_retries_and_configuration_changes(assistant_store):
    with ThreadPoolExecutor(3) as pool:
        results=list(pool.map(lambda _: selected(assistant_store).recommend('owner','same','Suggest an outfit'),range(3)))
    assert all(r['status']=='Selected' for r in results)
    assert len({r['id'] for r in results})==1 and count(assistant_store)==(1,1,1)
    invalid=selected(assistant_store,'unknown-profile')
    assert invalid.recommend('owner','new','Suggest an outfit')['status']=='ProfileUnavailable'
    assert invalid.recommend('owner','same','Suggest an outfit')['replayed']
    assert selected(assistant_store).recommend('owner','same','Suggest a blue outfit')['status']=='IdempotencyConflict'


@pytest.mark.parametrize('profile',[DEFERRED,DECISION,'unknown-profile'])
def test_real_api_composition_authentication_and_history(assistant_store,monkeypatch,profile):
    import app.infrastructure.persistence.recommendation_repository_adapter as adapter
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED','true')
    monkeypatch.setenv('SMART_WARDROBE_CHAT_HISTORY_ENABLED','true')
    monkeypatch.setenv(ENVIRONMENT_KEY,profile)
    monkeypatch.setattr(adapter,'SqliteRecommendationRepository',lambda:assistant_store[1])
    import app.infrastructure.persistence.chat_history_query_adapter as history_adapter
    monkeypatch.setattr(history_adapter,'SqliteChatHistoryQuery',lambda:SqliteChatHistoryQuery(assistant_store[0],cursor_secret='test'))
    headers={'Authorization':'Bearer '+issue_access_token('owner')}
    body={'request_text':'Suggest an outfit','submission_key':'api'}
    if profile=='unknown-profile':
        # Invalid server configuration is now rejected at startup, even before
        # authentication/routes become available. Direct replay remains covered.
        with pytest.raises(ValueError,match='Unknown Assistant scoring'):
            with TestClient(app):pass
        assert count(assistant_store)==(0,0,0)
        return
    with TestClient(app) as client:
        assert client.post('/api/v1/recommendations',json=body).status_code==401
        response=client.post('/api/v1/recommendations',headers=headers,json=body)
        assert response.status_code==201,response.text
        record=response.json()
        assert record['scoring_display']['kind']==('Decision' if profile==DECISION else 'Deferred')
        assert client.post('/api/v1/recommendations',headers=headers,json=body).status_code==200
        other={'Authorization':'Bearer '+issue_access_token('other')}
        assert client.get('/api/v1/chats/'+record['chat_id'],headers=other).status_code==404
        assert client.get('/api/v1/chats/'+record['chat_id'],headers=headers).json()['recommendation']['scoring_display']==record['scoring_display']


def test_legacy_inconsistent_metadata_and_allowlist():
    assert display_for_record({}).kind=='Unavailable'
    assert display_for_record({'provenance':{'scoring_profile':DEFERRED},'compatibility_score':None}).kind=='Deferred'
    assert display_for_record({'score_metadata':{'profile_name':DECISION},'compatibility_score':None}).kind=='Unavailable'
    for value in ('',None,'EXPERIMENTAL',{}):
        with pytest.raises((ValueError,TypeError)): AssistantScoringSelection(value)


@pytest.mark.parametrize('mode',['failure','interrupt','incomplete','close'])
def test_experimental_stream_failure_guarantees(assistant_store,mode,monkeypatch):
    # Reuse the existing end-to-end failure injector, selecting the new profile.
    import tests.test_outfit_assistant as legacy
    original=legacy.service
    def experimental(*args,**kwargs):
        result=original(*args,**kwargs)
        result.scoring_profile=DECISION
        return result
    monkeypatch.setattr(legacy,'service',experimental)
    legacy.test_stream_failure_after_provisional_winner(assistant_store,mode)


def test_stale_snapshot_and_failed_transaction_experimental(assistant_store,monkeypatch):
    import tests.test_outfit_assistant as legacy
    original=legacy.service
    def experimental(*args,**kwargs):
        result=original(*args,**kwargs);result.scoring_profile=DECISION;return result
    monkeypatch.setattr(legacy,'service',experimental)
    legacy.test_stale_garments_and_storage_failure(assistant_store)


@pytest.mark.parametrize('profile',[DEFERRED,DECISION])
def test_existing_save_action_keeps_exact_experimental_history(assistant_store,monkeypatch,profile):
    record=selected(assistant_store,profile).recommend('owner','save','Suggest an outfit')
    import app.infrastructure.persistence.chat_history_query_adapter as adapter
    query=adapter.SqliteChatHistoryQuery
    monkeypatch.setattr(adapter,'SqliteChatHistoryQuery',lambda:query(assistant_store[0]))
    headers={'Authorization':'Bearer '+issue_access_token('owner')}
    with TestClient(app) as client:
        before=client.get('/api/v1/chats/'+record['chat_id'],headers=headers).json()
        url='/api/v1/recommendations/'+record['id']+'/save-as-outfit'
        saved=client.post(url,headers=headers,json={'name':'Synthetic test saved outfit'})
        assert saved.status_code==201,saved.text
        assert client.post(url,headers=headers,json={'name':'Synthetic test saved outfit'}).json()==saved.json()
        assert client.get('/api/v1/chats/'+record['chat_id'],headers=headers).json()==before
        assert client.post(url,headers={'Authorization':'Bearer '+issue_access_token('other')},json={}).status_code==404


def test_experimental_visualisation_prepare_preserves_original_history(assistant_store,monkeypatch):
    record=selected(assistant_store).recommend('owner','visualise','Suggest an outfit')
    import tests.test_historical_recommendation_actions as actions
    # Existing prepare/VTON-role boundary test, using a newly integrated record.
    actions.test_supported_historical_visualisation_prepare_preserves_source_and_history((assistant_store[0],record),monkeypatch)


def test_exact_request_preference_variation_and_no_client_profile_override(assistant_store,monkeypatch):
    with connect(assistant_store[0]) as c:
        c.execute("INSERT INTO user_preferences VALUES('p','owner','colours','{\"values\":[\"blue\"]}',1,'test',1,'now','now')")
    r=selected(assistant_store).recommend('owner','r-p','Suggest an outfit with vintage style')
    assert (r['request_match_score'],r['preference_score'],r['compatibility_score'],r['total_score'])==(1,1,None,.9)
    assert r['scoring_display']['decision_contribution']=={'numerator':1,'denominator':2}
    assert score_from_json(json.dumps(r['score_metadata'])).total==Fraction(9,10)
    import app.infrastructure.persistence.recommendation_repository_adapter as adapter
    monkeypatch.setattr(adapter,'SqliteRecommendationRepository',lambda:assistant_store[1])
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED','true')
    monkeypatch.delenv(ENVIRONMENT_KEY,raising=False)
    with TestClient(app) as client:
        response=client.post('/api/v1/recommendations?pipeline=integrated&scoring_profile='+DECISION,
            headers={'Authorization':'Bearer '+issue_access_token('owner')},
            json={'request_text':'Suggest an outfit','submission_key':'client-override','scoring_profile':DECISION})
        assert response.status_code==422 and response.json()['outcome']=='InvalidInput'
        response=client.post('/api/v1/recommendations?pipeline=integrated&scoring_profile='+DECISION,
            headers={'Authorization':'Bearer '+issue_access_token('owner')},
            json={'request_text':'Suggest an outfit','submission_key':'query-override'})
        assert response.status_code==201
        assert response.json()['provenance']['scoring_profile']==DEFERRED

