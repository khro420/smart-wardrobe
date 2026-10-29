"""Real API/persistence tag lifecycle; isolated test runtime, no UI changes."""
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.persistence.postgresql_repository import connection
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from tests.test_o2_recommendation_boundary import jpeg

TAGS = ["rec:v1:occasion:campus:allow", "rec:v1:formality:casual:allow"]


def upload(client):
    response = client.post("/api/v1/processing/jobs",files={"file":("garment.jpg",jpeg("blue"),"image/jpeg")})
    assert response.status_code == 202
    job = client.get(f"/api/v1/processing/jobs/{response.json()['id']}").json()
    return job["id"],job["items"][0]["id"]


def review_and_confirm(client, category="vest_dress", tags=TAGS):
    job,item = upload(client)
    response = client.post(f"/api/v1/processing/jobs/{job}/review",json={"items":[{
        "item_id":item,"decision":"accepted","category":category,"primary_colour":"blue",
        "attributes":{"custom_tags":tags,"style":"vintage"}}]})
    assert response.status_code == 200
    saved = client.post(f"/api/v1/processing/jobs/{job}/confirm",json={"save_mode":"garments","item_ids":[item]})
    assert saved.status_code == 201
    return saved.json()["garment_ids"][0],item


def test_tags_survive_review_confirmation_edit_persistence_and_snapshot():
    owner = str(uuid.uuid4())
    query = SqliteConfirmedGarmentQuery()
    with TestClient(app,headers={"X-User-Id":owner}) as client:
        identifier,item = review_and_confirm(client)
        with connection() as conn:
            processing = conn.execute("SELECT review_status,attributes_json FROM processing_items WHERE id=?",(item,)).fetchone()
            assert processing["review_status"] == "confirmed"
            assert json.loads(processing["attributes_json"])["custom_tags"] == TAGS
        assert query.get_confirmed_available_garments(owner)[0].custom_tags == tuple(TAGS)
        changed = ["ordinary tag","rec:v1:occasion:work:deny","rec:v1:formality:smart_casual:allow"]
        revision = next(g for g in client.get("/api/v1/wardrobe/garments").json() if g["id"] == identifier)["tag_edit"]["revision"]
        response = client.patch(f"/api/v1/wardrobe/garments/{identifier}",headers={"If-Match":revision},json={"attributes":{"custom_tags":changed}})
        assert response.status_code == 200 and response.json()["custom_tags"] == changed
        fetched = client.get("/api/v1/wardrobe/garments").json()
        assert next(g for g in fetched if g["id"] == identifier)["attributes"]["custom_tags"] == changed
        with connection() as conn:
            row = conn.execute("SELECT custom_tags,attributes_json FROM garments WHERE id=?",(identifier,)).fetchone()
            assert json.loads(row["custom_tags"]) == changed
            assert json.loads(row["attributes_json"])["custom_tags"] == changed
    # Fresh query after client closes verifies persistence, not a response mirror.
    assert SqliteConfirmedGarmentQuery().get_confirmed_available_garments(owner)[0].custom_tags == tuple(changed)


@pytest.mark.parametrize("category",["vest","trousers"])
def test_frontend_shaped_review_payload_blocks_accept_and_confirmation(category):
    with TestClient(app,headers={"X-User-Id":str(uuid.uuid4())}) as client:
        job,item = upload(client)
        payload = {"items":[{"item_id":item,"decision":"accepted","category":category,
                  "attributes":{"fit":None,"style":None,"material":None,"neckline":None,"sleeve_length":None,
                                "custom_tags":TAGS,"color_temperature":"neutral","is_dominant":False}}]}
        reviewed = client.post(f"/api/v1/processing/jobs/{job}/review",json=payload)
        assert reviewed.status_code == 422
        assert "Only reviewable garment attributes" in reviewed.text
        confirmed = client.post(f"/api/v1/processing/jobs/{job}/confirm",json={"save_mode":"garments","item_ids":[item]})
        assert confirmed.status_code == 409
        # Supported API payload works; no teammate code is patched to bypass it.
        del payload["items"][0]["attributes"]["neckline"]
        del payload["items"][0]["attributes"]["sleeve_length"]
        assert client.post(f"/api/v1/processing/jobs/{job}/review",json=payload).status_code == 200
        assert client.post(f"/api/v1/processing/jobs/{job}/confirm",json={"save_mode":"garments","item_ids":[item]}).status_code == 201


@pytest.mark.parametrize("excluded",["accepted","pending","rejected","null","missing","archived","foreign_garment","foreign_job"])
def test_injected_engine_only_uses_phase1_eligible_records(excluded):
    from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
    from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
    owner = str(uuid.uuid4())
    with TestClient(app,headers={"X-User-Id":owner}) as client:
        valid,_ = review_and_confirm(client)
        invalid,item = review_and_confirm(client)
        with connection() as conn:
            if excluded in ("accepted","pending","rejected"):
                conn.execute("UPDATE processing_items SET review_status=? WHERE id=?",(excluded,item))
            elif excluded in ("null","missing"):
                conn.execute("UPDATE garments SET processing_item_id=? WHERE id=?",(None if excluded == "null" else "missing-"+str(uuid.uuid4()),invalid))
            elif excluded == "archived":
                conn.execute("UPDATE garments SET status='archived' WHERE id=?",(invalid,))
            elif excluded == "foreign_garment":
                conn.execute("UPDATE garments SET user_id='other' WHERE id=?",(invalid,))
            else:
                conn.execute("UPDATE processing_jobs SET user_id='other' WHERE id=(SELECT job_id FROM processing_items WHERE id=?)",(item,))
        session = RequestCandidateEngine(SqliteConfirmedGarmentQuery(),evaluator_factory=SuitabilityRequestEvaluator).generate_candidates(owner,StructuredOutfitRequest(occasion="campus",formality="casual"))
        candidates = list(session)
        assert len(candidates) == 1 and session.result.complete
        assert [m.garment.garment_id for m in candidates[0].candidate.members] == [valid]
        # No saved outfit is required or generated by candidate evaluation.
        assert client.get("/api/v1/wardrobe/outfits").json() == []


def test_malformed_persisted_tags_are_unknown_not_replaced_with_valid_mirror():
    from app.application.recommendation.suitability_evidence_mapper import SuitabilityEvidenceParser
    owner = str(uuid.uuid4())
    with TestClient(app,headers={"X-User-Id":owner}) as client:
        identifier,_ = review_and_confirm(client)
        with connection() as conn:
            conn.execute("UPDATE garments SET custom_tags='malformed-json' WHERE id=?",(identifier,))
    snapshot = SqliteConfirmedGarmentQuery().get_confirmed_available_garments(owner)[0]
    assert "custom_tags" in snapshot.invalid_attributes
    assert SuitabilityEvidenceParser().parse(snapshot).state_for("occasion","campus") == "Unknown"
