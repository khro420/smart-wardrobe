"""Focused geometry checks for the deterministic segmentation baseline."""

from io import BytesIO
import unittest

from PIL import Image, ImageDraw

from app.infrastructure.ai.segmentation_standardisation import (
    InvalidStandardisationSource,
    standardise_garment_png,
)


def encode(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class VtoffStandardisationTests(unittest.TestCase):
    def test_alpha_mask_is_cropped_scaled_and_centred_without_changing_source(self):
        source = Image.new("RGBA", (180, 300), (0, 0, 0, 0))
        ImageDraw.Draw(source).rectangle((40, 25, 139, 274), fill=(120, 40, 200, 255))
        source_bytes = encode(source)

        result = standardise_garment_png(source_bytes)
        output = Image.open(BytesIO(result.png_bytes))

        self.assertEqual(result.source_size, (180, 300))
        self.assertEqual(result.source_mask_box, (40, 25, 140, 275))
        self.assertEqual(output.size, (512, 512))
        self.assertEqual(output.mode, "RGBA")
        left, top, right, bottom = result.output_mask_box
        self.assertLessEqual(abs((left + right) - 512), 1)
        self.assertLessEqual(abs((top + bottom) - 512), 1)
        self.assertEqual(max(right - left, bottom - top), 448)
        self.assertEqual(output.getpixel((0, 0))[3], 0)
        self.assertEqual(encode(source), source_bytes)

    def test_missing_or_empty_alpha_mask_is_rejected(self):
        with self.assertRaises(InvalidStandardisationSource):
            standardise_garment_png(encode(Image.new("RGB", (50, 50), "red")))
        with self.assertRaises(InvalidStandardisationSource):
            standardise_garment_png(encode(Image.new("RGBA", (50, 50), (0, 0, 0, 0))))


if __name__ == "__main__":
    unittest.main()
