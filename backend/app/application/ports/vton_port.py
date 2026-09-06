from typing import Protocol

from app.domain.value_objects.generated_visualisation import GeneratedVisualisation
from app.domain.value_objects.visualisation_plan import VisualisationPlan


class VTONPort(Protocol):
    def generate(
        self, plan: VisualisationPlan, person_image: bytes, garment_image: bytes
    ) -> GeneratedVisualisation: ...
