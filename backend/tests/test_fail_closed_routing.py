"""J-14 authenticated routing and real disposable SQLite write boundaries."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from threading import Barrier
from unittest.mock import Mock

import pytest
from app.application.recommendation import recommendation_service as legacy
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.security import issue_access_token
from app.infrastructure import security
from app.infrastructure.workflow_runtime import configure_local_workflow
from tests.test_release_configuration import release, lifecycle
from tests.test_suitability_assistant_e2e import make, tag

TABLES = ('recommendations', 'nlp_chats', 'recommendation_items',
          'recommendation_metadata', 'recommendation_submissions', 'recommendation_item_snapshots')
TEXT = 'Suggest a casual outfit for campus with vintage style using blue colours with a vest dress'


def rows():
    with db.connection() as c:
        return {t: sorted(json.dumps(dict(r), sort_keys=True) for r in c.execute('SELECT * FROM '+t)) for t in TABLES}


def record(case, **values):
    target = os.getenv('SMART_WARDROBE_ROUTING_EVIDENCE')
    if target:
        with Path(target).open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'case': case, **values}, sort_keys=True)+'\n')


@pytest.mark.parametrize('enabled', [False, True])
@pytest.mark.parametrize('explicit', [False, True])
@pytest.mark.parametrize('key,model_invalid', [('valid-key', False), (None, False), ('bad key', True), (17, True), ('', True)])
def test_generation_matrix_no_legacy_dispatch(release, monkeypatch, enabled, explicit, key, model_invalid):
    client, create = release
    make(client, create, tags=[tag(), tag('formality', 'casual')])
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED', str(enabled).lower())
    configure_local_workflow()
    forbidden = Mock(side_effect=AssertionError('Public generation must never call legacy'))
    monkeypatch.setattr(legacy, 'create_recommendation', forbidden)
    before = rows()
    body = {'request_text': TEXT}
    if key is not None:
        body['submission_key'] = key
    response = client.post('/api/v1/recommendations'+('?pipeline=integrated' if explicit else ''), json=body)
    expected = 422 if model_invalid or (enabled and key is None) else 201 if enabled else 404
    assert response.status_code == expected, response.text
    if expected != 201:
        assert rows() == before
    if expected == 404:
        assert response.json() == {'status': 'IntegrationDisabled', 'outcome': 'IntegrationDisabled', 'complete': False}
    if expected == 201:
        assert response.json()['provenance']['scoring_profile'] == 'experimental_compatibility_decision_v1'
    forbidden.assert_not_called()
    record('matrix', enabled=enabled, explicit=explicit, key=key, http=response.status_code,
           generation_counts_before={t: len(v) for t, v in before.items()},
           generation_counts_after={t: len(v) for t, v in rows().items()})


@pytest.mark.parametrize('enabled', [False, True])
def test_authentication_validation_and_pipeline_order(release, monkeypatch, enabled):
    client, _ = release
    # The shared wardrobe fixture has an X-User-Id development header; production auth must ignore it.
    monkeypatch.setattr(security, 'ALLOW_DEVELOPMENT_IDENTITY', False)
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED', str(enabled).lower())
    configure_local_workflow()
    before = rows()
    for suffix in ['', '?pipeline=integrated']:
        url = '/api/v1/recommendations'+suffix
        # Invalid identity wins over even invalid body; authenticated model errors stay 422.
        for body in [{'request_text': TEXT}, {'request_text': '', 'submission_key': 'bad key'}]:
            assert client.post(url, headers={'Authorization': 'Bearer invalid'}, json=body).status_code == 401
        for body in [{}, {'request_text': ''}, {'request_text': TEXT, 'submission_key': 17}]:
            assert client.post(url, json=body).status_code == 422
        null_key = client.post(url, json={'request_text': TEXT, 'submission_key': None})
        assert null_key.status_code == (422 if enabled else 404)
        extra = client.post(url, json={'request_text': TEXT, 'submission_key': 'key', 'scoring_profile': 'client'})
        assert extra.status_code == (422 if enabled else 404)
    assert client.post('/api/v1/recommendations?pipeline=other', json={'request_text': TEXT}).status_code == 422
    assert rows() == before


@pytest.mark.parametrize('explicit', [False, True])
def test_repeated_and_conflicting_keys_share_integrated_receipt(release, explicit):
    client, create = release
    make(client, create, tags=[tag(), tag('formality', 'casual')])
    url = '/api/v1/recommendations'+('?pipeline=integrated' if explicit else '')
    body = {'request_text': TEXT, 'submission_key': 'repeat'}
    first = client.post(url, json=body)
    assert first.status_code == 201
    before = rows()
    replay = client.post('/api/v1/recommendations'+('' if explicit else '?pipeline=integrated'), json=body)
    assert replay.status_code == 200 and replay.json()['replayed']
    for field in ['id', 'chat_id', 'score_metadata', 'provenance', 'items', 'total_score']:
        assert replay.json()[field] == first.json()[field]
    conflict = client.post(url, json={**body, 'request_text': 'Suggest an outfit'})
    assert conflict.status_code == 409 and conflict.json()['outcome'] == 'IdempotencyConflict'
    assert rows() == before
    record('replay_conflict', explicit=explicit, first=first.json(), replay=replay.json(), conflict=conflict.json())


def test_concurrent_explicit_and_unqualified_duplicate_key(release):
    client, create = release
    make(client, create, tags=[tag(), tag('formality', 'casual')])
    barrier = Barrier(2)
    before = rows()
    def call(suffix):
        barrier.wait(timeout=10)
        response = client.post('/api/v1/recommendations'+suffix, json={'request_text': TEXT, 'submission_key': 'concurrent'})
        return response.status_code, response.json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(call, ['', '?pipeline=integrated']))
    assert sorted(code for code, _ in results) == [200, 201]
    assert len({r['id'] for _, r in results}) == len({r['chat_id'] for _, r in results}) == 1
    assert results[0][1]['score_metadata'] == results[1][1]['score_metadata']
    after = rows()
    assert {t: len(after[t])-len(before[t]) for t in TABLES} == {t: 1 for t in TABLES}
    record('concurrent', responses=[{'http': c, 'result': r} for c, r in results],
           added_rows={t: len(after[t])-len(before[t]) for t in TABLES})


def test_existing_legacy_history_save_and_visualisation_with_generation_disabled(release, monkeypatch):
    client, create = release
    garment = make(client, create, tags=[tag(), tag('formality', 'casual')])
    # Historical fixture: call the retained generator outside the public API, before disabling.
    original = legacy.create_recommendation('style-owner', 'Historical legacy outfit')
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED', 'false')
    configure_local_workflow()
    before = rows()
    for _ in range(2):
        for suffix in ['', '?pipeline=integrated']:
            response = client.post('/api/v1/recommendations'+suffix, json={'request_text': TEXT, 'submission_key': 'repeated-disabled'})
            assert response.status_code == 404
    assert rows() == before
    listed = client.get('/api/v1/recommendations').json()
    assert listed == [original] and listed[0]['items'][0]['garment_id'] == garment
    chat = client.get('/api/v1/chats/'+original['chat_id'])
    assert chat.status_code == 200 and chat.json()['request_text'] == 'Historical legacy outfit'
    foreign = {'Authorization': 'Bearer '+issue_access_token('other-owner')}
    assert client.get('/api/v1/chats/'+original['chat_id'], headers=foreign).status_code == 404
    url = '/api/v1/recommendations/'+original['id']+'/save-as-outfit'
    assert client.post(url, headers=foreign, json={}).status_code == 404
    saved = client.post(url, json={'name': 'Legacy survives'})
    assert saved.status_code == 201, saved.text
    prepared = client.post('/api/v1/visualisations/prepare', json={'outfit_id': saved.json()['id']})
    assert prepared.status_code == 200, prepared.text
    assert client.post('/api/v1/visualisations/prepare', headers=foreign, json={'outfit_id': saved.json()['id']}).status_code == 404
    assert client.get('/api/v1/wardrobe/quota').json()['used'] == 1
    # A legitimate save may update available->saved. No generation/chat/item/receipt is appended.
    after = rows()
    assert all(len(after[t]) == len(before[t]) for t in TABLES)
    with db.connection() as c:
        persisted = dict(c.execute('SELECT * FROM recommendations WHERE id=?', (original['id'],)).fetchone())
    assert persisted['compatibility_score'] == original['compatibility_score']
    record('historical_legacy', id=original['id'], chat_id=original['chat_id'], saved=saved.json(), prepared=prepared.json())
