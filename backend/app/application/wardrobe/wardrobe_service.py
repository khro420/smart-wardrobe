"""Confirmed wardrobe persistence with transaction-backed outfit integrity."""

import json
import uuid
import hmac
from fastapi import HTTPException

from app.application.ports.workflow_runtime import connection, utcnow, media_path_for_owner, runtime
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE, GarmentAttributes
from app.application.wardrobe.garment_tag_edit import tag_edit_view, tag_revision
from app.application.wardrobe import contextual_review
from app.application.wardrobe import owner_style_confirmation
from app.application.wardrobe import attribute_evidence_review
from app.domain.value_objects.general_context_evidence import KEY as APPEARANCE_KEY
from app.domain.value_objects.contextual_garment_evidence import KEY as CONTEXT_KEY
from app.domain.value_objects.saved_attribute_evidence import KEY as SOURCE_KEY, source_record
from app.application.garment_processing import automatic_garment_finalization as automatic


SORT_SQL = {
    "updated_desc": "updated_at DESC",
    "updated_asc": "updated_at ASC",
    "name_asc": "LOWER(name) ASC, updated_at DESC",
    "name_desc": "LOWER(name) DESC, updated_at DESC",
    "favourites": "is_favourite DESC, updated_at DESC",
}
OUTFIT_SORT_SQL = {
    "updated_desc": "o.updated_at DESC",
    "updated_asc": "o.updated_at ASC",
    "name_asc": "LOWER(o.name) ASC, o.updated_at DESC",
    "name_desc": "LOWER(o.name) DESC, o.updated_at DESC",
    "favourites": "o.is_favourite DESC, o.updated_at DESC",
}


WARDROBE_GARMENT_LIMIT = 100


def _quota_on_connection(conn, user_id: str, profile_id: str) -> dict:
    used = conn.execute(
        "SELECT COUNT(*) FROM garments WHERE user_id=? AND (status IS NULL OR status<>'archived')",
        (user_id,),
    ).fetchone()[0]
    return {"policy_version": "wardrobe-active-entries-1.0.0",
            "scope": "non_archived_garment_entries", "limit": WARDROBE_GARMENT_LIMIT,
            "used": used, "remaining": max(0, WARDROBE_GARMENT_LIMIT-used),
            "over_limit": used > WARDROBE_GARMENT_LIMIT, "pending_reserved": 0}


def get_wardrobe_quota(user_id: str, profile_id: str) -> dict:
    with connection() as conn:
        return _quota_on_connection(conn, user_id, profile_id)


def _require_capacity(quota: dict, requested: int | None, stage: str) -> None:
    if quota["used"] + (requested if requested is not None else 1) <= quota["limit"]:
        return
    if requested is None:
        message = f"Your wardrobe is full ({quota['used']}/{quota['limit']}). Archive a garment before adding another image."
    else:
        needed = quota["used"] + requested - quota["limit"]
        message = (f"You have {quota['used']} of {quota['limit']} active garments and selected {requested}. "
                   f"Archive at least {needed} garment(s) or select fewer candidates.")
    raise HTTPException(409, {"code": "WardrobeQuotaExceeded", "stage": stage,
                              "message": message, **quota, "requested": requested})


def check_upload_capacity(user_id: str, profile_id: str) -> None:
    # Advisory only: uploads/candidates do not reserve slots. Confirmation recounts.
    _require_capacity(get_wardrobe_quota(user_id, profile_id), None, "upload")


class WardrobeWriter:
    """ConfirmedGarmentWriter implementation supplied to candidate review."""
    def save_confirmed_candidates(self, job_id: str, user_id: str, item_ids: list[str], save_mode: str, outfit_name: str | None, profile_id: str | None = None) -> dict:
        return confirm_candidates(job_id, user_id, item_ids, save_mode, outfit_name, profile_id)

    def save_automatically_processed_candidates(self, job_id: str, user_id: str, item_ids: list[str] | None = None, profile_id: str | None = None) -> dict:
        return finalize_automatic_candidates(job_id, user_id, item_ids, profile_id)


def _serialise_garment(row) -> dict:
    data = dict(row)
    data["is_favourite"] = bool(data["is_favourite"])
    data["attributes"] = json.loads(data.pop("attributes_json"))
    for key in ("style_tags", "custom_tags", "structural_scores", "additional_attributes", "embedding"):
        data[key] = json.loads(data[key]) if data.get(key) else None
    data["tag_edit"] = tag_edit_view(row, data)
    data['contextual_edit'] = contextual_review.view(row)
    data['style_confirmation'] = owner_style_confirmation.garment_view(row, data['contextual_edit']['review_current'])
    data['appearance_edit'] = attribute_evidence_review.view(row)
    return data


def _write_representation(conn, garment_id: str, attrs: dict, *, write_style: bool = True, write_tags: bool = True) -> None:
    styles = attrs.get("style")
    if isinstance(styles, str):
        styles = [styles]
    additional_json = json.dumps(attrs, allow_nan=False)
    if not write_style or not write_tags:
        # Preserve omitted evidence in the legacy mirror too: Phase 1 can use it
        # when the dedicated/canonical representation is absent. Never reconcile
        # these historical representations merely because another field changed.
        raw = conn.execute("SELECT additional_attributes FROM garments WHERE id=?", (garment_id,)).fetchone()["additional_attributes"]
        try:
            previous = json.loads(raw) if raw is not None else {}
        except (ValueError, TypeError):
            previous = None
        if isinstance(previous, dict):
            mirrored = dict(attrs)
            for field, changed in (("style", write_style), ("custom_tags", write_tags)):
                if not changed:
                    if field in previous:
                        mirrored[field] = previous[field]
                    else:
                        mirrored.pop(field, None)
            additional_json = json.dumps(mirrored, allow_nan=False)
        else:
            additional_json = raw  # Preserve malformed evidence, not a guessed repair.
    palette = attrs.get("color_palette", [])
    secondary = palette[1].get("hex") if len(palette) > 1 else None
    conn.execute("UPDATE garments SET secondary_colour=?, structural_scores=?, additional_attributes=?, embedding=? WHERE id=?", (
        secondary,
        json.dumps({"garment_role": attrs.get("garment_type"), "layering_index": attrs.get("layering_index")}),
        additional_json, json.dumps(attrs.get("embedding"), allow_nan=False), garment_id,
    ))
    # Forward writes retain missing (JSON null), deliberate [], and assigned tags.
    # Omission on PATCH must not rewrite an existing authoritative representation.
    if write_style:
        conn.execute("UPDATE garments SET style_tags=? WHERE id=?", (json.dumps(styles), garment_id))
    if write_tags:
        conn.execute("UPDATE garments SET custom_tags=? WHERE id=?", (json.dumps(attrs.get("custom_tags", [])), garment_id))


def list_garments(
    user_id: str, profile_id: str, query: str = "", category: str | None = None,
    favourite: bool | None = None, sort: str = "updated_desc",
    colour: str | None = None, style: str | None = None, availability: str = "available",
) -> list[dict]:
    if availability not in {"available", "unavailable", "archived", "all"}:
        raise HTTPException(422, "Choose a supported availability filter.")
    sql = "SELECT * FROM garments WHERE user_id=?"
    parameters: list[object] = [user_id]
    if availability == "unavailable":
        sql += " AND (status IS NULL OR status NOT IN ('available','archived'))"
    elif availability != "all":
        sql += " AND status=?"
        parameters.append(availability)
    if query:
        sql += " AND (LOWER(name) LIKE ? OR LOWER(category) LIKE ?)"
        parameters.extend([f"%{query.lower()}%", f"%{query.lower()}%"])
    if category:
        sql += " AND category=?"
        parameters.append(category)
    if favourite is not None:
        sql += " AND is_favourite=?"
        parameters.append(int(favourite))
    if colour and colour.strip():
        sql += " AND LOWER(TRIM(primary_colour))=?"
        parameters.append(colour.strip().lower())
    sql += f" ORDER BY {SORT_SQL.get(sort, SORT_SQL['updated_desc'])}"
    with connection() as conn:
        garments = [_serialise_garment(row) for row in conn.execute(sql, parameters).fetchall()]
    if style and style.strip():
        target = style.strip().casefold()
        def matches(garment):
            # Listing compares stored labels only. Explicit empty lists remain empty.
            values = garment["style_tags"]
            if values is None:
                values = garment["attributes"].get("style")
            if isinstance(values, str):
                values = [values]
            return isinstance(values, list) and any(isinstance(value, str) and value.strip().casefold() == target for value in values)
        garments = [garment for garment in garments if matches(garment)]
    return garments


def _materialise_candidates(conn, job_id, user_id, profile_id, items, save_mode, outfit_name, automatic_mode=False):
    now, garment_ids = utcnow(), []
    for item in items:
        garment_id = str(uuid.uuid4())
        attrs = json.loads(item["attributes_json"])
        # Automatic processing cannot attest to an authenticated owner review.
        attrs.pop(CONTEXT_KEY, None)
        attrs.pop(APPEARANCE_KEY, None)
        owner_style_confirmation.transfer(item, user_id, attrs)
        attrs["requires_review"] = attrs.get("requires_review", True) if automatic_mode else False
        if automatic_mode:
            attrs[automatic.KEY] = automatic.record(user_id, job_id, item['id'], 'saved', garment_id=garment_id)
            role, layer = GARMENT_STRUCTURE[attrs.get('reviewed_category') or item['detected_category']]
            attrs.update(garment_type=role, layering_index=layer)
        conn.execute("INSERT INTO garments (id, user_id, profile_id, processing_item_id, preferred_media_id, name, category, primary_colour, pattern, attributes_json, status, is_favourite, created_at, updated_at, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'available', 0, ?, ?, NULL)", (
            garment_id, user_id, None, item["id"], item["preferred_media_id"], attrs.get("name") or attrs.get("reviewed_category") or item["detected_category"],
            attrs.get("reviewed_category") or item["detected_category"], attrs.get("primary_colour"), attrs.get("pattern"), json.dumps(attrs), now, now,
        ))
        _write_representation(conn, garment_id, attrs)
        if automatic_mode:
            conn.execute("UPDATE processing_items SET review_status='confirmed',attributes_json=? WHERE id=?", (json.dumps(attrs, allow_nan=False), item['id']))
        else:
            conn.execute("UPDATE processing_items SET review_status='confirmed' WHERE id=?", (item["id"],))
        garment_ids.append(garment_id)
    outfit_id = None
    if save_mode == "outfit":
        outfit_id = str(uuid.uuid4())
        conn.execute("INSERT INTO outfits (id,user_id,profile_id,name,description,creation_type,status,is_favourite,created_at,updated_at) VALUES (?, ?, NULL, ?, NULL, 'image_upload', 'available', 0, ?, ?)", (outfit_id, user_id, outfit_name, now, now))
        for order, (garment_id, item) in enumerate(zip(garment_ids, items), start=1):
            role = json.loads(item["attributes_json"]).get("garment_type", "garment")
            conn.execute("INSERT INTO outfit_items VALUES (?, ?, ?, ?)", (outfit_id, garment_id, role, order))
    conn.execute("UPDATE processing_jobs SET status='completed', updated_at=?, completed_at=? WHERE id=?", (now, now, job_id))
    return {"garment_ids": garment_ids, "outfit_id": outfit_id}


def confirm_candidates(job_id: str, user_id: str, item_ids: list[str], save_mode: str, outfit_name: str | None, profile_id: str | None = None) -> dict:
    if not item_ids or len(set(item_ids)) != len(item_ids):
        raise HTTPException(422, "Select one or more distinct candidates.")
    if save_mode not in {"garments", "outfit"}:
        raise HTTPException(422, "Choose garments or outfit saving.")
    if save_mode == "outfit" and not (outfit_name or "").strip():
        raise HTTPException(422, "An outfit name is required when saving as an outfit.")
    with connection() as conn:
        # Serialise competing review/confirm/cancel writes before checking state.
        conn.execute("BEGIN IMMEDIATE")
        job = conn.execute("SELECT status,profile_id FROM processing_jobs WHERE id=? AND user_id=?", (job_id, user_id)).fetchone()
        if not job:
            raise HTTPException(404, "Processing job was not found.")
        if job["status"] != "review_required":
            raise HTTPException(409, "This job is not ready to be saved.")
        all_attributes = conn.execute('SELECT attributes_json FROM processing_items WHERE job_id=?', (job_id,)).fetchall()
        if any(automatic.KEY in json.loads(value['attributes_json']) for value in all_attributes):
            raise HTTPException(409, 'Use the complete automatic submission protocol for this job.')
        placeholders = ",".join("?" for _ in item_ids)
        items = conn.execute(f"SELECT * FROM processing_items WHERE job_id=? AND id IN ({placeholders}) AND review_status='accepted'", [job_id, *item_ids]).fetchall()
        if len(items) != len(set(item_ids)):
            raise HTTPException(409, "Every saved candidate must be accepted during review.")
        by_id = {item["id"]: item for item in items}
        items = [by_id[item_id] for item_id in item_ids]
        for item in items:
            try:
                GarmentAttributes(json.loads(item["attributes_json"])).validate_embedding(runtime().embedding_dimension)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            if item["preferred_media_id"] not in {item["crop_media_id"], item["vtoff_media_id"], item["mirror_media_id"]}:
                raise HTTPException(409, "Review a valid garment representation before saving.")
            media_path_for_owner(item["preferred_media_id"], user_id)
        # The same write transaction owns the count and every subsequent insert.
        # Completed-job retries were already rejected above; they are never charged.
        profile_id = profile_id or job["profile_id"]
        if not profile_id:
            raise HTTPException(409, "This upload is missing its wardrobe profile.")
        _require_capacity(_quota_on_connection(conn, user_id, profile_id), len(items), "confirmation")
        result = _materialise_candidates(conn, job_id, user_id, profile_id, items, save_mode, outfit_name)
    return result


def finalize_automatic_candidates(job_id: str, user_id: str, item_ids: list[str] | None = None, profile_id: str | None = None) -> dict:
    """The same locked writer materialises complete automatic batches only."""
    with connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        job = conn.execute('SELECT * FROM processing_jobs WHERE id=? AND user_id=?', (job_id, user_id)).fetchone()
        if job is None:
            raise HTTPException(404, 'Processing job was not found.')
        profile_id = profile_id or job['profile_id']
        if not profile_id:
            raise HTTPException(409, "This upload is missing its wardrobe profile.")
        items = conn.execute('SELECT * FROM processing_items WHERE job_id=? ORDER BY created_at,id', (job_id,)).fetchall()
        if item_ids is not None and (len(item_ids) != len(items) or len(set(item_ids)) != len(item_ids) or set(item_ids) != {item['id'] for item in items}):
            raise HTTPException(409, 'Automatic saving requires the original complete batch.')
        attrs = [json.loads(item['attributes_json']) for item in items]
        if not items or not all(automatic.current(value.get(automatic.KEY), item, user_id) for item, value in zip(items, attrs)):
            raise HTTPException(409, 'This job does not have a valid automatic submission contract.')
        if job['status'] == 'completed':
            saved = automatic.projection(items, user_id)
            if saved['state'] != 'saved' or any(item['review_status'] != 'confirmed' for item in items):
                raise HTTPException(409, 'Automatic completion metadata is inconsistent.')
            return {'garment_ids': saved['garment_ids'], 'outfit_id': None, 'replayed': True, 'admission': saved}
        if job['status'] != 'review_required':
            raise HTTPException(409, 'This processing job is not ready for automatic saving.')
        reason = next((problem for item, value in zip(items, attrs) if (problem := automatic.readiness(item, value, user_id))), None)
        if reason is None:
            try:
                from PIL import Image
                media_path_for_owner(job['source_media_id'], user_id)
                for item, value in zip(items, attrs):
                    GarmentAttributes(value).validate_embedding(runtime().embedding_dimension)
                    path, mime = media_path_for_owner(item['preferred_media_id'], user_id)
                    if mime not in ('image/jpeg', 'image/png'):
                        raise ValueError('Invalid representation.')
                    with Image.open(path) as image:
                        image.verify()
            except (HTTPException, ValueError, OSError):
                reason = 'representation_or_processing_data_invalid'
        if reason is None:
            try:
                _require_capacity(_quota_on_connection(conn, user_id, profile_id), len(items), 'automatic_finalisation')
            except HTTPException:
                reason = 'WardrobeQuotaExceeded'
        if reason is not None:
            state = 'incomplete' if reason in ('category_missing_or_unsupported', 'candidate_not_ready') else 'blocked'
            for item, value in zip(items, attrs):
                value[automatic.KEY] = automatic.record(user_id, job_id, item['id'], state, reason)
                conn.execute('UPDATE processing_items SET attributes_json=? WHERE id=?', (json.dumps(value, allow_nan=False), item['id']))
            conn.execute('UPDATE processing_jobs SET progress_message=?,updated_at=? WHERE id=?',
                         ('Automatic saving needs attention: '+reason, utcnow(), job_id))
            return {'garment_ids': [], 'outfit_id': None, 'admission': {'mode': automatic.MODE, 'state': state, 'reason': reason, 'garment_ids': []}}
        result = _materialise_candidates(conn, job_id, user_id, profile_id, items, 'garments', None, automatic_mode=True)
        conn.execute('UPDATE processing_jobs SET error_message=NULL,progress_message=? WHERE id=?', ('Garments automatically added to your wardrobe.', job_id))
        result['admission'] = {'mode': automatic.MODE, 'state': 'saved', 'reason': None, 'garment_ids': result['garment_ids']}
        return result


def update_garment(garment_id: str, user_id: str, profile_id: str, payload: dict, expected_tag_revision: str | None = None) -> dict:
    if {CONTEXT_KEY, APPEARANCE_KEY, owner_style_confirmation.KEY, SOURCE_KEY, automatic.KEY}.intersection(payload.get('attributes') or {}):
        raise HTTPException(422, 'Use the contextual suitability review action.')
    with connection() as conn:
        # Keep the read/merge/write atomic so an unrelated PATCH cannot restore stale style evidence.
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM garments WHERE id=? AND user_id=? AND status='available'", (garment_id, user_id)).fetchone()
        if not row:
            raise HTTPException(404, "Garment was not found.")
        if "custom_tags" in (payload.get("attributes") or {}):
            if expected_tag_revision is None:
                raise HTTPException(428, "Reload the garment before editing its tags; a tag revision is required.")
            if not isinstance(expected_tag_revision, str) or not expected_tag_revision.isascii() or not hmac.compare_digest(expected_tag_revision, tag_revision(row)):
                raise HTTPException(409, "Tags changed in another session. Your changes were not saved. Reload and review before retrying.")
        data = _serialise_garment(row)
        for key in ("name", "category", "primary_colour", "pattern", "is_favourite"):
            if payload.get(key) is not None:
                data[key] = payload[key]
        if payload.get("attributes") is not None:
            data["attributes"].update(payload["attributes"])
        if payload.get("category") is not None:
            role, layering = GARMENT_STRUCTURE.get(data["category"], ("garment", None))
            data["attributes"].update(reviewed_category=data["category"], garment_type=role, layering_index=layering)
        if "primary_colour" in payload:
            data["primary_colour"] = payload["primary_colour"]
            data["attributes"].update(primary_colour=payload["primary_colour"], primary_color=payload["primary_colour"])
        if "pattern" in payload:
            data["pattern"] = payload["pattern"]
            data["attributes"]["pattern"] = payload["pattern"]
        if 'category' in payload or 'style' in (payload.get('attributes') or {}):
            contextual_review.invalidate_review(data['attributes'])
            data['attributes'].pop(owner_style_confirmation.KEY, None)
        action = payload.get('style_confirmation')
        if action is not None:
            if 'style' not in (payload.get('attributes') or {}):
                raise HTTPException(422, 'Explicitly select the style to confirm.')
            owner_style_confirmation.require_consistent_mirror(row)
            # Validate the old container before replacing its style proof.
            original_attrs = json.loads(row['attributes_json'])
            style = owner_style_confirmation.validate_action(action, owner_style_confirmation.garment_revision(row), data['attributes'], data['category'])
            confirmation = owner_style_confirmation.event(user_id, garment_id, None, data['category'],
                row['preferred_media_id'], style, utcnow(), 'garment_edit')
            owner_style_confirmation.admit(original_attrs, confirmation)
            data['attributes'][CONTEXT_KEY] = original_attrs[CONTEXT_KEY]
            data['attributes'][owner_style_confirmation.KEY] = original_attrs[owner_style_confirmation.KEY]
        if 'category' in payload:
            attribute_evidence_review.invalidate(data['attributes'])
        if 'category' in payload or 'style' in (payload.get('attributes') or {}):
            prior = data['attributes'].get(SOURCE_KEY)
            # A category-only correction does not prove who supplied its old style.
            origin = 'owner_supplied' if 'style' in (payload.get('attributes') or {}) else 'unknown'
            contributor = 'authenticated_garment_edit' if origin == 'owner_supplied' else 'unrecorded_prior_style'
            if origin == 'unknown' and isinstance(prior, dict) and isinstance(prior.get('style'), dict):
                origin = prior['style'].get('origin', 'unknown')
                contributor = prior['style'].get('contributor', 'unrecorded_prior_style')
            source_attrs = data['attributes']
            if 'style' not in (payload.get('attributes') or {}) and row['style_tags'] is not None:
                source_attrs = {**source_attrs, 'style': json.loads(row['style_tags'])}
            data['attributes'][SOURCE_KEY] = source_record(source_attrs, user_id, data['category'], row['preferred_media_id'], utcnow(), origin, contributor)
        conn.execute("UPDATE garments SET name=?, category=?, primary_colour=?, pattern=?, is_favourite=?, attributes_json=?, updated_at=? WHERE id=?", (
            data["name"], data["category"], data["primary_colour"], data["pattern"], int(data["is_favourite"]), json.dumps(data["attributes"]), utcnow(), garment_id
        ))
        _write_representation(
            conn, garment_id, data["attributes"],
            write_style="style" in (payload.get("attributes") or {}),
            write_tags="custom_tags" in (payload.get("attributes") or {}),
        )
        result = _serialise_garment(conn.execute("SELECT * FROM garments WHERE id=?", (garment_id,)).fetchone())
    return result


def review_contextual_suitability(garment_id: str, user_id: str, profile_id: str, payload: dict) -> dict:
    with connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute("SELECT * FROM garments WHERE id=? AND user_id=? AND status='available'", (garment_id, user_id)).fetchone()
        if row is None:
            raise HTTPException(404, 'Garment was not found.')
        if payload.get('appearance_review') is not None:
            attribute_evidence_review.save(conn, row, payload, utcnow())
            return _serialise_garment(conn.execute('SELECT * FROM garments WHERE id=?', (garment_id,)).fetchone())
        if not hmac.compare_digest(payload['revision'], contextual_review.revision(row)):
            raise HTTPException(409, 'Garment evidence changed. Reload and review before retrying.')
        attrs = json.loads(row['attributes_json'])
        try:
            mirror = json.loads(row['additional_attributes']) if row['additional_attributes'] is not None else {}
        except (ValueError, TypeError):
            raise HTTPException(422, 'Stored attribute mirror needs explicit repair before editing.') from None
        if not isinstance(mirror, dict) or ((CONTEXT_KEY in attrs or CONTEXT_KEY in mirror)
                and attrs.get(CONTEXT_KEY) != mirror.get(CONTEXT_KEY)):
            raise HTTPException(422, 'Stored contextual evidence is inconsistent and needs explicit repair.')
        raw = attrs.get(CONTEXT_KEY, {'schema_version': '1.0.0', 'style_review': None, 'occasion_overrides': {}})
        if (not isinstance(raw, dict) or set(raw) != {'schema_version', 'style_review', 'occasion_overrides'}
                or raw['schema_version'] != '1.0.0' or not isinstance(raw['occasion_overrides'], dict)
                or set(raw['occasion_overrides']) - {'wedding'}):
            raise HTTPException(422, 'Stored contextual evidence needs explicit repair before editing.')
        raw = {**raw, 'occasion_overrides': dict(raw['occasion_overrides'])}
        if payload.get('review_style') is True:
            projection = contextual_review.view(row)
            if projection['style_state'] != 'Known' or len(projection['styles']) != 1 or row['category'] not in GARMENT_STRUCTURE:
                raise HTTPException(422, 'Choose one supported style and a supported category before reviewing it.')
            raw['style_review'] = {'source': 'owner_review', 'styles': projection['styles'], 'category': row['category'], 'reviewed_at': utcnow()}
        elif payload.get('review_style') is False:
            raw['style_review'] = None
        if payload.get('review_style') is not None:
            attrs.pop(owner_style_confirmation.KEY, None)
            mirror.pop(owner_style_confirmation.KEY, None)
        if payload.get('wedding_choice') is not None:
            choice = payload['wedding_choice']
            if choice == 'unknown':
                raw['occasion_overrides'].pop('wedding', None)
            else:
                raw['occasion_overrides']['wedding'] = [choice]
        attrs[CONTEXT_KEY] = raw
        conn.execute('UPDATE garments SET attributes_json=?, updated_at=? WHERE id=?', (json.dumps(attrs), utcnow(), garment_id))
        # Update only this namespace in the mirror: do not repair or overwrite
        # unrelated historical style/custom-tag representations.
        mirror[CONTEXT_KEY] = raw
        conn.execute('UPDATE garments SET additional_attributes=? WHERE id=?', (json.dumps(mirror), garment_id))
        result = _serialise_garment(conn.execute('SELECT * FROM garments WHERE id=?', (garment_id,)).fetchone())
    return result


def _garment_dependencies(conn, garment_id: str, user_id: str, profile_id: str) -> dict:
    garment = conn.execute(
        "SELECT id, name FROM garments WHERE id=? AND user_id=? AND (profile_id=? OR profile_id IS NULL) AND status='available'",
        (garment_id, user_id, profile_id),
    ).fetchone()
    if not garment:
        raise HTTPException(404, "Garment was not found.")
    outfits = [dict(row) for row in conn.execute(
        "SELECT o.id, o.name FROM outfit_items oi JOIN outfits o ON o.id=oi.outfit_id "
        "WHERE oi.garment_id=? AND o.user_id=? AND o.profile_id=? AND o.status='available' ORDER BY LOWER(o.name)",
        (garment_id, user_id, profile_id),
    ).fetchall()]
    visualisations = [dict(row) for row in conn.execute(
        "SELECT DISTINCT v.id, v.status FROM visualisation_items vi "
        "JOIN visualisations v ON v.id=vi.visualisation_id "
        "WHERE vi.garment_id=? AND v.user_id=? AND v.status IN ('queued','processing') ORDER BY v.created_at",
        (garment_id, user_id),
    ).fetchall()]
    return {
        "resource": {"id": garment["id"], "name": garment["name"], "type": "garment"},
        "active_outfits": outfits,
        "active_visualisations": visualisations,
        "can_archive": not outfits and not visualisations,
        "policy": "Archive is blocked while the garment belongs to an available outfit or an unfinished visualisation.",
    }


def get_garment_dependencies(garment_id: str, user_id: str, profile_id: str) -> dict:
    with connection() as conn:
        return _garment_dependencies(conn, garment_id, user_id, profile_id)


def archive_garment(garment_id: str, user_id: str, profile_id: str) -> None:
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        dependencies = _garment_dependencies(conn, garment_id, user_id, profile_id)
        if not dependencies["can_archive"]:
            raise HTTPException(409, dependencies["policy"])
        conn.execute(
            "UPDATE garments SET status='archived', deleted_at=?, updated_at=? WHERE id=? AND user_id=? AND (profile_id=? OR profile_id IS NULL) AND status='available'",
            (utcnow(), utcnow(), garment_id, user_id, profile_id),
        )


def list_outfits(
    user_id: str, profile_id: str, query: str = "", category: str | None = None,
    creation_type: str | None = None, favourite: bool | None = None,
    sort: str = "updated_desc",
) -> list[dict]:
    with connection() as conn:
        sql = "SELECT * FROM outfits o WHERE o.user_id=? AND o.status='available'"
        parameters: list[object] = [user_id]
        if query:
            sql += (
                " AND (LOWER(o.name) LIKE ? OR LOWER(COALESCE(o.description,'')) LIKE ? OR EXISTS ("
                "SELECT 1 FROM outfit_items oi JOIN garments g ON g.id=oi.garment_id "
                "WHERE oi.outfit_id=o.id AND (LOWER(g.name) LIKE ? OR LOWER(g.category) LIKE ?)))"
            )
            needle = f"%{query.lower()}%"
            parameters.extend([needle, needle, needle, needle])
        if category:
            sql += " AND EXISTS (SELECT 1 FROM outfit_items oi JOIN garments g ON g.id=oi.garment_id WHERE oi.outfit_id=o.id AND g.category=?)"
            parameters.append(category)
        if creation_type:
            sql += " AND o.creation_type=?"
            parameters.append(creation_type)
        if favourite is not None:
            sql += " AND o.is_favourite=?"
            parameters.append(int(favourite))
        sql += f" ORDER BY {OUTFIT_SORT_SQL.get(sort, OUTFIT_SORT_SQL['updated_desc'])}"
        outfits = conn.execute(sql, parameters).fetchall()
        result = []
        for outfit in outfits:
            data = dict(outfit)
            data["is_favourite"] = bool(data["is_favourite"])
            data["items"] = [dict(item) for item in conn.execute("SELECT oi.*, g.name, g.category, g.preferred_media_id FROM outfit_items oi JOIN garments g ON g.id=oi.garment_id WHERE oi.outfit_id=? ORDER BY oi.item_order", (outfit["id"],)).fetchall()]
            result.append(data)
    return result


def _validated_garments(conn, user_id: str, profile_id: str, garment_ids: list[str]):
    placeholders = ",".join("?" for _ in garment_ids)
    garments = conn.execute(
        f"SELECT id, category, additional_attributes FROM garments WHERE user_id=? AND status='available' AND id IN ({placeholders})",
        [user_id, *garment_ids],
    ).fetchall()
    if len(garments) != len(garment_ids):
        raise HTTPException(404, "One or more garments are unavailable or do not belong to you.")
    return {row["id"]: row for row in garments}


def _role_for_garment(row) -> str:
    if row["additional_attributes"]:
        attributes = json.loads(row["additional_attributes"])
        role = attributes.get("garment_type")
        if isinstance(role, str) and role:
            return role
    return GARMENT_STRUCTURE.get(row["category"], ("garment", None))[0]


def create_outfit(user_id: str, profile_id: str, name: str, garment_ids: list[str], description: str | None) -> dict:
    if len(set(garment_ids)) != len(garment_ids):
        raise HTTPException(422, "The same garment cannot appear twice in an outfit.")
    with connection() as conn:
        by_id = _validated_garments(conn, user_id, profile_id, garment_ids)
        outfit_id, now = str(uuid.uuid4()), utcnow()
        conn.execute("INSERT INTO outfits (id,user_id,profile_id,name,description,creation_type,status,is_favourite,created_at,updated_at) VALUES (?, ?, NULL, ?, ?, 'manual', 'available', 0, ?, ?)", (outfit_id, user_id, name, description, now, now))
        for order, garment_id in enumerate(garment_ids, 1):
            conn.execute("INSERT INTO outfit_items VALUES (?, ?, ?, ?)", (outfit_id, garment_id, _role_for_garment(by_id[garment_id]), order))
    return {"id": outfit_id, "name": name, "garment_ids": garment_ids}


def update_outfit(outfit_id: str, user_id: str, profile_id: str, payload: dict) -> dict:
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        outfit = conn.execute("SELECT * FROM outfits WHERE id=? AND user_id=? AND status='available'", (outfit_id, user_id)).fetchone()
        if not outfit:
            raise HTTPException(404, "Outfit was not found.")
        data = dict(outfit)
        for key in ("name", "description", "is_favourite"):
            if payload.get(key) is not None:
                data[key] = payload[key]
        conn.execute("UPDATE outfits SET name=?, description=?, is_favourite=?, updated_at=? WHERE id=?", (
            data["name"], data["description"], int(data["is_favourite"]), utcnow(), outfit_id
        ))
        if payload.get("garment_ids") is not None:
            garment_ids = payload["garment_ids"]
            by_id = _validated_garments(conn, user_id, profile_id, garment_ids)
            conn.execute("DELETE FROM outfit_items WHERE outfit_id=?", (outfit_id,))
            for order, garment_id in enumerate(garment_ids, 1):
                conn.execute(
                    "INSERT INTO outfit_items VALUES (?, ?, ?, ?)",
                    (outfit_id, garment_id, _role_for_garment(by_id[garment_id]), order),
                )
        row = conn.execute("SELECT * FROM outfits WHERE id=?", (outfit_id,)).fetchone()
        result = dict(row)
        result["is_favourite"] = bool(result["is_favourite"])
        result["items"] = [dict(item) for item in conn.execute(
            "SELECT oi.*, g.name, g.category, g.preferred_media_id FROM outfit_items oi JOIN garments g ON g.id=oi.garment_id WHERE oi.outfit_id=? ORDER BY oi.item_order",
            (outfit_id,),
        ).fetchall()]
    return result


def _outfit_dependencies(conn, outfit_id: str, user_id: str, profile_id: str) -> dict:
    outfit = conn.execute(
        "SELECT id, name FROM outfits WHERE id=? AND user_id=? AND profile_id=? AND status='available'",
        (outfit_id, user_id, profile_id),
    ).fetchone()
    if not outfit:
        raise HTTPException(404, "Outfit was not found.")
    visualisations = [dict(row) for row in conn.execute(
        "SELECT id, status FROM visualisations WHERE outfit_id=? AND user_id=? AND status IN ('queued','processing') ORDER BY created_at",
        (outfit_id, user_id),
    ).fetchall()]
    return {
        "resource": {"id": outfit["id"], "name": outfit["name"], "type": "outfit"},
        "active_outfits": [],
        "active_visualisations": visualisations,
        "can_archive": not visualisations,
        "policy": "Archive is blocked while the outfit is required by an unfinished visualisation.",
    }


def get_outfit_dependencies(outfit_id: str, user_id: str, profile_id: str) -> dict:
    with connection() as conn:
        return _outfit_dependencies(conn, outfit_id, user_id, profile_id)


def archive_outfit(outfit_id: str, user_id: str, profile_id: str) -> None:
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        dependencies = _outfit_dependencies(conn, outfit_id, user_id, profile_id)
        if not dependencies["can_archive"]:
            raise HTTPException(409, dependencies["policy"])
        conn.execute(
            "UPDATE outfits SET status='archived', updated_at=? WHERE id=? AND user_id=? AND profile_id=? AND status='available'",
            (utcnow(), outfit_id, user_id, profile_id),
        )
