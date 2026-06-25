"""
attributes.py

Garment attribute extraction for outfit recommendation.

DESIGN PRINCIPLE:
=================
Only extract attributes that are:
1. Reliable from computer vision (color)
2. Rule-based from YOLO class (garment_type, layering_index)
3. User-provided with smart defaults (fit, style, material)

Removed: pattern, texture, structure, material estimation, formality, season, etc.
These were unreliable or irrelevant for recommendation.
"""

import cv2
import numpy as np

from app.cv.extraction.color_analyzer import ColorAnalyzer


class AttributeExtractor:
    """
    Extracts garment attributes for outfit recommendation.
    
    Attributes extracted:
    - garment_type: rule-based from YOLO class
    - layering_index: rule-based from YOLO class  
    - color: primary_color, palette, temperature, is_dominant (CV)
    - manual: fit, style, material (user-provided with defaults)
    """

    # DeepFashion2 class ID → garment category mapping
    # Layering index: 0 = base layer, 1 = mid layer, 2 = outer layer
    GARMENT_TYPE_MAP = {
        # Tops (layer 0 or 1)
        "short_sleeve_top":   ("top", 0),
        "long_sleeve_top":    ("top", 1),
        "vest":               ("top", 1),
        "sling":              ("top", 0),
        # Outerwear (layer 2)
        "short_sleeve_outwear": ("outerwear", 2),
        "long_sleeve_outwear":  ("outerwear", 2),
        "hoodie":               ("outerwear", 2),
        "sweater":              ("outerwear", 2),
        # Bottoms (layer 0)
        "shorts":             ("bottom", 0),
        "trousers":           ("bottom", 0),
        "jeans":              ("bottom", 0),
        "cargo_pants":        ("bottom", 0),
        "skirt":              ("bottom", 0),
        # Dresses (layer 0, one-piece)
        "short_sleeve_dress": ("dress", 0),
        "long_sleeve_dress":  ("dress", 0),
        "vest_dress":         ("dress", 0),
        "sling_dress":        ("dress", 0),
    }

    # Default manual attributes per garment type
    DEFAULT_MANUAL = {
        "top": {
            "fit": ["regular"],
            "style": ["casual"],
            "material": ["cotton"],
        },
        "bottom": {
            "fit": ["regular"],
            "style": ["casual"],
            "material": ["cotton"],
        },
        "outerwear": {
            "fit": ["regular"],
            "style": ["casual"],
            "material": ["polyester"],
        },
        "dress": {
            "fit": ["regular"],
            "style": ["casual"],
            "material": ["cotton"],
        },
    }

    def __init__(self):
        self.color_analyzer = ColorAnalyzer(num_dominant_colors=5)

    def get_garment_type(self, class_name: str) -> str:
        """Map YOLO class name to garment category."""
        return self.GARMENT_TYPE_MAP.get(class_name, ("unknown", 0))[0]

    def get_layering_index(self, class_name: str) -> int:
        """Map YOLO class name to layering index."""
        return self.GARMENT_TYPE_MAP.get(class_name, ("unknown", 0))[1]

    def get_manual_defaults(self, garment_type: str) -> dict:
        """Get default manual attributes for a garment type."""
        return self.DEFAULT_MANUAL.get(garment_type, {
            "fit": ["regular"],
            "style": ["casual"],
            "material": ["cotton"],
        })

    def extract_color(self, image, mask=None) -> dict:
        """Extract color attributes."""
        return self.color_analyzer.extract(image, mask)

    def extract(self, image, mask, class_name: str) -> dict:
        """
        Full attribute extraction for a single garment.
        
        Args:
            image: BGR image (canonicalized crop)
            mask: binary mask
            class_name: YOLO class name (e.g., "short_sleeve_top")
        
        Returns:
            dict with attributes, color, manual sections
        """
        # Rule-based attributes from YOLO class
        garment_type = self.get_garment_type(class_name)
        layering_index = self.get_layering_index(class_name)

        # Color extraction (CV)
        color_data = self.extract_color(image, mask)
        palette = color_data.get("palette", [])

        # Build color palette with coverage (filter noise < 5%)
        clean_palette = [
            {
                "hex": c["hex"],
                "coverage": round(c["percentage"], 4)
            }
            for c in palette
            if c.get("percentage", 0) > 0.05
        ]

        # Manual attributes (defaults, user can override)
        manual_defaults = self.get_manual_defaults(garment_type)

        return {
            "attributes": {
                "garment_type": garment_type,
                "layering_index": layering_index,
            },
            "color": {
                "primary_color": color_data.get("primary_color", "unknown"),
                "color_palette": clean_palette,
                "color_temperature": color_data.get("color_temperature", "neutral"),
                "is_dominant": color_data.get("is_dominant", False),
            },
            "manual": {
                "fit": manual_defaults["fit"],
                "style": manual_defaults["style"],
                "material": manual_defaults["material"],
            },
        }