"""Homepage-only request: caller supplies flow identity, never wardrobe IDs."""
from pydantic import BaseModel, ConfigDict, Field


class HomepageRecommendationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    submission_key: str = Field(strict=True, min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
