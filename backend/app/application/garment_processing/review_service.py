"""ReviewService owns candidate corrections and preferred-media decisions."""

import json
from fastapi import HTTPException
from app.application.ports.workflow_runtime import connection, media_path_for_owner, runtime

from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.application.garment_processing.processing_job_service import get_job


def confirm_reviewed_candidates(job_id: str, user_id: str, item_ids: list[str], save_mode: str, outfit_name: str | None) -> dict:
    return runtime().confirmed_writer.save_confirmed_candidates(job_id, user_id, item_ids, save_mode, outfit_name)


def review_job(job_id: str, user_id: str, updates: list[dict]) -> dict:
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        job = conn.execute("SELECT status FROM processing_jobs WHERE id=? AND user_id=?", (job_id, user_id)).fetchone()
        if not job:
            raise HTTPException(404, "Processing job was not found.")
        if job["status"] != "review_required":
            raise HTTPException(409, "Only review-required jobs can be updated.")
        for update in updates:
            item = conn.execute("SELECT * FROM processing_items WHERE id=? AND job_id=?", (update["item_id"], job_id)).fetchone()
            if not item:
                raise HTTPException(404, "Processing candidate was not found.")
            attrs = json.loads(item["attributes_json"])
            attrs.update(update.get("attributes") or {})
            if update.get("name"):
                attrs["name"] = update["name"]
            if update.get("category"):
                # Retain detected_category/confidence as model evidence; the
                # reviewed category becomes Garment.category on confirmation.
                attrs["reviewed_category"] = update["category"]
                role, layering = GARMENT_STRUCTURE.get(update["category"], ("garment", None))
                attrs.update(garment_type=role, layering_index=layering)
            if "primary_colour" in update:
                attrs["primary_colour"] = update["primary_colour"]
                attrs["primary_color"] = update["primary_colour"]
            if "pattern" in update:
                attrs["pattern"] = update["pattern"]
            preferred_id = item["preferred_media_id"]
            if update.get("preferred_media"):
                preferred_id = item["crop_media_id"] if update["preferred_media"] == "crop" else item["vtoff_media_id"]
                if not preferred_id:
                    raise HTTPException(422, "That garment representation is unavailable.")
            media_path_for_owner(preferred_id, user_id)
            conn.execute("UPDATE processing_items SET review_status=?, attributes_json=?, preferred_media_id=? WHERE id=?", (
                update["decision"], json.dumps(attrs, allow_nan=False), preferred_id, item["id"]
            ))
    return get_job(job_id, user_id)
