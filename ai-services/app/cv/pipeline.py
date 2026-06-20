import cv2
import os
import uuid
import numpy as np

from app.cv.canonicalization.yolo_model import YOLOModel
from app.cv.canonicalization.mask_processor import MaskProcessor
from app.cv.canonicalization.cropper import Cropper
from app.cv.extraction.attributes import AttributeExtractor
from app.cv.extraction.clip_route import CLIPTemplateRouter


class GarmentPipeline:

    def __init__(self, model_path: str):

        self.detector = YOLOModel(model_path)
        self.mask_processor = MaskProcessor()
        self.cropper = Cropper()
        self.attr = AttributeExtractor()
        self.router = CLIPTemplateRouter()

        self.SIZE = 512  # canonical size

    def canonicalize(self, image, mask):

        image = cv2.bitwise_and(image, image, mask=mask)

        h, w = image.shape[:2]

        if h == 0 or w == 0:
            return np.zeros((self.SIZE, self.SIZE, 3), dtype=np.uint8)

        scale = self.SIZE / max(h, w)
        nw, nh = int(w * scale), int(h * scale)

        resized_img = cv2.resize(image, (nw, nh))
        resized_mask = cv2.resize(mask, (nw, nh))

        canvas_img = np.zeros((self.SIZE, self.SIZE, 3), dtype=np.uint8)
        canvas_mask = np.zeros((self.SIZE, self.SIZE), dtype=np.uint8)

        y = (self.SIZE - nh) // 2
        x = (self.SIZE - nw) // 2

        canvas_img[y:y+nh, x:x+nw] = resized_img
        canvas_mask[y:y+nh, x:x+nw] = resized_mask

        return canvas_img, canvas_mask

    def process(self, image_path: str, save_dir: str = "static/crops"):

        os.makedirs(save_dir, exist_ok=True)

        image = cv2.imread(image_path)
        results = self.detector.predict(image_path)

        outputs = []

        for r in results:

            if r.masks is None or r.boxes is None:
                continue

            masks = r.masks.data
            boxes = r.boxes
            names = r.names

            for i in range(len(boxes)):

                mask = self.mask_processor.refine(masks[i], image.shape)

                cropped_img, cropped_mask = self.cropper.crop(image, mask)

                canonical_img, canonical_mask = self.canonicalize(
                    cropped_img,
                    cropped_mask
                )

                # -------------------------
                # CLIP TEMPLATE ROUTING (NEW)
                # -------------------------
                clip_result = self.router.predict(cropped_img)
                template_type = clip_result["template"]

                filename = f"{uuid.uuid4()}.jpg"
                path = os.path.join(save_dir, filename)

                cv2.imwrite(path, canonical_img)

                class_id = int(boxes.cls[i])
                confidence = float(boxes.conf[i])
                clip_confidence = float(clip_result["confidence"])

                scores_sorted = sorted(clip_result["top_k"].items(), key=lambda x: x[1], reverse=True)
                top1, top2 = scores_sorted[0], scores_sorted[1]

                clip_margin = top1[1] - top2[1]

                outputs.append({
                    # ---------------- YOLO ----------------
                    "class_id": class_id,
                    "class_name_yolo": names[class_id],
                    "yolo_confidence": confidence,

                    # ---------------- CLIP (STRUCTURE) ----------------
                    "template_type": template_type,
                    "class_name_clip": template_type,
                    "clip_confidence": clip_result["confidence"],
                    "clip_margin": clip_margin,

                    # top predictions (clean + usable)
                    "template_top_k": dict(scores_sorted[:3]),

                    # optional raw full scores (debug only)
                    "clip_scores": clip_result.get("scores", {}),

                    # ---------------- STYLE ----------------
                    "style": clip_result.get("style", {}),

                    # ---------------- IMAGE INFO ----------------
                    "crop_path": path,
                    "mask_coverage": float(np.mean(canonical_mask > 0)),

                    # ---------------- ATTRIBUTES ----------------
                    "attributes": self.attr.extract(canonical_img, canonical_mask)
                })

        return outputs