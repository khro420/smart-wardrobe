"""ReviewService owns candidate corrections and preferred-media decisions."""

import json
from fastapi import HTTPException
from app.application.ports.workflow_runtime import connection, media_path_for_owner, runtime, utcnow
from app.application.wardrobe import owner_style_confirmation as style_confirmation

from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.application.garment_processing.processing_job_service import get_job
from app.application.garment_processing import automatic_garment_finalization as automatic
from app.domain.value_objects.saved_attribute_evidence import KEY as SOURCE_KEY, source_record


def confirm_reviewed_candidates(job_id: str, user_id: str, item_ids: list[str], save_mode: str, outfit_name: str | None, admission_mode: str = automatic.MANUAL) -> dict:
    if admission_mode == automatic.MODE:
        if save_mode != 'garments':
            raise HTTPException(422, 'Automatic saving creates garments only.')
        result = runtime().confirmed_writer.save_automatically_processed_candidates(job_id, user_id, item_ids)
        if result['admission']['state'] != 'saved':
            raise HTTPException(409, {'code': result['admission']['reason'], 'message': 'Automatic saving could not finish. Check the processing details.', 'admission': result['admission']})
        return result
    if admission_mode != automatic.MANUAL:
        raise HTTPException(422, 'Unapproved admission mode.')
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
            if {style_confirmation.KEY, SOURCE_KEY, automatic.KEY}.intersection(update.get('attributes') or {}):
                raise HTTPException(422, 'Style confirmation metadata is server-owned.')
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
            action = update.get('style_confirmation')
            if action is not None:
                if update['decision'] != 'accepted' or 'style' not in (update.get('attributes') or {}):
                    raise HTTPException(422, 'Explicitly select a style when accepting the candidate.')
                category = attrs.get('reviewed_category') or item['detected_category']
                style = style_confirmation.validate_action(action, style_confirmation.candidate_revision(item, user_id), attrs, category)
                attrs[style_confirmation.KEY] = style_confirmation.event(user_id, item['id'], job_id,
                    category, preferred_id, style, utcnow(), 'candidate_accept')
            elif update['decision'] != 'accepted' or not style_confirmation.pending_current(attrs.get(style_confirmation.KEY), item, user_id, attrs, preferred_id):
                attrs.pop(style_confirmation.KEY, None)
            if 'category' in update or 'preferred_media' in update or 'style' in (update.get('attributes') or {}):
                previous = attrs.get(SOURCE_KEY)
                origin, contributor = 'unknown', 'unrecorded_prior_style'
                if isinstance(previous, dict) and isinstance(previous.get('style'), dict):
                    origin = previous['style'].get('origin', 'unknown')
                    contributor = previous['style'].get('contributor', 'unrecorded_prior_style')
                if 'style' in (update.get('attributes') or {}):
                    origin, contributor = 'owner_supplied', 'authenticated_candidate_correction'
                attrs[SOURCE_KEY] = source_record(attrs, user_id, attrs.get('reviewed_category') or item['detected_category'], preferred_id, utcnow(), origin, contributor)
            conn.execute("UPDATE processing_items SET review_status=?, attributes_json=?, preferred_media_id=? WHERE id=?", (
                update["decision"], json.dumps(attrs, allow_nan=False), preferred_id, item["id"]
            ))
    result = get_job(job_id, user_id)
    if result['admission']['mode'] == automatic.MODE:
        runtime().confirmed_writer.save_automatically_processed_candidates(job_id, user_id)
        result = get_job(job_id, user_id)
    return result
