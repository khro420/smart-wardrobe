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
from app.infrastructure.config import MEDIA_DIR


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


def list_profiles(user_id: str) -> list[dict]:
    with connection() as conn:
        ensure_default_profile(conn, user_id)
        rows = conn.execute(
            "SELECT id,name,is_default,created_at,updated_at FROM wardrobe_profiles WHERE user_id=? AND status='active' ORDER BY is_default DESC, LOWER(name), created_at",
            (user_id,),
        ).fetchall()
    return [{**dict(row), "is_default": bool(row["is_default"])} for row in rows]


def create_profile(user_id: str, name: str) -> dict:
    name = _clean_name(name)
    with connection() as conn:
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


def _profile_media_ids(conn, user_id: str, profile_id: str) -> set[str]:
    """Collect media produced for this profile before its rows are removed."""
    values: set[str] = set()
    queries = (
        "SELECT source_media_id AS media_id FROM processing_jobs WHERE user_id=? AND profile_id=?",
        "SELECT p.crop_media_id AS media_id FROM processing_items p JOIN processing_jobs j ON j.id=p.job_id WHERE j.user_id=? AND j.profile_id=?",
        "SELECT p.mask_media_id AS media_id FROM processing_items p JOIN processing_jobs j ON j.id=p.job_id WHERE j.user_id=? AND j.profile_id=?",
        "SELECT p.vtoff_media_id AS media_id FROM processing_items p JOIN processing_jobs j ON j.id=p.job_id WHERE j.user_id=? AND j.profile_id=?",
        "SELECT p.mirror_media_id AS media_id FROM processing_items p JOIN processing_jobs j ON j.id=p.job_id WHERE j.user_id=? AND j.profile_id=?",
        "SELECT p.preferred_media_id AS media_id FROM processing_items p JOIN processing_jobs j ON j.id=p.job_id WHERE j.user_id=? AND j.profile_id=?",
        "SELECT preferred_media_id AS media_id FROM garments WHERE user_id=? AND profile_id=?",
        "SELECT v.output_media_id AS media_id FROM visualisations v WHERE v.user_id=? AND (v.outfit_id IN (SELECT id FROM outfits WHERE profile_id=?) OR v.recommendation_id IN (SELECT id FROM recommendations WHERE profile_id=?))",
    )
    for query in queries:
        values.update(str(row["media_id"]) for row in conn.execute(query, (user_id, profile_id, *(() if "recommendation_id" not in query else (profile_id,)))).fetchall() if row["media_id"])
    return values


def _unreferenced_media(conn, user_id: str, media_ids: set[str]) -> list[dict]:
    retained: list[dict] = []
    for media_id in media_ids:
        referenced = conn.execute(
            "SELECT 1 WHERE EXISTS (SELECT 1 FROM processing_jobs WHERE source_media_id=?) "
            "OR EXISTS (SELECT 1 FROM processing_items WHERE crop_media_id=? OR mask_media_id=? OR vtoff_media_id=? OR mirror_media_id=? OR preferred_media_id=?) "
            "OR EXISTS (SELECT 1 FROM garments WHERE preferred_media_id=?) "
            "OR EXISTS (SELECT 1 FROM person_images WHERE media_id=?) "
            "OR EXISTS (SELECT 1 FROM visualisations WHERE output_media_id=? OR person_media_id=?) "
            "OR EXISTS (SELECT 1 FROM visualisation_items WHERE source_media_id=?)",
            (media_id, media_id, media_id, media_id, media_id, media_id, media_id, media_id, media_id, media_id, media_id),
        ).fetchone()
        if referenced:
            continue
        row = conn.execute("SELECT id,storage_key FROM media_assets WHERE id=? AND user_id=? AND status='available'", (media_id, user_id)).fetchone()
        if row:
            conn.execute("UPDATE media_assets SET status='archived' WHERE id=?", (media_id,))
            retained.append(dict(row))
    return retained


def delete_profile(user_id: str, profile_id: str) -> dict:
    """Remove one wearer while retaining the account's shared wardrobe."""
    removed_media: list[dict] = []
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        profiles = conn.execute("SELECT * FROM wardrobe_profiles WHERE user_id=? AND status='active' ORDER BY is_default DESC,created_at", (user_id,)).fetchall()
        target = next((row for row in profiles if row["id"] == profile_id), None)
        if target is None:
            raise HTTPException(404, "The wardrobe profile was not found.")
        if len(profiles) <= 1:
            raise HTTPException(409, "Create another wardrobe profile before deleting your only wardrobe.")
        successor = next(row for row in profiles if row["id"] != profile_id)
        media_ids = _profile_media_ids(conn, user_id, profile_id)
        visualisation_ids = [row["id"] for row in conn.execute(
            "SELECT id FROM visualisations WHERE user_id=? AND profile_id=?",
            (user_id, profile_id),
        ).fetchall()]
        if visualisation_ids:
            marks = ",".join("?" for _ in visualisation_ids)
            conn.execute(f"DELETE FROM visualisation_items WHERE visualisation_id IN ({marks})", visualisation_ids)
            conn.execute(f"DELETE FROM visualisations WHERE id IN ({marks})", visualisation_ids)
        conn.execute("DELETE FROM person_images WHERE user_id=? AND profile_id=?", (user_id, profile_id))
        recommendation_ids = [row["id"] for row in conn.execute("SELECT id FROM recommendations WHERE user_id=? AND profile_id=?", (user_id, profile_id)).fetchall()]
        if recommendation_ids:
            marks = ",".join("?" for _ in recommendation_ids)
            conn.execute(f"DELETE FROM recommendation_item_snapshots WHERE recommendation_id IN ({marks})", recommendation_ids)
            conn.execute(f"DELETE FROM recommendation_items WHERE recommendation_id IN ({marks})", recommendation_ids)
            conn.execute(f"DELETE FROM recommendation_metadata WHERE recommendation_id IN ({marks})", recommendation_ids)
            conn.execute(f"DELETE FROM recommendation_submissions WHERE recommendation_id IN ({marks})", recommendation_ids)
            conn.execute(f"DELETE FROM recommendations WHERE id IN ({marks})", recommendation_ids)
        conn.execute("DELETE FROM user_preferences WHERE user_id=? AND profile_id=?", (user_id, profile_id))
        conn.execute("DELETE FROM nlp_chats WHERE user_id=? AND profile_id=?", (user_id, profile_id))
        if target["is_default"]:
            conn.execute("UPDATE wardrobe_profiles SET is_default=1,updated_at=? WHERE id=?", (utcnow(), successor["id"]))
        conn.execute("DELETE FROM wardrobe_profiles WHERE id=? AND user_id=?", (profile_id, user_id))
        removed_media = _unreferenced_media(conn, user_id, media_ids)
    for media in removed_media:
        (MEDIA_DIR / media["storage_key"]).unlink(missing_ok=True)
    return {"deleted_profile_id": profile_id, "next_profile_id": successor["id"], "deleted_media_count": len(removed_media)}


def selected_profile(user_id: str, profile_id: str | None) -> dict:
    with connection() as conn:
        default = ensure_default_profile(conn, user_id)
        identifier = profile_id or default["id"]
        row = conn.execute(
            "SELECT * FROM wardrobe_profiles WHERE id=? AND user_id=? AND status='active'",
            (identifier, user_id),
        ).fetchone()
    if not row:
        raise HTTPException(404, "The selected wardrobe profile was not found for this account.")
    return dict(row)


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
