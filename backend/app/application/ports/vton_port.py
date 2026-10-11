from collections.abc import Callable
from typing import Protocol

from app.domain.value_objects.generated_visualisation import GeneratedVisualisation
from app.domain.value_objects.visualisation_plan import VisualisationPlan


class VTONPort(Protocol):
    def generate(
        self,
        plan: VisualisationPlan,
        person_image: bytes,
        garment_images: tuple[bytes, ...],
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> GeneratedVisualisation: ...
