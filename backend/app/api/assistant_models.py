from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal, Annotated
from app.domain.value_objects.recommendation_refinement import RefinementAction


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


class AssistantRecommendationCreate(BaseModel):
    model_config = ConfigDict(extra="allow")  # Legacy endpoint ignored extra keys.
    request_text: str = Field(strict=True,min_length=1,max_length=500)
    submission_key: str | None = Field(default=None,strict=True,min_length=1,max_length=200,pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
    refinement: Annotated[InitialRefinement | AlternativeRefinement, Field(discriminator='kind')] | None = None

    @model_validator(mode='after')
    def explicit_null_is_not_an_action(self):
        if 'refinement' in self.model_fields_set and self.refinement is None:
            raise ValueError('Omit refinement or supply a strict action object.')
        return self
