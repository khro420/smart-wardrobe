"""Acceptance tests for the VTON input, output and lifecycle boundaries."""

from dataclasses import replace
from io import BytesIO
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image

from app.application.visualisation.outfit_visualisation_service import cancel_visualisation
from app.application.ports.visualisation_repository import configure_visualisation, runtime
from app.domain.value_objects.generated_visualisation import GeneratedVisualisation, VTONFailure
from app.domain.value_objects.visualisation_plan import (
    CATEGORY_MODES, VTONConfiguration, VisualisationGarment, VisualisationPlan,
)
from app.infrastructure.ai.vton_preprocessing import (
    encode_png, prepare_garment, prepare_person, validate_generated_output,
)
from app.infrastructure.persistence.postgresql_repository import connection, utcnow
from app.main import app


def image_bytes(colour="navy", size=(256, 320), image_format="PNG") -> bytes:
    image = Image.new("RGB", size, colour)
    buffer = BytesIO()
    image.save(buffer, image_format)
    return buffer.getvalue()


def plan(category="short_sleeve_top", *, count=1) -> VisualisationPlan:
    garments = tuple(
        VisualisationGarment(f"garment-{index}", f"media-{index}", category, "garment", index)
        for index in range(1, count + 1)
    )
    return VisualisationPlan("outfit", "source", "person", "person-media", garments, VTONConfiguration())


def create_single_garment_outfit(client: TestClient) -> tuple[str, str, str]:
    uploaded = client.post(
        "/api/v1/processing/jobs",
        files={"file": ("shirt.png", image_bytes(), "image/png")},
    ).json()
    job = client.get(f"/api/v1/processing/jobs/{uploaded['id']}").json()
    item_id = job["items"][0]["id"]
    review = client.post(
        f"/api/v1/processing/jobs/{uploaded['id']}/review",
        json={"items": [{"item_id": item_id, "decision": "accepted", "name": "Navy top", "category": "short_sleeve_top"}]},
    )
    assert review.status_code == 200
    confirmed = client.post(
        f"/api/v1/processing/jobs/{uploaded['id']}/confirm",
        json={"save_mode": "outfit", "item_ids": [item_id], "outfit_name": "VTON source"},
    ).json()
    garment = client.get("/api/v1/wardrobe/garments").json()[0]
    person = client.post(
        "/api/v1/media/person-images",
        files={"file": ("person.png", image_bytes("teal"), "image/png")},
    ).json()
    return confirmed["outfit_id"], garment["id"], person["id"]


def test_supported_category_contract_and_single_garment_boundary():
    assert set(CATEGORY_MODES.values()) == {"upper", "lower", "overall"}
    assert len(CATEGORY_MODES) == 11
    for category, expected in CATEGORY_MODES.items():
        assert plan(category).mode == expected
    with pytest.raises(ValueError, match="outerwear"):
        plan("long_sleeve_outwear").mode
    with pytest.raises(ValueError, match="exactly one garment"):
        plan(count=2).mode


def test_preprocessing_and_generated_output_fail_closed():
    configuration = VTONConfiguration()
    current_plan = plan()
    person = image_bytes("navy")
    assert prepare_person(person, (configuration.width, configuration.height)).size == (768, 1024)

    transparent = Image.new("RGBA", (200, 300), (255, 0, 0, 0))
    transparent.putpixel((100, 150), (255, 0, 0, 255))
    payload = BytesIO(); transparent.save(payload, "PNG")
    prepared = prepare_garment(payload.getvalue(), (768, 1024))
    assert prepared.getpixel((0, 0)) == (255, 255, 255)

    copied = encode_png(prepare_person(person, (768, 1024)))
    development = GeneratedVisualisation(copied, 768, 1024, "development-copy", 0, "development")
    validate_generated_output(development, current_plan, person)
    with pytest.raises(VTONFailure, match="could not be validated"):
        validate_generated_output(replace(development, output_kind="generated"), current_plan, person)


def test_preflight_freezes_provenance_and_returns_safe_metadata():
    user = f"vton-{uuid.uuid4()}"
    with TestClient(app, headers={"X-User-Id": user}) as client:
        outfit_id, garment_id, person_id = create_single_garment_outfit(client)
        prepared = client.post("/api/v1/visualisations/prepare", json={"outfit_id": outfit_id})
        assert prepared.status_code == 200
        assert prepared.json()["category"] == "upper"
        assert prepared.json()["items"][0]["garment_id"] == garment_id
        assert "one person" in prepared.json()["capture_guidance"].lower()

        created = client.post(
            "/api/v1/visualisations",
            json={"outfit_id": outfit_id, "person_image_id": person_id},
        )
        assert created.status_code == 202
        result = client.get(f"/api/v1/visualisations/{created.json()['id']}").json()
        assert result["status"] == "completed"
        assert result["output_kind"] == "development"
        assert result["configuration"] == VTONConfiguration().to_dict()
        assert result["items"][0]["source_media_id"] == prepared.json()["items"][0]["source_media_id"]
        assert result["error_message"] is None

        foreign = client.get(
            f"/api/v1/visualisations/{created.json()['id']}",
            headers={"X-User-Id": "different-owner"},
        )
        assert foreign.status_code == 404


def test_invalid_generated_output_finishes_failed_without_media():
    class FlatGeneratedAdapter:
        def generate(self, current_plan, person_image, garment_image):
            return GeneratedVisualisation(
                image_bytes("black", (768, 1024)), 768, 1024,
                "invalid-test-adapter", 1.0, "generated",
            )

    user = f"invalid-output-{uuid.uuid4()}"
    with TestClient(app, headers={"X-User-Id": user}) as client:
        outfit_id, _, person_id = create_single_garment_outfit(client)
        original = runtime()
        configure_visualisation(replace(original, adapter=lambda: FlatGeneratedAdapter()))
        try:
            created = client.post(
                "/api/v1/visualisations",
                json={"outfit_id": outfit_id, "person_image_id": person_id},
            )
            result = client.get(f"/api/v1/visualisations/{created.json()['id']}").json()
        finally:
            configure_visualisation(original)
        assert result["status"] == "failed"
        assert result["error_code"] == "invalid_output"
        assert result["output_media_id"] is None
        assert "could not be validated" in result["error_message"]


def test_cancel_is_owner_scoped_and_terminal():
    identifier, user, now = str(uuid.uuid4()), f"cancel-{uuid.uuid4()}", utcnow()
    with connection() as conn:
        conn.execute(
            "INSERT INTO visualisations "
            "(id,user_id,source_type,outfit_id,person_image_id,status,created_at,updated_at,configuration_json) "
            "VALUES (?,?,'outfit','pending-outfit','pending-person','queued',?,?,?)",
            (identifier, user, now, now, "{}"),
        )
    with pytest.raises(HTTPException) as foreign:
        cancel_visualisation(identifier, "different-owner")
    assert foreign.value.status_code == 404
    cancel_visualisation(identifier, user)
    cancel_visualisation(identifier, user)
    with connection() as conn:
        assert conn.execute("SELECT status FROM visualisations WHERE id=?", (identifier,)).fetchone()[0] == "cancelled"
