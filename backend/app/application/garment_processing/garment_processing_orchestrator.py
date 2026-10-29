"""Processing-job lifecycle and review boundary (FR-02 to FR-16)."""

import json
import uuid
import logging

from app.domain.value_objects.garment_attributes import GarmentAttributes
from app.application.ports.garment_standardisation_port import GarmentStandardisationInput
from app.application.garment_processing import automatic_garment_finalization as automatic
from app.domain.value_objects.saved_attribute_evidence import KEY as SOURCE_KEY, source_record

from app.application.ports.workflow_runtime import (
    connection, utcnow, media_path_for_owner, store_media_bytes,
    get_garment_adapter, get_attribute_adapter, get_standardisation_adapter, runtime,
)


# Compatibility exports; each responsibility lives in its own service module.
from app.application.garment_processing.processing_job_service import create_job, get_job, cancel_job
from app.application.garment_processing.review_service import review_job


def run_job(job_id: str, user_id: str, admission_mode: str = automatic.MANUAL) -> None:
    if admission_mode not in (automatic.MANUAL, automatic.MODE):
        raise ValueError('Unapproved admission mode.')
    with connection() as conn:
        job = conn.execute("SELECT * FROM processing_jobs WHERE id = ? AND user_id = ?", (job_id, user_id)).fetchone()
        if not job:
            return
        now = utcnow()
        claimed = conn.execute("UPDATE processing_jobs SET status='processing', started_at=?, updated_at=?, progress_percent=5, progress_message='Analysing the uploaded image.' WHERE id=? AND status='queued'", (now, now, job_id)).rowcount
        if not claimed:
            return
    try:
        path, _ = media_path_for_owner(job["source_media_id"], user_id)
        detections = get_garment_adapter().analyse(path)
        if not detections:
            with connection() as conn:
                conn.execute("UPDATE processing_jobs SET status='failed', error_message=?, progress_message=?, updated_at=?, completed_at=? WHERE id=? AND status='processing'", ("No supported garments were detected. Try a clearer image with visible clothing.", "No supported garments were found.", utcnow(), utcnow(), job_id))
            return
        prepared_items = []
        for index, detection in enumerate(detections, start=1):
            with connection() as conn:
                conn.execute("UPDATE processing_jobs SET progress_percent=?, progress_message=?, updated_at=? WHERE id=? AND status='processing'", (25 + int(((index - 1) / len(detections)) * 65), f"Preparing garment {index} of {len(detections)}.", utcnow(), job_id))
            crop_media_id = store_media_bytes(detection.crop_png, user_id, "garment_crop") if detection.crop_png else job["source_media_id"]
            mask_media_id = store_media_bytes(detection.mask_png, user_id, "segmentation_mask") if detection.mask_png else None
            standardisation = get_standardisation_adapter().standardise(
                GarmentStandardisationInput(
                    source_media_id=job["source_media_id"],
                    crop_media_id=crop_media_id,
                    mask_media_id=mask_media_id,
                    category=detection.category,
                    segmentation_confidence=detection.confidence,
                ),
                user_id,
            )
            crop_path, _ = media_path_for_owner(crop_media_id, user_id)
            attributes = get_attribute_adapter().extract(str(crop_path)).values
            candidate_attributes = {**attributes, **detection.attributes,
                                    "standardisation_notice": standardisation.notice,
                                    "used_fallback": standardisation.used_fallback,
                                    "vtoff": standardisation.metadata,
                                    "embedding_status": "unavailable" if attributes.get("embedding") is None else "available"}
            # Automatic adapters cannot attest an authenticated owner's style choice.
            from app.application.wardrobe.owner_style_confirmation import KEY as STYLE_CONFIRMATION_KEY
            for reserved in (STYLE_CONFIRMATION_KEY, SOURCE_KEY, automatic.KEY, 'contextual_suitability_v1', 'appearance_evidence_v1'):
                candidate_attributes.pop(reserved, None)
            if admission_mode == automatic.MODE:
                # Adapter annotations are not authenticated owner declarations.
                tags = candidate_attributes.get('custom_tags')
                if isinstance(tags, list):
                    reserved_tags = [tag for tag in tags if isinstance(tag, str) and tag.casefold().startswith('rec:')]
                    candidate_attributes['custom_tags'] = [tag for tag in tags if tag not in reserved_tags]
                    if reserved_tags:
                        candidate_attributes['untrusted_model_declarations'] = [tag[:200] for tag in reserved_tags[:20]]
            contributor = 'garment_adapter' if 'style' in detection.attributes else 'attribute_adapter' if 'style' in attributes else 'unavailable'
            supplied = detection.attributes if contributor == 'garment_adapter' else attributes
            reported = supplied.get('style_source')
            origin = reported if reported in ('model_reported', 'synthetic') else 'adapter_output' if contributor != 'unavailable' else 'unknown'
            candidate_attributes[SOURCE_KEY] = source_record(candidate_attributes, user_id, detection.category,
                standardisation.preferred_media_id, utcnow(), origin, contributor)
            item_id = str(uuid.uuid4())
            if admission_mode == automatic.MODE:
                candidate_attributes[automatic.KEY] = automatic.record(user_id, job_id, item_id)
            # Necklines and sleeve lengths only describe upper-body garments
            # and dresses. Do not present an otherwise valid Fashionpedia
            # prediction for trousers, skirts, or shorts.
            if detection.category in {"shorts", "trousers", "skirt"}:
                visible = dict(candidate_attributes.get("fashionpedia_visible_attributes") or {})
                visible.pop("neckline", None)
                visible.pop("sleeve_length", None)
                candidate_attributes["fashionpedia_visible_attributes"] = visible
                candidate_attributes["custom_tags"] = [
                    tag for tag in candidate_attributes.get("custom_tags", [])
                    if not tag.startswith(("neckline:", "sleeve length:"))
                ]
            GarmentAttributes(candidate_attributes).validate_embedding(runtime().embedding_dimension)
            prepared_items.append((
                item_id,
                detection.category,
                detection.confidence,
                candidate_attributes,
                crop_media_id, standardisation.preferred_media_id,
                json.dumps(detection.bounding_box), mask_media_id, standardisation.vtoff_media_id,
            ))
            with connection() as conn:
                conn.execute("UPDATE processing_jobs SET progress_percent=?, progress_message=?, updated_at=? WHERE id=? AND status='processing'", (25 + int((index / len(detections)) * 65), f"Garment {index} of {len(detections)} prepared.", utcnow(), job_id))
        with connection() as conn:
            # Acquire the write lock before checking state: cancellation must win
            # if it was committed while inference ran outside the transaction.
            changed = conn.execute("UPDATE processing_jobs SET status='review_required', progress_percent=100, progress_message=?, updated_at=? WHERE id=? AND status='processing'", (f"{len(prepared_items)} garment candidate(s) are ready to review.", utcnow(), job_id)).rowcount
            if not changed:
                return
            for item_id, category, confidence, attributes, crop_id, preferred_id, box, mask_id, vtoff_id in prepared_items:
                conn.execute(
                    "INSERT INTO processing_items (id, job_id, detected_category, confidence, crop_media_id, preferred_media_id, attributes_json, review_status, created_at, bounding_box, mask_media_id, vtoff_media_id, embedding) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)",
                    (item_id, job_id, category, confidence, crop_id, preferred_id,
                     json.dumps(attributes, allow_nan=False), utcnow(), box, mask_id, vtoff_id, json.dumps(attributes.get("embedding"), allow_nan=False)),
                )
        if admission_mode == automatic.MODE:
            runtime().confirmed_writer.save_automatically_processed_candidates(job_id, user_id)
    except Exception:
        logging.getLogger(__name__).exception("Garment processing failed for job %s", job_id)
        with connection() as conn:
            conn.execute("UPDATE processing_jobs SET status='failed', error_message=?, progress_message=?, updated_at=?, completed_at=? WHERE id=? AND status='processing'", ("Garment processing could not finish. Please retry with another image; if it repeats, check the processing service.", "Garment processing could not finish.", utcnow(), utcnow(), job_id))
