"""
pipeline.py

Garment processing pipeline for outfit recommendation.

Pipeline flow:
1. YOLO detection → 2. Mask refinement → 3. Crop → 4. Canonicalize → 5. Attribute extraction

Output format matches the agreed specification:
- detection: class_id, class_name, confidence
- attributes: garment_type, layering_index
- color: primary_color, color_palette, color_temperature, is_dominant
- manual: fit, style, material (defaults, user can override via API)
"""

import cv2
import os
import uuid
import numpy as np

from app.cv.canonicalization.yolo_model import YOLOModel
from app.cv.canonicalization.mask_processor import MaskProcessor
from app.cv.canonicalization.cropper import Cropper
from app.cv.extraction.attributes import AttributeExtractor


class GarmentPipeline:

    def __init__(self, model_path: str):
        self.detector = YOLOModel(model_path)
        self.mask_processor = MaskProcessor()
        self.cropper = Cropper()
        self.attr = AttributeExtractor()

        self.SIZE = 512

    def canonicalize(self, image, mask):
        """Canonicalize garment image to fixed size with padding."""
        if mask is not None:
            image = cv2.bitwise_and(image, image, mask=mask)

        h, w = image.shape[:2]
        if h == 0 or w == 0:
            return (
                np.zeros((self.SIZE, self.SIZE, 3), dtype=np.uint8),
                np.zeros((self.SIZE, self.SIZE), dtype=np.uint8)
            )

        scale = self.SIZE / max(h, w)
        nw, nh = int(w * scale), int(h * scale)

        resized_img = cv2.resize(image, (nw, nh))

        canvas_img = np.zeros((self.SIZE, self.SIZE, 3), dtype=np.uint8)
        canvas_mask = np.zeros((self.SIZE, self.SIZE), dtype=np.uint8)

        y = (self.SIZE - nh) // 2
        x = (self.SIZE - nw) // 2

        canvas_img[y:y+nh, x:x+nw] = resized_img

        if mask is not None:
            resized_mask = cv2.resize(mask, (nw, nh))
            canvas_mask[y:y+nh, x:x+nw] = resized_mask

        return canvas_img, canvas_mask

    def process(self, image_path: str, save_dir: str = "static/crops"):
        """
        Process image through full pipeline.
        Returns list of garment outputs with attributes for recommendation.
        """
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs("static/uploads", exist_ok=True)

        image = cv2.imread(image_path)
        if image is None:
            return {"error": f"Could not load image: {image_path}"}

        results = self.detector.predict(image_path)
        outputs = []

        for r in results:
            if r.masks is None or r.boxes is None:
                continue

            masks = r.masks.data
            boxes = r.boxes
            names = r.names

            for i in range(len(boxes)):
                # Process mask
                mask = self.mask_processor.refine(masks[i], image.shape)

                # Crop
                cropped_img, cropped_mask = self.cropper.crop(image, mask)

                # Canonicalize
                canonical_img, canonical_mask = self.canonicalize(cropped_img, cropped_mask)

                # Get YOLO class name
                class_id = int(boxes.cls[i])
                class_name = names[class_id]
                confidence = float(boxes.conf[i])

                # Extract attributes (pass class_name for rule-based mapping)
                attr_result = self.attr.extract(canonical_img, canonical_mask, class_name)

                # Save canonical image
                filename = f"{uuid.uuid4()}.jpg"
                path = os.path.join(save_dir, filename)
                cv2.imwrite(path, canonical_img)

                # Build output
                output = {
                    "detection": {
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": confidence,
                    },
                    "attributes": attr_result["attributes"],
                    "color": attr_result["color"],
                    "manual": attr_result["manual"],
                    "image_info": {
                        "crop_path": path,
                        "canonical_size": self.SIZE,
                        "mask_coverage": float(np.mean(canonical_mask > 0)),
                    },
                }

                outputs.append(output)

        # Sanitize numpy types for JSON serialization
        def sanitize(obj):
            if isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize(x) for x in obj]
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        return sanitize({
            "num_garments": len(outputs),
            "results": outputs,
        })