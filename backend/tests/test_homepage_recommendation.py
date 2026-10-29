"""Homepage streaming, exact sampling paths, real persistence and API checks."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from itertools import product
import json
from random import Random
import threading
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.application.ports.homepage_runtime import homepage_service
from app.application.recommendation.homepage_recommendation_service import HomepageRecommendationService
from app.application.recommendation.reservoir_selector import ReservoirSelector, IncompleteSelection
from app.application.recommendation.recommendation_engine import RecommendationEngine, CandidateGenerationSession
from app.domain.value_objects.candidate_generation_result import CandidateGenerationResult
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
from app.infrastructure.security import issue_access_token
from tests.test_structural_candidates import garment, Query
from tests.test_recommendation_persistence import store, connect


def engine(rows):
    return RecommendationEngine(Query(tuple(rows)))


def candidates():
    return tuple(engine([garment('top','vest'),garment('bottom','trousers'),garment('dress','vest_dress'),garment('outer','long_sleeve_outwear')]).generate_homepage_candidates('owner'))


def session(rows):
    return CandidateGenerationSession(rows, CandidateGenerationResult('Pending',False))


@pytest.mark.parametrize('target,draws', [(0,[1,1,1]),(1,[0,1,1]),(2,[1,0,1]),(3,[1,1,0])])
def test_four_structures_and_injected_draws(target, draws):
    rows = candidates()
    source = Mock(side_effect=draws)
    result = ReservoirSelector(source).select(session(rows))
    assert result.candidate == rows[target] and result.count == 4
    assert [call.args[0] for call in source.call_args_list] == [2,3,4]
    assert tuple(m.role for m in result.candidate.members) == [('upper','lower'),('upper','lower','outerwear'),('one_piece',),('one_piece','outerwear')][target]


def test_exact_uniform_probability_by_all_equiprobable_draw_paths():
    rows = candidates()
    counts = Counter()
    for draws in product(range(2),range(3),range(4)):
        sequence = iter(draws)
        result = ReservoirSelector(lambda n:next(sequence)).select(session(rows))
        counts[result.candidate.candidate_id] += 1
    assert set(counts.values()) == {6} and len(counts) == 4


def test_seeded_statistical_uniformity():
    rows, random, counts = candidates(), Random(51005), Counter()
    for _ in range(6000):
        counts[ReservoirSelector(random.randrange).select(session(rows)).candidate.candidate_id] += 1
    # Pearson goodness-of-fit sanity check, df=3, p=.001 critical value 16.266.
    assert sum((counts[r.candidate_id]-1500)**2/1500 for r in rows) < 16.266


def test_single_candidate_does_not_need_random_draw():
    random = Mock(side_effect=AssertionError('unnecessary draw'))
    assert ReservoirSelector(random).select(session(candidates()[:1])).count == 1
    random.assert_not_called()


@pytest.mark.parametrize('draw', [-1,2,True,None,.5])
def test_invalid_random_source_rejected(draw):
    with pytest.raises(IncompleteSelection):
        ReservoirSelector(lambda n:draw).select(session(candidates()[:2]))


def test_failure_and_interrupt_after_provisional_sample():
    for exception in (RuntimeError('failure'), KeyboardInterrupt()):
        def broken():
            yield candidates()[0]
            raise exception
        repo = Mock()
        repo.find_homepage_submission.return_value = None
        fake = Mock()
        fake.generate_homepage_candidates.return_value = session(broken())
        outcome = HomepageRecommendationService(fake,repo).recommend('owner','flow')
        assert outcome['status'] == ('Interrupted' if isinstance(exception,KeyboardInterrupt) else 'ProcessingFailure')
        assert not outcome['complete'] and 'recommendation' not in outcome
        repo.persist_homepage.assert_not_called()


@pytest.mark.parametrize('failure', ['incomplete','count','close'])
def test_incomplete_or_inconsistent_stream_cannot_select(failure):
    class Stream:
        result = SimpleNamespace(complete=failure!='incomplete',candidate_count=2 if failure=='count' else 1,status='StructuralCandidates')
        def __iter__(self):
            yield candidates()[0]
        def close(self):
            if failure == 'close':
                raise RuntimeError('close failed')
    with pytest.raises((IncompleteSelection, RuntimeError)):
        ReservoirSelector().select(Stream())


@pytest.mark.parametrize('rows,status', [([], 'NoEligibleGarments'),([garment('top','vest')], 'InsufficientStructure'),([garment('outer','long_sleeve_outwear')], 'InsufficientStructure')])
def test_controlled_empty_wardrobes(rows,status):
    repo = Mock()
    repo.find_homepage_submission.return_value = None
    result = HomepageRecommendationService(engine(rows),repo).recommend('owner','flow')
    assert result['status'] == status and result['complete']
    repo.persist_homepage.assert_not_called()


def test_no_structural_candidates_and_unknown_category():
    repo = Mock()
    repo.find_homepage_submission.return_value = None
    structural = engine([garment('dress','vest_dress')])
    structural.evaluator.is_structurally_valid = lambda members:False
    assert HomepageRecommendationService(structural,repo).recommend('owner','flow')['status'] == 'NoStructuralCandidates'
    assert HomepageRecommendationService(engine([garment('bad','unknown')]),repo).recommend('owner','unknown')['status'] == 'NoEligibleGarments'
    repo.persist_homepage.assert_not_called()


def service(store, selector=None, repo=None):
    _, repository, _ = store
    return HomepageRecommendationService(RecommendationEngine(SqliteConfirmedGarmentQuery()),repo or repository,selector)


def test_homepage_success_retry_new_key_and_no_chat_scores(store):
    path, repo, _ = store
    homepage = service(store)
    result = homepage.recommend('owner','flow')
    assert result['status'] == 'Selected' and not result['replayed']
    saved = result['recommendation']
    assert saved['chat_id'] is None
    assert all(saved[x] is None for x in ('request_match_score','compatibility_score','preference_score','total_score'))
    assert [(i['garment_id'],i['garment_role'],i['item_order']) for i in saved['items']] == [('garment','one_piece',1)]
    with connect(path) as c:
        assert c.execute('SELECT count(*) FROM nlp_chats').fetchone()[0] == 0
        assert c.execute('SELECT count(*) FROM outfits').fetchone()[0] == 0
        c.execute("UPDATE garments SET status='archived'")
    homepage.engine = Mock(side_effect=AssertionError('must not regenerate'))
    replay = homepage.recommend('owner','flow')
    assert replay['status'] == 'Selected' and replay['replayed'] and not replay['currently_eligible']
    assert replay['recommendation']['id'] == saved['id']
    with connect(path) as c:
        c.execute("UPDATE garments SET status='available'")
    new = service(store).recommend('owner','new-flow')
    assert new['recommendation']['id'] != saved['id']


def test_all_four_structures_persist_exact_order(store):
    path, _, _ = store
    with connect(path) as c:
        for identifier,category in [('top','vest'),('bottom','trousers'),('outer','long_sleeve_outwear')]:
            c.execute("INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES(?,'job',?,1,'media','media','{}','confirmed','now')",(identifier,category))
            c.execute("INSERT INTO garments(id,user_id,processing_item_id,preferred_media_id,name,category,attributes_json,created_at,updated_at) VALUES(?,'owner',?,'media',?,?,'{}','now','now')",(identifier,identifier,identifier,category))
    expected = [ [('top','upper'),('bottom','lower')], [('top','upper'),('bottom','lower'),('outer','outerwear')], [('garment','one_piece')], [('garment','one_piece'),('outer','outerwear')] ]
    for index,draws in enumerate(([1,1,1],[0,1,1],[1,0,1],[1,1,0])):
        sequence = iter(draws)
        result = service(store,ReservoirSelector(lambda n:next(sequence))).recommend('owner',f'structure-{index}')
        assert result['status'] == 'Selected'
        saved = result['recommendation']
        assert [(i['garment_id'],i['garment_role']) for i in saved['items']] == expected[index]
        assert [i['item_order'] for i in saved['items']] == list(range(1,len(expected[index])+1))
        assert saved['provenance']['candidate_count'] == 4
        assert saved['chat_id'] is None and saved['score_metadata'] is None


def test_no_nlp_preferences_scoring_or_assistant_calls(store,monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError('Homepage crossed its integration boundary')
    from app.application.nlp.nlp_interpreter import NLPInterpreter
    from app.application.recommendation.recommendation_scorer import RecommendationScorer
    from app.application.recommendation.holistic_recommendation_scorer import HolisticRecommendationScorer
    from app.infrastructure.persistence.active_preference_query_adapter import SqliteActivePreferenceQuery
    from app.application.recommendation import recommendation_service
    monkeypatch.setattr(NLPInterpreter,'interpret',forbidden)
    monkeypatch.setattr(RecommendationScorer,'rank',forbidden)
    monkeypatch.setattr(HolisticRecommendationScorer,'rank',forbidden)
    monkeypatch.setattr(SqliteActivePreferenceQuery,'get_active_preferences',forbidden)
    monkeypatch.setattr(recommendation_service,'create_recommendation',forbidden)
    assert service(store).recommend('owner','independent')['status'] == 'Selected'


@pytest.mark.parametrize('change', ["UPDATE processing_items SET review_status='accepted'", "UPDATE garments SET processing_item_id=NULL", "UPDATE garments SET status='archived'", "UPDATE processing_jobs SET user_id='other'", "UPDATE garments SET user_id='other'"])
def test_phase1_eligibility_and_owner_scope(store,change):
    path, _, _ = store
    with connect(path) as c:
        c.execute(change)
    assert service(store).recommend('owner','flow')['status'] == 'NoEligibleGarments'


def test_stale_selection_and_rollback_are_controlled(store):
    path, repo, _ = store
    class EditingSelector(ReservoirSelector):
        def select(self, stream):
            result = super().select(stream)
            with connect(path) as c:
                c.execute("UPDATE garments SET primary_colour='red'")
            return result
    assert service(store, EditingSelector()).recommend('owner','stale')['status'] == 'WardrobeChanged'
    def fail(stage, conn):
        if stage == 'metadata':
            raise RuntimeError('storage failure')
    assert service(store,repo=SqliteRecommendationRepository(path,fail)).recommend('owner','failed')['status'] == 'PersistenceFailure'
    with connect(path) as c:
        assert c.execute('SELECT count(*) FROM recommendations').fetchone()[0] == 0


def test_concurrent_homepage_retries_persist_one(store):
    path, repo, _ = store
    barrier = threading.Barrier(4)
    class ConcurrentRepository:
        def find_homepage_submission(self,*args):
            result = repo.find_homepage_submission(*args)
            barrier.wait(timeout=5)
            return result
        def persist_homepage(self,command):
            return repo.persist_homepage(command)
    def run(_):
        return service(store, repo=ConcurrentRepository()).recommend('owner','same-flow')
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(run, range(4)))
    assert all(r['status'] == 'Selected' for r in results)
    assert len({r['recommendation']['id'] for r in results}) == 1
    assert sum(r['replayed'] for r in results) == 3
    with connect(path) as c:
        assert c.execute('SELECT count(*) FROM recommendations').fetchone()[0] == 1
        assert c.execute('SELECT count(*) FROM nlp_chats').fetchone()[0] == 0


def test_existing_conflict_rejected_before_generation(store):
    _, repo, command = store
    repo.persist(replace(command,request_json='{"other":true}'))
    forbidden_engine = Mock(side_effect=AssertionError('no generation'))
    assert HomepageRecommendationService(forbidden_engine,repo).recommend('owner','key')['status'] == 'IdempotencyConflict'


def test_lost_response_recovers_committed_result_without_reroll(store):
    path, repo, _ = store
    class LostResponseRepository:
        def find_homepage_submission(self,*args):
            return repo.find_homepage_submission(*args)
        def persist_homepage(self,command):
            repo.persist_homepage(command)
            raise OSError('response lost after commit')
    assert service(store,repo=LostResponseRepository()).recommend('owner','lost')['status'] == 'PersistenceFailure'
    replay = HomepageRecommendationService(Mock(side_effect=AssertionError('no reroll')),repo).recommend('owner','lost')
    assert replay['status'] == 'Selected' and replay['replayed']
    with connect(path) as c:
        assert c.execute('SELECT count(*) FROM recommendations').fetchone()[0] == 1


@pytest.mark.parametrize('key', ['', ' ', 'bad key', 'x'*201, None, 12])
def test_invalid_keys_do_not_access_repository(key):
    repo = Mock()
    assert HomepageRecommendationService(Mock(),repo).recommend('owner',key)['status'] == 'InvalidInput'
    repo.find_homepage_submission.assert_not_called()


def test_api_flag_authentication_success_and_existing_list(store,monkeypatch):
    monkeypatch.delenv('SMART_WARDROBE_HOMEPAGE_ENABLED',raising=False)
    headers = {'Authorization':'Bearer '+issue_access_token('owner')}
    with TestClient(app) as client:
        assert client.post('/api/v1/recommendations/homepage',json={'submission_key':'flow'}).status_code == 401
        disabled = client.post('/api/v1/recommendations/homepage',headers=headers,json={'submission_key':'flow'})
        assert disabled.status_code == 404 and disabled.json()['status'] == 'IntegrationDisabled'
        app.dependency_overrides[homepage_service] = lambda:service(store)
        try:
            for invalid in ({'submission_key':' '},{'submission_key':12},{'submission_key':'flow','garment_ids':['bad']}):
                assert client.post('/api/v1/recommendations/homepage',headers=headers,json=invalid).status_code == 422
            response = client.post('/api/v1/recommendations/homepage',headers=headers,json={'submission_key':'flow'})
            assert response.status_code == 201 and response.json()['status'] == 'Selected'
            replay = client.post('/api/v1/recommendations/homepage',headers=headers,json={'submission_key':'flow'})
            assert replay.status_code == 200 and replay.json()['replayed']
            assert client.get('/api/v1/recommendations',headers=headers).json() == []
        finally:
            app.dependency_overrides.pop(homepage_service,None)


def test_opt_in_composition_wires_actual_service(store,monkeypatch):
    _, repo, _ = store
    import app.infrastructure.persistence.recommendation_repository_adapter as adapter
    monkeypatch.setenv('SMART_WARDROBE_HOMEPAGE_ENABLED','true')
    monkeypatch.setattr(adapter,'SqliteRecommendationRepository',lambda:repo)
    with TestClient(app) as client:
        result = client.post('/api/v1/recommendations/homepage',headers={'Authorization':'Bearer '+issue_access_token('owner')},json={'submission_key':'enabled'})
        assert result.status_code == 201
        other = client.post('/api/v1/recommendations/homepage',headers={'Authorization':'Bearer '+issue_access_token('other')},json={'submission_key':'enabled'})
        assert other.json()['status'] == 'NoEligibleGarments'


@pytest.mark.parametrize('status,http', [('NoEligibleGarments',200),('InsufficientStructure',200),('NoStructuralCandidates',200),('IdempotencyConflict',409),('WardrobeChanged',409),('ProcessingFailure',503),('PersistenceFailure',503),('Interrupted',503)])
def test_api_structured_outcome_mapping(store,status,http):
    fake = Mock()
    fake.recommend.return_value = {'status':status,'complete':http==200}
    with TestClient(app) as client:
        app.dependency_overrides[homepage_service] = lambda:fake
        try:
            response = client.post('/api/v1/recommendations/homepage',headers={'Authorization':'Bearer '+issue_access_token('owner')},json={'submission_key':'flow'})
            assert response.status_code == http and response.json()['status'] == status
            fake.recommend.assert_called_once_with('owner','flow')
        finally:
            app.dependency_overrides.pop(homepage_service,None)
