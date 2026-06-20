import cv2
import numpy as np
from torch import embedding


class AttributeExtractor:

    # -------------------------
    # 1. DOMINANT COLOR (KMEANS MODE)
    # -------------------------
    def get_dominant_color(self, image, k=3):
        pixels = image.reshape(-1, 3)

        pixels = pixels[np.any(pixels != [0, 0, 0], axis=1)]

        if len(pixels) == 0:
            return "#000000"

        pixels = np.float32(pixels)

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.2)
        _, labels, centers = cv2.kmeans(
            pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
        )

        labels = labels.flatten()
        counts = np.bincount(labels)
        dominant = centers[np.argmax(counts)]

        return "#{:02x}{:02x}{:02x}".format(
            int(dominant[2]), int(dominant[1]), int(dominant[0])
        )

    # -------------------------
    # 2. COLOR VARIANCE (pattern proxy)
    # -------------------------
    def color_variance(self, image):
        pixels = image.reshape(-1, 3)
        pixels = pixels[np.any(pixels != [0, 0, 0], axis=1)]

        if len(pixels) == 0:
            return 0.0

        std = np.std(pixels)
        return float(min(std / 128.0, 1.0))

    # -------------------------
    # 3. SILHOUETTE SCORE
    # -------------------------
    def silhouette_score(self, mask):
        mask = mask.astype(np.uint8)

        area = np.sum(mask)
        total = mask.shape[0] * mask.shape[1]

        if total == 0:
            return 0.0

        return float(area / total)

    # -------------------------
    # 4. STRUCTURE SCORE
    # -------------------------
    def structure_score(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])

        return float(min(edge_density * 3.0, 1.0))

    # -------------------------
    # 5. BRIGHTNESS
    # -------------------------
    def brightness(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray) / 255.0)

    # -------------------------
    # 6. COLOR TEMPERATURE (NEW 🔥)
    # -------------------------
    def color_temperature(self, image):
        mean = np.mean(image, axis=(0, 1))  # BGR

        b, g, r = mean[0], mean[1], mean[2]

        warm = r + 0.5 * g
        cool = b + 0.5 * g

        if warm > cool * 1.1:
            return "warm"
        elif cool > warm * 1.1:
            return "cool"
        else:
            return "neutral"

    # -------------------------
    # 7. FIT CATEGORY (NEW 🔥)
    # -------------------------
    def fit_category(self, silhouette):
        if silhouette < 0.3:
            return "tight"
        elif silhouette < 0.6:
            return "regular"
        else:
            return "loose"

    # -------------------------
    # 8. TEXTURE COMPLEXITY (IMPROVED)
    # -------------------------
    def texture_complexity(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        score = np.var(laplacian)

        return float(min(score / 500.0, 1.0))

    # -------------------------
    # 9. FORMALITY SCORE (VERY IMPORTANT)
    # -------------------------
    def formality_score(self, structure, variance, brightness):
        score = (
            0.45 * structure +
            0.35 * (1.0 - variance) +
            0.20 * (1.0 - brightness)
        )
        return float(min(max(score, 0.0), 1.0))
    
    def semantic_score(self, embedding, template_embedding):
        return float(np.dot(embedding, template_embedding))

    # -------------------------
    # MAIN FUNCTION
    # -------------------------
    def extract(self, image, mask):

        masked = cv2.bitwise_and(image, image, mask=mask)

        silhouette = self.silhouette_score(mask)
        variance = self.color_variance(masked)
        structure = self.structure_score(masked)
        brightness = self.brightness(masked)

        return {
            "dominant_color": self.get_dominant_color(masked),
            "color_variance": variance,
            "silhouette_score": silhouette,
            "structure_score": structure,
            "brightness": brightness,

            # NEW FEATURES
            "color_temperature": self.color_temperature(masked),
            "fit_category": self.fit_category(silhouette),
            "texture_complexity": self.texture_complexity(masked),
            "formality_score": self.formality_score(structure, variance, brightness)
        }