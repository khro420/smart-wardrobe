import os

# Model inference must not mutate the Python environment at request time.
os.environ["YOLO_AUTOINSTALL"] = "false"
from ultralytics import YOLO


class YOLOModel:

    def __init__(self, model_path: str):
        self.model = YOLO(model_path)
        if self.model.task != "segment":
            raise ValueError("The configured weights must be an instance segmentation model.")

    def predict(self, image_path: str):
        # Native masks avoid stretching letterbox padding onto source coordinates.
        return self.model(image_path, retina_masks=True, conf=0.25, verbose=False)
