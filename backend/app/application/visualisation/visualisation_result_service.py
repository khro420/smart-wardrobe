import json

from fastapi import HTTPException

from app.application.ports.visualisation_repository import connection, runtime, utcnow


def complete(visualisation_id, user_id, result, plan, person_bytes):
    runtime().validate_output(result, plan, person_bytes)
    with connection() as conn:
        row = conn.execute(
            "SELECT status FROM visualisations WHERE id=? AND user_id=?",
            (visualisation_id, user_id),
        ).fetchone()
        if not row or row["status"] != "processing":
            return
    media_type = (
        "visualisation_output_development"
        if result.output_kind == "development"
        else "vton_output"
    )
    output_id = runtime().media.store_bytes(
        result.image, user_id, media_type, result.content_type
    )
    with connection() as conn:
        conn.execute(
            "UPDATE visualisations SET status='completed', output_media_id=?, "
            "output_kind=?, model_version=?, metrics_json=?, error_message=NULL, "
            "error_code=NULL, updated_at=?, completed_at=? "
            "WHERE id=? AND user_id=? AND status='processing'",
            (
                output_id,
                result.output_kind,
                result.model_version,
                json.dumps({"latency_ms": result.latency_ms, **result.metadata}),
                utcnow(),
                utcnow(),
                visualisation_id,
                user_id,
            ),
        )


def fail(visualisation_id, user_id, error):
    with connection() as conn:
        conn.execute(
            "UPDATE visualisations SET status='failed', error_message=?, "
            "error_code=?, updated_at=? WHERE id=? AND user_id=? "
            "AND status IN ('queued','processing')",
            (str(error), error.code, utcnow(), visualisation_id, user_id),
        )


def get_visualisation(visualisation_id: str, user_id: str) -> dict:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM visualisations WHERE id=? AND user_id=?",
            (visualisation_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Visualisation was not found.")
        result = dict(row)
        result["items"] = [
            dict(item)
            for item in conn.execute(
                "SELECT * FROM visualisation_items WHERE visualisation_id=? "
                "ORDER BY item_order",
                (visualisation_id,),
            ).fetchall()
        ]
    result["configuration"] = json.loads(result.pop("configuration_json") or "{}")
    result["metrics"] = json.loads(result.pop("metrics_json") or "{}")
    result["notice"] = (
        "AI-generated visualisation. It is not a measurement-accurate physical-fit prediction."
    )
    result["is_development_fallback"] = result["output_kind"] == "development"
    if result["status"] != "completed":
        result["output_media_id"] = None
    elif result["output_media_id"]:
        runtime().media.path_for_owner(result["output_media_id"], user_id)
    return result
