"""Actual composition replacement/rollback; synthetic disposable wardrobe only."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
import json
import pytest
from app.application.ports.assistant_runtime import assistant_service
from app.application.recommendation.assistant_execution_selection import AssistantExecutionSelection, REFERENCE, COMPACT, ENVIRONMENT_KEY
from app.application.recommendation.assistant_scoring_selection import DEFERRED, DECISION, ENVIRONMENT_KEY as SCORING_KEY
from app.infrastructure.workflow_runtime import configure_local_workflow
from tests.test_outfit_assistant import assistant_store, count
from tests.test_recommendation_persistence import store, connect


def compose(data, monkeypatch, engine, profile):
    import app.infrastructure.persistence.chat_history_query_adapter as history
    import app.infrastructure.persistence.recommendation_repository_adapter as persistence
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED', 'true')
    monkeypatch.setenv('SMART_WARDROBE_HOMEPAGE_ENABLED', 'false')
    monkeypatch.setenv(ENVIRONMENT_KEY, engine)
    monkeypatch.setenv(SCORING_KEY, profile)
    monkeypatch.setattr(persistence, 'SqliteRecommendationRepository', lambda: data[1])
    original = history.SqliteChatHistoryQuery
    # Resolve the class rather than nesting a lambda on repeated composition.
    if hasattr(original, '_readiness_original'):
        original = original._readiness_original
    def reader():
        return original(data[0], cursor_secret='synthetic-readiness')
    reader._readiness_original = original
    monkeypatch.setattr(history, 'SqliteChatHistoryQuery', reader)
    configure_local_workflow()
    return assistant_service()


def pause_first_rank(monkeypatch):
    entered, release = Event(), Event()
    original = AssistantExecutionSelection.scorer
    calls = []
    def factory(selection, *args):
        scorer = original(selection, *args)
        calls.append((selection.engine, args[0].profile))
        if len(calls) != 1:
            return scorer
        class Paused:
            def __getattr__(self, name):
                return getattr(scorer, name)
            def rank(self, *args, **kwargs):
                entered.set()
                if not release.wait(15):
                    raise RuntimeError('Synthetic rollout test did not release ranking')
                return scorer.rank(*args, **kwargs)
        return Paused()
    monkeypatch.setattr(AssistantExecutionSelection, 'scorer', factory)
    return entered, release, calls


def executor(record):
    return record['provenance'].get('assistant_execution_selection', {}).get('engine', REFERENCE)


def test_historical_review_plan_is_preserved_and_approved_default_is_compact():
    from inspect import signature
    from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
    from app.application.recommendation.assistant_scoring_selection import AssistantScoringSelection
    path = Path(__file__).resolve().parents[2] / 'docs/config/assistant_execution_transition.v1.json'
    plan = json.loads(path.read_text())
    assert plan['version'] == 'assistant-execution-transition-1.0.0'
    assert plan['status'] == 'pending_owner_approval' and plan['applied'] is False
    assert AssistantExecutionSelection().engine == COMPACT
    assert AssistantScoringSelection().profile == DEFERRED
    parameters = signature(OutfitAssistantService).parameters
    assert parameters['execution_engine'].default == COMPACT
    assert parameters['scoring_profile'].default == DEFERRED
    assert plan['current_defaults'] == {ENVIRONMENT_KEY: REFERENCE, SCORING_KEY: DEFERRED}
    assert plan['proposed_defaults'] == plan['explicit_rollout_environment_after_approval'] == {ENVIRONMENT_KEY: COMPACT, SCORING_KEY: DEFERRED}
    assert plan['explicit_rollback_environment'] == plan['current_defaults']
    assert plan['restart_required'] and not plan['runtime_hot_reload'] and not plan['database_migration']


def test_actual_composition_with_unset_configuration_uses_compact_deferred(assistant_store, monkeypatch):
    compose(assistant_store, monkeypatch, REFERENCE, DEFERRED)
    monkeypatch.delenv(ENVIRONMENT_KEY)
    monkeypatch.delenv(SCORING_KEY)
    configure_local_workflow()
    svc = assistant_service()
    assert (svc.execution_engine, svc.scoring_profile) == (COMPACT, DEFERRED)
    result = svc.recommend('owner', 'defaults', 'Suggest an outfit')
    assert result['status'] == 'Selected' and executor(result) == COMPACT
    assert result['score_metadata']['profile_name'] == DEFERRED


@pytest.mark.parametrize('start', [REFERENCE, COMPACT])
@pytest.mark.parametrize('profile', [DEFERRED, DECISION])
def test_inflight_request_keeps_captured_context_across_rollout_and_rollback(assistant_store, monkeypatch, start, profile):
    old = compose(assistant_store, monkeypatch, start, profile)
    target = COMPACT if start == REFERENCE else REFERENCE
    entered, release, calls = pause_first_rank(monkeypatch)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(old.recommend, 'owner', 'inflight', 'Suggest an outfit')
        try:
            assert entered.wait(10)
            monkeypatch.setenv(ENVIRONMENT_KEY, target)
            assert old.execution_engine == start  # Environment is not hot reload.
            new = compose(assistant_store, monkeypatch, target, profile)
            current = new.recommend('owner', 'after-switch', 'Suggest an outfit')
            assert current['status'] == 'Selected' and executor(current) == target
        finally:
            release.set()
        previous = pending.result(timeout=15)
    assert previous['status'] == 'Selected' and executor(previous) == start
    assert previous['score_metadata'] == current['score_metadata']
    assert calls == [(start, profile), (target, profile)]
    with connect(assistant_store[0]) as c:
        frozen = {table: [tuple(row) for row in c.execute('SELECT * FROM ' + table)]
                  for table in ('recommendation_metadata', 'nlp_chats', 'recommendation_item_snapshots')}
    rolled_back = compose(assistant_store, monkeypatch, start, profile)
    for initial, key in ((previous, 'inflight'), (current, 'after-switch')):
        replay = rolled_back.recommend('owner', key, 'Suggest an outfit')
        assert replay['replayed'] and replay['id'] == initial['id']
        assert replay['provenance'] == initial['provenance']
        assert replay['score_metadata'] == initial['score_metadata']
    assert len(calls) == 2 and count(assistant_store) == (2, 2, 2)
    with connect(assistant_store[0]) as c:
        for table, rows in frozen.items():
            assert [tuple(row) for row in c.execute('SELECT * FROM ' + table)] == rows


@pytest.mark.parametrize('start', [REFERENCE, COMPACT])
@pytest.mark.parametrize('profile', [DEFERRED, DECISION])
def test_failed_inflight_write_can_retry_on_other_engine_without_partial_rows(assistant_store, monkeypatch, start, profile):
    from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
    old = compose(assistant_store, monkeypatch, start, profile)
    def fail(stage, connection):
        if stage == 'before_commit':
            raise RuntimeError('Synthetic old-process late failure')
    old.repository = SqliteRecommendationRepository(assistant_store[0], checkpoint=fail)
    entered, release, calls = pause_first_rank(monkeypatch)
    target = COMPACT if start == REFERENCE else REFERENCE
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(old.recommend, 'owner', 'retry', 'Suggest an outfit')
        try:
            assert entered.wait(10)
            new = compose(assistant_store, monkeypatch, target, profile)
        finally:
            release.set()
        assert pending.result(timeout=15)['status'] == 'PersistenceFailure'
    assert count(assistant_store) == (0, 0, 0)
    successful = new.recommend('owner', 'retry', 'Suggest an outfit')
    replay = old.recommend('owner', 'retry', 'Suggest an outfit')
    assert successful['status'] == replay['status'] == 'Selected'
    assert not successful['replayed'] and replay['replayed']
    assert executor(successful) == target and successful['id'] == replay['id']
    assert successful['provenance'] == replay['provenance']
    assert calls == [(start, profile), (target, profile)] and count(assistant_store) == (1, 1, 1)


@pytest.mark.parametrize('value', ['', 'compact', 'COMPACT_EXHAUSTIVE', ' reference ', 'unknown'])
@pytest.mark.parametrize('enabled', ['false', 'true'])
def test_invalid_engine_configuration_rejects_composition_even_when_disabled(monkeypatch, value, enabled):
    monkeypatch.setenv(ENVIRONMENT_KEY, value)
    monkeypatch.setenv(SCORING_KEY, DEFERRED)
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED', enabled)
    with pytest.raises(ValueError, match='Unknown Assistant execution configuration'):
        configure_local_workflow()


def test_application_lifespan_restart_default_rollback_and_restore(assistant_store, monkeypatch):
    """Three real ASGI lifespan restarts against one SQLite DB (not OS restarts)."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.infrastructure.security import issue_access_token
    compose(assistant_store, monkeypatch, REFERENCE, DEFERRED)
    monkeypatch.delenv(ENVIRONMENT_KEY)
    monkeypatch.delenv(SCORING_KEY)
    headers={'Authorization':'Bearer '+issue_access_token('owner')}
    url='/api/v1/recommendations?pipeline=integrated'
    body={'request_text':'Suggest an outfit','submission_key':'restart-compact'}
    with TestClient(app) as client:
        assert assistant_service().execution_engine==COMPACT
        response=client.post(url,headers=headers,json=body)
        assert response.status_code==201,response.text
        initial=response.json()
        assert executor(initial)==COMPACT
        assert initial['score_metadata']['profile_name']==DEFERRED
    tables=('recommendation_metadata','nlp_chats','recommendation_item_snapshots')
    with connect(assistant_store[0]) as c:
        frozen={t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in tables}
    monkeypatch.setenv(ENVIRONMENT_KEY,REFERENCE)
    with TestClient(app) as client:
        assert assistant_service().execution_engine==REFERENCE
        restored=client.get('/api/v1/chats/'+initial['chat_id'],headers=headers).json()['recommendation']
        for field in ('score_metadata','provenance'):
            assert restored[field]==initial[field]
        replay=client.post(url,headers=headers,json=body).json()
        assert replay['replayed'] and replay['id']==initial['id']
        with connect(assistant_store[0]) as c:
            for t in tables:assert [tuple(r) for r in c.execute('SELECT * FROM '+t)]==frozen[t]
        rollback_body={**body,'submission_key':'restart-reference'}
        rollback=client.post(url,headers=headers,json=rollback_body).json()
        assert rollback['outcome']=='Selected' and executor(rollback)==REFERENCE
    monkeypatch.delenv(ENVIRONMENT_KEY)
    with TestClient(app) as client:
        assert assistant_service().execution_engine==COMPACT
        for original, submission in ((initial,body),(rollback,rollback_body)):
            replay=client.post(url,headers=headers,json=submission).json()
            assert replay['replayed'] and replay['id']==original['id']
            assert replay['provenance']==original['provenance']
        final=client.post(url,headers=headers,json={**body,'submission_key':'restored-default'}).json()
        assert final['outcome']=='Selected' and executor(final)==COMPACT
    assert count(assistant_store)==(3,3,3)
