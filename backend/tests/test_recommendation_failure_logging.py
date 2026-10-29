"""Controlled actual failures, safe log payloads and real transaction recovery."""
from datetime import datetime
import io
import json
import logging
from types import SimpleNamespace

import pytest

from app.application.recommendation import failure_diagnostics as diagnostics
from app.application.recommendation.homepage_recommendation_service import HomepageRecommendationService
from app.application.recommendation.recommendation_engine import RecommendationEngine
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
from tests.test_outfit_assistant import assistant_store, service
from tests.test_recommendation_persistence import connect, store

SENSITIVE = ('Bearer SECRET_AUTH_TOKEN', 'SECRET_PASSWORD', 'SECRET_CONFIG_VALUE',
             'PRIVATE_REQUEST medical personal note', 'PRIVATE_WARDROBE colour attributes',
             'private-person@example.test', 'PRIVATE_SUBMISSION_KEY')


def failure():
    # Real exception chaining/messages must not reach the logger or LogRecord.exc_info.
    try:
        raise ValueError(' | '.join(SENSITIVE))
    except ValueError as original:
        raise RuntimeError(' | '.join(reversed(SENSITIVE))) from original


def events(caplog):
    records = [r for r in caplog.records if r.name == diagnostics.LOGGER.name]
    for record in records:
        assert record.levelno == logging.ERROR
        assert record.exc_info is None and record.stack_info is None
        assert not record.args
        payload = json.loads(record.getMessage())
        assert payload == record.recommendation_failure
        assert set(payload) == {'schema','event','timestamp_utc','diagnostic_id','operation','stage','outcome','reason','error_kind','locations'}
        assert payload['schema'] == 'recommendation-failure-1.0.0'
        assert payload['event'] == 'recommendation_failure'
        assert len(payload['diagnostic_id']) == 32
        assert datetime.fromisoformat(payload['timestamp_utc']).utcoffset().total_seconds() == 0
        assert len(payload['locations']) <= 6
        for location in payload['locations']:
            assert set(location) == {'file','line'} and location['line'] > 0
            assert not location['file'].startswith(('/', '\\')) and ':' not in location['file']
        for secret in SENSITIVE:
            assert secret not in record.getMessage() and secret not in caplog.text
    return [r.recommendation_failure for r in records]


def table_counts(path):
    with connect(path) as c:
        return {name: c.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]
                for name in ['nlp_chats','recommendations','recommendation_items','recommendation_item_snapshots','recommendation_metadata','recommendation_submissions']}


def homepage(store, repository=None):
    return HomepageRecommendationService(RecommendationEngine(SqliteConfirmedGarmentQuery()), repository or store[1])


@pytest.mark.parametrize('operation', ['assistant','homepage'])
@pytest.mark.parametrize('stage', ['lookup','generation','persistence'])
def test_actual_failure_context_safe_json_and_original_status(assistant_store,monkeypatch,caplog,operation,stage):
    caplog.set_level(logging.ERROR,logger=diagnostics.LOGGER.name)
    path, repository, _ = assistant_store
    application = service(assistant_store) if operation == 'assistant' else homepage(assistant_store)
    expected_stage = stage
    if stage == 'lookup':
        name = 'find_assistant_submission' if operation == 'assistant' else 'find_homepage_submission'
        monkeypatch.setattr(repository,name,lambda *a:failure())
    elif stage == 'generation':
        if operation == 'assistant':
            expected_stage='interpretation'
            monkeypatch.setattr(application.interpreter,'interpret',lambda *a:failure())
        else:
            monkeypatch.setattr(application.engine,'generate_homepage_candidates',lambda *a:failure())
    else:
        name = 'persist_assistant' if operation == 'assistant' else 'persist_homepage'
        monkeypatch.setattr(repository,name,lambda *a:failure())
    before=table_counts(path)
    text='Suggest an outfit' if stage=='persistence' else SENSITIVE[3]
    result = application.recommend('owner',SENSITIVE[-1],text) if operation=='assistant' else application.recommend('owner',SENSITIVE[-1])
    expected='ProcessingFailure' if stage=='generation' else 'PersistenceFailure'
    assert result == {'status':expected,'complete':False}
    assert table_counts(path)==before
    logged=events(caplog)
    assert len(logged)==1
    assert logged[0]['operation']==operation and logged[0]['stage']==expected_stage and logged[0]['outcome']==expected
    assert logged[0]['error_kind']=='RuntimeError'
    assert logged[0]['locations']  # Service catch site, never test/customer traceback text.


@pytest.mark.parametrize('operation',['assistant','homepage'])
@pytest.mark.parametrize('fault_stage',['chat','recommendation','item','metadata','snapshot','submission','before_commit'])
def test_injected_transaction_failure_logs_rollback_then_same_key_retry(assistant_store,caplog,operation,fault_stage):
    caplog.set_level(logging.ERROR,logger=diagnostics.LOGGER.name)
    path, repository, _=assistant_store
    observed=[]
    def fail(stage, connection):
        observed.append(stage)
        if stage==fault_stage:failure()
    broken=SqliteRecommendationRepository(path,fail)
    application=service(assistant_store,repo=broken) if operation=='assistant' else homepage(assistant_store,broken)
    before=table_counts(path)
    call=lambda app:app.recommend('owner','stable-fault-key','Suggest an outfit') if operation=='assistant' else app.recommend('owner','stable-fault-key')
    result=call(application)
    # Homepage has no chat write; its stage hook is deliberately not reached.
    if operation=='homepage' and fault_stage=='chat':
        assert result['status']=='Selected' and not events(caplog)
        return
    assert fault_stage in observed
    assert result=={'status':'PersistenceFailure','complete':False}
    assert table_counts(path)==before
    log=events(caplog)
    assert len(log)==1 and log[0]['stage']=='persistence'
    good=service(assistant_store) if operation=='assistant' else homepage(assistant_store)
    saved=call(good);replayed=call(good)
    assert saved['status']==replayed['status']=='Selected' and replayed['replayed']
    rid=saved['id'] if operation=='assistant' else saved['recommendation']['id']
    assert rid==(replayed['id'] if operation=='assistant' else replayed['recommendation']['id'])
    after=table_counts(path)
    assert after['recommendations']==before['recommendations']+1
    assert after['nlp_chats']==before['nlp_chats']+(operation=='assistant')
    assert len(events(caplog))==1  # Success/replay does not emit failure events.


def test_ranker_returned_failure_does_not_log_its_private_diagnostics(assistant_store,monkeypatch,caplog):
    caplog.set_level(logging.ERROR,logger=diagnostics.LOGGER.name)
    from app.application.recommendation.assistant_scoring_selection import AssistantScoringSelection
    monkeypatch.setattr(AssistantScoringSelection,'rank',lambda *a:SimpleNamespace(status='ProcessingFailure',complete=False,diagnostics=SENSITIVE))
    result=service(assistant_store).recommend('owner','rank-fail','Suggest an outfit')
    assert result['status']=='ProcessingFailure'  # Existing response shape is unchanged.
    assert events(caplog)[0]['reason']=='controlled_failure'
    assert table_counts(assistant_store[0])['recommendations']==0


def test_custom_exception_name_message_and_string_conversion_are_excluded(caplog):
    caplog.set_level(logging.ERROR,logger=diagnostics.LOGGER.name)
    def forbidden(self):raise AssertionError('Exception string must never be rendered')
    Custom=type('SECRET_CONFIG_VALUE',(Exception,),{'__str__':forbidden})
    diagnostics.log_failure(SENSITIVE[0],SENSITIVE[1],SENSITIVE[2],Custom())
    value=events(caplog)[0]
    assert value['operation']==value['stage']=='unknown' and value['outcome']=='ProcessingFailure'
    assert value['error_kind']=='ApplicationError'


@pytest.mark.parametrize('operation',['assistant','homepage'])
def test_logging_handler_failure_preserves_api_result_and_rollback(assistant_store,monkeypatch,operation):
    path,repository,_=assistant_store
    def broken_logger(*a,**k):raise OSError('secret log sink credentials')
    monkeypatch.setattr(diagnostics.LOGGER,'error',broken_logger)
    name='find_assistant_submission' if operation=='assistant' else 'find_homepage_submission'
    monkeypatch.setattr(repository,name,lambda *a:failure())
    application=service(assistant_store) if operation=='assistant' else homepage(assistant_store)
    result=application.recommend('owner','key','Suggest an outfit') if operation=='assistant' else application.recommend('owner','key')
    assert result=={'status':'PersistenceFailure','complete':False} and table_counts(path)['recommendations']==0


def test_default_message_formatter_contains_safe_technical_context():
    output=io.StringIO();handler=logging.StreamHandler(output)
    handler.setFormatter(logging.Formatter('%(message)s'))
    diagnostics.LOGGER.addHandler(handler)
    try:
        diagnostics.log_failure('assistant','interpretation','ProcessingFailure',ValueError(SENSITIVE[0]))
    finally:
        diagnostics.LOGGER.removeHandler(handler)
    record=json.loads(output.getvalue())
    assert record['operation']=='assistant' and record['stage']=='interpretation' and record['error_kind']=='ValueError'
    assert SENSITIVE[0] not in output.getvalue()


@pytest.mark.parametrize('status',['ProcessingError','InvalidScoringInput','InvalidPreferenceData','ProfileUnavailable'])
def test_returned_technical_failures_are_logged_without_diagnostics(assistant_store,monkeypatch,caplog,status):
    from app.application.recommendation.assistant_scoring_selection import AssistantScoringSelection
    monkeypatch.setattr(AssistantScoringSelection,'rank',lambda *a:SimpleNamespace(status=status,complete=False,diagnostics=SENSITIVE))
    result=service(assistant_store).recommend('owner','controlled-key','Suggest an outfit')
    assert result['status']==status and events(caplog)[0]['outcome']==status


def test_actual_nlp_internal_failure_logs_controlled_interpretation(assistant_store,monkeypatch,caplog):
    application=service(assistant_store)
    monkeypatch.setattr(application.interpreter.classifier,'classify',lambda *a:failure())
    result=application.recommend('owner','nlp-fault','Suggest an outfit')
    assert result['status']=='ProcessingError'
    assert events(caplog)[0]['stage']=='interpretation'
