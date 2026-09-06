"""Configured CatVTON adapter and an explicitly labelled development substitute."""
from functools import lru_cache
from io import BytesIO
import os

from PIL import Image, ImageOps

from app.application.ports.vton_port import VTONPort
from app.domain.value_objects.generated_visualisation import GeneratedVisualisation, VTONFailure
from app.domain.value_objects.visualisation_plan import VisualisationPlan
from app.infrastructure.ai.vton_preprocessing import encode_png
from app.infrastructure.config import VTON_DEVICE, VTON_ENABLED, VTON_MODEL_DIR


class DevelopmentVTONAdapter:
    def generate(
        self, plan: VisualisationPlan, person_image: bytes, garment_image: bytes
    ) -> GeneratedVisualisation:
        with Image.open(BytesIO(person_image)) as source:
            image = ImageOps.fit(
                ImageOps.exif_transpose(source).convert("RGB"),
                (plan.configuration.width, plan.configuration.height),
                Image.Resampling.LANCZOS,
            )
        return GeneratedVisualisation(
            image=encode_png(image),
            width=plan.configuration.width,
            height=plan.configuration.height,
            model_version="development-copy-v2",
            latency_ms=0.0,
            output_kind="development",
            metadata={"generated": False},
        )


class UnavailableVTONAdapter:
    def generate(self, plan, person_image, garment_image):
        raise VTONFailure("unavailable")


@lru_cache(maxsize=1)
def _catvton():
    from app.infrastructure.ai.catvton_runtime import CatVTONRuntime
    return CatVTONRuntime(VTON_MODEL_DIR, VTON_DEVICE)


def get_vton_adapter() -> VTONPort:
    if os.getenv("SMART_WARDROBE_AI_MODE", "production").lower() == "development":
        return DevelopmentVTONAdapter()
    if VTON_ENABLED in {"0", "false", "off", "disabled"}:
        return UnavailableVTONAdapter()
    if VTON_ENABLED == "auto" and not (VTON_MODEL_DIR / "manifest.json").is_file():
        return UnavailableVTONAdapter()
    return _catvton()
