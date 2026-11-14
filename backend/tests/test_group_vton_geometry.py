import pytest
from PIL import Image, ImageDraw

from app.infrastructure.ai.group_vton_geometry import PersonCrop, validate_separate_masks


def test_composite_changes_only_allowed_region():
    original = Image.new("RGB", (12, 8), "white")
    crop = PersonCrop((0, 0, 6, 8), (6, 8))
    mask = Image.new("L", original.size)
    ImageDraw.Draw(mask).rectangle((1, 2, 3, 5), fill=255)
    output = crop.composite(original, Image.new("RGB", crop.size, "red"), mask)
    assert output.getpixel((2, 3)) == (255, 0, 0)
    assert output.getpixel((5, 3)) == (255, 255, 255)
    assert output.getpixel((9, 3)) == (255, 255, 255)


def test_rejects_overlapping_masks_and_distorted_crop():
    mask = Image.new("L", (12, 8), 255)
    with pytest.raises(ValueError):
        validate_separate_masks([mask, mask])
    with pytest.raises(ValueError):
        PersonCrop((0, 0, 8, 8))
