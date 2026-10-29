"""Persisted wardrobe recommendation flow using only confirmed garments.

The report assigns conversational interpretation/recommendation internals to an
integration boundary.  This implementation intentionally provides a small,
deterministic local strategy so that the documented NLPChat, Recommendation,
RecommendationItem, save, and visualisation source lifecycles are executable
without an external LLM service.
"""

import json
import uuid

from fastapi import HTTPException

from app.infrastructure.persistence.postgresql_repository import connection, utcnow
from app.application.ports.recommendation_runtime import confirmed_garment_query


def _role_for(category: str, order: int) -> str:
    normalised = category.lower().replace("-", "_").replace(" ", "_")
    if any(token in normalised for token in ("shirt", "top", "blouse", "jacket", "hoodie", "coat")):
        return "upper"
    if any(token in normalised for token in ("trouser", "pants", "jean", "skirt", "short")):
        return "lower"
    if any(token in normalised for token in ("dress", "jumpsuit", "romper")):
        return "one_piece"
    if any(token in normalised for token in ("shoe", "sneaker", "boot", "sandal")):
        return "footwear"
    return "garment" if order == 1 else "accessory"


def _recommended_garments(user_id: str) -> list[dict]:
    """Pick a compact outfit from confirmed, currently available wardrobe items."""
    rows = confirmed_garment_query().get_confirmed_available_garments(user_id)
    picked: list[dict] = []
    used_roles: set[str] = set()
    for row in rows:
        item = {"id": row.garment_id, "name": row.name, "category": row.category,
                "preferred_media_id": row.preferred_media_id, "is_favourite": int(row.is_favourite)}
        role = _role_for(item["category"], len(picked) + 1)
        # A recommendation should not contain two competing top/lower/etc. slots.
        if role in used_roles and role != "accessory":
            continue
        item["garment_role"] = role
        picked.append(item)
        used_roles.add(role)
        if len(picked) == 4:
            break
    return picked


def _preference_score(user_id: str) -> float:
    with connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM user_preferences WHERE user_id=? AND is_active=1",
            (user_id,),
        ).fetchone()[0]
    # The deterministic local strategy has no external ranking model, but it
    # records whether an explicit user preference was available to the request.
    return 1.0 if count else 0.5


def create_recommendation(user_id: str, request_text: str) -> dict:
    garments = _recommended_garments(user_id)
    if not garments:
        raise HTTPException(422, "Add and confirm at least one available garment before requesting a recommendation.")
    chat_id, recommendation_id, now = str(uuid.uuid4()), str(uuid.uuid4()), utcnow()
    preference_score = _preference_score(user_id)
    entities = {"keywords": [word.lower() for word in request_text.split() if word.strip()][:12]}
    with connection() as conn:
        conn.execute(
            "INSERT INTO nlp_chats (id, user_id, request_text, interpreted_intent, extracted_entities_json, status, created_at, completed_at) "
            "VALUES (?, ?, ?, 'outfit_recommendation', ?, 'completed', ?, ?)",
            (chat_id, user_id, request_text, json.dumps(entities), now, now),
        )
        conn.execute(
            "INSERT INTO recommendations (id, user_id, chat_id, recommendation_type, status, created_at, expires_at, request_match_score, compatibility_score, preference_score, total_score) "
            "VALUES (?, ?, ?, 'wardrobe_outfit', 'available', ?, NULL, ?, ?, ?, ?)",
            (recommendation_id, user_id, chat_id, now, 1.0, 1.0, preference_score, (2.0 + preference_score) / 3.0),
        )
        for order, garment in enumerate(garments, 1):
            conn.execute(
                "INSERT INTO recommendation_items (recommendation_id, garment_id, garment_role, item_order, created_at) VALUES (?, ?, ?, ?, ?)",
                (recommendation_id, garment["id"], garment["garment_role"], order, now),
            )
    return get_recommendation(recommendation_id, user_id)


def _items(recommendation_id: str, user_id: str) -> list[dict]:
    """Resolve recommendation IDs without leaking foreign or archived garments."""
    with connection() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT ri.recommendation_id, ri.garment_id, ri.garment_role, ri.item_order, "
            "g.name, g.category, g.preferred_media_id "
            "FROM recommendation_items ri "
            "JOIN recommendations r ON r.id=ri.recommendation_id "
            "JOIN garments g ON g.id=ri.garment_id "
            "WHERE ri.recommendation_id=? AND r.user_id=? AND g.user_id=? "
            "AND g.status='available' ORDER BY ri.item_order",
            (recommendation_id, user_id, user_id),
        ).fetchall()]


def get_recommendation(recommendation_id: str, user_id: str) -> dict:
    with connection() as conn:
        row = conn.execute(
            "SELECT r.*, c.request_text FROM recommendations r "
            "JOIN nlp_chats c ON c.id=r.chat_id AND c.user_id=r.user_id "
            "WHERE r.id=? AND r.user_id=?",
            (recommendation_id, user_id),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Recommendation was not found.")
    result = dict(row)
    result["items"] = _items(recommendation_id, user_id)
    return result


def list_recommendations(user_id: str) -> list[dict]:
    with connection() as conn:
        identifiers = conn.execute(
            "SELECT id FROM recommendations WHERE user_id=? AND chat_id IS NOT NULL AND status IN ('available', 'saved') ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [get_recommendation(row["id"], user_id) for row in identifiers]


def validated_recommendation_items(user_id: str, recommendation_id: str) -> list[dict]:
    from app.application.recommendation.recommendation_actions import strict_items
    with connection() as conn:
        conn.execute("BEGIN")
        return strict_items(conn, user_id, recommendation_id)


def saved_outfit_state(recommendation_id: str, user_id: str) -> dict:
    from app.application.recommendation.recommendation_actions import saved_outfit_id
    with connection() as conn:
        if not conn.execute("SELECT 1 FROM recommendations WHERE id=? AND user_id=?", (recommendation_id,user_id)).fetchone():
            raise HTTPException(404, "Recommendation was not found.")
        row = conn.execute("SELECT id FROM outfits WHERE id=? AND user_id=? AND creation_type='recommendation' AND status='available'",
                           (saved_outfit_id(user_id,recommendation_id),user_id)).fetchone()
    return {"saved": row is not None, "outfit_id": row["id"] if row else None}


def save_as_outfit(recommendation_id: str, user_id: str, name: str | None) -> dict:
    from app.application.recommendation.recommendation_actions import strict_items, saved_outfit_id
    outfit_id, now = saved_outfit_id(user_id,recommendation_id), utcnow()
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            items = strict_items(conn, user_id, recommendation_id)
            existing = conn.execute("SELECT * FROM outfits WHERE id=?", (outfit_id,)).fetchone()
            if existing:
                if existing["user_id"] != user_id or existing["creation_type"] != "recommendation" or existing["status"] != "available":
                    raise HTTPException(409, "The previously saved outfit is no longer available.")
                saved_items = conn.execute("SELECT garment_id FROM outfit_items WHERE outfit_id=? ORDER BY item_order", (outfit_id,)).fetchall()
                return {"id":outfit_id,"name":existing["name"],"garment_ids":[x["garment_id"] for x in saved_items]}
            if conn.execute("SELECT status FROM recommendations WHERE id=?", (recommendation_id,)).fetchone()[0] == "saved":
                raise HTTPException(409, "This legacy recommendation was already saved. Open the existing Outfits collection.")
            conn.execute(
                "INSERT INTO outfits (id,user_id,name,description,creation_type,status,is_favourite,created_at,updated_at) "
                "VALUES (?,?,?,?,'recommendation','available',0,?,?)",
                (outfit_id,user_id,name or "Recommended outfit","Saved from a wardrobe recommendation.",now,now),
            )
            for item in items:
                conn.execute("INSERT INTO outfit_items (outfit_id,garment_id,role,item_order) VALUES (?,?,?,?)",
                             (outfit_id,item["garment_id"],item["garment_role"],item["item_order"]))
            # Original recommendation, scores, snapshots and chat stay unchanged.
        except BaseException:
            conn.rollback()
            raise
    return {"id":outfit_id,"name":name or "Recommended outfit","garment_ids":[x["garment_id"] for x in items]}
