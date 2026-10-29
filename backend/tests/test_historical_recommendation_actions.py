"""Read-only history with independent existing action APIs; no production changes."""
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.security import issue_access_token
from app.application.ports.visualisation_repository import configure_visualisation, runtime
from app.domain.value_objects.visualisation_plan import VTONConfiguration
from tests.test_recommendation_persistence import store, connect, assistant
from tests.test_recommendation_actions import history


@pytest.fixture
def completed(store, monkeypatch):
    from app.infrastructure.persistence import chat_history_query_adapter as adapter
    original_query = adapter.SqliteChatHistoryQuery
    monkeypatch.setattr(adapter, "SqliteChatHistoryQuery", lambda: original_query(store[0]))
    record = store[1].persist(assistant(store[2]))
    return store[0], record


def headers(owner="owner"):
    return {"Authorization":"Bearer "+issue_access_token(owner)}


def test_historical_save_api_state_concurrent_retry_and_unchanged_history(completed):
    path, record = completed
    with TestClient(app) as client:
        auth = headers(); url = "/api/v1/recommendations/"+record["id"]
        original = client.get("/api/v1/chats/"+record["chat_id"],headers=auth)
        assert original.status_code == 200
        with connect(path) as conn: before = history(conn)
        assert client.get(url+"/saved-outfit",headers=auth).json() == {"saved":False,"outfit_id":None}
        with ThreadPoolExecutor(4) as pool:
            results = list(pool.map(lambda _:client.post(url+"/save-as-outfit",headers=auth,json={"name":"Historical outfit"}), range(4)))
        assert all(r.status_code == 201 for r in results)
        assert all(r.json() == results[0].json() for r in results)
        assert client.get(url+"/saved-outfit",headers=auth).json() == {"saved":True,"outfit_id":results[0].json()["id"]}
        assert client.get("/api/v1/chats/"+record["chat_id"],headers=auth).json() == original.json()
        with connect(path) as conn:
            assert history(conn) == before
            assert conn.execute("SELECT count(*) FROM outfits").fetchone()[0] == 1


@pytest.mark.parametrize("change",[
    "UPDATE garments SET status='archived'", "UPDATE garments SET status='unavailable'",
    "UPDATE processing_items SET review_status='pending'", "UPDATE garments SET processing_item_id=NULL",
    "DELETE FROM garments", "UPDATE garments SET user_id='other'",
])
def test_history_survives_stale_source_but_action_apis_reject(completed,change):
    path, record = completed
    with connect(path) as conn: conn.execute(change)
    with TestClient(app) as client:
        auth = headers()
        detail = client.get("/api/v1/chats/"+record["chat_id"],headers=auth)
        assert detail.status_code == 200
        body = detail.json()
        assert body["request_text"] == "Suggest an outfit"
        assert body["recommendation"]["items"][0]["name"] == "Original dress"
        assert body["recommendation"]["items"][0]["currently_eligible"] is False
        assert client.post("/api/v1/recommendations/"+record["id"]+"/save-as-outfit",headers=auth,json={}).status_code == 409
        source = {"recommendation_id":record["id"]}
        assert client.post("/api/v1/visualisations/prepare",headers=auth,json=source).status_code == 409
        assert client.post("/api/v1/visualisations",headers=auth,json={**source,"person_image_id":"unused"}).status_code == 409
        with connect(path) as conn:
            assert conn.execute("SELECT count(*) FROM visualisations").fetchone()[0] == 0
            assert conn.execute("SELECT count(*) FROM outfits").fetchone()[0] == 0
            assert conn.execute("SELECT count(*) FROM nlp_chats").fetchone()[0] == 1


def test_legacy_conflict_and_cross_user_actions_are_controlled(completed):
    path, record = completed
    with connect(path) as conn: conn.execute("UPDATE recommendations SET status='saved'")
    with TestClient(app) as client:
        url = "/api/v1/recommendations/"+record["id"]
        assert client.get(url+"/saved-outfit",headers=headers()).json()["saved"] is False
        result = client.post(url+"/save-as-outfit",headers=headers(),json={})
        assert result.status_code == 409 and "legacy" in result.json()["detail"]
        assert client.get("/api/v1/chats/"+record["chat_id"],headers=headers()).status_code == 200
        assert client.get("/api/v1/chats/"+record["chat_id"],headers=headers("other")).status_code == 404
        assert client.get(url+"/saved-outfit",headers=headers("other")).status_code == 404
        assert client.post(url+"/save-as-outfit",headers=headers("other"),json={}).status_code == 404
        assert client.post("/api/v1/visualisations/prepare",headers=headers("other"),json={"recommendation_id":record["id"]}).status_code == 404
        assert client.post(url+"/save-as-outfit",json={}).status_code == 401


def test_supported_historical_visualisation_prepare_preserves_source_and_history(completed,monkeypatch):
    path, record = completed
    with TestClient(app) as client:
        original = runtime()
        from types import SimpleNamespace
        configure_visualisation(replace(original,media=SimpleNamespace(path_for_owner=lambda *_:None),configuration=VTONConfiguration))
        try:
            with connect(path) as conn: before = history(conn)
            result = client.post("/api/v1/visualisations/prepare",headers=headers(),json={"recommendation_id":record["id"]})
            assert result.status_code == 200
            assert result.json()["source_type"] == "recommendation" and result.json()["source_id"] == record["id"]
            assert result.json()["items"][0]["role"] == "one_piece"
            assert result.json()["items"][0]["item_order"] == 1
            with connect(path) as conn:
                assert history(conn) == before
                conn.execute("UPDATE garments SET category='long_sleeve_outwear'")
            result = client.post("/api/v1/visualisations/prepare",headers=headers(),json={"recommendation_id":record["id"]})
            assert result.status_code == 422 and "outerwear" in result.json()["detail"]
        finally: configure_visualisation(original)
