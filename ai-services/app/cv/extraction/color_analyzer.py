"""
color_analyzer.py

Simplified color analysis for garment images.
Extracts only what the recommender needs:
- primary_color (string name)
- color_palette (hex + coverage)
- color_temperature (warm/cool/neutral)
- is_dominant (shadow-tolerant dominance check)
"""

import cv2
import numpy as np


class ColorAnalyzer:
    """
    Extracts color information from garment images.
    """

    # Named color mapping for human-readable output
    # OpenCV HSV Ranges: Hue (0-180), Saturation (0-255), Value (0-255)
    COLOR_NAMES = {
        # 1. Neutral Basics (Low Saturation - Catch these first!)
        "black":     [(0, 0, 0),       (180, 50, 55)],   # Low brightness, low saturation
        "white":     [(0, 0, 200),     (180, 30, 255)],  # High brightness, very low saturation
        "gray":      [(0, 0, 55),      (180, 30, 200)],  # Mid brightness, very low saturation
        
        # 2. Muted Earth Tones / Complex Neutrals
        "beige":     [(10, 30, 150),   (30, 90, 255)],   # Muted, light warm tones (cream, tan, beige)
        "brown":     [(10, 30, 30),    (25, 180, 150)],  # Darker, richer warm muted tones
        
        # 3. Core Color Families (Lowered saturation floor to 30-40 to catch muted/dusty shades)
        "red":       [(0, 40, 40),     (10, 255, 255)],  # Includes crimson/burgundy
        "orange":    [(10, 40, 40),    (25, 255, 255)],  # Includes peach/terracotta
        "yellow":    [(25, 40, 40),    (35, 255, 255)],  # Includes gold
        "green":     [(35, 30, 30),    (85, 255, 255)],  # Dropped floor to 30: catches sage, olive, mint
        "blue":      [(85, 30, 30),    (130, 255, 255)], # Dropped floor to 30: catches teal, slate, navy, sky
        "purple":    [(130, 40, 40),   (165, 255, 255)], # Includes lavender, plum, magenta
        "pink":      [(165, 40, 40),   (180, 255, 255)], # Wraps around back to pink/red-pinks
    }

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

    def get_color_name_from_hsv(self, hsv_color):
        """Map HSV color to nearest named color."""
        h, s, v = hsv_color
        for name, (lower, upper) in self.COLOR_NAMES.items():
            if (lower[0] <= h <= upper[0] and
                lower[1] <= s <= upper[1] and
                lower[2] <= v <= upper[2]):
                return name
        return "unknown"

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

        # Build palette with names and track name aggregates for shadow handling
        palette = []
        name_percentages = {}
        
        for hex_color, pct, rgb in dominant:
            rgb_arr = np.uint8([[rgb]])
            hsv = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2HSV)[0][0]
            color_name = self.get_color_name_from_hsv(hsv)

            palette.append({
                "hex": hex_color,
                "rgb": list(rgb),
                "percentage": round(float(pct), 4),
                "color_name": color_name,
            })
            
            # Aggregate totals by color family name to group shadows together
            name_percentages[color_name] = name_percentages.get(color_name, 0.0) + float(pct)

        # Base defaults if no palette was extracted
        primary_name = "unknown"
        is_dominant = False

        if palette:
            # Primary color is now explicitly the name string of the top cluster
            primary_name = palette[0]["color_name"]
            
            # Shadow-tolerant check: use the combined total of the primary color family
            combined_primary_coverage = name_percentages.get(primary_name, 0.0)
            is_dominant = combined_primary_coverage > 0.60

        return {
            "primary_color": str(primary_name),
            "palette": palette,
            "color_temperature": lab.get("color_temperature", "neutral"),
            "is_dominant": bool(is_dominant),
        }