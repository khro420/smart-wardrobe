"""Geometry primitives for a future instance-masked group try-on pipeline.

These helpers deliberately require a caller-supplied mask; a bounding box alone
cannot safely distinguish a wearer from another person or an occluder.
"""
from dataclasses import dataclass

from PIL import Image, ImageChops


@dataclass(frozen=True)
class PersonCrop:
    box: tuple[int, int, int, int]
    size: tuple[int, int] = (768, 1024)

    def __post_init__(self):
        left, top, right, bottom = self.box
        if right <= left or bottom <= top:
            raise ValueError("Invalid person crop")
        # An aspect-matched crop is essential: prepare_person uses ImageOps.fit.
        if (right - left) * self.size[1] != (bottom - top) * self.size[0]:
            raise ValueError("Person crop must match inference aspect ratio")

    def extract(self, image: Image.Image) -> Image.Image:
        left, top, right, bottom = self.box
        if right <= 0 or bottom <= 0 or left >= image.width or top >= image.height:
            raise ValueError("Person crop does not intersect the image")
        if (right - left) * (bottom - top) > 50_000_000:
            raise ValueError("Person crop is too large to process.")
        # Pad at image edges instead of cutting off the wearer. This padded
        # context is only used for inference and is never pasted into output.
        padded = Image.new('RGB', (right - left, bottom - top), (240, 240, 240))
        padded.paste(image.convert('RGB'), (-left, -top))
        return padded.resize(self.size, Image.Resampling.LANCZOS)

    def composite(self, original: Image.Image, generated: Image.Image,
                  allowed_mask: Image.Image) -> Image.Image:
        if generated.size != self.size or allowed_mask.size != original.size:
            raise ValueError("Image or mask dimensions do not match")
        if self.box[2] <= 0 or self.box[3] <= 0 or self.box[0] >= original.width or self.box[1] >= original.height:
            raise ValueError("Person crop does not intersect the image")
        width = self.box[2] - self.box[0]
        height = self.box[3] - self.box[1]
        result = original.convert("RGB").copy()
        rendered = generated.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
        mask = allowed_mask.convert("L").crop(self.box)
        result.paste(rendered, self.box[:2], mask)
        return result


def validate_separate_masks(masks: list[Image.Image]) -> None:
    """Reject ambiguous overlapping edit regions before any compositing."""
    if not masks:
        raise ValueError("At least one mask is required")
    size = masks[0].size
    occupied = Image.new("L", size)
    for mask in masks:
        if mask.size != size:
            raise ValueError("Mask dimensions do not match")
        binary = mask.convert("L").point(lambda value: 255 if value else 0)
        if binary.getbbox() is None or ImageChops.multiply(occupied, binary).getbbox():
            raise ValueError("Empty or overlapping person edit regions")
        occupied = ImageChops.lighter(occupied, binary)
