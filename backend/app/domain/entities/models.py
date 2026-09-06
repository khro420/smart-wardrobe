"""Domain entities named in the report's class and package diagrams.

Persistence currently serialises these through the repository boundary; these
types keep the domain vocabulary explicit and independent of database rows.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class MediaAsset:
    id: str; user_id: str; media_type: str; storage_key: str; status: str = "available"


@dataclass
class User:
    id: str; email: str; display_name: str; account_status: str = "active"


@dataclass
class UserPreference:
    id: str; user_id: str; preference_type: str; preference_value: Any; is_active: bool = True


@dataclass
class ProcessingJob:
    id: str; user_id: str; source_media_id: str; status: str


@dataclass
class ProcessingItem:
    id: str; job_id: str; detected_category: str; confidence: float; review_status: str


@dataclass
class Garment:
    id: str; user_id: str; preferred_media_id: str; name: str; category: str; attributes: dict[str, Any]


@dataclass
class Outfit:
    id: str; user_id: str; name: str; status: str = "available"


@dataclass
class OutfitItem:
    outfit_id: str; garment_id: str; role: str; item_order: int


@dataclass
class NLPChat:
    id: str; user_id: str; request_text: str; status: str


@dataclass
class Recommendation:
    id: str; user_id: str; recommendation_type: str; status: str


@dataclass
class RecommendationItem:
    recommendation_id: str; garment_id: str; garment_role: str; item_order: int


@dataclass
class PersonImage:
    id: str; user_id: str; media_id: str; status: str = "available"


@dataclass
class Visualisation:
    id: str; user_id: str; person_image_id: str; status: str


@dataclass
class VisualisationItem:
    visualisation_id: str; garment_id: str; source_media_id: str; role: str; item_order: int
