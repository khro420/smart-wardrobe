"""Owner-scoped job visibility and removable try-on history."""
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone

from app.application.ports.visualisation_repository import connection


def list_activity(user_id, profile_id):
    # This is a status view, not a scheduler: the shared GPU lock is not FIFO.
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    with connection() as conn:
        rows = conn.execute("""
            SELECT * FROM (
            SELECT 'processing' AS kind, id, status, progress_message, error_message,
                   progress_percent, created_at, updated_at
            FROM processing_jobs WHERE user_id=? AND profile_id=?
              AND (status IN ('queued','processing','review_required') OR (status IN ('completed','failed','cancelled') AND updated_at>=?))
            UNION ALL
            SELECT 'single' AS kind, id, status, progress_message, error_message,
                   progress_percent, created_at, updated_at
            FROM visualisations WHERE user_id=? AND profile_id=?
              AND history_hidden=0 AND (status IN ('queued','processing') OR (status IN ('completed','failed','cancelled') AND updated_at>=?))
            UNION ALL
            SELECT 'group' AS kind, id, status, progress_message, error_message,
                   NULL AS progress_percent, created_at, updated_at
            FROM group_visualisations WHERE user_id=? AND profile_id=?
              AND history_hidden=0 AND (status IN ('queued','processing') OR (status IN ('completed','failed','cancelled') AND updated_at>=?))
            ) ORDER BY CASE WHEN status IN ('queued','processing','review_required') THEN 0 ELSE 1 END,
                       updated_at DESC LIMIT 100
        """, (user_id, profile_id, cutoff, user_id, profile_id, cutoff, user_id, profile_id, cutoff)).fetchall()
    return [dict(row) for row in rows]


def list_history(user_id, limit=50, offset=0):
    if not 1 <= limit <= 100 or not 0 <= offset <= 10000:
        raise HTTPException(422, 'Invalid history page.')
    with connection() as conn:
        rows = conn.execute("""
            SELECT 'single' AS kind, v.id, v.output_media_id, v.created_at,
                   v.completed_at AS finished_at, v.output_kind
            FROM visualisations v JOIN media_assets m ON m.id=v.output_media_id
            WHERE v.user_id=? AND v.status='completed' AND v.history_hidden=0
              AND m.user_id=? AND m.status='available'
            UNION ALL
            SELECT 'group' AS kind, v.id, v.output_media_id, v.created_at,
                   v.updated_at AS finished_at, 'generated' AS output_kind
            FROM group_visualisations v JOIN media_assets m ON m.id=v.output_media_id
            WHERE v.user_id=? AND v.status='completed' AND v.history_hidden=0
              AND m.user_id=? AND m.status='available'
            ORDER BY 5 DESC, 2 DESC LIMIT ? OFFSET ?
        """, (user_id, user_id, user_id, user_id, limit, offset)).fetchall()
    return [dict(row) for row in rows]


def remove_history(user_id, kind, identifier):
    tables = {'single': 'visualisations', 'group': 'group_visualisations'}
    if kind not in tables:
        raise HTTPException(404, 'Try-on result not found.')
    with connection() as conn:
        changed = conn.execute(
            f"UPDATE {tables[kind]} SET history_hidden=1 WHERE id=? AND user_id=? AND status='completed' AND history_hidden=0",
            (identifier, user_id),
        ).rowcount
    if not changed:
        raise HTTPException(404, 'Try-on result not found.')
