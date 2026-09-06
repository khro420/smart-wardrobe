"""Model-backed VTOFF adapter with segmentation evidence as safe fallback."""

from functools import lru_cache
import logging
from threading import Lock

from app.application.ports.garment_standardisation_port import GarmentStandardisationInput, GarmentStandardisationPort
from app.domain.value_objects.standardisation_result import StandardisationResult
from app.infrastructure.config import (
    VTOFF_DEVICE, VTOFF_ENABLED, VTOFF_GUIDANCE_SCALE, VTOFF_INFERENCE_STEPS,
    VTOFF_MODEL_DIR, VTOFF_SEED,
)
from app.infrastructure.ai.gpu_runtime import gpu_inference_slot


LOGGER = logging.getLogger(__name__)
MIN_VTOFF_OFFER_CONFIDENCE = 0.50


class TryOffDiffAdapter:
    """Generate a synthetic alternative; never prefer it silently."""

    def __init__(self):
        self._inference_lock = Lock()

    def standardise(self, item: GarmentStandardisationInput, user_id: str) -> StandardisationResult:
        fallback = StandardisationResult(
            preferred_media_id=item.crop_media_id,
            used_fallback=True,
            notice="AI VTOFF is unavailable; the original segmentation crop was retained.",
            metadata={"status": "fallback", "generated": False},
        )
        manifest = VTOFF_MODEL_DIR / "manifest.json"
        if VTOFF_ENABLED in {"0", "false", "off", "disabled"}:
            return fallback
        if VTOFF_ENABLED == "auto" and not manifest.exists():
            return fallback

        from app.infrastructure.ai.tryoffdiff_runtime import (
            CATEGORY_LABELS, MODEL_CLASS, MODEL_FILENAME, MODEL_REPOSITORY, MODEL_REVISION,
            MODEL_SHA256, TryOffDiffRuntime,
        )
        from app.infrastructure.media.protected_media_store import media_path_for_owner, store_media_bytes

        if item.category not in CATEGORY_LABELS:
            return StandardisationResult(
                preferred_media_id=item.crop_media_id,
                used_fallback=True,
                notice="This garment category is unsupported by VTOFF; the original segmentation crop was retained.",
                metadata={"status": "unsupported_category", "generated": False},
            )
        if not MIN_VTOFF_OFFER_CONFIDENCE <= item.segmentation_confidence <= 1.0:
            return StandardisationResult(
                preferred_media_id=item.crop_media_id,
                used_fallback=True,
                notice="VTOFF was withheld because the garment classification is uncertain; review the observed segmentation crop instead.",
                metadata={
                    "status": "withheld_low_segmentation_confidence", "generated": False,
                    "segmentation_confidence": item.segmentation_confidence,
                    "minimum_offer_confidence": MIN_VTOFF_OFFER_CONFIDENCE,
                },
            )

        try:
            source_path, _ = media_path_for_owner(item.source_media_id, user_id)
            with gpu_inference_slot(), self._inference_lock:
                generated = _runtime().generate(
                    source_path, item.category, seed=VTOFF_SEED,
                    guidance_scale=VTOFF_GUIDANCE_SCALE, inference_steps=VTOFF_INFERENCE_STEPS,
                )
            media_id = store_media_bytes(generated.png_bytes, user_id, "vtoff_output", "image/png")
        except Exception as exc:
            # VTOFF is optional. Failure must not discard observed segmentation
            # evidence or fail an otherwise valid extraction job.
            LOGGER.exception("VTOFF generation failed; retaining segmentation crop")
            return StandardisationResult(
                preferred_media_id=fallback.preferred_media_id,
                used_fallback=True,
                notice=f"AI VTOFF failed ({type(exc).__name__}); the original segmentation crop was retained.",
                metadata=fallback.metadata,
            )

        return StandardisationResult(
            preferred_media_id=item.crop_media_id,
            used_fallback=False,
            vtoff_media_id=media_id,
            notice="An AI-generated VTOFF reconstruction is available for review. It may invent hidden details; the observed crop remains selected by default.",
            metadata={
                "status": "generated", "generated": True,
                "model_repository": MODEL_REPOSITORY, "model_revision": MODEL_REVISION,
                "model_file": MODEL_FILENAME, "model_sha256": MODEL_SHA256, "model_class": MODEL_CLASS,
                "category_label": item.category, "seed": generated.seed,
                "inference_steps": generated.inference_steps, "guidance_scale": generated.guidance_scale,
                "latency_seconds": round(generated.latency_seconds, 3),
                "peak_vram_bytes": generated.peak_vram_bytes,
                "conditioning_media_id": item.source_media_id,
                "crop_evidence_media_id": item.crop_media_id,
                "mask_evidence_media_id": item.mask_media_id,
                "segmentation_confidence": item.segmentation_confidence,
                "minimum_offer_confidence": MIN_VTOFF_OFFER_CONFIDENCE,
                "requires_review": True,
            },
        )


@lru_cache(maxsize=1)
def _runtime():
    from app.infrastructure.ai.tryoffdiff_runtime import TryOffDiffRuntime
    return TryOffDiffRuntime(VTOFF_MODEL_DIR, VTOFF_DEVICE)


@lru_cache(maxsize=1)
def get_standardisation_adapter() -> GarmentStandardisationPort:
    return TryOffDiffAdapter()
