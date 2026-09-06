"""ProcessingJobService owns creation, retrieval and cancellation."""

import json
import uuid
from fastapi import HTTPException
from app.application.ports.workflow_runtime import connection, utcnow, media_path_for_owner


def create_job(source_media_id: str, user_id: str) -> str:
    media_path_for_owner(source_media_id, user_id)
    job_id, now = str(uuid.uuid4()), utcnow()
    with connection() as conn:
        conn.execute("INSERT INTO processing_jobs VALUES (?, ?, ?, 'queued', NULL, ?, NULL, ?, NULL)", (job_id, user_id, source_media_id, now, now))
    return job_id


def get_job(job_id: str, user_id: str) -> dict:
    with connection() as conn:
        job = conn.execute("SELECT * FROM processing_jobs WHERE id=? AND user_id=?", (job_id, user_id)).fetchone()
        if not job:
            raise HTTPException(404, "Processing job was not found.")
        items = conn.execute("SELECT * FROM processing_items WHERE job_id=? ORDER BY created_at", (job_id,)).fetchall()
    result = dict(job)
    result["items"] = [{**{key: value for key, value in dict(item).items() if key != "attributes_json"}, "attributes": json.loads(item["attributes_json"]), "bounding_box": json.loads(item["bounding_box"] or "null"), "embedding": json.loads(item["embedding"] or "null")} for item in items]
    return result


def cancel_job(job_id: str, user_id: str) -> None:
    with connection() as conn:
        changed = conn.execute("UPDATE processing_jobs SET status='cancelled', updated_at=?, completed_at=? WHERE id=? AND user_id=? AND status IN ('queued','processing','review_required')", (utcnow(), utcnow(), job_id, user_id)).rowcount
    if not changed:
        raise HTTPException(409, "This processing job cannot be cancelled.")


def recover_interrupted_jobs() -> None:
    """The local prototype runs one API process; background tasks are not durable."""
    with connection() as conn:
        conn.execute("UPDATE processing_jobs SET status='failed', error_message=?, updated_at=?, completed_at=? WHERE status IN ('queued','processing')", (
            "Processing was interrupted by a service restart. Please upload the image again.", utcnow(), utcnow(),
        ))
