from typing import Protocol
from app.domain.value_objects.garment_attributes import GarmentAttributes


class GarmentAttributePort(Protocol):
    def extract(self, image_path: str) -> GarmentAttributes: ...
