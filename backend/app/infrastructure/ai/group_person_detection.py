"""Local person instance segmentation for group try-on preparation."""
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
import os
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps

os.environ.setdefault("YOLO_AUTOINSTALL", "false")


@dataclass(frozen=True)
class DetectedPerson:
    box: tuple[int, int, int, int]
    confidence: float
    mask: Image.Image


@lru_cache(maxsize=1)
def _model():
    from ultralytics import YOLO

    path = Path(__file__).resolve().parents[3] / "models" / "cv" / "yolov8s-seg.pt"
    if not path.is_file():
        raise RuntimeError("Person segmentation model is unavailable.")
    model = YOLO(str(path))
    if model.task != "segment":
        raise RuntimeError("Person segmentation model must support instance masks.")
    return model


def detect_people(payload: bytes) -> list[DetectedPerson]:
    import numpy as np

    with Image.open(BytesIO(payload)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    if min(image.size) < 128 or image.width * image.height > 25_000_000:
        raise ValueError("Choose an image between 128 pixels and 25 megapixels.")
    # Ultralytics interprets numpy images as BGR, unlike PIL's RGB convention.
    prediction = _model().predict(np.asarray(image)[:, :, ::-1].copy(), conf=0.35,
                                  retina_masks=True, verbose=False)[0]
    if prediction.masks is None:
        return []
    people = []
    protected = Image.new("L", image.size)
    for box, mask in zip(prediction.boxes, prediction.masks.data):
        values = box.xyxy[0].cpu().tolist()
        bounds = (max(0, int(values[0])), max(0, int(values[1])),
                  min(image.width, int(values[2] + 0.999)),
                  min(image.height, int(values[3] + 0.999)))
        pixels = (mask.cpu().numpy() > 0.5).astype("uint8") * 255
        instance = Image.fromarray(pixels, mode="L")
        if instance.size != image.size:
            raise RuntimeError("Person segmentation returned an unexpected mask size.")
        # Protect foreground objects, including carried animals. Dilation keeps
        # antialiased edges from leaking into generated clothing.
        if int(box.cls[0]) != 0:
            protected = ImageChops.lighter(protected, instance.filter(ImageFilter.MaxFilter(5)))
            continue
        if bounds[2] > bounds[0] and bounds[3] > bounds[1] and instance.getbbox():
            people.append(DetectedPerson(bounds, float(box.conf[0]), instance))
    people = sorted(people, key=lambda person: (person.box[0], person.box[1]))
    # Pixels claimed by multiple instances have uncertain ownership. Preserve
    # them in the original rather than assigning them to either wearer.
    ambiguous = protected
    for i, person in enumerate(people):
        for other in people[i + 1:]:
            ambiguous = ImageChops.lighter(ambiguous, ImageChops.multiply(person.mask, other.mask).filter(ImageFilter.MaxFilter(5)))
    return [DetectedPerson(person.box, person.confidence, ImageChops.subtract(person.mask, ambiguous)) for person in people]
