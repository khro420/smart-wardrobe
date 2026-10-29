"""Authoritative per-bearer revocation in the configured SQLite prototype DB."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import logging
import secrets
import sqlite3
import time

from app.infrastructure.persistence import postgresql_repository as provider

logger = logging.getLogger('app.authentication.failure')


class RevocationUnavailable(Exception):
    """No authentication or logout success is permitted after a store failure."""


def record_failure(stage: str) -> None:
    # Fixed fields only: never stringify exceptions, credentials, digests or owners.
    if stage not in {'lookup', 'write', 'migration'}:
        stage = 'lookup'
    event = {'event': 'authentication_storage_failure', 'stage': stage,
             'error_kind': 'StorageUnavailable', 'diagnostic_id': secrets.token_hex(16),
             'timestamp': datetime.now(timezone.utc).isoformat()}
    try:
        logger.error(json.dumps(event), extra={'authentication_failure': event})
    except Exception:
        pass  # A failing sink must not turn a fail-closed response into success.


@contextmanager
def _connection():
    # Independent connections and a bounded wait; existing global timeouts unchanged.
    conn = sqlite3.connect(provider.DATABASE_PATH, timeout=1.0)
    try:
        conn.execute('PRAGMA foreign_keys=ON')
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _matches(row, user_id: str, expires_at: int) -> None:
    if row is not None and (row[0] != user_id or row[1] != expires_at):
        raise RevocationUnavailable()


def is_revoked(digest: str, user_id: str, expires_at: int) -> bool:
    try:
        with _connection() as conn:
            row = conn.execute('SELECT user_id, expires_at FROM revoked_access_tokens WHERE token_sha256=?', (digest,)).fetchone()
            _matches(row, user_id, expires_at)
        return row is not None
    except Exception:
        record_failure('lookup')
        raise RevocationUnavailable() from None


def revoke(digest: str, user_id: str, expires_at: int) -> None:
    try:
        with _connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT user_id, expires_at FROM revoked_access_tokens WHERE token_sha256=?', (digest,)).fetchone()
            _matches(row, user_id, expires_at)
            if row is None:
                conn.execute('INSERT INTO revoked_access_tokens VALUES (?, ?, ?, ?)',
                             (digest, user_id, expires_at, int(time.time())))
        # The context has committed before acknowledgement is allowed.
    except Exception:
        record_failure('write')
        raise RevocationUnavailable() from None


def cleanup_expired(now: int, limit: int = 100) -> int:
    """Explicit bounded housekeeping only; never automatically run during requests."""
    if type(now) is not int or type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError('Invalid cleanup bounds.')
    try:
        with _connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            count = conn.execute('DELETE FROM revoked_access_tokens WHERE token_sha256 IN '
                                 '(SELECT token_sha256 FROM revoked_access_tokens WHERE expires_at < ? '
                                 'ORDER BY expires_at, token_sha256 LIMIT ?)', (now, limit)).rowcount
        return count
    except Exception:
        record_failure('write')
        raise RevocationUnavailable() from None
