"""Additive SQLite prototype auth schema; no historical table/data rewrites."""
import re
import sqlite3

TABLE = """CREATE TABLE revoked_access_tokens (
 token_sha256 TEXT NOT NULL PRIMARY KEY
   CHECK(length(token_sha256)=64 AND token_sha256 NOT GLOB '*[^0-9a-f]*'),
 user_id TEXT NOT NULL REFERENCES users(id),
 expires_at INTEGER NOT NULL CHECK(typeof(expires_at)='integer'),
 revoked_at INTEGER NOT NULL CHECK(typeof(revoked_at)='integer')
)"""
INDEX = "CREATE INDEX idx_revoked_access_tokens_expiry ON revoked_access_tokens(expires_at)"


def _normalized(sql: str) -> str:
    return re.sub(r'\s+', '', sql).lower()


def migrate_session_revocations(conn: sqlite3.Connection) -> None:
    """Caller commits on success. DDL/shape/commit errors prevent startup readiness."""
    conn.execute('BEGIN IMMEDIATE')
    for kind, name, sql in [('table', 'revoked_access_tokens', TABLE),
                            ('index', 'idx_revoked_access_tokens_expiry', INDEX)]:
        existing = conn.execute('SELECT type, sql FROM sqlite_master WHERE name=?', (name,)).fetchone()
        if existing is None:
            conn.execute(sql)
        elif existing[0] != kind or _normalized(existing[1] or '') != _normalized(sql):
            raise RuntimeError('Invalid session revocation schema.')
    if not conn.execute('PRAGMA foreign_keys').fetchone()[0]:
        raise RuntimeError('Session revocation foreign keys must be enabled.')
