import numpy as np
import cv2


class Cropper:

    def crop(self, image, mask):

        ys, xs = np.where(mask > 0)

        if len(xs) == 0 or len(ys) == 0:
            return image, mask

        x1, x2 = xs.min(), xs.max()
        y1, y2 = ys.min(), ys.max()

        cropped_img = image[y1:y2, x1:x2]
        cropped_mask = mask[y1:y2, x1:x2]

        return cropped_img, cropped_mask