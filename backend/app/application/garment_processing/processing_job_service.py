"""ProcessingJobService owns creation, retrieval and cancellation."""

import json
import uuid
from fastapi import HTTPException
from app.application.ports.workflow_runtime import connection, utcnow, media_path_for_owner, runtime
from app.application.wardrobe import owner_style_confirmation
from app.application.wardrobe.profile_service import require_active_profile
from app.application.garment_processing.automatic_garment_finalization import projection


def resolve_profile_id(user_id: str, profile_id: str | None) -> str:
    if profile_id:
        return profile_id
    from app.application.wardrobe.profile_service import ensure_default_profile
    with connection() as conn:
        return ensure_default_profile(conn, user_id)["id"]


def create_job(source_media_id: str, user_id: str, profile_id: str | None = None) -> str:
    profile_id = resolve_profile_id(user_id, profile_id)
    media_path_for_owner(source_media_id, user_id)
    job_id, now = str(uuid.uuid4()), utcnow()
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        require_active_profile(conn,user_id,profile_id)
        from app.application.wardrobe.wearer_category_service import require_profile
        require_profile(user_id,profile_id,conn)
        conn.execute("INSERT INTO processing_jobs (id,user_id,profile_id,source_media_id,status,error_message,created_at,started_at,updated_at,completed_at,progress_percent,progress_message) VALUES (?, ?, ?, ?, 'queued', NULL, ?, NULL, ?, NULL, 0, ?)", (job_id, user_id, profile_id, source_media_id, now, now, "Waiting to analyse your image."))
    return job_id


def get_job(job_id: str, user_id: str, profile_id: str | None = None) -> dict:
    profile_id = resolve_profile_id(user_id, profile_id)
    with connection() as conn:
        # Status and item admission must describe one read snapshot. Otherwise
        # automatic finalisation can commit between these SELECTs, producing a
        # review-required job with already-confirmed/saved items in the UI.
        conn.execute("BEGIN")
        job = conn.execute("SELECT * FROM processing_jobs WHERE id=? AND user_id=? AND profile_id=?", (job_id, user_id, profile_id)).fetchone()
        if not job:
            raise HTTPException(404, "Processing job was not found.")
        items = conn.execute("SELECT * FROM processing_items WHERE job_id=? ORDER BY created_at", (job_id,)).fetchall()
    result=_project_job(job,items,user_id)
    from app.application.wardrobe import wearer_category_service as categories
    if categories.policy() is not None:
        with connection() as conn:
            views=categories.annotations(conn,user_id,profile_id,items)
        for item,view in zip(result['items'],views):
            item['wearer_category_eligibility']=view['wearer_category_eligibility']
            if 'verified_subtype' in view:item['verified_subtype']=view['verified_subtype']
    return result


def _project_job(job,items,user_id):
    result = dict(job)
    result["items"] = [{**{key: value for key, value in dict(item).items() if key != "attributes_json"}, "attributes": json.loads(item["attributes_json"]), "bounding_box": json.loads(item["bounding_box"] or "null"), "embedding": json.loads(item["embedding"] or "null")} for item in items]
    for value, item in zip(result['items'], items):
        value['style_confirmation'] = owner_style_confirmation.candidate_view(item, user_id)
        from app.application.wardrobe import description_projector as description
        description_view = description.view(item, user_id, runtime().description_policy, candidate=True)
        if description_view is not None:
            description_view['editable'] = description_view['editable'] and job['status'] == 'review_required'
            value['description'] = description_view
    result['admission'] = projection(items, user_id)
    return result


def cancel_job(job_id: str, user_id: str, profile_id: str | None = None) -> None:
    profile_id = resolve_profile_id(user_id, profile_id)
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        require_active_profile(conn,user_id,profile_id)
        changed = conn.execute("UPDATE processing_jobs SET status='cancelled', updated_at=?, completed_at=? WHERE id=? AND user_id=? AND profile_id=? AND status IN ('queued','processing','review_required')", (utcnow(), utcnow(), job_id, user_id, profile_id)).rowcount
    if not changed:
        raise HTTPException(409, "This processing job cannot be cancelled.")


def recover_interrupted_jobs() -> None:
    """The local prototype runs one API process; background tasks are not durable."""
    with connection() as conn:
        conn.execute("UPDATE processing_jobs SET status='failed', error_message=?, updated_at=?, completed_at=? WHERE status IN ('queued','processing')", (
            "Processing was interrupted by a service restart. Please upload the image again.", utcnow(), utcnow(),
        ))


def historical_job(job_id: str, user_id: str) -> dict:
    with connection() as conn:
        conn.execute('BEGIN')
        job = conn.execute("SELECT * FROM processing_jobs WHERE id=? AND user_id=? AND status IN ('completed','failed','cancelled')",(job_id,user_id)).fetchone()
        if not job:
            raise HTTPException(404,'Processing job was not found.')
        items = conn.execute('SELECT * FROM processing_items WHERE job_id=? ORDER BY created_at,id',(job_id,)).fetchall()
    result = _project_job(job,items,user_id)
    result['read_only'] = True
    result['uploader_provenance'] = 'stored_association' if job['profile_id'] else 'legacy_unrecorded'
    # Historical access never broadens media ownership or revives hidden files.
    for obj in [result,*result['items']]:
        for key,value in list(obj.items()):
            if key.endswith('media_id') and value:
                try:
                    media_path_for_owner(value,user_id)
                except HTTPException:
                    obj[key] = None
    return result


def list_historical_jobs(user_id: str, profile_id: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
    if not 1 <= limit <= 100 or offset < 0 or offset > 10000:
        raise HTTPException(422,'Invalid historical job page.')
    with connection() as conn:
        if profile_id is not None:
            from app.application.wardrobe.profile_service import historical_profile
            historical_profile(conn,user_id,profile_id)
        predicate = ' AND profile_id=?' if profile_id is not None else ''
        args = (user_id,profile_id,limit,offset) if profile_id is not None else (user_id,limit,offset)
        rows = conn.execute("SELECT id,profile_id,status,created_at,completed_at FROM processing_jobs WHERE user_id=? AND status IN ('completed','failed','cancelled')"+predicate+' ORDER BY created_at DESC,id LIMIT ? OFFSET ?',args).fetchall()
    return [{**dict(row),'read_only':True,'uploader_provenance':'stored_association' if row['profile_id'] else 'legacy_unrecorded'} for row in rows]

