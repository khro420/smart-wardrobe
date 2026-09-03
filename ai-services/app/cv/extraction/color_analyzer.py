import cv2
import numpy as np


class ColorAnalyzer:
    """
    Extracts color information from garment images.
    """

    def __init__(self, num_dominant_colors=5):
        self.num_dominant_colors = num_dominant_colors

    def _remove_black_background(self, image, mask=None):
        """Remove black background pixels from analysis."""
        if mask is not None:
            pixels = image[mask > 0]
        else:
            pixels = image.reshape(-1, 3)
            pixels = pixels[np.any(pixels != [0, 0, 0], axis=1)]
        return pixels

    def get_dominant_colors_kmeans(self, image, mask=None, k=5):
        """
        Extract k dominant colors using K-Means clustering.
        Returns list of (hex_color, percentage, rgb) tuples.
        """
        pixels = self._remove_black_background(image, mask)

        if len(pixels) == 0:
            return [("#000000", 1.0, (0, 0, 0))]

        pixels = np.float32(pixels)

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.2)
        _, labels, centers = cv2.kmeans(
            pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
        )

        labels = labels.flatten()
        counts = np.bincount(labels, minlength=k)
        total = counts.sum()

        results = []
        for i in range(k):
            color = centers[i]
            hex_color = "#{:02x}{:02x}{:02x}".format(
                int(color[2]), int(color[1]), int(color[0])
            )
            rgb = (int(color[2]), int(color[1]), int(color[0]))
            percentage = counts[i] / total if total > 0 else 0
            results.append((hex_color, percentage, rgb))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def analyze_lab(self, image, mask=None):
        """
        LAB color space analysis for color temperature.
        """
        pixels = self._remove_black_background(image, mask)

        if len(pixels) == 0:
            return {"color_temperature": "neutral"}

        lab_pixels = cv2.cvtColor(pixels.reshape(-1, 1, 3), cv2.COLOR_BGR2LAB).reshape(-1, 3)

        l, a, b = lab_pixels[:, 0], lab_pixels[:, 1], lab_pixels[:, 2]

        warm = a + 0.5 * b
        cool = -a + 0.5 * b

        mean_warm = np.mean(warm)
        mean_cool = np.mean(cool)

        if mean_warm > mean_cool * 1.05:
            temperature = "warm"
        elif mean_cool > mean_warm * 1.05:
            temperature = "cool"
        else:
            temperature = "neutral"

        return {
            "color_temperature": temperature,
        }

    def extract(self, image, mask=None):
        """
        Full color analysis pipeline.
        Returns only what the recommender needs.
        """
        dominant = self.get_dominant_colors_kmeans(image, mask, self.num_dominant_colors)
        lab = self.analyze_lab(image, mask)

        # Build palette cleanly without color name mappings
        palette = []
        for hex_color, pct, rgb in dominant:
            palette.append({
                "hex": hex_color,
                "rgb": list(rgb),
                "percentage": round(float(pct), 4),
            })

        # Base defaults if no palette was extracted
        primary_hex = "#000000"
        is_dominant = False

        if palette:
            # Primary color is now directly the top hex value
            primary_hex = palette[0]["hex"]
            
            # Check if the primary hex cluster alone covers > 60% of the image
            is_dominant = palette[0]["percentage"] > 0.60

        return {
            "primary_color": primary_hex,
            "palette": palette,
            "color_temperature": lab.get("color_temperature", "neutral"),
            "is_dominant": bool(is_dominant),
        }