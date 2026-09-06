"""Confirmed wardrobe persistence with transaction-backed outfit integrity."""

import json
import uuid
from fastapi import HTTPException

from app.application.ports.workflow_runtime import connection, utcnow, media_path_for_owner, runtime
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE, GarmentAttributes


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


class WardrobeWriter:
    """ConfirmedGarmentWriter implementation supplied to candidate review."""
    def save_confirmed_candidates(self, job_id: str, user_id: str, item_ids: list[str], save_mode: str, outfit_name: str | None) -> dict:
        return confirm_candidates(job_id, user_id, item_ids, save_mode, outfit_name)


def _serialise_garment(row) -> dict:
    data = dict(row)
    data["is_favourite"] = bool(data["is_favourite"])
    data["attributes"] = json.loads(data.pop("attributes_json"))
    for key in ("style_tags", "custom_tags", "structural_scores", "additional_attributes", "embedding"):
        data[key] = json.loads(data[key]) if data.get(key) else None
    return data


def _write_representation(conn, garment_id: str, attrs: dict) -> None:
    styles = attrs.get("style")
    if isinstance(styles, str):
        styles = [styles] if styles else []
    palette = attrs.get("color_palette", [])
    secondary = palette[1].get("hex") if len(palette) > 1 else None
    conn.execute("UPDATE garments SET secondary_colour=?, style_tags=?, custom_tags=?, structural_scores=?, additional_attributes=?, embedding=? WHERE id=?", (
        secondary, json.dumps(styles or []), json.dumps(attrs.get("custom_tags", [])),
        json.dumps({"garment_role": attrs.get("garment_type"), "layering_index": attrs.get("layering_index")}),
        json.dumps(attrs, allow_nan=False), json.dumps(attrs.get("embedding"), allow_nan=False), garment_id,
    ))


def list_garments(
    user_id: str, query: str = "", category: str | None = None,
    favourite: bool | None = None, sort: str = "updated_desc",
) -> list[dict]:
    sql = "SELECT * FROM garments WHERE user_id=? AND status='available'"
    parameters: list[object] = [user_id]
    if query:
        sql += " AND (LOWER(name) LIKE ? OR LOWER(category) LIKE ?)"
        parameters.extend([f"%{query.lower()}%", f"%{query.lower()}%"])
    if category:
        sql += " AND category=?"
        parameters.append(category)
    if favourite is not None:
        sql += " AND is_favourite=?"
        parameters.append(int(favourite))
    sql += f" ORDER BY {SORT_SQL.get(sort, SORT_SQL['updated_desc'])}"
    with connection() as conn:
        return [_serialise_garment(row) for row in conn.execute(sql, parameters).fetchall()]


def confirm_candidates(job_id: str, user_id: str, item_ids: list[str], save_mode: str, outfit_name: str | None) -> dict:
    if not item_ids or len(set(item_ids)) != len(item_ids):
        raise HTTPException(422, "Select one or more distinct candidates.")
    if save_mode not in {"garments", "outfit"}:
        raise HTTPException(422, "Choose garments or outfit saving.")
    if save_mode == "outfit" and not (outfit_name or "").strip():
        raise HTTPException(422, "An outfit name is required when saving as an outfit.")
    with connection() as conn:
        # Serialise competing review/confirm/cancel writes before checking state.
        conn.execute("BEGIN IMMEDIATE")
        job = conn.execute("SELECT status FROM processing_jobs WHERE id=? AND user_id=?", (job_id, user_id)).fetchone()
        if not job:
            raise HTTPException(404, "Processing job was not found.")
        if job["status"] != "review_required":
            raise HTTPException(409, "This job is not ready to be saved.")
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
            if item["preferred_media_id"] not in {item["crop_media_id"], item["vtoff_media_id"]}:
                raise HTTPException(409, "Review a valid garment representation before saving.")
            media_path_for_owner(item["preferred_media_id"], user_id)
        now, garment_ids = utcnow(), []
        for item in items:
            garment_id = str(uuid.uuid4())
            attrs = json.loads(item["attributes_json"])
            attrs["requires_review"] = False
            conn.execute("INSERT INTO garments (id, user_id, processing_item_id, preferred_media_id, name, category, primary_colour, pattern, attributes_json, status, is_favourite, created_at, updated_at, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'available', 0, ?, ?, NULL)", (
                garment_id, user_id, item["id"], item["preferred_media_id"], attrs.get("name") or attrs.get("reviewed_category") or item["detected_category"],
                attrs.get("reviewed_category") or item["detected_category"], attrs.get("primary_colour"), attrs.get("pattern"), json.dumps(attrs), now, now,
            ))
            _write_representation(conn, garment_id, attrs)
            conn.execute("UPDATE processing_items SET review_status='confirmed' WHERE id=?", (item["id"],))
            garment_ids.append(garment_id)
        outfit_id = None
        if save_mode == "outfit":
            outfit_id = str(uuid.uuid4())
            conn.execute("INSERT INTO outfits VALUES (?, ?, ?, NULL, 'image_upload', 'available', 0, ?, ?)", (outfit_id, user_id, outfit_name, now, now))
            for order, (garment_id, item) in enumerate(zip(garment_ids, items), start=1):
                role = json.loads(item["attributes_json"]).get("garment_type", "garment")
                conn.execute("INSERT INTO outfit_items VALUES (?, ?, ?, ?)", (outfit_id, garment_id, role, order))
        conn.execute("UPDATE processing_jobs SET status='completed', updated_at=?, completed_at=? WHERE id=?", (now, now, job_id))
    return {"garment_ids": garment_ids, "outfit_id": outfit_id}


def update_garment(garment_id: str, user_id: str, payload: dict) -> dict:
    with connection() as conn:
        row = conn.execute("SELECT * FROM garments WHERE id=? AND user_id=? AND status='available'", (garment_id, user_id)).fetchone()
        if not row:
            raise HTTPException(404, "Garment was not found.")
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
        conn.execute("UPDATE garments SET name=?, category=?, primary_colour=?, pattern=?, is_favourite=?, attributes_json=?, updated_at=? WHERE id=?", (
            data["name"], data["category"], data["primary_colour"], data["pattern"], int(data["is_favourite"]), json.dumps(data["attributes"]), utcnow(), garment_id
        ))
        _write_representation(conn, garment_id, data["attributes"])
        result = _serialise_garment(conn.execute("SELECT * FROM garments WHERE id=?", (garment_id,)).fetchone())
    return result


def _garment_dependencies(conn, garment_id: str, user_id: str) -> dict:
    garment = conn.execute(
        "SELECT id, name FROM garments WHERE id=? AND user_id=? AND status='available'",
        (garment_id, user_id),
    ).fetchone()
    if not garment:
        raise HTTPException(404, "Garment was not found.")
    outfits = [dict(row) for row in conn.execute(
        "SELECT o.id, o.name FROM outfit_items oi JOIN outfits o ON o.id=oi.outfit_id "
        "WHERE oi.garment_id=? AND o.user_id=? AND o.status='available' ORDER BY LOWER(o.name)",
        (garment_id, user_id),
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


def get_garment_dependencies(garment_id: str, user_id: str) -> dict:
    with connection() as conn:
        return _garment_dependencies(conn, garment_id, user_id)


def archive_garment(garment_id: str, user_id: str) -> None:
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        dependencies = _garment_dependencies(conn, garment_id, user_id)
        if not dependencies["can_archive"]:
            raise HTTPException(409, dependencies["policy"])
        conn.execute(
            "UPDATE garments SET status='archived', deleted_at=?, updated_at=? WHERE id=? AND user_id=? AND status='available'",
            (utcnow(), utcnow(), garment_id, user_id),
        )


def list_outfits(
    user_id: str, query: str = "", category: str | None = None,
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
            data["items"] = [dict(item) for item in conn.execute("SELECT oi.*, g.name, g.category FROM outfit_items oi JOIN garments g ON g.id=oi.garment_id WHERE oi.outfit_id=? ORDER BY oi.item_order", (outfit["id"],)).fetchall()]
            result.append(data)
    return result


def _validated_garments(conn, user_id: str, garment_ids: list[str]):
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


def create_outfit(user_id: str, name: str, garment_ids: list[str], description: str | None) -> dict:
    if len(set(garment_ids)) != len(garment_ids):
        raise HTTPException(422, "The same garment cannot appear twice in an outfit.")
    with connection() as conn:
        by_id = _validated_garments(conn, user_id, garment_ids)
        outfit_id, now = str(uuid.uuid4()), utcnow()
        conn.execute("INSERT INTO outfits VALUES (?, ?, ?, ?, 'manual', 'available', 0, ?, ?)", (outfit_id, user_id, name, description, now, now))
        for order, garment_id in enumerate(garment_ids, 1):
            conn.execute("INSERT INTO outfit_items VALUES (?, ?, ?, ?)", (outfit_id, garment_id, _role_for_garment(by_id[garment_id]), order))
    return {"id": outfit_id, "name": name, "garment_ids": garment_ids}


def update_outfit(outfit_id: str, user_id: str, payload: dict) -> dict:
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
            by_id = _validated_garments(conn, user_id, garment_ids)
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
            "SELECT oi.*, g.name, g.category FROM outfit_items oi JOIN garments g ON g.id=oi.garment_id WHERE oi.outfit_id=? ORDER BY oi.item_order",
            (outfit_id,),
        ).fetchall()]
    return result


def _outfit_dependencies(conn, outfit_id: str, user_id: str) -> dict:
    outfit = conn.execute(
        "SELECT id, name FROM outfits WHERE id=? AND user_id=? AND status='available'",
        (outfit_id, user_id),
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


def get_outfit_dependencies(outfit_id: str, user_id: str) -> dict:
    with connection() as conn:
        return _outfit_dependencies(conn, outfit_id, user_id)


def archive_outfit(outfit_id: str, user_id: str) -> None:
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        dependencies = _outfit_dependencies(conn, outfit_id, user_id)
        if not dependencies["can_archive"]:
            raise HTTPException(409, dependencies["policy"])
        conn.execute(
            "UPDATE outfits SET status='archived', updated_at=? WHERE id=? AND user_id=? AND status='available'",
            (utcnow(), outfit_id, user_id),
        )
