"""Behavioural acceptance checks for the author's upload/review/save scope.

Synthetic detector outputs test workflow invariants, not model accuracy.
Real-weight/browser evidence is recorded separately by the demo walkthrough.
"""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import sqlite3
import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch

from tests.test_workflow import app, jpeg
from fastapi.testclient import TestClient
from PIL import Image
from app.application.garment_processing import garment_processing_orchestrator as processing
from app.application.wardrobe.wardrobe_service import confirm_candidates
from app.domain.value_objects.detected_garment import DetectedGarment
from app.domain.value_objects.standardisation_result import StandardisationResult
from app.domain.value_objects.garment_attributes import GarmentAttributes
from app.infrastructure.persistence.postgresql_repository import connection
from app.infrastructure.config import DATABASE_PATH
from app.application.garment_processing.processing_job_service import recover_interrupted_jobs
from app.application.visualisation.outfit_visualisation_service import recover_interrupted_visualisations
from app.infrastructure.media.protected_media_store import find_orphaned_media, media_path_for_owner, purge_orphaned_media, store_media_bytes


def png(colour, size=(256, 256), mode="RGB"):
    buffer = BytesIO()
    Image.new(mode, size, colour).save(buffer, "PNG")
    return buffer.getvalue()


class Detector:
    def analyse(self, path):
        return [DetectedGarment(
            category, 0.9, {"source": "test detector", "garment_type": role, "primary_colour": colour},
            (0, 0, 256, 256), png(255, mode="L"), png(colour, mode="RGBA"),
        ) for category, role, colour in [
            ("short_sleeve_top", "top", "#ff0000"),
            ("trousers", "bottom", "#0000ff"),
            ("vest", "top", "#00ff00"),
        ]] 


class GeneratedVtoffStub:
    """Fast test double; model accuracy is verified outside unit tests."""

    def standardise(self, item, user_id):
        media_id = store_media_bytes(png("#7f3f9f", (512, 512)), user_id, "vtoff_output")
        return StandardisationResult(
            preferred_media_id=item.crop_media_id,
            used_fallback=False,
            vtoff_media_id=media_id,
            notice="Synthetic test VTOFF output; review required.",
            metadata={"status": "generated", "generated": True, "requires_review": True},
        )


class GarmentWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.owner = str(uuid.uuid4())
        self.client = self.enterContext(TestClient(app, headers={"X-User-Id": self.owner}))
        self.enterContext(patch.object(processing, "get_garment_adapter", return_value=Detector()))
        self.enterContext(patch.object(processing, "get_standardisation_adapter", return_value=GeneratedVtoffStub()))

    def upload(self):
        response = self.client.post("/api/v1/processing/jobs", files={"file": ("outfit.jpg", jpeg(), "image/jpeg")})
        self.assertEqual(response.status_code, 202, response.text)
        job = self.client.get("/api/v1/processing/jobs/" + response.json()["id"]).json()
        self.assertEqual(job["status"], "review_required", job)
        return job

    def review(self, job, indices=(0,), **changes):
        response = self.client.post(f"/api/v1/processing/jobs/{job['id']}/review", json={"items": [
            {"item_id": job["items"][i]["id"], "decision": "accepted", **changes} for i in indices
        ]})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def confirm(self, job, indices=(0,), mode="garments"):
        return self.client.post(f"/api/v1/processing/jobs/{job['id']}/confirm", json={
            "item_ids": [job["items"][i]["id"] for i in indices], "save_mode": mode, "outfit_name": "Reviewed outfit",
        })

    def test_separate_protected_evidence_and_explicit_review(self):
        job = self.upload()
        self.assertIsNone(job["completed_at"])
        self.assertEqual(self.client.get("/api/v1/wardrobe/garments").json(), [])
        crops = []
        for item in job["items"]:
            self.assertEqual(item["bounding_box"], [0, 0, 256, 256])
            self.assertEqual(item["review_status"], "pending")
            self.assertIsNotNone(item["vtoff_media_id"])
            self.assertEqual(item["preferred_media_id"], item["crop_media_id"])
            for media in (item["crop_media_id"], item["mask_media_id"], item["vtoff_media_id"]):
                self.assertEqual(self.client.get(f"/api/v1/media/{media}").status_code, 200)
                self.assertEqual(self.client.get(f"/api/v1/media/{media}", headers={"X-User-Id": "intruder"}).status_code, 404)
            crops.append(self.client.get(f"/api/v1/media/{item['crop_media_id']}").content)
        self.assertEqual(len(set(crops)), 3)
        self.assertEqual(crops, [png(colour, mode="RGBA") for colour in ("#ff0000", "#0000ff", "#00ff00")])
        self.assertEqual(self.confirm(job).status_code, 409)
        reviewed = self.review(job, name="Reviewed dress", category="sling_dress", primary_colour="navy",
                               attributes={"fit": "loose", "style": "casual", "material": None, "custom_tags": ["campus"],
                                           "color_temperature": "cool", "is_dominant": False})
        self.assertEqual([i["review_status"] for i in reviewed["items"]], ["accepted", "pending", "pending"])
        self.assertEqual(reviewed["items"][0]["detected_category"], "short_sleeve_top")
        result = self.confirm(job)
        self.assertEqual(result.status_code, 201)
        garments = self.client.get("/api/v1/wardrobe/garments").json()
        self.assertEqual(len(garments), 1)
        self.assertEqual(garments[0]["name"], "Reviewed dress")
        self.assertEqual(garments[0]["category"], "sling_dress")
        self.assertEqual(garments[0]["primary_colour"], "navy")
        self.assertEqual(garments[0]["attributes"]["garment_type"], "dress")
        self.assertFalse(garments[0]["attributes"]["requires_review"])
        self.assertEqual(self.client.get("/api/v1/wardrobe/outfits").json(), [])
        self.assertEqual(self.confirm(job).status_code, 409)
        with TestClient(app, headers={"X-User-Id": self.owner}) as restarted:
            self.assertEqual(restarted.get("/api/v1/wardrobe/garments").json(), garments)
        # Read the committed file from a fresh interpreter, independent of the
        # API process, its lifespan and any in-memory state.
        read = subprocess.run([sys.executable, "-c",
            "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print(c.execute('SELECT name FROM garments WHERE user_id=?',(sys.argv[2],)).fetchone()[0])",
            str(DATABASE_PATH), self.owner], check=True, capture_output=True, text=True)
        self.assertEqual(read.stdout.strip(), "Reviewed dress")
        self.assertEqual(garments[0]["structural_scores"]["garment_role"], "dress")
        self.assertEqual(garments[0]["style_tags"], ["casual"])
        self.assertEqual(garments[0]["custom_tags"], ["campus"])
        self.assertEqual(garments[0]["attributes"]["color_temperature"], "cool")
        self.assertFalse(garments[0]["attributes"]["is_dominant"])

    def test_original_and_standardised_media_can_both_be_selected_and_saved(self):
        job = self.upload()
        original_item, standardised_item = job["items"][:2]
        self.assertNotEqual(original_item["crop_media_id"], original_item["vtoff_media_id"])

        original_bytes = self.client.get(f"/api/v1/media/{original_item['crop_media_id']}").content
        standardised_bytes = self.client.get(f"/api/v1/media/{standardised_item['vtoff_media_id']}").content
        self.assertNotEqual(original_bytes, standardised_bytes)
        original = Image.open(BytesIO(original_bytes))
        standardised = Image.open(BytesIO(standardised_bytes))
        self.assertEqual(original.size, (256, 256))
        self.assertEqual(standardised.size, (512, 512))
        self.assertEqual(standardised.mode, "RGB")

        response = self.client.post(f"/api/v1/processing/jobs/{job['id']}/review", json={"items": [
            {"item_id": original_item["id"], "decision": "accepted", "preferred_media": "crop"},
            {"item_id": standardised_item["id"], "decision": "accepted", "preferred_media": "vtoff"},
        ]})
        self.assertEqual(response.status_code, 200, response.text)
        reviewed = response.json()["items"]
        self.assertEqual(reviewed[0]["preferred_media_id"], original_item["crop_media_id"])
        self.assertEqual(reviewed[1]["preferred_media_id"], standardised_item["vtoff_media_id"])

        saved = self.confirm(job, (0, 1))
        self.assertEqual(saved.status_code, 201, saved.text)
        garments = {item["processing_item_id"]: item for item in self.client.get("/api/v1/wardrobe/garments").json()}
        self.assertEqual(garments[original_item["id"]]["preferred_media_id"], original_item["crop_media_id"])
        self.assertEqual(garments[standardised_item["id"]]["preferred_media_id"], standardised_item["vtoff_media_id"])

    def test_rejection_and_atomic_outfit_preserve_selection_order(self):
        job = self.upload()
        self.review(job, (0, 1))
        self.review(job, (2,), decision="rejected")
        self.assertEqual(self.confirm(job, (2,)).status_code, 409)
        saved = self.confirm(job, (1, 0), "outfit")
        self.assertEqual(saved.status_code, 201, saved.text)
        outfit = self.client.get("/api/v1/wardrobe/outfits").json()[0]
        self.assertEqual([i["garment_id"] for i in outfit["items"]], saved.json()["garment_ids"])
        self.assertEqual([i["role"] for i in outfit["items"]], ["bottom", "top"])
        self.assertEqual(len(self.client.get("/api/v1/wardrobe/garments").json()), 2)

    def test_foreign_jobs_candidates_and_media_are_rejected(self):
        job = self.upload()
        for suffix, body in [("/review", {"items": [{"item_id": job["items"][0]["id"], "decision": "accepted"}]}),
                             ("/confirm", {"item_ids": [job["items"][0]["id"]], "save_mode": "garments"})]:
            response = self.client.post(f"/api/v1/processing/jobs/{job['id']}{suffix}", json=body, headers={"X-User-Id": "intruder"})
            self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/processing/jobs/{job['id']}", headers={"X-User-Id": "intruder"}).status_code, 404)
        other = self.upload()
        response = self.client.post(f"/api/v1/processing/jobs/{job['id']}/review", json={"items": [
            {"item_id": other["items"][0]["id"], "decision": "accepted"}]})
        self.assertEqual(response.status_code, 404)
        with patch("app.infrastructure.security.ALLOW_DEVELOPMENT_IDENTITY", False):
            self.assertEqual(self.client.get("/api/v1/media/" + job["source_media_id"], headers={"Authorization": "Bearer invalid"}).status_code, 401)

    def test_invalid_review_and_confirmation(self):
        job = self.upload()
        path = f"/api/v1/processing/jobs/{job['id']}"
        item_id = job["items"][0]["id"]
        for body in [{"item_ids": [], "save_mode": "garments"},
                     {"item_ids": [item_id, item_id], "save_mode": "garments"},
                     {"item_ids": [item_id], "save_mode": "outfit", "outfit_name": "   "}]:
            self.assertEqual(self.client.post(path + "/confirm", json=body).status_code, 422)
        for extra in [{"name": " "}, {"preferred_media": "generated"}, {"attributes": {"embedding": [1, 2]}},
                      {"attributes": {"source": "fake model"}}, {"attributes": {"fit": {"bad": "object"}}},
                      {"attributes": {"color_temperature": "hot"}}, {"attributes": {"is_dominant": "yes"}}]:
            response = self.client.post(path + "/review", json={"items": [{"item_id": item_id, "decision": "accepted", **extra}]})
            self.assertEqual(response.status_code, 422, response.text)

    def test_invalid_uploads_never_create_jobs(self):
        before = self.count_jobs()
        gif = BytesIO(); Image.new("RGB", (256, 256)).save(gif, "GIF")
        for payload, mime, expected in [(b"not an image", "image/jpeg", 422), (png("red"), "image/jpeg", 415),
                                        (gif.getvalue(), "image/png", 415), (png("red", (32, 256)), "image/png", 422),
                                        (b"", "image/png", 413), (b"x", "image/webp", 415),
                                        (jpeg()[:50], "image/jpeg", 422)]:
            response = self.client.post("/api/v1/processing/jobs", files={"file": ("upload", payload, mime)})
            self.assertEqual(response.status_code, expected, response.text)
        with patch("app.infrastructure.media.protected_media_store.MAX_IMAGE_BYTES", 100):
            self.assertEqual(self.client.post("/api/v1/processing/jobs", files={"file": ("large.jpg", jpeg(), "image/jpeg")}).status_code, 413)
        self.assertEqual(self.count_jobs(), before)

    def count_jobs(self):
        with connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM processing_jobs WHERE user_id=?", (self.owner,)).fetchone()[0]

    def test_cancel_during_inference_and_repeated_run(self):
        class CancellingDetector:
            def analyse(_, path):
                with connection() as conn:
                    job_id = conn.execute("SELECT id FROM processing_jobs WHERE user_id=?", (self.owner,)).fetchone()[0]
                processing.cancel_job(job_id, self.owner)
                return Detector().analyse(path)
        with patch.object(processing, "get_garment_adapter", return_value=CancellingDetector()):
            uploaded = self.client.post("/api/v1/processing/jobs", files={"file": ("photo.jpg", jpeg(), "image/jpeg")}).json()
        job_id = uploaded["id"]
        processing.run_job(job_id, self.owner)
        job = processing.get_job(job_id, self.owner)
        self.assertEqual(job["status"], "cancelled")
        self.assertEqual(job["items"], [])

    def test_no_detection_and_internal_errors_are_controlled(self):
        for result, error in [([], None), (None, RuntimeError("SECRET_INTERNAL_PATH"))]:
            with patch.object(Detector, "analyse", return_value=result, side_effect=error):
                response = self.client.post("/api/v1/processing/jobs", files={"file": ("photo.jpg", jpeg(), "image/jpeg")})
            job = processing.get_job(response.json()["id"], self.owner)
            self.assertEqual(job["status"], "failed")
            self.assertEqual(job["items"], [])
            self.assertNotIn("SECRET_INTERNAL_PATH", job["error_message"])

    def test_concurrent_confirm_creates_only_one_copy(self):
        job = self.upload(); self.review(job)
        def save():
            return self.confirm(job).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda _: save(), range(2)))
        self.assertEqual(sorted(statuses), [201, 409])
        self.assertEqual(len(self.client.get("/api/v1/wardrobe/garments").json()), 1)

    def test_failed_outfit_transaction_rolls_back_and_can_retry(self):
        job = self.upload(); self.review(job, (0, 1))
        with connection() as conn:
            conn.execute("CREATE TRIGGER fail_outfit_test BEFORE INSERT ON outfit_items BEGIN SELECT RAISE(ABORT, 'injected failure'); END")
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                confirm_candidates(job["id"], self.owner, [i["id"] for i in job["items"][:2]], "outfit", "Test")
        finally:
            with connection() as conn:
                conn.execute("DROP TRIGGER fail_outfit_test")
        self.assertEqual(self.client.get("/api/v1/wardrobe/garments").json(), [])
        self.assertEqual(self.client.get("/api/v1/wardrobe/outfits").json(), [])
        self.assertEqual(processing.get_job(job["id"], self.owner)["status"], "review_required")
        self.assertEqual(self.confirm(job, (0, 1), "outfit").status_code, 201)

    def test_invalid_embedding_rejected(self):
        for vector in [[0.0], [float("nan")] * 768, [True] * 768, [float("inf")] * 768]:
            with self.assertRaises(ValueError):
                GarmentAttributes({"embedding": vector}).validate_embedding(768)
        GarmentAttributes({"embedding": None}).validate_embedding(768)
        GarmentAttributes({"embedding": [0.1] * 768}).validate_embedding(768)

    def test_restart_recovers_interrupted_jobs_but_preserves_review(self):
        job = self.upload()
        with connection() as conn:
            conn.execute("UPDATE processing_jobs SET status='processing' WHERE id=?", (job["id"],))
        waiting = self.upload()
        recover_interrupted_jobs()
        recovered = processing.get_job(job["id"], self.owner)
        self.assertEqual(recovered["status"], "failed")
        self.assertIn("service restart", recovered["error_message"])
        self.assertEqual(processing.get_job(waiting["id"], self.owner)["status"], "review_required")

    def test_restart_recovers_interrupted_visualisations(self):
        visualisation_id = str(uuid.uuid4())
        person_media_id = store_media_bytes(png("white"), self.owner, "personal_image")
        with connection() as conn:
            conn.execute("INSERT INTO person_images VALUES (?, ?, ?, ?, 'available', ?)", (str(uuid.uuid4()), self.owner, person_media_id, "Test image", "2026-01-01T00:00:00+00:00"))
            conn.execute(
                "INSERT INTO visualisations (id, user_id, outfit_id, recommendation_id, source_type, person_image_id, output_media_id, status, error_message, created_at, updated_at, completed_at) VALUES (?, ?, ?, NULL, 'outfit', ?, NULL, 'processing', NULL, ?, ?, NULL)",
                (visualisation_id, self.owner, str(uuid.uuid4()), conn.execute("SELECT id FROM person_images WHERE media_id=?", (person_media_id,)).fetchone()[0], "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
            )
        recover_interrupted_visualisations()
        with connection() as conn:
            visualisation = conn.execute("SELECT status, error_message FROM visualisations WHERE id=?", (visualisation_id,)).fetchone()
        self.assertEqual(visualisation["status"], "failed")
        self.assertIn("service restart", visualisation["error_message"])

    def test_orphan_cleanup_keeps_referenced_media_and_archives_only_aged_orphans(self):
        orphan_id = store_media_bytes(png("purple"), self.owner, "temporary")
        retained_id = store_media_bytes(png("orange"), self.owner, "upload")
        with connection() as conn:
            conn.execute("UPDATE media_assets SET created_at='2020-01-01T00:00:00+00:00' WHERE id IN (?, ?)", (orphan_id, retained_id))
            conn.execute("INSERT INTO processing_jobs VALUES (?, ?, ?, 'failed', NULL, ?, NULL, ?, ?)", (str(uuid.uuid4()), self.owner, retained_id, "2020-01-01T00:00:00+00:00", "2020-01-01T00:00:00+00:00", "2020-01-01T00:00:00+00:00"))
        candidates = find_orphaned_media(retention_hours=1)
        self.assertIn(orphan_id, {candidate["id"] for candidate in candidates})
        self.assertNotIn(retained_id, {candidate["id"] for candidate in candidates})
        orphan_path, _ = media_path_for_owner(orphan_id, self.owner)
        purge_orphaned_media(retention_hours=1, dry_run=False)
        self.assertFalse(orphan_path.exists())
        with connection() as conn:
            self.assertEqual(conn.execute("SELECT status FROM media_assets WHERE id=?", (orphan_id,)).fetchone()[0], "archived")
            self.assertEqual(conn.execute("SELECT status FROM media_assets WHERE id=?", (retained_id,)).fetchone()[0], "available")

    def test_bearer_ownership_without_development_identity(self):
        with patch("app.infrastructure.security.ALLOW_DEVELOPMENT_IDENTITY", False):
            users = []
            for _ in range(2):
                response = self.client.post("/api/v1/account/register", json={
                    "email": f"{uuid.uuid4().hex}@example.test", "password": "Long-test-password", "display_name": "Test owner"})
                self.assertEqual(response.status_code, 201)
                users.append({"Authorization": "Bearer " + response.json()["access_token"]})
            uploaded = self.client.post("/api/v1/processing/jobs", headers=users[0], files={"file": ("photo.jpg", jpeg(), "image/jpeg")})
            self.assertEqual(uploaded.status_code, 202)
            job_path = "/api/v1/processing/jobs/" + uploaded.json()["id"]
            job = self.client.get(job_path, headers=users[0]).json()
            self.assertEqual(self.client.get(job_path, headers=users[1]).status_code, 404)
            self.assertEqual(self.client.get("/api/v1/media/" + job["items"][0]["crop_media_id"], headers=users[1]).status_code, 404)
            self.assertEqual(self.client.post(job_path + "/confirm", headers=users[1], json={"save_mode": "garments", "item_ids": [job["items"][0]["id"]]}).status_code, 404)
            self.assertEqual(self.client.post("/api/v1/processing/jobs", files={"file": ("photo.jpg", jpeg(), "image/jpeg")}).status_code, 401)


if __name__ == "__main__":
    unittest.main()
