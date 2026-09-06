"""Validate the complete source; never silently drop an invalid member."""
from fastapi import HTTPException

from app.application.ports.visualisation_repository import connection, runtime
from app.domain.value_objects.visualisation_plan import (
    CAPTURE_GUIDANCE,
    VTONConfiguration,
    VisualisationGarment,
    VisualisationPlan,
)


def resolve_source(conn, user_id, outfit_id=None, recommendation_id=None):
    if bool(outfit_id) == bool(recommendation_id):
        raise HTTPException(422, "Provide exactly one outfit or recommendation source.")
    if outfit_id:
        source = conn.execute(
            "SELECT id FROM outfits WHERE id=? AND user_id=? AND status='available'",
            (outfit_id, user_id),
        ).fetchone()
        members = conn.execute(
            "SELECT garment_id, role, item_order FROM outfit_items "
            "WHERE outfit_id=? ORDER BY item_order",
            (outfit_id,),
        ).fetchall()
    else:
        source = conn.execute(
            "SELECT id FROM recommendations WHERE id=? AND user_id=? "
            "AND status IN ('available','saved')",
            (recommendation_id, user_id),
        ).fetchone()
        members = conn.execute(
            "SELECT garment_id, garment_role AS role, item_order "
            "FROM recommendation_items WHERE recommendation_id=? ORDER BY item_order",
            (recommendation_id,),
        ).fetchall()
    if not source:
        raise HTTPException(404, "The selected source is unavailable.")
    if not members or len({row["garment_id"] for row in members}) != len(members):
        raise HTTPException(422, "The source must contain unique confirmed garments.")

    garments, previews = [], []
    for member in members:
        row = conn.execute(
            "SELECT g.*, p.review_status FROM garments g "
            "LEFT JOIN processing_items p ON p.id=g.processing_item_id "
            "WHERE g.id=? AND g.user_id=? AND g.status='available'",
            (member["garment_id"], user_id),
        ).fetchone()
        if not row or (
            row["processing_item_id"]
            and row["review_status"] not in ("accepted", "confirmed")
        ):
            raise HTTPException(
                409,
                "The source contains a garment that is no longer confirmed, owned and available.",
            )
        runtime().media.path_for_owner(row["preferred_media_id"], user_id)
        garments.append(
            VisualisationGarment(
                row["id"],
                row["preferred_media_id"],
                row["category"],
                member["role"],
                member["item_order"],
            )
        )
        previews.append(
            {
                "garment_id": row["id"],
                "name": row["name"],
                "category": row["category"],
                "source_media_id": row["preferred_media_id"],
                "role": member["role"],
                "item_order": member["item_order"],
            }
        )
    plan = VisualisationPlan(
        "outfit" if outfit_id else "recommendation",
        outfit_id or recommendation_id,
        "",
        "",
        tuple(garments),
        runtime().configuration(),
    )
    try:
        mode = plan.mode
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    return plan, {
        "source_type": plan.source_type,
        "source_id": plan.source_id,
        "items": previews,
        "category": mode,
        "capture_guidance": CAPTURE_GUIDANCE,
    }


def prepare_visualisation(user_id, outfit_id=None, recommendation_id=None):
    with connection() as conn:
        return resolve_source(conn, user_id, outfit_id, recommendation_id)[1]


def validated_outfit_items(user_id: str, outfit_id: str):
    with connection() as conn:
        return resolve_source(conn, user_id, outfit_id)[1]["items"]
