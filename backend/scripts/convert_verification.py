import cv2
import os
import random
import numpy as np
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
img_dir = BACKEND_DIR / "datasets" / "deepfashion2_yolo_seg" / "images" / "validation"
label_dir = BACKEND_DIR / "datasets" / "deepfashion2_yolo_seg" / "labels" / "validation"

files = [f for f in os.listdir(img_dir) if f.endswith(".jpg")]

sample = random.sample(files, 40)

for f in sample:
    img_path = img_dir / f
    label_path = label_dir / f.replace(".jpg", ".txt")

    img = cv2.imread(img_path)

    if not os.path.exists(label_path):
        continue

    h, w = img.shape[:2]

    with open(label_path, "r") as file:
        lines = file.readlines()

    for line in lines:
        parts = list(map(float, line.strip().split()))
        cls = int(parts[0])
        coords = parts[1:]

        pts = []
        for i in range(0, len(coords), 2):
            x = int(coords[i] * w)
            y = int(coords[i+1] * h)
            pts.append((x, y))

        pts = np.array(pts, np.int32)
        cv2.polylines(img, [pts], True, (0,255,0), 2)

    cv2.imshow("check", img)
    cv2.waitKey(0)

cv2.destroyAllWindows()
