"""Literal mirror-and-gap presentation transform for a segmentation crop."""

from dataclasses import dataclass
from io import BytesIO
from typing import Literal

from PIL import Image


CANVAS_SIZE = 512
CONTENT_SIZE = 448


@dataclass(frozen=True)
class MirroredGarment:
    png_bytes: bytes
    seam_side: str
    source_size: tuple[int, int]
    edge_coverage: dict[str, float]


def reconstruct_mirrored_garment_png(payload: bytes, mirrored_side: Literal["left", "right"] = "right") -> MirroredGarment | None:
    """Place the untouched crop beside its horizontal mirror with a clear gap.

    This deliberately performs no silhouette cleanup, seam detection, trimming,
    or hidden-side inference. The review image is only a visual duplicate of
    the exact observed crop, so the user can decide whether it is useful.
    """
    with Image.open(BytesIO(payload)) as source:
        source.load()
        crop = source.convert("RGBA")
    alpha = crop.getchannel("A")
    if alpha.getbbox() is None:
        return None

    if mirrored_side not in {"left", "right"}:
        raise ValueError("Mirrored copy must be placed on the left or right.")
    width, height = crop.size
    gap = max(12, min(32, round(width * 0.08)))
    mirrored = crop.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    combined = Image.new("RGBA", (width * 2 + gap, height), (0, 0, 0, 0))
    if mirrored_side == "right":
        combined.alpha_composite(crop, (0, 0))
        combined.alpha_composite(mirrored, (width + gap, 0))
    else:
        combined.alpha_composite(mirrored, (0, 0))
        combined.alpha_composite(crop, (width + gap, 0))

    scale = min(CONTENT_SIZE / combined.width, CONTENT_SIZE / combined.height)
    output_size = (max(1, round(combined.width * scale)), max(1, round(combined.height * scale)))
    combined = combined.resize(output_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
    canvas.alpha_composite(combined, ((CANVAS_SIZE - output_size[0]) // 2, (CANVAS_SIZE - output_size[1]) // 2))
    encoded = BytesIO()
    canvas.save(encoded, "PNG", optimize=True)
    return MirroredGarment(
        encoded.getvalue(), f"middle_gap_mirror_{mirrored_side}", crop.size,
        {"middle_gap_pixels": float(gap), "source_width": float(width), "source_height": float(height)},
    )
