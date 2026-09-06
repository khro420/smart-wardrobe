"""Contract tests for VTOFF provenance and failure fallback."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.application.ports.garment_standardisation_port import GarmentStandardisationInput
from app.infrastructure.ai.tryoffdiff_runtime import CATEGORY_LABELS, _pad_to_square
from app.infrastructure.ai.vtoff_adapter import MIN_VTOFF_OFFER_CONFIDENCE, TryOffDiffAdapter
from PIL import Image


class VtoffAdapterTests(unittest.TestCase):
    def test_every_deepfashion_category_has_a_multi_garment_label(self):
        self.assertEqual(len(CATEGORY_LABELS), 13)
        self.assertEqual(set(CATEGORY_LABELS.values()), {0, 1, 2})

    def test_conditioning_image_is_edge_padded_to_square(self):
        image = Image.new("RGB", (100, 50), "red")
        padded = _pad_to_square(image)
        self.assertEqual(padded.size, (512, 512))
        self.assertEqual(padded.getpixel((0, 0)), (255, 0, 0))

    def test_disabled_model_retains_crop_without_claiming_generation(self):
        item = GarmentStandardisationInput("source", "crop", "mask", "trousers")
        with tempfile.TemporaryDirectory() as folder, \
             patch("app.infrastructure.ai.vtoff_adapter.VTOFF_ENABLED", "false"), \
             patch("app.infrastructure.ai.vtoff_adapter.VTOFF_MODEL_DIR", Path(folder)):
            result = TryOffDiffAdapter().standardise(item, "owner")
        self.assertTrue(result.used_fallback)
        self.assertEqual(result.preferred_media_id, "crop")
        self.assertIsNone(result.vtoff_media_id)
        self.assertEqual(result.metadata, {"status": "fallback", "generated": False})

    def test_generated_asset_keeps_crop_default_and_records_evidence(self):
        item = GarmentStandardisationInput("source", "crop", "mask", "trousers")
        generated = SimpleNamespace(
            png_bytes=b"generated", latency_seconds=1.25, peak_vram_bytes=123,
            seed=42, inference_steps=20, guidance_scale=2.0,
        )
        fake_runtime = SimpleNamespace(generate=lambda *args, **kwargs: generated)
        with patch("app.infrastructure.ai.vtoff_adapter.VTOFF_ENABLED", "true"), \
             patch("app.infrastructure.ai.vtoff_adapter._runtime", return_value=fake_runtime), \
             patch("app.infrastructure.media.protected_media_store.media_path_for_owner", return_value=(Path("source.png"), "image/png")), \
             patch("app.infrastructure.media.protected_media_store.store_media_bytes", return_value="generated-media") as store:
            result = TryOffDiffAdapter().standardise(item, "owner")
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.preferred_media_id, "crop")
        self.assertEqual(result.vtoff_media_id, "generated-media")
        self.assertTrue(result.metadata["generated"])
        self.assertTrue(result.metadata["requires_review"])
        self.assertEqual(result.metadata["conditioning_media_id"], "source")
        self.assertEqual(result.metadata["crop_evidence_media_id"], "crop")
        self.assertEqual(result.metadata["mask_evidence_media_id"], "mask")
        store.assert_called_once_with(b"generated", "owner", "vtoff_output", "image/png")

    def test_low_confidence_category_withholds_generation(self):
        item = GarmentStandardisationInput(
            "source", "crop", "mask", "trousers",
            segmentation_confidence=MIN_VTOFF_OFFER_CONFIDENCE - 0.01,
        )
        with patch("app.infrastructure.ai.vtoff_adapter.VTOFF_ENABLED", "true"), \
             patch("app.infrastructure.ai.vtoff_adapter._runtime") as runtime:
            result = TryOffDiffAdapter().standardise(item, "owner")
        self.assertTrue(result.used_fallback)
        self.assertIsNone(result.vtoff_media_id)
        self.assertEqual(result.metadata["status"], "withheld_low_segmentation_confidence")
        runtime.assert_not_called()


if __name__ == "__main__":
    unittest.main()
