"""Transactional request snapshot, single claim, cancellation and safe completion."""
from dataclasses import replace
import json
import logging
import uuid

from fastapi import HTTPException

from app.application.ports.visualisation_repository import (
    connection,
    get_vton_adapter,
    runtime,
    utcnow,
)
from app.application.visualisation.outfit_identifier_validator import (
    prepare_visualisation,
    resolve_source,
)
from app.application.visualisation.personal_image_service import (
    list_person_images,
    register_person_image,
    require_person,
)
from app.application.visualisation.visualisation_result_service import (
    complete,
    fail,
    get_visualisation,
)
from app.domain.value_objects.generated_visualisation import VTONFailure
from app.domain.value_objects.visualisation_plan import (
    VTONConfiguration,
    VisualisationGarment,
    VisualisationPlan,
)

LOGGER = logging.getLogger(__name__)


def create_visualisation(
    user_id, person_image_id, outfit_id=None, recommendation_id=None
):
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        queued = conn.execute(
            "SELECT COUNT(*) FROM visualisations WHERE status='queued'"
        ).fetchone()[0]
        if queued >= runtime().queue_limit:
            raise HTTPException(429, "The try-on queue is full. Please try again shortly.")
        plan, _ = resolve_source(conn, user_id, outfit_id, recommendation_id)
        person = require_person(conn, person_image_id, user_id)
        plan = replace(
            plan,
            person_image_id=person_image_id,
            person_media_id=person["media_id"],
        )
        identifier, now = str(uuid.uuid4()), utcnow()
        conn.execute(
            "INSERT INTO visualisations "
            "(id,user_id,outfit_id,recommendation_id,source_type,person_image_id,"
            "person_media_id,status,created_at,updated_at,configuration_json) "
            "VALUES (?,?,?,?,?,?,?,'queued',?,?,?)",
            (
                identifier,
                user_id,
                outfit_id,
                recommendation_id,
                plan.source_type,
                person_image_id,
                plan.person_media_id,
                now,
                now,
                json.dumps(plan.configuration.to_dict()),
            ),
        )
        for item in plan.garments:
            conn.execute(
                "INSERT INTO visualisation_items "
                "(visualisation_id,garment_id,source_media_id,role,item_order,category) "
                "VALUES (?,?,?,?,?,?)",
                (
                    identifier,
                    item.garment_id,
                    item.source_media_id,
                    item.role,
                    item.item_order,
                    item.category,
                ),
            )
    return identifier


def run_visualisation(visualisation_id, user_id):
    try:
        # Keep the record queued while another AI subsystem owns the GPU.
        with runtime().gpu_slot():
            with connection() as conn:
                claimed = conn.execute(
                    "UPDATE visualisations SET status='processing',started_at=?,updated_at=? "
                    "WHERE id=? AND user_id=? AND status='queued'",
                    (utcnow(), utcnow(), visualisation_id, user_id),
                ).rowcount
                if not claimed:
                    return
                visual = conn.execute(
                    "SELECT * FROM visualisations WHERE id=?", (visualisation_id,)
                ).fetchone()
                person = require_person(conn, visual["person_image_id"], user_id)
                if person["media_id"] != visual["person_media_id"]:
                    raise VTONFailure("unprocessable")
                items = conn.execute(
                    "SELECT * FROM visualisation_items WHERE visualisation_id=? "
                    "ORDER BY item_order",
                    (visualisation_id,),
                ).fetchall()
                for item in items:
                    if not conn.execute(
                        "SELECT id FROM garments WHERE id=? AND user_id=? "
                        "AND status='available'",
                        (item["garment_id"], user_id),
                    ).fetchone():
                        raise VTONFailure("unprocessable")
                plan = VisualisationPlan(
                    visual["source_type"],
                    visual["outfit_id"] or visual["recommendation_id"],
                    visual["person_image_id"],
                    visual["person_media_id"],
                    tuple(
                        VisualisationGarment(
                            item["garment_id"],
                            item["source_media_id"],
                            item["category"],
                            item["role"],
                            item["item_order"],
                        )
                        for item in items
                    ),
                    VTONConfiguration(**json.loads(visual["configuration_json"])),
                )
            plan.mode
            person_path, _ = runtime().media.path_for_owner(
                plan.person_media_id, user_id
            )
            garment_path, _ = runtime().media.path_for_owner(
                plan.garments[0].source_media_id, user_id
            )
            person_bytes = person_path.read_bytes()
            result = get_vton_adapter().generate(
                plan, person_bytes, garment_path.read_bytes()
            )
            complete(visualisation_id, user_id, result, plan, person_bytes)
    except Exception as exc:
        LOGGER.exception("Visualisation %s failed", visualisation_id)
        error = exc if isinstance(exc, VTONFailure) else VTONFailure("inference_failed")
        fail(visualisation_id, user_id, error)


def cancel_visualisation(visualisation_id, user_id):
    with connection() as conn:
        row = conn.execute(
            "SELECT status FROM visualisations WHERE id=? AND user_id=?",
            (visualisation_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Visualisation was not found.")
        if row["status"] == "cancelled":
            return
        if row["status"] not in ("queued", "processing"):
            raise HTTPException(409, "This visualisation has already finished.")
        conn.execute(
            "UPDATE visualisations SET status='cancelled',updated_at=? "
            "WHERE id=? AND user_id=? AND status IN ('queued','processing')",
            (utcnow(), visualisation_id, user_id),
        )


def recover_interrupted_visualisations():
    with connection() as conn:
        conn.execute(
            "UPDATE visualisations SET status='failed',error_code='interrupted',"
            "error_message=?,updated_at=? WHERE status IN ('queued','processing')",
            (
                "Visualisation was interrupted by a service restart. Please submit it again.",
                utcnow(),
            ),
        )


class LocalVisualisationGateway:
    def create_from_outfit(self, user_id, outfit_id, person_image_id):
        return create_visualisation(user_id, person_image_id, outfit_id=outfit_id)

    def create_from_recommendation(self, user_id, recommendation_id, person_image_id):
        return create_visualisation(
            user_id, person_image_id, recommendation_id=recommendation_id
        )
