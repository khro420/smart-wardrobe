"""Image geometry and attribute invariants independent of model accuracy."""
from io import BytesIO
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import cv2
import numpy as np
from PIL import Image
import torch

from app.infrastructure.ai.cv.pipeline import GarmentPipeline
from app.infrastructure.ai.cv.canonicalization.cropper import Cropper
from app.infrastructure.ai.cv.canonicalization.mask_processor import MaskProcessor
from app.infrastructure.ai.cv.extraction.attributes import AttributeExtractor
from app.infrastructure.ai.cv.extraction.color_analyzer import ColorAnalyzer


class Boxes(SimpleNamespace):
    def __len__(self):
        return len(self.cls)


class SegmentationGeometryTests(unittest.TestCase):
    def test_crop_keeps_last_row_column_and_single_pixel(self):
        image = np.zeros((20, 30, 3), dtype=np.uint8)
        mask = np.zeros((20, 30), dtype=np.uint8)
        mask[10:20, 20:30] = 1
        crop, cropped_mask = Cropper().crop(image, mask)
        self.assertEqual(crop.shape, (10, 10, 3))
        self.assertEqual(int(cropped_mask.sum()), 100)
        mask[:] = 0; mask[19, 29] = 1
        crop, cropped_mask = Cropper().crop(image, mask)
        self.assertEqual(crop.shape, (1, 1, 3))
        self.assertEqual(int(cropped_mask.sum()), 1)

    def test_each_mask_produces_its_own_transparent_crop(self):
        source = np.full((80, 120, 3), 255, dtype=np.uint8)
        source[10:70, 10:40] = [0, 0, 255]
        source[10:70, 80:110] = [255, 0, 0]
        masks = torch.zeros((2, 80, 120))
        masks[0, 10:70, 10:40] = 1
        masks[1, 10:70, 80:110] = 1
        result = SimpleNamespace(masks=SimpleNamespace(data=masks), boxes=Boxes(
            cls=torch.tensor([0, 1]), conf=torch.tensor([0.9, 0.8]),
            xyxy=torch.tensor([[10, 10, 40, 70], [80, 10, 110, 70]])), names={0: "short_sleeve_top", 1: "trousers"})
        pipeline = GarmentPipeline.__new__(GarmentPipeline)
        pipeline.detector = SimpleNamespace(predict=lambda _: [result])
        pipeline.mask_processor = MaskProcessor(); pipeline.cropper = Cropper()
        pipeline.attr = AttributeExtractor(); pipeline.SIZE = 512
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.png"; cv2.imwrite(str(path), source)
            output = pipeline.process(str(path), include_media=True)
        self.assertEqual(output["num_garments"], 2)
        for index, expected in enumerate([(255, 0, 0), (0, 0, 255)]):
            item = output["results"][index]
            crop = Image.open(BytesIO(item["crop_png"]))
            mask = Image.open(BytesIO(item["mask_png"]))
            self.assertEqual(mask.size, (120, 80))
            self.assertEqual(crop.mode, "RGBA")
            self.assertEqual(crop.size, (30, 60))
            self.assertEqual(crop.getpixel((15, 30)), (*expected, 255))
            self.assertEqual(item["image_info"]["crop_size"], [30, 60])
            self.assertEqual(item["detection"]["bounding_box"], result.boxes.xyxy[index].tolist())
            self.assertIsNone(item["manual"]["fit"])
            self.assertIsNone(item["manual"]["material"])

    def test_black_garments_and_neutral_temperature_are_retained(self):
        analyzer = ColorAnalyzer()
        for value in (0, 128, 255):
            image = np.full((10, 10, 3), value, dtype=np.uint8)
            result = analyzer.extract(image, np.ones((10, 10), dtype=np.uint8))
            self.assertEqual(result["color_temperature"], "neutral")
            self.assertAlmostEqual(result["palette"][0]["percentage"], 1)
            self.assertEqual(result["primary_color"], "#" + f"{value:02x}" * 3)


if __name__ == "__main__":
    unittest.main()
