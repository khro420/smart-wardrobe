"""Phase 1 contract and acquisition regressions; no recommendation algorithms."""
import ast
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.persistence.postgresql_repository import connection
from app.application.recommendation import recommendation_service as service
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot, GarmentPaletteEntry
from app.domain.value_objects.requests import ReviewItem
from tests.test_o2_recommendation_boundary import confirmed_garment


@pytest.fixture
def wardrobe():
    owner = str(uuid.uuid4())
    with TestClient(app, headers={"X-User-Id": owner}) as client:
        garment_id = confirmed_garment(client, "Contract top", "navy")
        yield owner, client, garment_id, SqliteConfirmedGarmentQuery()


def test_identity_missing_attributes_and_immutability(wardrobe):
    owner, _, garment_id, query = wardrobe
    with connection() as conn:
        conn.execute("UPDATE garments SET attributes_json='{}', additional_attributes=NULL, style_tags=NULL, custom_tags=NULL, primary_colour=NULL, pattern=NULL WHERE id=?", (garment_id,))
    snapshot = query.get_confirmed_available_garments(owner)[0]
    assert (snapshot.garment_id, snapshot.user_id, snapshot.status) == (garment_id, owner, "available")
    assert snapshot.style_tags is None and snapshot.primary_colour is None
    assert snapshot.is_dominant is None and snapshot.colour_temperature is None
    assert snapshot.structural_role is None  # Manual category 'Top' is not aliased.
    with pytest.raises(FrozenInstanceError):
        snapshot.name = "changed"


@pytest.mark.parametrize("state", ["accepted", "pending", "rejected", "missing", "null"])
def test_strict_confirmation_preserves_legacy_ids_and_records(wardrobe, state):
    owner, client, garment_id, query = wardrobe
    with connection() as conn:
        if state in {"missing", "null"}:
            conn.execute("UPDATE garments SET processing_item_id=? WHERE id=?", (None if state == "null" else "missing-item", garment_id))
        else:
            conn.execute("UPDATE processing_items SET review_status=? WHERE id=(SELECT processing_item_id FROM garments WHERE id=?)", (state, garment_id))
    assert query.get_confirmed_available_garments(owner) == ()
    assert query.list_available_garment_ids(owner) == [garment_id]
    assert client.post("/api/v1/recommendations", json={"request_text": "Use my wardrobe"}).status_code == 404
    assert client.get("/api/v1/wardrobe/garments").json()[0]["id"] == garment_id
    assert client.get("/api/v1/recommendations").json() == []


@pytest.mark.parametrize("status", ["archived", "deleted"])
def test_availability_and_foreign_owner(wardrobe, status):
    owner, _, garment_id, query = wardrobe
    assert query.get_confirmed_available_garments("foreign") == ()
    with connection() as conn:
        conn.execute("UPDATE garments SET status=? WHERE id=?", (status, garment_id))
    assert query.get_confirmed_available_garments(owner) == ()
    assert query.list_available_garment_ids(owner) == []


def test_foreign_processing_provenance_is_excluded(wardrobe):
    owner, _, garment_id, query = wardrobe
    with connection() as conn:
        conn.execute("UPDATE processing_jobs SET user_id='foreign' WHERE id=(SELECT job_id FROM processing_items WHERE id=(SELECT processing_item_id FROM garments WHERE id=?))", (garment_id,))
    assert query.get_confirmed_available_garments(owner) == ()


@pytest.mark.parametrize("category,structure", GARMENT_STRUCTURE.items())
def test_structure_mapping_without_rewriting(wardrobe, category, structure):
    owner, _, garment_id, query = wardrobe
    with connection() as conn:
        conn.execute("UPDATE garments SET category=? WHERE id=?", (category, garment_id))
    snapshot = query.get_confirmed_available_garments(owner)[0]
    assert snapshot.category == category
    assert (snapshot.structural_role, snapshot.layering_index) == structure


def test_projection_precedence_and_nested_immutability(wardrobe):
    owner, _, garment_id, query = wardrobe
    attrs = {"style": "fallback", "fit": "regular", "material": "cotton", "color_temperature": "cool", "is_dominant": False,
             "color_palette": [{"hex": "#112233", "coverage": 0.7}], "custom_tags": ["campus"]}
    with connection() as conn:
        conn.execute("UPDATE garments SET attributes_json=?, style_tags=?, custom_tags=NULL, primary_colour='navy', secondary_colour='#ffffff' WHERE id=?", (json.dumps(attrs), json.dumps(["casual", "casual"]), garment_id))
    snapshot = query.get_confirmed_available_garments(owner)[0]
    assert snapshot.style_tags == ("casual",)
    assert snapshot.custom_tags == ("campus",)
    assert snapshot.primary_colour == "navy" and snapshot.secondary_colour == "#ffffff"
    assert snapshot.is_dominant is False and snapshot.fit == "regular"
    assert snapshot.colour_palette[0].coverage == 0.7
    with pytest.raises(FrozenInstanceError):
        snapshot.colour_palette[0].coverage = 1


def test_malformed_optional_json_and_style_string(wardrobe):
    owner, _, garment_id, query = wardrobe
    with connection() as conn:
        conn.execute("UPDATE garments SET attributes_json='invalid', additional_attributes='{}', style_tags=? WHERE id=?", (json.dumps("casual"), garment_id))
    snapshot = query.get_confirmed_available_garments(owner)[0]
    assert snapshot.style_tags == ("casual",) and snapshot.fit is None


def test_acquisition_uses_injected_snapshots_preserves_heuristic(wardrobe):
    owner, _, _, query = wardrobe
    base = query.get_confirmed_available_garments(owner)[0]
    snapshots = tuple(replace(base, garment_id=str(index), category=category) for index, category in enumerate([
        "short_sleeve_top", "long_sleeve_top", "trousers", "vest_dress", "long_sleeve_outwear"]))
    expected = []
    used = set()
    for snapshot in snapshots:
        role = service._role_for(snapshot.category, len(expected) + 1)
        if role in used and role != "accessory":
            continue
        expected.append((snapshot.garment_id, role))
        used.add(role)
        if len(expected) == 4:
            break
    class FakeQuery:
        def get_confirmed_available_garments(self, user_id):
            assert user_id == owner
            return snapshots
    with patch.object(service, "confirmed_garment_query", return_value=FakeQuery()), patch.object(service, "connection", side_effect=AssertionError("Acquisition must not read SQL")):
        result = service._recommended_garments(owner)
    assert [(item["id"], item["garment_role"]) for item in result] == expected


def test_adapter_order_matches_legacy_for_same_eligibility(wardrobe):
    owner, client, _, query = wardrobe
    second = confirmed_garment(client, "Second top", "red")
    with connection() as conn:
        conn.execute("UPDATE garments SET is_favourite=1 WHERE id=?", (second,))
    assert [item.garment_id for item in query.get_confirmed_available_garments(owner)] == query.list_available_garment_ids(owner)


def test_stricter_acquisition_does_not_rewrite_history_or_save(wardrobe):
    owner, client, garment_id, query = wardrobe
    # Seed a historical legacy result directly; J-14 closes public legacy generation.
    recommendation = service.create_recommendation(owner, "Use my wardrobe")
    with connection() as conn:
        before = tuple(conn.execute("SELECT * FROM recommendations WHERE id=?", (recommendation["id"],)).fetchone())
        conn.execute("UPDATE garments SET processing_item_id=NULL WHERE id=?", (garment_id,))
    assert query.get_confirmed_available_garments(owner) == ()
    assert client.get("/api/v1/recommendations").json()[0] == recommendation
    assert client.post("/api/v1/recommendations", json={"request_text": "Use my wardrobe"}).status_code == 404
    with connection() as conn:
        assert tuple(conn.execute("SELECT * FROM recommendations WHERE id=?", (recommendation["id"],)).fetchone()) == before
    saved = client.post(f"/api/v1/recommendations/{recommendation['id']}/save-as-outfit", json={"name": "Legacy saved"})
    assert saved.status_code == 409  # Integration correction now revalidates strict eligibility.


def test_recommendation_has_no_concrete_query_import():
    tree = ast.parse(Path(service.__file__).read_text(encoding="utf-8"))
    assert not any(isinstance(node, ast.ImportFrom) and node.module == "app.infrastructure.persistence.confirmed_garment_query_adapter" for node in ast.walk(tree))


@pytest.mark.parametrize("field", ["fit", "material"])
@pytest.mark.parametrize("value", ["regular", "", None, [], ["cotton", "linen"], ["", None, "regular", "regular"]])
def test_supported_description_values_are_preserved(wardrobe, field, value):
    owner, _, garment_id, query = wardrobe
    reviewed = ReviewItem(item_id="item", decision="accepted", attributes={field: value})
    with connection() as conn:
        conn.execute("UPDATE garments SET attributes_json=? WHERE id=?", (json.dumps(reviewed.attributes), garment_id))
    snapshot = query.get_confirmed_available_garments(owner)[0]
    assert getattr(snapshot, field) == (tuple(value) if isinstance(value, list) else value)
    assert field not in snapshot.invalid_attributes


@pytest.mark.parametrize("field", ["style_tags", "custom_tags"])
@pytest.mark.parametrize("value,expected,invalid", [(None, None, False), ([], (), False), ([42], None, True), (["casual", {}], None, True), ({}, None, True), ([None], None, True), ("", None, True)])
def test_missing_empty_and_malformed_tags(wardrobe, field, value, expected, invalid):
    owner, _, garment_id, query = wardrobe
    with connection() as conn:
        conn.execute(f"UPDATE garments SET {field}=?, attributes_json='{{}}', additional_attributes='{{}}' WHERE id=?", (json.dumps(value), garment_id))
    snapshot = query.get_confirmed_available_garments(owner)[0]
    assert getattr(snapshot, field) == expected
    assert (field in snapshot.invalid_attributes) is invalid


def test_malformed_json_is_not_replaced_by_valid_fallback(wardrobe):
    owner, _, garment_id, query = wardrobe
    with connection() as conn:
        conn.execute("UPDATE garments SET style_tags='broken', attributes_json=? WHERE id=?", (json.dumps({"style": ["casual"]}), garment_id))
    snapshot = query.get_confirmed_available_garments(owner)[0]
    assert snapshot.style_tags is None and "style_tags" in snapshot.invalid_attributes


@pytest.mark.parametrize("value,expected,invalid", [(None, None, False), ([], (), False), ([{}], None, True), ([{"hex": "#123456", "coverage": 2}], None, True), ([{"hex": "#123456"}, {}], None, True)])
def test_palette_missing_empty_invalid(wardrobe, value, expected, invalid):
    owner, _, garment_id, query = wardrobe
    with connection() as conn:
        conn.execute("UPDATE garments SET attributes_json=? WHERE id=?", (json.dumps({"color_palette": value}), garment_id))
    snapshot = query.get_confirmed_available_garments(owner)[0]
    assert snapshot.colour_palette == expected
    assert ("colour_palette" in snapshot.invalid_attributes) is invalid


def test_constructor_detaches_all_mutable_nested_inputs():
    values = {"style_tags": ["casual"], "custom_tags": ["campus"], "fit": ["regular", None], "material": ["cotton"], "invalid_attributes": ["pattern"]}
    entry = {"hex_value": "#123456", "coverage": 0.5}
    palette = [entry]
    snapshot = ConfirmedGarmentSnapshot("g", "u", "available", "vest", "Vest", "m", False, "t", colour_palette=palette, **values)
    for name, source in values.items():
        expected = tuple(source)
        source.append("changed")
        assert getattr(snapshot, name) == expected
        with pytest.raises(FrozenInstanceError):
            setattr(snapshot, name, ())
    entry["coverage"] = 1
    palette.clear()
    assert snapshot.colour_palette == (GarmentPaletteEntry("#123456", 0.5),)
    with pytest.raises(FrozenInstanceError):
        snapshot.colour_palette[0].coverage = 0
    with pytest.raises(TypeError):
        snapshot.fit[0] = "changed"


@pytest.mark.parametrize("field", ["style_tags", "custom_tags", "fit", "material", "invalid_attributes", "colour_palette", "primary_colour"])
def test_constructor_rejects_invalid_mutable_nested_values(field):
    with pytest.raises((ValueError, TypeError)):
        ConfirmedGarmentSnapshot("g", "u", "available", "vest", "Vest", "m", False, "t", **{field: [["nested"]]})
