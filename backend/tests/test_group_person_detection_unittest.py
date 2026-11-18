import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from PIL import Image

from app.infrastructure.ai.group_person_detection import detect_people


class Tensor:
    def __init__(self, value): self.value = np.asarray(value)
    def cpu(self): return self
    def numpy(self): return self.value


class DetectionTest(unittest.TestCase):
    def test_contact_and_detected_object_are_protected(self):
        shape = (160, 240)
        left, right, dog = (np.zeros(shape, dtype=np.uint8) for _ in range(3))
        left[10:150, 20:110] = 1
        right[10:150, 100:210] = 1
        dog[60:90, 40:80] = 1
        boxes = [SimpleNamespace(xyxy=[[20, 10, 110, 150]], cls=[0], conf=[.9]),
                 SimpleNamespace(xyxy=[[100, 10, 210, 150]], cls=[0], conf=[.9]),
                 SimpleNamespace(xyxy=[[40, 60, 80, 90]], cls=[16], conf=[.9])]
        # Detector box coordinates use tensor-style cpu() and tolist().
        for box in boxes:
            box.xyxy = [Tensor(box.xyxy[0])]
        Tensor.tolist = lambda self: self.value.tolist()
        prediction = SimpleNamespace(boxes=boxes, masks=SimpleNamespace(data=[Tensor(x) for x in (left, right, dog)]))
        model = SimpleNamespace(predict=lambda *a, **kw: [prediction])
        data = BytesIO()
        Image.new('RGB', (240, 160), 'white').save(data, format='PNG')
        with patch('app.infrastructure.ai.group_person_detection._model', return_value=model):
            people = detect_people(data.getvalue())
        self.assertEqual(len(people), 2)
        self.assertEqual(people[0].mask.getpixel((50, 70)), 0)  # dog
        self.assertEqual(people[0].mask.getpixel((105, 50)), 0)  # contact
        self.assertEqual(people[1].mask.getpixel((105, 50)), 0)
        self.assertEqual(people[0].mask.getpixel((30, 30)), 255)
        self.assertEqual(people[1].mask.getpixel((180, 30)), 255)


if __name__ == '__main__':
    unittest.main()
