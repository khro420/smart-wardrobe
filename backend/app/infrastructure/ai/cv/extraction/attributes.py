"""
attributes.py

Garment attribute extraction for outfit recommendation.

DESIGN PRINCIPLE:
=================
Only extract attributes that are:
1. Reliable from computer vision (color)
2. Rule-based from YOLO class (garment_type, layering_index)
3. User-provided descriptions (fit, style, material); unavailable before review

Removed: pattern, texture, structure, material estimation, formality, season, etc.
These were unreliable or irrelevant for recommendation.
"""

from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE

from app.infrastructure.ai.cv.extraction.color_analyzer import ColorAnalyzer


class AttributeExtractor:
    """
    Extracts garment attributes for outfit recommendation.
    
    Attributes extracted:
    - garment_type: rule-based from YOLO class
    - layering_index: rule-based from YOLO class  
    - color: primary_color, palette, temperature, is_dominant (CV)
    - manual: fit, style, material (user-provided; no inferred defaults)
    """

    GARMENT_TYPE_MAP = GARMENT_STRUCTURE

    def __init__(self):
        self.color_analyzer = ColorAnalyzer(num_dominant_colors=5)

    def get_garment_type(self, class_name: str) -> str:
        """Map YOLO class name to garment category."""
        return self.GARMENT_TYPE_MAP.get(class_name, ("unknown", 0))[0]

    def get_layering_index(self, class_name: str) -> int:
        """Map YOLO class name to layering index."""
        return self.GARMENT_TYPE_MAP.get(class_name, ("unknown", 0))[1]

    def get_manual_defaults(self, garment_type: str) -> dict:
        """Unmeasured attributes remain unavailable until supplied during review."""
        return {"fit": None, "style": None, "material": None}

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
