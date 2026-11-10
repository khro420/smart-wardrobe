from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal, Annotated
from app.domain.value_objects.recommendation_refinement import RefinementAction,canonical_uuid
from app.api.homepage_models import HomepageRecommendationCreate as LegacyHomepageCreate
from pydantic import field_validator


class InitialRefinement(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    version: Literal['assistant-refinement-request-1.0.0']
    kind: Literal['initial']
    excluded_categories: list[str] = Field(max_length=13)

    @model_validator(mode='after')
    def validate_categories(self):
        self.excluded_categories=list(RefinementAction.parse(self.model_dump()).excluded_categories)
        return self


class AlternativeRefinement(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    version: Literal['assistant-refinement-request-1.0.0']
    kind: Literal['alternative']
    parent_recommendation_id: str

    @model_validator(mode='after')
    def validate_parent(self):
        RefinementAction.parse(self.model_dump())
        return self


class WearerRequest(BaseModel):
    wearer_profile_id: str | None = Field(default=None,strict=True)

    @field_validator('wearer_profile_id')
    @classmethod
    def canonical_wearer(cls,value):
        if value is None:raise ValueError('Omit wearer or supply a canonical UUID.')
        return canonical_uuid(value)


class HomepageRecommendationCreate(LegacyHomepageCreate,WearerRequest):
    pass


class AssistantRecommendationCreate(WearerRequest):
    model_config = ConfigDict(extra="allow")  # Legacy endpoint ignored extra keys.
    request_text: str = Field(strict=True,min_length=1,max_length=500)
    submission_key: str | None = Field(default=None,strict=True,min_length=1,max_length=200,pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
    refinement: Annotated[InitialRefinement | AlternativeRefinement, Field(discriminator='kind')] | None = None
    attribute_conditions: dict | None = None
    preference_profile: Literal['attribute_preference_decision_v2'] | None = None
    compatibility_profile: Literal['recorded_palette_compatibility_v1'] | None = None

    @model_validator(mode='after')
    def explicit_null_is_not_an_action(self):
        if 'compatibility_profile' in self.model_fields_set and self.compatibility_profile is None:
            raise ValueError('Omit compatibility profile or select C2 explicitly.')
        if 'preference_profile' in self.model_fields_set and self.preference_profile is None:
            raise ValueError('Omit preference profile or select P2 explicitly.')
        if 'refinement' in self.model_fields_set and self.refinement is None:
            raise ValueError('Omit refinement or supply a strict action object.')
        if 'attribute_conditions' in self.model_fields_set:
            if self.attribute_conditions is None:raise ValueError('Omit attributes or supply a strict supplement.')
            from app.domain.value_objects.attribute_conditions import AttributeConditions,encode
            self.attribute_conditions=AttributeConditions.from_dict(self.attribute_conditions).to_dict()
            if len(encode(self.model_dump(exclude_unset=True)))>40960:raise ValueError('Attribute request body exceeds40KiB.')
        return self
