import cv2
import numpy as np


class MaskProcessor:

    def refine(self, mask, image_shape):

        mask = mask.cpu().numpy()

        mask = cv2.resize(mask, (image_shape[1], image_shape[0]))

        mask = (mask > 0.5).astype(np.uint8)

        kernel = np.ones((5, 5), np.uint8)

        # stronger cleanup (data quality lock)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        return mask