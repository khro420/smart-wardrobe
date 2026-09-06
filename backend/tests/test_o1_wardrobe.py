"""O1 acceptance tests for the personal wardrobe and outfit collection.

These tests exercise the HTTP contract required by FR-17 and FR-19--FR-24.
The model pipeline is covered separately; here the development adapter keeps the
tests deterministic and focused on wardrobe persistence and ownership.
"""

import unittest
import uuid

from fastapi.testclient import TestClient

from app.infrastructure.persistence.postgresql_repository import connection, utcnow
from tests.test_workflow import app, jpeg


class O1WardrobeTests(unittest.TestCase):
    def setUp(self):
        self.owner = f"o1-{uuid.uuid4()}"
        self.client = self.enterContext(TestClient(app, headers={"X-User-Id": self.owner}))

    def create_garment(self, name: str, category: str, colour: str = "navy") -> dict:
        uploaded = self.client.post(
            "/api/v1/processing/jobs",
            files={"file": (f"{name}.jpg", jpeg(), "image/jpeg")},
        )
        self.assertEqual(uploaded.status_code, 202, uploaded.text)
        job = self.client.get(f"/api/v1/processing/jobs/{uploaded.json()['id']}").json()
        item_id = job["items"][0]["id"]
        reviewed = self.client.post(
            f"/api/v1/processing/jobs/{job['id']}/review",
            json={
                "items": [{
                    "item_id": item_id,
                    "decision": "accepted",
                    "name": name,
                    "category": category,
                    "primary_colour": colour,
                }]
            },
        )
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        saved = self.client.post(
            f"/api/v1/processing/jobs/{job['id']}/confirm",
            json={"save_mode": "garments", "item_ids": [item_id]},
        )
        self.assertEqual(saved.status_code, 201, saved.text)
        garment_id = saved.json()["garment_ids"][0]
        return next(item for item in self.client.get("/api/v1/wardrobe/garments").json() if item["id"] == garment_id)

    def test_garment_search_filter_sort_complete_edit_and_owner_isolation(self):
        shirt = self.create_garment("Navy Campus Shirt", "short_sleeve_top")
        trousers = self.create_garment("Stone Trousers", "trousers", "stone")

        updated = self.client.patch(
            f"/api/v1/wardrobe/garments/{shirt['id']}",
            json={
                "name": "Blue Oxford Shirt",
                "category": "long_sleeve_top",
                "primary_colour": "blue",
                "pattern": "solid",
                "is_favourite": True,
                "attributes": {
                    "fit": "regular",
                    "style": ["smart-casual"],
                    "material": "cotton",
                    "custom_tags": ["campus"],
                },
            },
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        body = updated.json()
        self.assertEqual(body["name"], "Blue Oxford Shirt")
        self.assertEqual(body["category"], "long_sleeve_top")
        self.assertEqual(body["primary_colour"], "blue")
        self.assertEqual(body["pattern"], "solid")
        self.assertTrue(body["is_favourite"])
        self.assertEqual(body["attributes"]["fit"], "regular")
        self.assertEqual(body["attributes"]["material"], "cotton")
        self.assertEqual(body["attributes"]["garment_type"], "top")

        self.assertEqual(
            [item["id"] for item in self.client.get("/api/v1/wardrobe/garments", params={"query": "oxford"}).json()],
            [shirt["id"]],
        )
        self.assertEqual(
            [item["id"] for item in self.client.get("/api/v1/wardrobe/garments", params={"category": "trousers"}).json()],
            [trousers["id"]],
        )
        self.assertEqual(
            [item["name"] for item in self.client.get("/api/v1/wardrobe/garments", params={"sort": "name_asc"}).json()],
            ["Blue Oxford Shirt", "Stone Trousers"],
        )
        self.assertEqual(
            [item["id"] for item in self.client.get("/api/v1/wardrobe/garments", params={"favourite": "true"}).json()],
            [shirt["id"]],
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/wardrobe/garments/{shirt['id']}",
                headers={"X-User-Id": "another-owner"},
                json={"name": "stolen"},
            ).status_code,
            404,
        )
        self.assertEqual(self.client.get("/api/v1/wardrobe/garments", params={"sort": "invalid"}).status_code, 422)

    def test_outfit_browse_search_filter_sort_and_atomic_membership_edit(self):
        shirt = self.create_garment("Oxford Shirt", "long_sleeve_top")
        trousers = self.create_garment("Wide Trousers", "trousers")
        vest = self.create_garment("Layering Vest", "vest")
        created = self.client.post(
            "/api/v1/wardrobe/outfits",
            json={"name": "Lecture Day", "description": "Comfortable campus layers", "garment_ids": [shirt["id"], trousers["id"]]},
        )
        self.assertEqual(created.status_code, 201, created.text)
        outfit_id = created.json()["id"]

        changed = self.client.patch(
            f"/api/v1/wardrobe/outfits/{outfit_id}",
            json={
                "name": "Library Layers",
                "description": "Quiet study outfit",
                "is_favourite": True,
                "garment_ids": [vest["id"], trousers["id"]],
            },
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["name"], "Library Layers")
        self.assertEqual(changed.json()["description"], "Quiet study outfit")
        self.assertTrue(changed.json()["is_favourite"])
        self.assertEqual([item["garment_id"] for item in changed.json()["items"]], [vest["id"], trousers["id"]])
        self.assertEqual([item["item_order"] for item in changed.json()["items"]], [1, 2])
        self.assertEqual(changed.json()["items"][0]["role"], "top")

        for params in (
            {"query": "study"},
            {"query": "layering"},
            {"category": "trousers"},
            {"creation_type": "manual"},
            {"favourite": "true"},
        ):
            self.assertEqual([item["id"] for item in self.client.get("/api/v1/wardrobe/outfits", params=params).json()], [outfit_id])
        self.assertEqual(self.client.get("/api/v1/wardrobe/outfits", params={"category": "long_sleeve_top"}).json(), [])
        self.assertEqual(self.client.get("/api/v1/wardrobe/outfits", params={"sort": "invalid"}).status_code, 422)

        foreign = self.create_garment("Owner Shoe", "sling")
        with TestClient(app, headers={"X-User-Id": "foreign-owner"}) as foreign_client:
            other = O1WardrobeTests.create_garment.__get__(self, O1WardrobeTests)
            original_client = self.client
            try:
                self.client = foreign_client
                foreign_item = other("Foreign Coat", "long_sleeve_outwear")
            finally:
                self.client = original_client
        rejected = self.client.patch(
            f"/api/v1/wardrobe/outfits/{outfit_id}",
            json={"name": "Must Roll Back", "garment_ids": [foreign["id"], foreign_item["id"]]},
        )
        self.assertEqual(rejected.status_code, 404)
        unchanged = self.client.get("/api/v1/wardrobe/outfits", params={"query": "Library Layers"}).json()[0]
        self.assertEqual(unchanged["name"], "Library Layers")
        self.assertEqual([item["garment_id"] for item in unchanged["items"]], [vest["id"], trousers["id"]])

        self.assertEqual(self.client.post("/api/v1/wardrobe/outfits", json={"name": "   ", "garment_ids": [shirt["id"]]}).status_code, 422)
        self.assertEqual(self.client.post("/api/v1/wardrobe/outfits", json={"name": "Duplicate", "garment_ids": [shirt["id"], shirt["id"]]}).status_code, 422)

    def test_dependency_preview_archive_policy_and_owner_isolation(self):
        garment = self.create_garment("Archive Test Shirt", "short_sleeve_top")
        outfit = self.client.post(
            "/api/v1/wardrobe/outfits",
            json={"name": "Active Outfit", "garment_ids": [garment["id"]]},
        ).json()
        outfit_id = outfit["id"]

        dependencies = self.client.get(f"/api/v1/wardrobe/garments/{garment['id']}/dependencies")
        self.assertEqual(dependencies.status_code, 200, dependencies.text)
        self.assertFalse(dependencies.json()["can_archive"])
        self.assertEqual(dependencies.json()["active_outfits"], [{"id": outfit_id, "name": "Active Outfit"}])
        self.assertEqual(self.client.delete(f"/api/v1/wardrobe/garments/{garment['id']}").status_code, 409)

        now = utcnow()
        visualisation_id = str(uuid.uuid4())
        with connection() as conn:
            conn.execute(
                "INSERT INTO visualisations (id, user_id, outfit_id, recommendation_id, source_type, person_image_id, output_media_id, status, error_message, created_at, updated_at, completed_at) "
                "VALUES (?, ?, ?, NULL, 'outfit', ?, NULL, 'queued', NULL, ?, ?, NULL)",
                (visualisation_id, self.owner, outfit_id, str(uuid.uuid4()), now, now),
            )
            conn.execute(
                "INSERT INTO visualisation_items "
                "(visualisation_id,garment_id,source_media_id,role,item_order) "
                "VALUES (?, ?, ?, 'top', 1)",
                (visualisation_id, garment["id"], garment["preferred_media_id"]),
            )

        outfit_dependencies = self.client.get(f"/api/v1/wardrobe/outfits/{outfit_id}/dependencies")
        self.assertFalse(outfit_dependencies.json()["can_archive"])
        self.assertEqual(outfit_dependencies.json()["active_visualisations"], [{"id": visualisation_id, "status": "queued"}])
        self.assertEqual(self.client.delete(f"/api/v1/wardrobe/outfits/{outfit_id}").status_code, 409)
        self.assertEqual(
            self.client.get(
                f"/api/v1/wardrobe/outfits/{outfit_id}/dependencies",
                headers={"X-User-Id": "intruder"},
            ).status_code,
            404,
        )

        with connection() as conn:
            conn.execute("UPDATE visualisations SET status='cancelled', updated_at=? WHERE id=?", (utcnow(), visualisation_id))
        self.assertTrue(self.client.get(f"/api/v1/wardrobe/outfits/{outfit_id}/dependencies").json()["can_archive"])
        self.assertEqual(self.client.delete(f"/api/v1/wardrobe/outfits/{outfit_id}").status_code, 204)
        self.assertTrue(self.client.get(f"/api/v1/wardrobe/garments/{garment['id']}/dependencies").json()["can_archive"])
        self.assertEqual(self.client.delete(f"/api/v1/wardrobe/garments/{garment['id']}").status_code, 204)
        self.assertEqual(self.client.get("/api/v1/wardrobe/garments").json(), [])


if __name__ == "__main__":
    unittest.main()
