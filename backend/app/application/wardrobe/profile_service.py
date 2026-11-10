"""Wardrobe-profile ownership and request selection.

An account owns one shared wardrobe. A wearer profile holds the person-specific
preferences, conversations, base images and visualisation history for someone
who uses that wardrobe.
"""

from __future__ import annotations

import re
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import AsyncIterator

from fastapi import Depends, Header, HTTPException

from app.infrastructure.security import current_user_id

from app.infrastructure.persistence.postgresql_repository import connection, utcnow


_selected_profile_id: ContextVar[str | None] = ContextVar("selected_wardrobe_profile_id", default=None)


def _clean_name(value: str) -> str:
    value = value.strip()
    if not 1 <= len(value) <= 60 or not re.search(r"\S", value):
        raise HTTPException(422, "Enter a wardrobe profile name of 1 to 60 characters.")
    return value


def ensure_default_profile(conn, user_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM wardrobe_profiles WHERE user_id=? AND is_default=1 AND status='active'",
        (user_id,),
    ).fetchone()
    if row:
        return dict(row)
    now, identifier = utcnow(), str(uuid.uuid4())
    conn.execute(
        "INSERT INTO wardrobe_profiles (id,user_id,name,is_default,status,created_at,updated_at) VALUES (?,?,?,1,'active',?,?)",
        (identifier, user_id, "My wardrobe", now, now),
    )
    return dict(conn.execute("SELECT * FROM wardrobe_profiles WHERE id=?", (identifier,)).fetchone())


def list_profiles(user_id: str, status: str = 'active') -> list[dict]:
    if status not in ('active','archived','all'):
        raise HTTPException(422,'Unknown wearer status filter.')
    with connection() as conn:
        if status == 'active':
            ensure_default_profile(conn, user_id)
        predicate = '' if status == 'all' else ' AND status=?'
        args = (user_id,) if status == 'all' else (user_id,status)
        rows = conn.execute('SELECT id,name,status,is_default,created_at,updated_at FROM wardrobe_profiles WHERE user_id=?'+predicate+' ORDER BY is_default DESC,LOWER(name),created_at,id',args).fetchall()
    return [{**dict(row),'is_default':bool(row['is_default'])} for row in rows]


def create_profile(user_id: str, name: str) -> dict:
    name = _clean_name(name)
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        ensure_default_profile(conn, user_id)
        if conn.execute("SELECT 1 FROM wardrobe_profiles WHERE user_id=? AND status='active' AND LOWER(name)=LOWER(?)", (user_id, name)).fetchone():
            raise HTTPException(409, "A wardrobe profile with that name already exists.")
        now, identifier = utcnow(), str(uuid.uuid4())
        conn.execute(
            "INSERT INTO wardrobe_profiles (id,user_id,name,is_default,status,created_at,updated_at) VALUES (?,?,?,0,'active',?,?)",
            (identifier, user_id, name, now, now),
        )
        row = conn.execute("SELECT id,name,is_default,created_at,updated_at FROM wardrobe_profiles WHERE id=?", (identifier,)).fetchone()
    return {**dict(row), "is_default": bool(row["is_default"])}


def historical_profile(conn, user_id: str, profile_id: str) -> dict:
    """Owned profile lookup for historical reads; never creates or activates one."""
    row = conn.execute("SELECT * FROM wardrobe_profiles WHERE id=? AND user_id=?", (profile_id,user_id)).fetchone()
    if not row:
        raise HTTPException(404, "The wardrobe profile was not found.")
    return dict(row)


def require_active_profile(conn, user_id: str, profile_id: str) -> dict:
    row = historical_profile(conn,user_id,profile_id)
    if row['status'] != 'active':
        raise HTTPException(409, {'code':'WearerArchived','message':'This wearer is archived. Choose an active wearer for new work.'})
    return row


def delete_profile(user_id: str, profile_id: str) -> dict:
    with connection() as conn:
        historical_profile(conn,user_id,profile_id)
    raise HTTPException(409, {'code':'ProfileArchiveRequired','message':'Use Archive wearer to preserve shared inventory and history.'})


def archive_profile(user_id: str, profile_id: str) -> dict:
    """Atomically archive intent, retaining all original records and media."""
    with connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        target = require_active_profile(conn,user_id,profile_id)
        others = conn.execute("SELECT id FROM wardrobe_profiles WHERE user_id=? AND status='active' AND id<>? ORDER BY is_default DESC,created_at,id",(user_id,profile_id)).fetchall()
        if not others:
            raise HTTPException(409, {'code':'LastActiveWearer','message':'Create another active wearer before archiving this one.'})
        jobs = conn.execute("SELECT 1 FROM processing_jobs WHERE user_id=? AND profile_id=? AND status IN ('queued','processing','review_required') LIMIT 1",(user_id,profile_id)).fetchone()
        visuals = conn.execute("SELECT 1 FROM visualisations WHERE user_id=? AND profile_id=? AND status IN ('queued','processing') LIMIT 1",(user_id,profile_id)).fetchone()
        if jobs or visuals:
            raise HTTPException(409, {'code':'ProfileBusy','message':'Finish or cancel this wearer’s pending work before archival.'})
        now = utcnow()
        conn.execute("UPDATE wardrobe_profiles SET status='archived',is_default=0,updated_at=? WHERE id=? AND user_id=?",(now,profile_id,user_id))
        successor = others[0]['id']
        if target['is_default']:
            conn.execute('UPDATE wardrobe_profiles SET is_default=1,updated_at=? WHERE id=? AND user_id=?',(now,successor,user_id))
    return {'archived_profile_id':profile_id,'next_profile_id':successor,'status':'archived'}


def selected_profile(user_id: str, profile_id: str | None) -> dict:
    with connection() as conn:
        default = ensure_default_profile(conn, user_id)
        identifier = profile_id or default["id"]
        return require_active_profile(conn,user_id,identifier)



async def active_profile_id(user_id: str = Depends(current_user_id), x_wardrobe_profile_id: str | None = Header(default=None)) -> AsyncIterator[str]:
    profile = selected_profile(user_id, x_wardrobe_profile_id)
    token = _selected_profile_id.set(profile["id"])
    try:
        yield profile["id"]
    finally:
        _selected_profile_id.reset(token)


def current_profile_id() -> str | None:
    return _selected_profile_id.get()


@contextmanager
def profile_scope(profile_id: str):
    token = _selected_profile_id.set(profile_id)
    try:
        yield
    finally:
        _selected_profile_id.reset(token)


def selected_history_profile(user_id: str,profile_id: str | None) -> dict:
    """Read-only selection; absent subjects cannot create phantom profiles."""
    with connection() as conn:
        if not conn.execute("SELECT 1 FROM users WHERE id=? AND account_status='active'",(user_id,)).fetchone():
            raise HTTPException(404,"Completed chat not found.")
        if profile_id is None:
            row=conn.execute("SELECT id FROM wardrobe_profiles WHERE user_id=? AND is_default=1 AND status='active'",(user_id,)).fetchone()
            if row is None:raise HTTPException(404,"Completed chat not found.")
            profile_id=row['id']
        return require_active_profile(conn,user_id,profile_id)
