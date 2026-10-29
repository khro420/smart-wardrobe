"""J22 real SQLite, authenticated HTTP, fault, restart and token-contract checks."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from threading import Barrier, Event
import time

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure import security
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.persistence import session_revocation_store as store
from app.infrastructure.persistence.session_revocation_migrations import migrate_session_revocations, TABLE

PASSWORD = 'J22-disposable-password-123'


def audit(case, **values):
    folder = os.getenv('SMART_WARDROBE_LOGOUT_EVIDENCE')
    if folder:
        with (Path(folder) / 'api-evidence.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'case': case, **values}) + '\n')


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DATABASE_PATH', tmp_path / 'logout.sqlite')
    monkeypatch.setattr(security, 'ALLOW_DEVELOPMENT_IDENTITY', False)
    with TestClient(app) as http:
        yield http


def account(client, name='owner'):
    email = name + '@example.test'
    response = client.post('/api/v1/account/register', json={'email': email, 'password': PASSWORD,
                           'password_confirmation': PASSWORD, 'display_name': name})
    assert response.status_code == 201
    response = client.post('/api/v1/account/login', json={'email': email, 'password': PASSWORD})
    assert response.status_code == 200
    return response.json()['access_token']


def header(token):
    return {'Authorization': 'Bearer ' + token}


def signed(payload):
    return payload + '.' + hmac.new(security.TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def rows():
    with db.connection() as conn:
        return [tuple(r) for r in conn.execute('SELECT * FROM revoked_access_tokens ORDER BY token_sha256')]


def unrelated():
    with db.connection() as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name!='revoked_access_tokens'")]
        return {name: sorted([tuple(r) for r in conn.execute('SELECT * FROM "' + name + '"')], key=repr) for name in tables}


def test_logout_copies_retry_sessions_and_exact_persistence(client):
    first = account(client)
    claims = security.verified_bearer(first)
    second = client.post('/api/v1/account/login', json={'email': 'owner@example.test', 'password': PASSWORD}).json()['access_token']
    foreign = account(client, 'foreign')
    before = unrelated()
    response = client.post('/api/v1/account/logout', headers=header(first))
    assert response.status_code == 204 and response.content == b''
    original = rows()
    assert len(original) == 1 and original[0][:3] == (hashlib.sha256(first.encode()).hexdigest(), claims.user_id, claims.expires_at)
    assert first not in repr(original) and first.split('.')[-1] not in repr(original)
    assert client.get('/api/v1/account/profile', headers=header(first)).status_code == 401
    assert client.post('/api/v1/account/logout', headers=header(first)).status_code == 204
    assert rows() == original and unrelated() == before
    assert client.get('/api/v1/account/profile', headers=header(second)).status_code == 200
    assert client.get('/api/v1/account/profile', headers=header(foreign)).status_code == 200
    new = client.post('/api/v1/account/login', json={'email': 'owner@example.test', 'password': PASSWORD}).json()['access_token']
    assert new != first and client.get('/api/v1/account/profile', headers=header(new)).status_code == 200
    audit('logout_copies_retry_sessions', logout=204, copied=401, independent=200, immediate_relogin=200, rows=1, unrelated_unchanged=True)


def test_same_second_unique_signed_tokens(client, monkeypatch):
    token = account(client)
    owner = security.token_user_id(token)
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 24, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(security, 'datetime', Frozen)
    tokens = [security.issue_access_token(owner) for _ in range(100)]
    assert len(set(tokens)) == 100 and len({t.split('.')[2] for t in tokens}) == 1
    assert all(security.token_user_id(t) == owner for t in tokens)
    assert client.post('/api/v1/account/logout', headers=header(tokens[0])).status_code == 204
    fresh = security.issue_access_token(owner)
    assert fresh not in tokens and client.get('/api/v1/account/profile', headers=header(fresh)).status_code == 200
    audit('frozen_second', issued_distinct=101, expiry_seconds=1, immediate_login=200)


def test_legacy_identical_tokens_and_inclusive_expiry_cleanup(client, monkeypatch):
    owner = security.token_user_id(account(client))
    current = int(time.time())
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromtimestamp(current, timezone.utc)
    monkeypatch.setattr(security, 'datetime', Frozen)
    legacy = signed(f'{owner}.{current}')
    assert client.get('/api/v1/account/profile', headers=header(legacy)).status_code == 200
    assert client.post('/api/v1/account/logout', headers=header(legacy)).status_code == 204
    assert store.cleanup_expired(current) == 0
    assert client.get('/api/v1/account/profile', headers=header(legacy)).status_code == 401
    assert client.post('/api/v1/account/logout', headers=header(legacy)).status_code == 204
    assert store.cleanup_expired(current + 1) == 1
    # It is expired once wall time moves beyond its original inclusive second.
    current += 1
    assert client.get('/api/v1/account/profile', headers=header(legacy)).status_code == 401
    assert client.post('/api/v1/account/logout', headers=header(legacy)).status_code == 401
    audit('legacy_expiry', valid_at_expiry=200, revoked_at_expiry=401, cleanup_at_expiry=0, cleanup_after_expiry=1)


def test_legacy_owner_prefix_is_unambiguous_and_new_claims_are_signed(client):
    # Legacy owner IDs may contain dots, including what looks like a v2 prefix.
    db.ensure_user('v2.owner.with')
    legacy = signed(f'v2.owner.with.{int(time.time()) + 60}')
    assert client.get('/api/v1/account/profile', headers=header(legacy)).status_code == 200
    assert client.post('/api/v1/account/logout', headers=header(legacy)).status_code == 204
    assert client.get('/api/v1/account/profile', headers=header(legacy)).status_code == 401
    token = account(client)
    parts = token.split('.')
    for index, replacement in [(0, 'v3'), (1, 'eA'), (2, str(int(parts[2]) + 1)), (3, '0'*32)]:
        changed = parts.copy()
        changed[index] = replacement
        assert security.verified_bearer('.'.join(changed)) is None


@pytest.mark.parametrize('value', ['', 'bad', 'v2.bad.9999999999.bad.bad', 'owner.invalid.signature'])
def test_invalid_credentials_no_write_or_development_bypass(client, monkeypatch, value):
    monkeypatch.setattr(security, 'ALLOW_DEVELOPMENT_IDENTITY', True)
    before = unrelated()
    headers = {**header(value), 'X-User-Id': 'bypass'}
    assert client.get('/api/v1/account/profile', headers=headers).status_code == 401
    assert client.post('/api/v1/account/logout', headers=headers).status_code == 401
    assert not rows() and unrelated() == before


@pytest.mark.parametrize('payload', ['v2.eA.9999999999.short', 'v2.@@@.9999999999.' + 'a'*32,
                                     'v3.eA.9999999999.' + 'a'*32,
                                     'v2.eA.bad.' + 'a'*32, 'x.0', '.9999999999'])
def test_signed_malformed_claims_rejected(client, payload):
    token = payload + '.' + hmac.new(security.TOKEN_SECRET.encode(), b'wardrobe-access-v2\0' + payload.encode(), hashlib.sha256).hexdigest()
    assert security.verified_bearer(token) is None
    assert client.post('/api/v1/account/logout', headers=header(token)).status_code == 401


def test_tampering_normalization_and_development_path(client, monkeypatch):
    token = account(client)
    tampered = token[:-1] + ('0' if token[-1] != '0' else '1')
    assert client.get('/api/v1/account/profile', headers=header(tampered)).status_code == 401
    assert client.get('/api/v1/account/profile').status_code == 401
    monkeypatch.setattr(security, 'ALLOW_DEVELOPMENT_IDENTITY', True)
    assert client.get('/api/v1/account/profile', headers={'X-User-Id': 'fixture-only'}).status_code == 200
    assert client.get('/api/v1/account/profile', headers={'Authorization': 'Basic invalid', 'X-User-Id': 'fixture-only'}).status_code == 401
    assert client.post('/api/v1/account/logout', headers={'Authorization': 'bEaReR   ' + token + ' '}).status_code == 204
    assert rows()[0][0] == hashlib.sha256(token.encode()).hexdigest()
    assert client.get('/api/v1/account/profile', headers={**header(token), 'X-User-Id': 'fixture-only'}).status_code == 401


def test_concurrent_duplicate_logout_and_restart_process(client):
    token = account(client)
    barrier = Barrier(2)
    def revoke(_):
        barrier.wait()
        return client.post('/api/v1/account/logout', headers=header(token)).status_code
    with ThreadPoolExecutor(2) as pool:
        assert list(pool.map(revoke, range(2))) == [204, 204]
    assert len(rows()) == 1
    # Fresh Python process, same DB/secret. Pass bearer through stdin only, not argv/logs.
    code = """import json,sys
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as c:
    r=c.get('/api/v1/account/profile',headers={'Authorization':'Bearer '+sys.stdin.read()})
    print(json.dumps({'copied_after_restart':r.status_code}))
"""
    env = {**os.environ, 'SMART_WARDROBE_DATABASE': str(db.DATABASE_PATH),
           'SMART_WARDROBE_TOKEN_SECRET': security.TOKEN_SECRET, 'SMART_WARDROBE_ALLOW_DEV_IDENTITY': 'false'}
    result = subprocess.run([sys.executable, '-B', '-c', code], input=token, text=True, env=env, capture_output=True, timeout=30)
    assert result.returncode == 0 and json.loads(result.stdout)['copied_after_restart'] == 401
    assert len(rows()) == 1
    audit('concurrent_and_restart', concurrent=[204, 204], rows=1, independent_process_copied=401, process_exit=0)


def test_already_authenticated_request_can_finish_after_logout(client, monkeypatch):
    token = account(client)
    checked, release = Event(), Event()
    original = store.is_revoked
    def paused(*args):
        result = original(*args)
        if not checked.is_set():
            checked.set()
            assert release.wait(10)
        return result
    monkeypatch.setattr(store, 'is_revoked', paused)
    with ThreadPoolExecutor(1) as pool:
        in_flight = pool.submit(client.get, '/api/v1/account/profile', headers=header(token))
        try:
            assert checked.wait(10)
            assert client.post('/api/v1/account/logout', headers=header(token)).status_code == 204
        finally:
            release.set()
        assert in_flight.result(timeout=10).status_code == 200
    assert client.get('/api/v1/account/profile', headers=header(token)).status_code == 401
    audit('concurrent_auth_boundary', authenticated_before_commit=200, fresh_after_ack=401)


@pytest.mark.parametrize('path', ['/account/profile', '/account/preferences', '/account/preference-options',
                                 '/wardrobe/garments', '/wardrobe/outfits', '/wardrobe/quota',
                                 '/chats', '/recommendations', '/media/not-owned',
                                 '/visualisations/person-images', '/processing/jobs/missing'])
def test_revoked_route_families_and_media(client, path):
    token = account(client)
    assert client.post('/api/v1/account/logout', headers=header(token)).status_code == 204
    assert client.get('/api/v1' + path, headers=header(token)).status_code == 401


def test_all_protected_dependencies_are_authoritative():
    from app.api import (account_routes, media_routes, wardrobe_routes, garment_processing_routes,
                         recommendation_routes, chat_history_routes, visualisation_routes)
    protected = 0
    # This FastAPI version wraps included routers in app.routes; inspect the
    # actual seven mounted API routers rather than counting wrapper objects.
    routes = [route for module in (account_routes, media_routes, wardrobe_routes, garment_processing_routes,
                                   recommendation_routes, chat_history_routes, visualisation_routes)
              for route in module.router.routes]
    for route in routes:
        dependency = getattr(route, 'dependant', None)
        if dependency:
            for child in dependency.dependencies:
                if child.call is security.current_user_id:
                    protected += 1
                if child.call is security.logout_bearer:
                    assert route.endpoint is account_routes.logout
    # Additive contextual-review endpoint uses the same authoritative dependency.
    review_route = next(route for route in wardrobe_routes.router.routes
                       if route.endpoint is wardrobe_routes.contextual_suitability)
    assert any(child.call is security.current_user_id for child in review_route.dependant.dependencies)
    assert protected == 36


@pytest.mark.parametrize('operation', ['lookup', 'logout'])
def test_missing_schema_fails_closed_no_dev_fallback(client, monkeypatch, operation):
    token = account(client)
    monkeypatch.setattr(security, 'ALLOW_DEVELOPMENT_IDENTITY', True)
    with db.connection() as conn:
        conn.execute('DROP TABLE revoked_access_tokens')
    response = client.get('/api/v1/account/profile', headers={**header(token), 'X-User-Id': 'bypass'}) if operation == 'lookup' else client.post('/api/v1/account/logout', headers=header(token))
    assert response.status_code == 503 and 'sqlite' not in response.text.lower()
    audit('missing_schema_' + operation, http=503)


@pytest.mark.parametrize('operation', ['lookup', 'logout'])
def test_exclusive_database_lock_bounded_fail_closed(client, operation):
    token = account(client)
    conn = sqlite3.connect(db.DATABASE_PATH)
    conn.execute('BEGIN EXCLUSIVE')
    started = time.perf_counter()
    try:
        response = client.get('/api/v1/account/profile', headers=header(token)) if operation == 'lookup' else client.post('/api/v1/account/logout', headers=header(token))
    finally:
        elapsed = time.perf_counter() - started
        conn.rollback()
        conn.close()
    assert response.status_code == 503 and .8 <= elapsed < 4
    assert not rows()
    audit('locked_' + operation, http=503, elapsed_seconds=elapsed, writes=0)


def test_write_trigger_rolls_back_then_retry(client):
    token = account(client)
    before = unrelated()
    with db.connection() as conn:
        conn.execute("CREATE TRIGGER deny_revoke BEFORE INSERT ON revoked_access_tokens BEGIN SELECT RAISE(ABORT,'private credential sentinel'); END")
    response = client.post('/api/v1/account/logout', headers=header(token))
    assert response.status_code == 503 and 'sentinel' not in response.text
    assert not rows() and unrelated() == before
    with db.connection() as conn:
        conn.execute('DROP TRIGGER deny_revoke')
    assert client.get('/api/v1/account/profile', headers=header(token)).status_code == 200
    assert client.post('/api/v1/account/logout', headers=header(token)).status_code == 204


@pytest.mark.parametrize('operation', ['lookup', 'logout'])
def test_read_or_commit_error_controlled_and_no_false_ack(client, monkeypatch, operation):
    token = account(client)
    connect = sqlite3.connect
    class Fault(sqlite3.Connection):
        def execute(self, sql, *args):
            if operation == 'lookup' and sql.startswith('SELECT user_id'):
                raise sqlite3.OperationalError('private token sentinel')
            return super().execute(sql, *args)
        def commit(self):
            if operation == 'logout':
                raise sqlite3.OperationalError('private commit sentinel')
            return super().commit()
    monkeypatch.setattr(sqlite3, 'connect', lambda *args, **kwargs: connect(*args, **kwargs, factory=Fault))
    response = client.get('/api/v1/account/profile', headers=header(token)) if operation == 'lookup' else client.post('/api/v1/account/logout', headers=header(token))
    assert response.status_code == 503 and 'sentinel' not in response.text
    monkeypatch.setattr(sqlite3, 'connect', connect)
    # The commit failure rolled the real INSERT back.
    with connect(db.DATABASE_PATH) as conn:
        assert conn.execute('SELECT COUNT(*) FROM revoked_access_tokens').fetchone()[0] == 0


def test_inconsistent_row_metadata_is_not_treated_as_unrevoked(client):
    token = account(client)
    claims = security.verified_bearer(token)
    with db.connection() as conn:
        conn.execute('INSERT INTO revoked_access_tokens VALUES(?,?,?,?)', (claims.digest, claims.user_id, claims.expires_at + 1, int(time.time())))
    assert client.get('/api/v1/account/profile', headers=header(token)).status_code == 503
    assert client.post('/api/v1/account/logout', headers=header(token)).status_code == 503


def test_logging_redaction_and_failing_sink(client, monkeypatch, caplog):
    token = account(client)
    claims = security.verified_bearer(token)
    class Hostile(sqlite3.Error):
        def __str__(self):
            raise AssertionError('Must not stringify private errors')
    @contextmanager
    def broken():
        raise Hostile(token, claims.digest, 'private-password-header-request')
        yield
    monkeypatch.setattr(store, '_connection', broken)
    assert client.get('/api/v1/account/profile', headers=header(token)).status_code == 503
    assert client.post('/api/v1/account/logout', headers=header(token)).status_code == 503
    assert token not in caplog.text and claims.digest not in caplog.text and 'private-password-header-request' not in caplog.text
    events = [json.loads(r.message) for r in caplog.records if r.name == store.logger.name]
    assert {r['stage'] for r in events} == {'lookup', 'write'}
    assert all(set(r) == {'event', 'stage', 'error_kind', 'diagnostic_id', 'timestamp'} for r in events)
    monkeypatch.setattr(store.logger, 'error', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('sink private')))
    assert client.post('/api/v1/account/logout', headers=header(token)).status_code == 503


def test_async_auth_lookup_does_not_block_event_loop(client, monkeypatch):
    token = account(client)
    def slow(*args):
        time.sleep(.15)
        return False
    monkeypatch.setattr(store, 'is_revoked', slow)
    async def check():
        task = asyncio.create_task(security.current_user_id('Bearer ' + token, None))
        await asyncio.sleep(.03)
        assert not task.done()
        return await task
    assert asyncio.run(check()) == security.token_user_id(token)


def test_migration_idempotent_preserves_all_rows(client):
    token = account(client)
    assert client.post('/api/v1/account/logout', headers=header(token)).status_code == 204
    before, revoked = unrelated(), rows()
    db.initialise_database()
    db.initialise_database()
    assert unrelated() == before and rows() == revoked
    with db.connection() as conn:
        assert conn.execute("PRAGMA index_info('idx_revoked_access_tokens_expiry')").fetchone()[2] == 'expires_at'
    audit('migration', idempotent=True, unrelated_unchanged=True, retained_revocations=True)


@pytest.mark.parametrize('kind', ['weak_table', 'wrong_index', 'ddl_failure', 'commit_failure'])
def test_unsafe_migration_prevents_startup(tmp_path, monkeypatch, kind):
    monkeypatch.setattr(db, 'DATABASE_PATH', tmp_path / 'bad-migration.sqlite')
    db.initialise_database()
    with db.connection() as conn:
        conn.execute('DROP TABLE revoked_access_tokens')
        if kind == 'weak_table':
            conn.execute('CREATE TABLE revoked_access_tokens(token_sha256 TEXT PRIMARY KEY, user_id TEXT, expires_at INTEGER, revoked_at INTEGER)')
        elif kind == 'wrong_index':
            conn.execute(TABLE)
            conn.execute('CREATE INDEX idx_revoked_access_tokens_expiry ON revoked_access_tokens(user_id)')
    if kind in {'ddl_failure', 'commit_failure'}:
        connect = sqlite3.connect
        class Fault(sqlite3.Connection):
            auth_ddl = False
            def execute(self, sql, *args):
                if sql.startswith('CREATE TABLE revoked_access_tokens'):
                    self.auth_ddl = True
                    if kind == 'ddl_failure':
                        raise sqlite3.OperationalError('private migration sentinel')
                return super().execute(sql, *args)
            def commit(self):
                if self.auth_ddl and kind == 'commit_failure':
                    raise sqlite3.OperationalError('private commit sentinel')
                return super().commit()
        monkeypatch.setattr(sqlite3, 'connect', lambda *a, **k: connect(*a, **k, factory=Fault))
    with pytest.raises(RuntimeError, match='Authentication storage initialization failed'):
        with TestClient(app):
            pytest.fail('Unsafe startup must not become ready')


def test_cleanup_is_bounded_and_constraints_reject_invalid_rows(client):
    token = account(client)
    owner = security.token_user_id(token)
    for index in range(4):
        store.revoke(hashlib.sha256(str(index).encode()).hexdigest(), owner, 10)
    assert store.cleanup_expired(10, 2) == 0
    assert store.cleanup_expired(11, 2) == 2 and len(rows()) == 2
    for digest, expiry in [('bad', 1), ('f'*64, 'not_integer')]:
        with pytest.raises(sqlite3.IntegrityError):
            with db.connection() as conn:
                conn.execute('INSERT INTO revoked_access_tokens VALUES(?,?,?,?)', (digest, owner, expiry, 1))
    with pytest.raises(ValueError):
        store.cleanup_expired(11, 1001)
