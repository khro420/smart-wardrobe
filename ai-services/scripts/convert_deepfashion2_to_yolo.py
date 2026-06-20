import os
import json
import cv2
import numpy as np
from tqdm import tqdm

DATASET_PATH = "../datasets/deepfashion2"
OUTPUT_PATH = "../datasets/deepfashion2_yolo_seg"

SPLITS = ["train", "validation"]  # you can add "validation" later

CATEGORY_MAP = {
    1: 0, 2: 1, 3: 2, 4: 3, 5: 4,
    6: 5, 7: 6, 8: 7, 9: 8,
    10: 9, 11: 10, 12: 11, 13: 12
}


def normalize_seg(poly, w, h):
    seg = []
    for i in range(0, len(poly), 2):
        x = poly[i] / w
        y = poly[i + 1] / h

        if x < 0 or x > 1 or y < 0 or y > 1:
            return None

        seg.extend([x, y])

    return seg


def polygon_area(poly):
    pts = np.array(poly, dtype=np.float32).reshape(-1, 2)
    if len(pts) < 3:
        return 0
    return abs(cv2.contourArea(pts.astype(np.float32)))


def is_valid_poly(poly, img_area):
    if poly is None or len(poly) < 6:
        return False

    if len(poly) > 400:
        return False

    area = polygon_area(poly)

    if area > 0.75 * img_area:
        return False

    return True


for split in SPLITS:

    img_dir = os.path.join(DATASET_PATH, split, "image")
    anno_dir = os.path.join(DATASET_PATH, split, "annos")

    out_img = os.path.join(OUTPUT_PATH, "images", split)
    out_lbl = os.path.join(OUTPUT_PATH, "labels", split)

    os.makedirs(out_img, exist_ok=True)
    os.makedirs(out_lbl, exist_ok=True)

    images = [f for f in os.listdir(img_dir) if f.endswith(".jpg")]

    print(f"\nProcessing {split}...")

    # 👇 proper tqdm setup with desc + total
    for img_name in tqdm(images, desc=f"{split} processing", unit="img"):

        img_id = img_name.replace(".jpg", "")
        anno_path = os.path.join(anno_dir, img_id + ".json")
        img_path = os.path.join(img_dir, img_name)

        if not os.path.exists(anno_path):
            continue

        image = cv2.imread(img_path)
        if image is None:
            continue

        h, w = image.shape[:2]
        img_area = h * w

        with open(anno_path, "r") as f:
            data = json.load(f)

        lines = []

        for key, obj in data.items():

            if not key.startswith("item"):
                continue

            cat = obj.get("category_id")
            if cat not in CATEGORY_MAP:
                continue

            cls = CATEGORY_MAP[cat]

            segs = obj.get("segmentation", [])
            if not segs:
                continue

            best_poly = max(segs, key=len)

            if not is_valid_poly(best_poly, img_area):
                continue

            norm_poly = normalize_seg(best_poly, w, h)
            if norm_poly is None:
                continue

            lines.append(f"{cls} " + " ".join(map(str, norm_poly)))

        label_path = os.path.join(out_lbl, img_id + ".txt")
        with open(label_path, "w") as f:
            f.write("\n".join(lines))

        cv2.imwrite(os.path.join(out_img, img_name), image)

print("\nDONE ✅ conversion complete")