"""Real NLP, request gate/ranking, SQLite and opt-in Assistant endpoint."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import threading
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.application.nlp.nlp_interpreter import NLPInterpreter
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
from app.application.recommendation.request_match_scorer import RequestMatchScorer
from app.application.recommendation.recommendation_engine import CandidateGenerationSession
from app.domain.value_objects.candidate_generation_result import CandidateGenerationResult
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
from app.infrastructure.persistence import active_preference_query_adapter as preferences
from app.application.ports.assistant_runtime import assistant_service
from app.infrastructure.security import issue_access_token
from tests.test_recommendation_persistence import store,connect


@pytest.fixture
def assistant_store(store,monkeypatch):
    monkeypatch.setattr(preferences,'DATABASE_PATH',store[0])
    with connect(store[0]) as c:
        c.execute("UPDATE garments SET style_tags='[\"vintage\"]'")
    return store


def service(store,repo=None,query=None,evaluator=None,prefs=None):
    return OutfitAssistantService(NLPInterpreter(),RequestCandidateEngine(query or SqliteConfirmedGarmentQuery(),evaluator_factory=evaluator),
        prefs or preferences.SqliteActivePreferenceQuery(),repo or store[1])


def count(store):
    with connect(store[0]) as c:
        return tuple(c.execute(f'SELECT count(*) FROM {table}').fetchone()[0] for table in ('nlp_chats','recommendations','recommendation_items'))


def test_success_original_interpretation_exact_scores_and_replay(assistant_store):
    s = service(assistant_store)
    text = '  Suggest an outfit with vintage style  '
    result = s.recommend('owner','flow',text)
    assert result['status'] == 'Selected' and result['complete']
    assert result['request_text'] == text and result['request_match_score'] == 1
    assert result['compatibility_score'] is None and result['total_score'] == .7
    assert result['score_metadata']['weights'] == [{'numerator':7,'denominator':10},{'numerator':0,'denominator':1},{'numerator':3,'denominator':10}]
    with connect(assistant_store[0]) as c:
        row = c.execute('SELECT * FROM nlp_chats').fetchone()
        assert row['request_text'] == text and json.loads(row['extracted_entities_json'])['style'] == 'vintage'
        c.execute("UPDATE garments SET status='archived'")
    s.interpreter = Mock(side_effect=AssertionError('no NLP retry'))
    s.scorer_factory = Mock(side_effect=AssertionError('no ranking retry'))
    replay = s.recommend('owner','flow',text)
    assert replay['replayed'] and replay['id'] == result['id']
    assert not replay['items'][0]['currently_eligible']
    assert s.recommend('owner','flow',text.strip())['status'] == 'IdempotencyConflict'
    assert count(assistant_store) == (1,1,1)


@pytest.mark.parametrize('text,status', [('', 'InvalidInput'),('   ','InvalidInput'),('What is the capital of France?', 'UnsupportedRequest'),('Suggest an outfit with no blue','UnsupportedRequest'),('Recommend a blue top and black trousers outfit','UnsupportedRequest'),('Suggest an outfit for campus','PolicyUnavailable'),('Suggest a formal outfit','PolicyUnavailable'),('Suggest an outfit with red colours','NoMatchingCandidates')])
def test_controlled_no_history_outcomes(assistant_store,text,status):
    result = service(assistant_store).recommend('owner','flow',text)
    assert result['status'] == status
    assert count(assistant_store) == (0,0,0)


@pytest.mark.parametrize('sql,text,status', [
    ("UPDATE garments SET primary_colour='#182a46'",'Suggest an outfit with blue colours','InsufficientEvidence'),
    ("UPDATE garments SET primary_colour='broken colour'",'Suggest an outfit with blue colours','InsufficientEvidence'),
    ("UPDATE garments SET style_tags=NULL,attributes_json='{}',additional_attributes=NULL",'Suggest an outfit with vintage style','InsufficientEvidence'),
    ("UPDATE garments SET style_tags='[17]'",'Suggest an outfit with vintage style','InsufficientEvidence'),
    ("UPDATE garments SET style_tags='[\"classic\"]'",'Suggest an outfit with vintage style','NoMatchingCandidates'),
])
def test_unknown_and_failed_conditions_never_scored(assistant_store,sql,text,status,monkeypatch):
    with connect(assistant_store[0]) as c:
        c.execute(sql)
    score = Mock(side_effect=AssertionError('invalid candidate scored'))
    monkeypatch.setattr(RequestMatchScorer,'score',score)
    assert service(assistant_store).recommend('owner','flow',text)['status'] == status
    score.assert_not_called()
    assert count(assistant_store) == (0,0,0)


@pytest.mark.parametrize('sql', ["UPDATE garments SET status='archived'", "UPDATE garments SET user_id='other'", "UPDATE processing_items SET review_status='accepted'", "UPDATE garments SET processing_item_id=NULL", "UPDATE processing_jobs SET user_id='other'"])
def test_strict_phase1_eligibility(assistant_store,sql):
    with connect(assistant_store[0]) as c:
        c.execute(sql)
    assert service(assistant_store).recommend('owner','flow','Suggest an outfit')['status'] == 'NoEligibleGarments'
    assert count(assistant_store) == (0,0,0)


def add_garment(store,identifier,category,colour='blue',styles='["vintage"]'):
    with connect(store[0]) as c:
        c.execute("INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES(?,'job',?,1,'media','media','{}','confirmed','now')",(identifier,category))
        c.execute("INSERT INTO garments(id,user_id,processing_item_id,preferred_media_id,name,category,primary_colour,style_tags,attributes_json,created_at,updated_at) VALUES(?,'owner',?,'media',?,?,?,?,'{}','now','now')",(identifier,identifier,identifier,category,colour,styles))


@pytest.mark.parametrize('structure', ['pair','trio','dress','dress_outer'])
def test_all_structures_and_collective_constraints(assistant_store,structure):
    if structure in ('pair','trio'):
        with connect(assistant_store[0]) as c:
            c.execute("UPDATE garments SET status='archived'")
        add_garment(assistant_store,'top','vest')
        add_garment(assistant_store,'bottom','trousers')
    if structure in ('trio','dress_outer'):
        add_garment(assistant_store,'outer','long_sleeve_outwear')
    text = 'Suggest an outfit'
    if structure in ('trio','dress_outer'):
        text += ' including outerwear'
    result = service(assistant_store).recommend('owner','flow',text)
    assert result['status'] == 'Selected'
    assert [i['garment_role'] for i in result['items']] == {'pair':['upper','lower'],'trio':['upper','lower','outerwear'],'dress':['one_piece'],'dress_outer':['one_piece','outerwear']}[structure]


def test_preference_snapshot_is_stable_during_processing(assistant_store):
    path = assistant_store[0]
    with connect(path) as c:
        c.execute("INSERT INTO user_preferences VALUES('p','owner','colours','{\"values\":[\"blue\"]}',1,'test',1,'now','now')")
    class EditingPreferences:
        def get_active_preferences(self,user_id):
            rows = preferences.SqliteActivePreferenceQuery().get_active_preferences(user_id)
            with connect(path) as c:
                c.execute("UPDATE user_preferences SET preference_value_json='{\"values\":[\"red\"]}'")
            return rows
    result = service(assistant_store,prefs=EditingPreferences()).recommend('owner','flow','Suggest an outfit')
    assert result['status'] == 'Selected' and result['preference_score'] == 1 and result['total_score'] == .3
    assert json.loads(result['provenance']['preference_snapshot'][0]['value_json']) == {'values':['blue']}


def test_independent_ranking_calculation_and_generic_ties(assistant_store):
    add_garment(assistant_store,'a','vest_dress','red','["classic"]')
    with connect(assistant_store[0]) as c:
        c.execute("INSERT INTO user_preferences VALUES('p','owner','colours','{\"values\":[\"red\"]}',1,'test',1,'now','now')")
    result = service(assistant_store).recommend('owner','flow','Suggest an outfit')
    # No request fields: R=0, C unavailable, red preference P=1 -> S=.30.
    assert result['items'][0]['garment_id'] == 'a' and result['total_score'] == .3
    with connect(assistant_store[0]) as c:
        c.execute('DELETE FROM user_preferences')
    tied = service(assistant_store).recommend('owner','new','Suggest an outfit')
    assert tied['total_score'] == 0 and tied['items'][0]['garment_id'] == 'a'


def test_suitability_explicit_only(assistant_store):
    with connect(assistant_store[0]) as c:
        c.execute("UPDATE garments SET custom_tags='[\"rec:v1:occasion:campus:allow\",\"rec:v1:formality:casual:allow\"]'")
    assert service(assistant_store).recommend('owner','off','Suggest an outfit for campus')['status'] == 'PolicyUnavailable'
    enabled = service(assistant_store,evaluator=SuitabilityRequestEvaluator)
    assert enabled.recommend('owner','on','Suggest a casual outfit for campus')['status'] == 'Selected'
    assert enabled.recommend('owner','exercise','Suggest an outfit for exercise')['status'] == 'PolicyUnavailable'
    assert enabled.recommend('owner','formal','Suggest a formal outfit')['status'] == 'PolicyUnavailable'


def test_stale_garments_and_storage_failure(assistant_store):
    path,repo,_ = assistant_store
    class EditingRepository:
        def find_assistant_submission(self,*args):
            return repo.find_assistant_submission(*args)
        def persist_assistant(self,command):
            with connect(path) as c:
                c.execute("UPDATE garments SET primary_colour='red'")
            return repo.persist_assistant(command)
    assert service(assistant_store,repo=EditingRepository()).recommend('owner','stale','Suggest an outfit')['status'] == 'WardrobeChanged'
    def fail(stage,conn):
        if stage == 'metadata': raise RuntimeError('failure')
    assert service(assistant_store,repo=SqliteRecommendationRepository(path,fail)).recommend('owner','failed','Suggest an outfit')['status'] == 'PersistenceFailure'
    assert count(assistant_store) == (0,0,0)


def test_concurrent_retries_new_keys_and_lost_response(assistant_store):
    path,repo,_ = assistant_store
    barrier = threading.Barrier(3)
    class ConcurrentRepository:
        def find_assistant_submission(self,*args):
            result = repo.find_assistant_submission(*args)
            barrier.wait(timeout=5)
            return result
        def persist_assistant(self,cmd): return repo.persist_assistant(cmd)
    with ThreadPoolExecutor(3) as pool:
        results = list(pool.map(lambda _:service(assistant_store,repo=ConcurrentRepository()).recommend('owner','same','Suggest an outfit'),range(3)))
    assert all(r['status']=='Selected' for r in results)
    assert len({r['id'] for r in results}) == 1 and sum(r['replayed'] for r in results) == 2
    assert service(assistant_store).recommend('owner','new','Suggest an outfit')['id'] != results[0]['id']
    class LostResponse:
        def find_assistant_submission(self,*args): return repo.find_assistant_submission(*args)
        def persist_assistant(self,command):
            repo.persist_assistant(command)
            raise OSError('lost response')
    assert service(assistant_store,repo=LostResponse()).recommend('owner','lost','Suggest an outfit')['status'] == 'PersistenceFailure'
    assert service(assistant_store).recommend('owner','lost','Suggest an outfit')['replayed']
    assert count(assistant_store) == (3,3,3)


@pytest.mark.parametrize('mode',['failure','interrupt','incomplete','close'])
def test_stream_failure_after_provisional_winner(assistant_store,mode):
    rows = SqliteConfirmedGarmentQuery().get_confirmed_available_garments('owner')
    base = service(assistant_store)
    base.execution_engine = 'reference'  # Fault injection targets the reference stream.
    original = base.engine.structural_engine.generate_homepage_candidates
    first = next(original('owner'))
    def broken():
        yield first
        if mode == 'interrupt': raise KeyboardInterrupt()
        raise RuntimeError('late failure')
    if mode in ('failure','interrupt'):
        base.engine.structural_engine.generate_homepage_candidates = lambda user:CandidateGenerationSession(broken(),CandidateGenerationResult('Pending',False))
    else:
        generate = base.engine.generate_candidates
        def modified(user,request):
            stream = generate(user,request)
            if mode == 'close':
                def close(): raise RuntimeError('close failure')
                stream.close = close
            else:
                original_next = stream.structural_session.__class__.__next__
                class IncompleteStructural(CandidateGenerationSession):
                    def __next__(self):
                        try: return original_next(self)
                        except StopIteration:
                            self._result = CandidateGenerationResult('Interrupted',False)
                            raise
                stream.structural_session = IncompleteStructural((first,),CandidateGenerationResult('Pending',False))
            return stream
        base.engine.generate_candidates = modified
    assert base.recommend('owner','flow','Suggest an outfit')['status'] == ('Interrupted' if mode=='interrupt' else 'ProcessingFailure')
    assert count(assistant_store) == (0,0,0)


def test_five_fields_preserved_and_minimum_rules_applied(assistant_store):
    with connect(assistant_store[0]) as c:
        c.execute("UPDATE garments SET custom_tags='[\"rec:v1:occasion:campus:allow\",\"rec:v1:formality:casual:allow\"]'")
    text = 'Suggest a casual outfit for campus with vintage style using blue colours with a dress'
    result = service(assistant_store,evaluator=SuitabilityRequestEvaluator).recommend('owner','combined',text)
    assert result['status'] == 'Selected'
    with connect(assistant_store[0]) as c:
        fields = json.loads(c.execute('SELECT extracted_entities_json FROM nlp_chats').fetchone()[0])
    assert fields == {'intent':'outfit_recommendation','occasion':'campus','style':'vintage','colours':['blue'],'garment_categories':[{'kind':'group','value':'dress'}],'formality':'casual'}
    assert result['request_match_score'] == 1 and result['total_score'] == .7


def test_real_composition_enables_only_requested_policies(assistant_store,monkeypatch):
    # This test explicitly verifies the default, independently of test-run settings.
    monkeypatch.delenv('SMART_WARDROBE_ASSISTANT_SCORING_PROFILE',raising=False)
    import app.infrastructure.persistence.recommendation_repository_adapter as adapter
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED','true')
    monkeypatch.delenv('SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED',raising=False)
    monkeypatch.setattr(adapter,'SqliteRecommendationRepository',lambda:assistant_store[1])
    headers = {'Authorization':'Bearer '+issue_access_token('owner')}
    with TestClient(app) as client:
        response = client.post('/api/v1/recommendations',headers=headers,json={'request_text':'Suggest an outfit','submission_key':'enabled'})
        assert response.status_code == 201 and response.json()['outcome'] == 'Selected'
        assert response.json()['provenance']['scoring_profile'] == 'compatibility_deferred'
        unavailable = client.post('/api/v1/recommendations',headers=headers,json={'request_text':'Suggest an outfit for campus','submission_key':'campus'})
        assert unavailable.json()['outcome'] == 'PolicyUnavailable'
    with connect(assistant_store[0]) as c:
        c.execute("UPDATE garments SET custom_tags='[\"rec:v1:occasion:campus:allow\",\"rec:v1:formality:casual:allow\"]'")
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED','true')
    with TestClient(app) as client:
        enabled = client.post('/api/v1/recommendations',headers=headers,json={'request_text':'Suggest a casual outfit for campus','submission_key':'campus-enabled'})
        assert enabled.status_code == 201 and enabled.json()['provenance']['suitability_policy'] == 'owner-declarations-1.0.0'


def test_api_default_off_opt_in_auth_and_no_fallback(assistant_store,monkeypatch):
    headers = {'Authorization':'Bearer '+issue_access_token('owner')}
    monkeypatch.delenv('SMART_WARDROBE_ASSISTANT_ENABLED',raising=False)
    with TestClient(app) as client:
        assert client.post('/api/v1/recommendations',json={'request_text':'Suggest an outfit'}).status_code == 401
        legacy = client.post('/api/v1/recommendations',headers=headers,json={'request_text':'Suggest an outfit'})
        assert legacy.status_code == 404 and legacy.json()['outcome'] == 'IntegrationDisabled'
        app.dependency_overrides[assistant_service] = lambda:service(assistant_store)
        from app.application.recommendation import recommendation_service
        monkeypatch.setattr(recommendation_service,'create_recommendation',Mock(side_effect=AssertionError('no fallback')))
        try:
            missing = client.post('/api/v1/recommendations',headers=headers,json={'request_text':'Suggest an outfit'})
            assert missing.status_code == 422
            unsupported = client.post('/api/v1/recommendations',headers=headers,json={'request_text':'Tell me a joke','submission_key':'bad'})
            assert unsupported.status_code == 422 and unsupported.json()['outcome'] == 'UnsupportedRequest'
            response = client.post('/api/v1/recommendations',headers=headers,json={'request_text':'Suggest an outfit','submission_key':'ok'})
            assert response.status_code == 201 and response.json()['outcome'] == 'Selected' and response.json()['status'] == 'available'
            other = client.post('/api/v1/recommendations',headers={'Authorization':'Bearer '+issue_access_token('other')},json={'request_text':'Suggest an outfit','submission_key':'ok'})
            assert other.json()['status'] == 'NoEligibleGarments'
        finally:
            app.dependency_overrides.pop(assistant_service,None)
