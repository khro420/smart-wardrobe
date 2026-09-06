from pathlib import Path
from typing import Protocol
from app.domain.value_objects.detected_garment import DetectedGarment


class GarmentSegmentationPort(Protocol):
    def analyse(self, image_path: Path) -> list[DetectedGarment]: ...
