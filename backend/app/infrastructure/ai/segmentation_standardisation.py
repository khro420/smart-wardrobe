"""Deterministic presentation transform for segmentation-crop evidence.

This is deliberately not VTOFF: it cannot reconstruct occluded garment regions.
It remains useful as a reproducible visual baseline for generative evaluation.
"""

from dataclasses import dataclass
from io import BytesIO

from PIL import Image


CANVAS_SIZE = 512
CONTENT_SIZE = 448


class InvalidStandardisationSource(ValueError):
    """Raised when a source does not contain segmentation transparency."""


@dataclass(frozen=True)
class StandardisedGarment:
    png_bytes: bytes
    source_size: tuple[int, int]
    source_mask_box: tuple[int, int, int, int]
    output_mask_box: tuple[int, int, int, int]


def standardise_garment_png(payload: bytes) -> StandardisedGarment:
    """Centre an alpha-masked observed crop on a transparent 512 px canvas."""
    with Image.open(BytesIO(payload)) as source:
        source.load()
        has_alpha = source.mode in {"RGBA", "LA"} or "transparency" in source.info
        if not has_alpha:
            raise InvalidStandardisationSource("A segmentation alpha mask is required.")
        source_size = source.size
        rgba = source.convert("RGBA")

    alpha = rgba.getchannel("A")
    mask_box = alpha.getbbox()
    if mask_box is None:
        raise InvalidStandardisationSource("The segmentation mask is empty.")

    garment = rgba.crop(mask_box)
    width, height = garment.size
    scale = min(CONTENT_SIZE / width, CONTENT_SIZE / height)
    output_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    garment = garment.resize(output_size, Image.Resampling.LANCZOS)

    left = (CANVAS_SIZE - output_size[0]) // 2
    top = (CANVAS_SIZE - output_size[1]) // 2
    canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
    canvas.alpha_composite(garment, (left, top))

    encoded = BytesIO()
    canvas.save(encoded, "PNG", optimize=True)
    output_box = canvas.getchannel("A").getbbox()
    if output_box is None:
        raise InvalidStandardisationSource("Standardisation produced an empty mask.")
    return StandardisedGarment(encoded.getvalue(), source_size, mask_box, output_box)
