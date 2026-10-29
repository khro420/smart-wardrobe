"""Strict current eligibility for recommendation-source actions, not acquisition."""
import json
import uuid
from fastapi import HTTPException
from app.application.ports.recommendation_runtime import transaction_garment_query


def saved_outfit_id(user_id, recommendation_id):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, json.dumps(
        ["smart-wardrobe-recommendation-outfit-v1", user_id, recommendation_id], separators=(",", ":"))))


def strict_items(conn, user_id, recommendation_id):
    source = conn.execute("SELECT id FROM recommendations WHERE id=? AND user_id=? AND status IN ('available','saved')",
                          (recommendation_id, user_id)).fetchone()
    if not source:
        raise HTTPException(404, "Recommendation was not found or is unavailable.")
    items = [dict(x) for x in conn.execute(
        "SELECT garment_id,garment_role,item_order FROM recommendation_items WHERE recommendation_id=? ORDER BY item_order",
        (recommendation_id,)).fetchall()]
    if not items or len({x["garment_id"] for x in items}) != len(items) or [x["item_order"] for x in items] != list(range(1, len(items)+1)):
        raise HTTPException(409, "Recommendation contains missing, duplicate or invalid item references.")
    eligible = {x.garment_id: x for x in transaction_garment_query(conn).get_confirmed_available_garments(user_id)}
    for item in items:
        garment = eligible.get(item["garment_id"])
        if garment is None:
            raise HTTPException(409, "Recommendation contains a garment that is no longer confirmed, owned and available.")
        item.update(name=garment.name, category=garment.category, preferred_media_id=garment.preferred_media_id)
    return items
