"""Actual SQLite transactions; synthetic garment/media data, no real AI claim."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from types import SimpleNamespace
import sqlite3
import threading
import uuid
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.application.recommendation import recommendation_service as service
from app.application.visualisation import outfit_identifier_validator as visual
from app.application.visualisation import outfit_visualisation_service as jobs
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.ports.visualisation_repository import runtime, configure_visualisation
from app.domain.value_objects.visualisation_plan import VTONConfiguration
from tests.test_recommendation_persistence import store, connect, assistant


@pytest.fixture
def ready(store, monkeypatch):
    configure_local_workflow()
    path, repo, command = store
    record = repo.persist(assistant(command))
    monkeypatch.setattr(visual, "runtime", lambda: SimpleNamespace(media=SimpleNamespace(path_for_owner=lambda *_: None), configuration=VTONConfiguration))
    return path, record


@pytest.mark.parametrize("mutation", [
    "UPDATE processing_items SET review_status='pending'",
    "UPDATE processing_items SET review_status='accepted'",
    "UPDATE processing_items SET review_status='rejected'",
    "UPDATE garments SET status='archived'",
    "UPDATE garments SET status='deleted'",
    "UPDATE garments SET processing_item_id=NULL",
    "UPDATE garments SET processing_item_id='missing'",
    "DELETE FROM processing_items",
    "UPDATE processing_jobs SET user_id='other'",
    "UPDATE garments SET user_id='other'",
    "DELETE FROM garments",
])
def test_strict_save_and_visualisation_reject_every_invalid_member(ready, mutation):
    path, record = ready
    with connect(path) as conn: conn.execute(mutation)
    with pytest.raises(HTTPException) as error: service.save_as_outfit(record["id"], "owner", "Must fail")
    assert error.value.status_code == 409
    with connect(path) as conn:
        with pytest.raises(HTTPException) as error: visual.resolve_source(conn, "owner", recommendation_id=record["id"])
        assert error.value.status_code == 409
        assert conn.execute("SELECT count(*) FROM outfits").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM visualisations").fetchone()[0] == 0


def history(conn):
    return {table: [tuple(r) for r in conn.execute("SELECT * FROM "+table)] for table in
            ("recommendations", "recommendation_items", "recommendation_metadata", "recommendation_item_snapshots", "nlp_chats", "garments")}


def test_save_is_atomic_idempotent_and_history_immutable(ready):
    path, record = ready
    with connect(path) as conn: before = history(conn)
    with ThreadPoolExecutor(4) as pool:
        saved = list(pool.map(lambda _: service.save_as_outfit(record["id"], "owner", "Once"), range(8)))
    assert all(x == saved[0] for x in saved)
    assert service.saved_outfit_state(record["id"],"owner")["outfit_id"] == saved[0]["id"]
    with connect(path) as conn:
        assert history(conn) == before
        assert conn.execute("SELECT count(*) FROM outfits").fetchone()[0] == 1
        assert [tuple(r) for r in conn.execute("SELECT garment_id,role,item_order FROM outfit_items")] == [("garment","one_piece",1)]
    with pytest.raises(HTTPException) as error: service.save_as_outfit(record["id"], "other", None)
    assert error.value.status_code == 404
    with pytest.raises(HTTPException): service.saved_outfit_state(record["id"], "other")


def test_item_failure_rolls_back_entire_outfit(ready):
    path, record = ready
    with connect(path) as conn:
        conn.execute("CREATE TRIGGER injected_failure BEFORE INSERT ON outfit_items BEGIN SELECT RAISE(ABORT,'injected item failure'); END")
    with pytest.raises(sqlite3.IntegrityError): service.save_as_outfit(record["id"], "owner", None)
    with connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM outfits").fetchone()[0] == 0
        assert conn.execute("SELECT status FROM recommendations").fetchone()[0] == "available"


def test_legacy_saved_record_is_not_rewritten_or_duplicated(ready):
    path, record = ready
    with connect(path) as conn: conn.execute("UPDATE recommendations SET status='saved'")
    with pytest.raises(HTTPException) as error: service.save_as_outfit(record["id"], "owner", None)
    assert error.value.status_code == 409
    with connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM outfits").fetchone()[0] == 0
        assert conn.execute("SELECT status FROM recommendations").fetchone()[0] == "saved"


def test_invalid_second_member_is_not_silently_dropped(ready):
    path, record = ready
    with connect(path) as conn:
        conn.execute("INSERT INTO recommendation_items VALUES(?, 'missing-garment', 'lower', 2, 'now')", (record["id"],))
    with pytest.raises(HTTPException): service.save_as_outfit(record["id"], "owner", None)
    with connect(path) as conn:
        with pytest.raises(HTTPException): visual.resolve_source(conn,"owner",recommendation_id=record["id"])
        assert conn.execute("SELECT count(*) FROM outfits").fetchone()[0] == 0


def test_visualisation_validation_failure_creates_no_job(ready, monkeypatch):
    path, record = ready
    monkeypatch.setattr(jobs,"require_person",lambda *args: {"media_id":"person-media"})
    with connect(path) as conn: conn.execute("UPDATE garments SET status='archived'")
    with pytest.raises(HTTPException) as error: jobs.create_visualisation("owner","person",recommendation_id=record["id"])
    assert error.value.status_code == 409
    with connect(path) as conn: assert conn.execute("SELECT count(*) FROM visualisations").fetchone()[0] == 0


def test_corrupt_legacy_duplicate_references_are_rejected_not_dropped(ready):
    path, record = ready
    # Simulate legacy/corrupt storage without the current primary-key protection.
    # Only this disposable test database is changed, never the application schema.
    with connect(path) as conn:
        conn.execute("ALTER TABLE recommendation_items RENAME TO original_items")
        conn.execute("CREATE TABLE recommendation_items AS SELECT * FROM original_items")
        conn.execute("INSERT INTO recommendation_items SELECT * FROM original_items")
    with pytest.raises(HTTPException) as error: service.save_as_outfit(record["id"],"owner",None)
    assert error.value.status_code == 409
    with connect(path) as conn:
        with pytest.raises(HTTPException) as error: visual.resolve_source(conn,"owner",recommendation_id=record["id"])
        assert error.value.status_code == 422


def test_outerwear_category_cannot_be_disguised_as_supported_role(ready):
    path, record = ready
    with connect(path) as conn: conn.execute("UPDATE garments SET category='long_sleeve_outwear'")
    with connect(path) as conn:
        with pytest.raises(HTTPException) as error: visual.resolve_source(conn,"owner",recommendation_id=record["id"])
        assert error.value.status_code == 422


def test_write_lock_prevents_change_between_revalidation_and_insert(ready, monkeypatch):
    from app.application.recommendation import recommendation_actions
    path, record = ready
    original = recommendation_actions.strict_items
    attempts = []
    def checked(conn, *args):
        result = original(conn, *args)
        def change():
            other = sqlite3.connect(path, timeout=.05)
            try:
                other.execute("UPDATE garments SET status='archived'"); other.commit()
            except sqlite3.OperationalError as exc: attempts.append(str(exc))
            finally: other.close()
        worker = threading.Thread(target=change); worker.start(); worker.join()
        return result
    monkeypatch.setattr(recommendation_actions, "strict_items", checked)
    service.save_as_outfit(record["id"], "owner", None)
    assert attempts and "locked" in attempts[0]
    with connect(path) as conn: conn.execute("UPDATE garments SET status='archived'")
    with pytest.raises(HTTPException): service.save_as_outfit(record["id"], "owner", None)


def test_visualisation_role_ownership_and_order_checks(ready):
    path, record = ready
    with connect(path) as conn:
        plan, _ = visual.resolve_source(conn,"owner",recommendation_id=record["id"])
        assert plan.garments[0].role == "one_piece" and plan.garments[0].item_order == 1
        with pytest.raises(HTTPException) as error: visual.resolve_source(conn,"other",recommendation_id=record["id"])
        assert error.value.status_code == 404
        conn.execute("UPDATE recommendation_items SET garment_role='outerwear'")
    with connect(path) as conn:
        with pytest.raises(HTTPException) as error: visual.resolve_source(conn,"owner",recommendation_id=record["id"])
        assert error.value.status_code == 422


def test_execution_revalidates_queued_recommendation_and_never_calls_inference(ready, monkeypatch):
    from dataclasses import replace
    from unittest.mock import Mock
    path, record = ready
    # Use real request creation, stubbing only protected personal-media resolution.
    monkeypatch.setattr(jobs,"require_person",lambda *args: {"media_id":"person-media"})
    original = runtime(); adapter = Mock()
    configure_visualisation(replace(original, gpu_slot=lambda:nullcontext(), adapter=lambda:adapter))
    try:
        job = jobs.create_visualisation("owner", "person", recommendation_id=record["id"])
        with connect(path) as conn: conn.execute("UPDATE processing_items SET review_status='pending'")
        jobs.run_visualisation(job,"owner")
        adapter.generate.assert_not_called()
        with connect(path) as conn:
            result = conn.execute("SELECT status,error_code FROM visualisations WHERE id=?",(job,)).fetchone()
            assert tuple(result) == ("failed","unprocessable")
    finally: configure_visualisation(original)


@pytest.mark.parametrize("category",["short_sleeve_top","trousers"])
def test_actual_upload_review_confirm_strict_query_with_synthetic_detector(monkeypatch, category):
    from tests.test_garment_workflow import Detector, GeneratedVtoffStub, jpeg
    from app.application.garment_processing import garment_processing_orchestrator as processing
    from app.main import app
    monkeypatch.setattr(processing,"get_garment_adapter",lambda:Detector())
    monkeypatch.setattr(processing,"get_standardisation_adapter",lambda:GeneratedVtoffStub())
    owner = "review-"+str(uuid.uuid4())
    with TestClient(app,headers={"X-User-Id":owner}) as client:
        uploaded = client.post("/api/v1/processing/jobs",files={"file":("wardrobe.jpg",jpeg(),"image/jpeg")})
        assert uploaded.status_code == 202
        job = client.get("/api/v1/processing/jobs/"+uploaded.json()["id"]).json()
        item = next(x for x in job["items"] if x["detected_category"] == category)
        base = "/api/v1/processing/jobs/"+job["id"]
        assert client.post(base+"/confirm",json={"item_ids":[item["id"]],"save_mode":"garments"}).status_code == 409
        payload = {"item_id":item["id"],"decision":"accepted","name":"Reviewed correction","primary_colour":None,"pattern":None,
                   "attributes":{"fit":["regular",None],"style":["vintage","classic"],"material":None,"custom_tags":["owner note"]}}
        bad = {**payload,"attributes":{**payload["attributes"],"neckline":None,"sleeve_length":None}}
        assert client.post(base+"/review",json={"items":[bad]}).status_code == 422
        assert client.post(base+"/review",json={"items":[payload]}).status_code == 200
        saved = client.post(base+"/confirm",json={"item_ids":[item["id"]],"save_mode":"garments"})
        assert saved.status_code == 201, saved.text
        rows = SqliteConfirmedGarmentQuery().get_confirmed_available_garments(owner)
        assert len(rows) == 1 and rows[0].garment_id == saved.json()["garment_ids"][0]
        assert rows[0].name == "Reviewed correction" and rows[0].style_tags == ("vintage","classic")
        assert rows[0].fit == ("regular",None) and rows[0].material is None
        assert rows[0].primary_colour is None and rows[0].pattern is None
        assert "owner note" in rows[0].custom_tags
