"""End-to-end smoke test for the documented garment-processing workflow."""

import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

TEST_DATA_DIR = tempfile.mkdtemp(prefix="smart-wardrobe-test-")
os.environ["SMART_WARDROBE_DATA_DIR"] = TEST_DATA_DIR
os.environ["SMART_WARDROBE_AI_MODE"] = "development"
os.environ["SMART_WARDROBE_ALLOW_DEV_IDENTITY"] = "true"

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402
from app.main import app  # noqa: E402
from app.infrastructure.ai.attribute_embedding_adapter import get_attribute_adapter  # noqa: E402


def jpeg() -> bytes:
    image = Image.new("RGB", (256, 256), "navy")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


class WorkflowTests(unittest.TestCase):
    def test_attribute_embedding_port(self):
        attributes = get_attribute_adapter().extract("not-used-by-development-adapter.jpg")
        self.assertEqual(attributes.values["source"], "pipeline-managed")
        self.assertIsNone(attributes.values["embedding"])

    def test_report_route_surface_and_job_cancellation(self):
        expected_routes = {
            "/health": {"get"},
            "/api/v1/account/register": {"post"}, "/api/v1/account/login": {"post"},
            "/api/v1/account/profile": {"get", "patch"}, "/api/v1/account/preferences": {"get"},
            "/api/v1/account/preferences/{preference_type}": {"put"},
            "/api/v1/media/{media_id}": {"get"}, "/api/v1/media/person-images": {"post"},
            "/api/v1/processing/jobs": {"post"}, "/api/v1/processing/jobs/{job_id}": {"get"},
            "/api/v1/processing/jobs/{job_id}/review": {"post"}, "/api/v1/processing/jobs/{job_id}/confirm": {"post"},
            "/api/v1/processing/jobs/{job_id}/cancel": {"post"},
            "/api/v1/wardrobe/garments": {"get"}, "/api/v1/wardrobe/garments/{garment_id}": {"patch", "delete"},
            "/api/v1/wardrobe/garments/{garment_id}/dependencies": {"get"},
            "/api/v1/wardrobe/outfits": {"get", "post"}, "/api/v1/wardrobe/outfits/{outfit_id}": {"patch", "delete"},
            "/api/v1/wardrobe/outfits/{outfit_id}/dependencies": {"get"},
            "/api/v1/recommendations": {"get", "post"}, "/api/v1/recommendations/{recommendation_id}/save-as-outfit": {"post"},
            "/api/v1/visualisations/person-images": {"get"}, "/api/v1/visualisations/prepare": {"post"},
            "/api/v1/visualisations": {"post"}, "/api/v1/visualisations/{visualisation_id}": {"get"},
            "/api/v1/visualisations/{visualisation_id}/cancel": {"post"},
        }
        # Convert OpenAPI's path-centric representation into method sets.
        route_surface = {path: set(methods.keys()) for path, methods in app.openapi()["paths"].items()}
        for path, methods in expected_routes.items():
            self.assertTrue(methods <= route_surface[path], path)

        with TestClient(app, headers={"X-User-Id": "cancel-user"}) as client:
            self.assertEqual(client.get("/health").status_code, 200)
            job = client.post("/api/v1/processing/jobs", files={"file": ("cancel.jpg", jpeg(), "image/jpeg")})
            self.assertEqual(job.status_code, 202)
            self.assertEqual(client.post(f"/api/v1/processing/jobs/{job.json()['id']}/cancel").status_code, 204)
            self.assertEqual(client.get(f"/api/v1/processing/jobs/{job.json()['id']}").json()["status"], "cancelled")

    def test_registration_and_bearer_token(self):
        with TestClient(app, headers={"X-User-Id": "demo-user"}) as client:
            registered = client.post("/api/v1/account/register", json={"email": "student@example.com", "password": "A-long-test-password", "display_name": "Student"})
            self.assertEqual(registered.status_code, 201)
            token = registered.json()["access_token"]
            bearer = {"Authorization": f"Bearer {token}"}
            self.assertEqual(client.get("/api/v1/account/profile", headers=bearer).json()["display_name"], "Student")
            preference = client.put(
                "/api/v1/account/preferences/style_note",
                headers=bearer,
                json={"preference_value": {"value": "minimal neutral outfits"}, "weight": 0.9},
            )
            self.assertEqual(preference.status_code, 200)
            self.assertEqual(preference.json()["preference_value"]["value"], "minimal neutral outfits")
            self.assertEqual(client.get("/api/v1/account/preferences", headers=bearer).json()[0]["weight"], 0.9)
            self.assertEqual(client.post("/api/v1/account/login", json={"email": "student@example.com", "password": "A-long-test-password"}).status_code, 200)

    def test_upload_review_confirm_and_owner_isolation(self):
        with TestClient(app, headers={"X-User-Id": "demo-user"}) as client:
            profile = client.get("/api/v1/account/profile")
            self.assertEqual(profile.status_code, 200)
            self.assertEqual(profile.json()["account_status"], "active")
            self.assertEqual(client.patch("/api/v1/account/profile", json={"display_name": "Wardrobe tester"}).json()["display_name"], "Wardrobe tester")
            uploaded = client.post("/api/v1/processing/jobs", files={"file": ("shirt.jpg", jpeg(), "image/jpeg")})
            self.assertEqual(uploaded.status_code, 202)
            job = client.get(f"/api/v1/processing/jobs/{uploaded.json()['id']}").json()
            self.assertEqual(job["status"], "review_required")
            self.assertEqual(len(job["items"]), 1)
            self.assertEqual(job["items"][0]["attributes"]["source"], "development fallback")
            self.assertIn("embedding", job["items"][0]["attributes"])

            item_id = job["items"][0]["id"]
            reviewed = client.post(f"/api/v1/processing/jobs/{job['id']}/review", json={"items": [{"item_id": item_id, "decision": "accepted", "name": "Navy shirt", "category": "short_sleeve_top"}]})
            self.assertEqual(reviewed.status_code, 200)
            confirmed = client.post(f"/api/v1/processing/jobs/{job['id']}/confirm", json={"save_mode": "outfit", "item_ids": [item_id], "outfit_name": "Test outfit"})
            self.assertEqual(confirmed.status_code, 201)

            garments = client.get("/api/v1/wardrobe/garments").json()
            self.assertEqual(garments[0]["name"], "Navy shirt")
            self.assertEqual(len(client.get("/api/v1/wardrobe/outfits").json()), 1)
            self.assertEqual(client.patch(f"/api/v1/wardrobe/outfits/{confirmed.json()['outfit_id']}", json={"is_favourite": True}).status_code, 200)
            self.assertEqual(client.get("/api/v1/wardrobe/garments", headers={"X-User-Id": "another-user"}).json(), [])
            self.assertEqual(
                client.put(
                    "/api/v1/account/preferences/style_note",
                    json={"preference_value": {"value": "comfortable campus outfits"}, "weight": 1},
                ).status_code,
                200,
            )

            recommendation = client.post(
                "/api/v1/recommendations",
                json={"request_text": "Suggest an outfit from my confirmed wardrobe"},
            )
            self.assertEqual(recommendation.status_code, 201)
            self.assertEqual(recommendation.json()["items"][0]["garment_id"], garments[0]["id"])
            self.assertEqual(recommendation.json()["request_text"], "Suggest an outfit from my confirmed wardrobe")
            self.assertEqual(recommendation.json()["preference_score"], 1.0)
            self.assertEqual(len(client.get("/api/v1/recommendations").json()), 1)
            saved_recommendation = client.post(
                f"/api/v1/recommendations/{recommendation.json()['id']}/save-as-outfit",
                json={"name": "Saved recommendation"},
            )
            self.assertEqual(saved_recommendation.status_code, 201)

            person = client.post("/api/v1/media/person-images", files={"file": ("me.jpg", jpeg(), "image/jpeg")})
            self.assertEqual(person.status_code, 201)
            visual = client.post("/api/v1/visualisations", json={"outfit_id": confirmed.json()["outfit_id"], "person_image_id": person.json()["id"]})
            self.assertEqual(visual.status_code, 202)
            finished = client.get(f"/api/v1/visualisations/{visual.json()['id']}").json()
            self.assertEqual(finished["status"], "completed")
            self.assertEqual(client.get(f"/api/v1/media/{finished['output_media_id']}").status_code, 200)
            self.assertEqual(client.get(f"/api/v1/media/{finished['output_media_id']}", headers={"X-User-Id": "another-user"}).status_code, 404)

            recommendation_visual = client.post(
                "/api/v1/visualisations",
                json={"recommendation_id": recommendation.json()["id"], "person_image_id": person.json()["id"]},
            )
            self.assertEqual(recommendation_visual.status_code, 202)
            recommendation_result = client.get(f"/api/v1/visualisations/{recommendation_visual.json()['id']}").json()
            self.assertEqual(recommendation_result["source_type"], "recommendation")
            self.assertEqual(recommendation_result["status"], "completed")
            self.assertEqual(
                client.post(
                    "/api/v1/visualisations",
                    json={"outfit_id": confirmed.json()["outfit_id"], "recommendation_id": recommendation.json()["id"], "person_image_id": person.json()["id"]},
                ).status_code,
                422,
            )


if __name__ == "__main__":
    unittest.main()
