from io import BytesIO
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.application.garment_processing import garment_processing_orchestrator as processing
from app.domain.value_objects.detected_garment import DetectedGarment
from app.infrastructure.ai.mirrored_garment_reconstruction import reconstruct_mirrored_garment_png
from tests.test_workflow import app, jpeg


def _encode(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def test_reconstructs_an_untouched_crop_and_its_mirror_with_a_middle_gap():
    half = Image.new("RGBA", (70, 200), (0, 0, 0, 0))
    ImageDraw.Draw(half).polygon([(69, 0), (40, 12), (22, 60), (0, 158), (11, 199), (69, 199)], fill=(86, 90, 70, 255))

    result = reconstruct_mirrored_garment_png(_encode(half))

    assert result is not None
    assert result.seam_side == "middle_gap_mirror_right"
    assert result.source_size == (70, 200)
    assert result.edge_coverage["middle_gap_pixels"] == 12
    image = Image.open(BytesIO(result.png_bytes))
    assert image.mode == "RGBA"
    assert image.size == (512, 512)
    left, top, right, bottom = image.getchannel("A").getbbox()
    assert right - left > 300
    assert bottom - top > 400
    assert image.getpixel((256, 256))[3] == 0


def test_mirrors_a_complete_crop_without_attempting_to_clean_or_trim_it():
    complete = Image.new("RGBA", (100, 180), (80, 80, 80, 255))

    result = reconstruct_mirrored_garment_png(_encode(complete))
    assert result is not None
    assert result.source_size == complete.size


def test_existing_review_candidate_can_request_and_select_a_mirrored_preview():
    half = Image.new("RGBA", (70, 200), (0, 0, 0, 0))
    ImageDraw.Draw(half).polygon([(69, 0), (40, 12), (22, 60), (0, 158), (11, 199), (69, 199)], fill=(86, 90, 70, 255))

    class Detector:
        def analyse(self, _):
            return [DetectedGarment("long_sleeve_outwear", 0.9, {"source": "test detector"}, crop_png=_encode(half))]

    with TestClient(app, headers={"X-User-Id": str(uuid.uuid4())}) as client, patch.object(processing, "get_garment_adapter", return_value=Detector()):
        submitted = client.post("/api/v1/processing/jobs", files={"file": ("jacket.jpg", jpeg(), "image/jpeg")})
        assert submitted.status_code == 202, submitted.text
        job_id = submitted.json()["id"]
        job = client.get(f"/api/v1/processing/jobs/{job_id}").json()
        item = job["items"][0]
        assert item["mirror_media_id"] is None

        created = client.post(f"/api/v1/processing/jobs/{job_id}/items/{item['id']}/mirror-reconstruction")
        assert created.status_code == 200, created.text
        mirror_media_id = created.json()["items"][0]["mirror_media_id"]
        assert mirror_media_id
        assert client.get(f"/api/v1/media/{mirror_media_id}").status_code == 200

        rearranged = client.post(f"/api/v1/processing/jobs/{job_id}/items/{item['id']}/mirror-reconstruction?replace=true&mirrored_side=left")
        assert rearranged.status_code == 200, rearranged.text
        mirror_media_id = rearranged.json()["items"][0]["mirror_media_id"]
        assert mirror_media_id
        assert rearranged.json()["items"][0]["attributes"]["mirrored_reconstruction"]["mirrored_side"] == "left"

        reviewed = client.post(f"/api/v1/processing/jobs/{job_id}/review", json={"items": [
            {"item_id": item["id"], "decision": "accepted", "preferred_media": "mirror"},
        ]})
        assert reviewed.status_code == 200, reviewed.text
        assert reviewed.json()["items"][0]["preferred_media_id"] == mirror_media_id
