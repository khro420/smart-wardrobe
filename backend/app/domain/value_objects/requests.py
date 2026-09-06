from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class ReviewItem(BaseModel):
    item_id: str
    decision: Literal["accepted", "rejected"]
    name: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=50)
    primary_colour: str | None = Field(default=None, max_length=50)
    pattern: str | None = Field(default=None, max_length=50)
    attributes: dict[str, object] = Field(default_factory=dict)
    preferred_media: Literal["crop", "vtoff"] | None = None

    @field_validator("name", "category", "primary_colour", "pattern")
    @classmethod
    def trim_review_text(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Review values must not be blank.")
        return value

    @field_validator("attributes")
    @classmethod
    def manual_attributes_only(cls, value):
        for key, item in value.items():
            if key not in {"fit", "style", "material", "custom_tags", "color_temperature", "is_dominant"}:
                raise ValueError("Only reviewable garment attributes may be edited here.")
            if key == "color_temperature":
                if item not in {"warm", "cool", "neutral"}:
                    raise ValueError("Colour temperature must be warm, cool or neutral.")
                continue
            if key == "is_dominant":
                if not isinstance(item, bool):
                    raise ValueError("Colour dominance must be true or false.")
                continue
            values = item if isinstance(item, list) else [item]
            if len(values) > 20 or any(v is not None and (not isinstance(v, str) or len(v) > 100) for v in values):
                raise ValueError("Use at most 20 text values of up to 100 characters per attribute.")
        return value


class ReviewRequest(BaseModel):
    items: list[ReviewItem] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_items(self):
        if len({item.item_id for item in self.items}) != len(self.items):
            raise ValueError("Review each candidate only once per request.")
        return self


class ConfirmRequest(BaseModel):
    save_mode: Literal["garments", "outfit"]
    item_ids: list[str] = Field(min_length=1, max_length=100)
    outfit_name: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def valid_selection(self):
        if len(set(self.item_ids)) != len(self.item_ids):
            raise ValueError("Select each candidate only once.")
        if self.outfit_name is not None:
            self.outfit_name = self.outfit_name.strip()
        if self.save_mode == "outfit" and not self.outfit_name:
            raise ValueError("An outfit name is required.")
        return self


class GarmentUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=50)
    primary_colour: str | None = Field(default=None, max_length=50)
    pattern: str | None = Field(default=None, max_length=50)
    is_favourite: bool | None = None
    attributes: dict[str, object] | None = None

    @field_validator("attributes")
    @classmethod
    def validate_manual_attributes(cls, value):
        return ReviewItem.manual_attributes_only(value) if value is not None else None

    @field_validator("name", "category", "primary_colour", "pattern")
    @classmethod
    def validate_text(cls, value):
        return ReviewItem.trim_review_text(value)


class OutfitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    garment_ids: list[str] = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Outfit name must not be blank.")
        return value

    @field_validator("description")
    @classmethod
    def trim_description(cls, value):
        return value.strip() if value is not None else None

    @field_validator("garment_ids")
    @classmethod
    def unique_garments(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Select each garment only once.")
        return value


class OutfitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_favourite: bool | None = None
    garment_ids: list[str] | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value):
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Outfit name must not be blank.")
        return value

    @field_validator("description")
    @classmethod
    def trim_description(cls, value):
        return value.strip() if value is not None else None

    @field_validator("garment_ids")
    @classmethod
    def unique_garments(cls, value):
        if value is not None and len(set(value)) != len(value):
            raise ValueError("Select each garment only once.")
        return value


class VisualisationCreate(BaseModel):
    person_image_id: str
    outfit_id: str | None = None
    recommendation_id: str | None = None

    @model_validator(mode="after")
    def has_exactly_one_source(self) -> "VisualisationCreate":
        if bool(self.outfit_id) == bool(self.recommendation_id):
            raise ValueError("Provide exactly one of outfit_id or recommendation_id.")
        return self


class VisualisationPrepare(BaseModel):
    outfit_id: str | None = None
    recommendation_id: str | None = None

    @model_validator(mode="after")
    def has_exactly_one_source(self) -> "VisualisationPrepare":
        if bool(self.outfit_id) == bool(self.recommendation_id):
            raise ValueError("Provide exactly one of outfit_id or recommendation_id.")
        return self


class RecommendationCreate(BaseModel):
    request_text: str = Field(min_length=1, max_length=500)


class RecommendationSaveAsOutfit(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class PreferenceUpsert(BaseModel):
    preference_value: dict[str, object] = Field(default_factory=dict)
    weight: float | None = Field(default=None, ge=0, le=1)
