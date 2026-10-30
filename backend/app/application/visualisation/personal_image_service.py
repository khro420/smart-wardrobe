import uuid

from fastapi import HTTPException

from app.application.ports.visualisation_repository import connection, runtime, utcnow


def require_person(conn, person_image_id: str, user_id: str, profile_id: str | None = None):
    profile_filter = "AND p.profile_id=? " if profile_id else ""
    row = conn.execute(
        "SELECT p.* FROM person_images p JOIN media_assets m ON m.id=p.media_id "
        "WHERE p.id=? AND p.user_id=? AND p.status='available' " + profile_filter
        + "AND m.user_id=? AND m.status='available' AND m.media_type='person_image'",
        (person_image_id, user_id, profile_id, user_id) if profile_id else (person_image_id, user_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(422, "The selected personal image is unavailable.")
    runtime().media.path_for_owner(row["media_id"], user_id)
    return row


def list_person_images(user_id: str, profile_id: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT p.* FROM person_images p JOIN media_assets m ON m.id=p.media_id "
            "WHERE p.user_id=? AND p.profile_id=? AND p.status='available' AND m.user_id=? "
            "AND m.status='available' ORDER BY p.created_at DESC",
            (user_id, profile_id, user_id),
        ).fetchall()
    result = []
    for row in rows:
        try:
            runtime().media.path_for_owner(row["media_id"], user_id)
            result.append(dict(row))
        except HTTPException:
            continue
    return result


def register_person_image(media_id: str, user_id: str, display_name: str, profile_id: str | None = None) -> dict:
    image_id = str(uuid.uuid4())
    with connection() as conn:
        valid = conn.execute(
            "SELECT id FROM media_assets WHERE id=? AND user_id=? "
            "AND status='available' AND media_type='person_image'",
            (media_id, user_id),
        ).fetchone()
        if not valid:
            raise HTTPException(404, "Personal image media was not found.")
        conn.execute(
            "INSERT INTO person_images (id,user_id,profile_id,media_id,display_name,status,created_at) VALUES (?, ?, ?, ?, ?, 'available', ?)",
            (image_id, user_id, profile_id, media_id, display_name[:200], utcnow()),
        )
    return {
        "id": image_id,
        "media_id": media_id,
        "display_name": display_name[:200],
        "status": "available",
    }


def archive_person_image(person_image_id: str, user_id: str, profile_id: str) -> None:
    """Hide a wearer's base image without invalidating completed visualisations."""
    with connection() as conn:
        person = conn.execute(
            "SELECT id FROM person_images WHERE id=? AND user_id=? AND profile_id=? AND status='available'",
            (person_image_id, user_id, profile_id),
        ).fetchone()
        if not person:
            raise HTTPException(404, "Personal image was not found.")
        active_visualisation = conn.execute(
            "SELECT id FROM visualisations WHERE person_image_id=? AND user_id=? AND profile_id=? "
            "AND status IN ('queued', 'processing') LIMIT 1",
            (person_image_id, user_id, profile_id),
        ).fetchone()
        if active_visualisation:
            raise HTTPException(409, "This personal image is being used for a visualisation. Wait for it to finish or cancel it first.")
        conn.execute(
            "UPDATE person_images SET status='archived' WHERE id=? AND user_id=? AND profile_id=?",
            (person_image_id, user_id, profile_id),
        )
