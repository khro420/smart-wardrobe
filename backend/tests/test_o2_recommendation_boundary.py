"""O2 checks for the confirmed-garment recommendation identifier boundary."""

from io import BytesIO
import unittest

from fastapi.testclient import TestClient
from PIL import Image

from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.persistence.postgresql_repository import connection, utcnow
from app.main import app


def jpeg(colour: str) -> bytes:
    image = Image.new("RGB", (192, 192), colour)
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def confirmed_garment(client: TestClient, name: str, colour: str) -> str:
    uploaded = client.post("/api/v1/processing/jobs", files={"file": (f"{name}.jpg", jpeg(colour), "image/jpeg")})
    job = client.get(f"/api/v1/processing/jobs/{uploaded.json()['id']}").json()
    item_id = job["items"][0]["id"]
    reviewed = client.post(
        f"/api/v1/processing/jobs/{job['id']}/review",
        json={"items": [{"item_id": item_id, "decision": "accepted", "name": name, "category": "Top"}]},
    )
    assert reviewed.status_code == 200
    saved = client.post(
        f"/api/v1/processing/jobs/{job['id']}/confirm",
        json={"save_mode": "garments", "item_ids": [item_id]},
    )
    assert saved.status_code == 201
    return saved.json()["garment_ids"][0]


class RecommendationBoundaryTests(unittest.TestCase):
    def test_boundary_returns_only_callers_available_confirmed_ids(self):
        with TestClient(app, headers={"X-User-Id": "boundary-owner"}) as owner:
            owned = confirmed_garment(owner, "Owned top", "navy")
        with TestClient(app, headers={"X-User-Id": "boundary-other"}) as other:
            foreign = confirmed_garment(other, "Foreign top", "red")
        with connection() as conn:
            conn.execute("UPDATE garments SET status='archived', updated_at=? WHERE id=?", (utcnow(), foreign))
        query = SqliteConfirmedGarmentQuery()
        self.assertEqual(query.list_available_garment_ids("boundary-owner"), [owned])
        self.assertEqual(query.list_available_garment_ids("boundary-other"), [])

    def test_tampered_or_archived_recommendation_items_are_not_exposed_or_saved(self):
        with TestClient(app, headers={"X-User-Id": "recommendation-owner"}) as owner:
            owned = confirmed_garment(owner, "Owned recommendation top", "navy")
            recommendation = owner.post("/api/v1/recommendations", json={"request_text": "Use my confirmed wardrobe"}).json()
        with TestClient(app, headers={"X-User-Id": "recommendation-other"}) as other:
            foreign = confirmed_garment(other, "Other person's top", "red")

        with connection() as conn:
            conn.execute("UPDATE garments SET status='archived', updated_at=? WHERE id=?", (utcnow(), owned))
            conn.execute(
                "INSERT INTO recommendation_items (recommendation_id, garment_id, garment_role, item_order, created_at) VALUES (?, ?, 'upper', 2, ?)",
                (recommendation["id"], foreign, utcnow()),
            )

        with TestClient(app, headers={"X-User-Id": "recommendation-owner"}) as owner:
            fetched = owner.get(f"/api/v1/recommendations").json()[0]
            self.assertEqual(fetched["items"], [])
            saved = owner.post(f"/api/v1/recommendations/{recommendation['id']}/save-as-outfit", json={"name": "Must fail"})
            self.assertEqual(saved.status_code, 409)
        with TestClient(app, headers={"X-User-Id": "recommendation-other"}) as other:
            self.assertEqual(other.get("/api/v1/recommendations").json(), [])


if __name__ == "__main__":
    unittest.main()
