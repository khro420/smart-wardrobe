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

from app.infrastructure.ai.cv.canonicalization.yolo_model import YOLOModel
from app.infrastructure.ai.cv.canonicalization.mask_processor import MaskProcessor
from app.infrastructure.ai.cv.canonicalization.cropper import Cropper
from app.infrastructure.ai.cv.extraction.attributes import AttributeExtractor


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
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))

        resized_img = cv2.resize(image, (nw, nh))

        canvas_img = np.zeros((self.SIZE, self.SIZE, 3), dtype=np.uint8)
        canvas_mask = np.zeros((self.SIZE, self.SIZE), dtype=np.uint8)

        y = (self.SIZE - nh) // 2
        x = (self.SIZE - nw) // 2

        canvas_img[y:y+nh, x:x+nw] = resized_img

        if mask is not None:
            resized_mask = cv2.resize(mask, (nw, nh), interpolation=cv2.INTER_NEAREST)
            canvas_mask[y:y+nh, x:x+nw] = resized_mask

        return canvas_img, canvas_mask

    def process(self, image_path: str, save_dir: str | None = None, include_media: bool = False):
        """
        Process image through full pipeline.
        Returns list of garment outputs with attributes for recommendation.
        """
        if save_dir is not None:
            os.makedirs(save_dir, exist_ok=True)

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
                if not np.any(mask):
                    continue

                # Crop
                cropped_img, cropped_mask = self.cropper.crop(image, mask)

                # Canonicalize a private working copy for attribute extraction.
                # The review crop below remains the original, tightly bounded
                # segmentation result so it can be compared with VTOFF output.
                canonical_img, canonical_mask = self.canonicalize(cropped_img, cropped_mask)

                # Get YOLO class name
                class_id = int(boxes.cls[i])
                class_name = names[class_id]
                confidence = float(boxes.conf[i])
                bounding_box = boxes.xyxy[i].cpu().tolist()
                if class_name not in self.attr.GARMENT_TYPE_MAP or not np.isfinite(confidence) or not 0.25 <= confidence <= 1:
                    continue
                if not np.all(np.isfinite(bounding_box)):
                    continue
                x1, y1, x2, y2 = bounding_box
                bounding_box = [max(0, x1), max(0, y1), min(image.shape[1], x2), min(image.shape[0], y2)]
                if bounding_box[0] >= bounding_box[2] or bounding_box[1] >= bounding_box[3]:
                    continue

                # Extract attributes (pass class_name for rule-based mapping)
                attr_result = self.attr.extract(canonical_img, canonical_mask, class_name)

                # Save canonical image
                path = None
                if save_dir is not None:
                    filename = f"{uuid.uuid4()}.jpg"
                    path = os.path.join(save_dir, filename)
                    cv2.imwrite(path, canonical_img)

                # Build output
                output = {
                    "detection": {
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": confidence,
                        "bounding_box": bounding_box,
                    },
                    "attributes": attr_result["attributes"],
                    "color": attr_result["color"],
                    "manual": attr_result["manual"],
                    "image_info": {
                        "crop_path": path,
                        "crop_size": [cropped_img.shape[1], cropped_img.shape[0]],
                        "canonical_size": self.SIZE,
                        "mask_coverage": float(np.mean(canonical_mask > 0)),
                    },
                }
                if include_media:
                    rgba = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2BGRA)
                    rgba[:, :, 3] = cropped_mask * 255
                    crop_ok, crop_encoded = cv2.imencode(".png", rgba)
                    mask_ok, mask_encoded = cv2.imencode(".png", mask * 255)
                    if not crop_ok or not mask_ok:
                        raise RuntimeError("Could not encode the garment segmentation evidence.")
                    output["crop_png"] = crop_encoded.tobytes()
                    output["mask_png"] = mask_encoded.tobytes()

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
