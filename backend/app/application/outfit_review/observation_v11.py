"""Additive hosiery/appearance contract. The 1.0 reader and meanings stay intact."""
import json
from typing import Literal
from pydantic import Field, model_validator
from . import contract as old

VERSION = "outfit-review-observation-1.1.0"
Category = Literal["top","shirt","t_shirt","jersey","sweater","jacket","coat","dress","skirt","shorts","trousers","jeans","footwear","socks","unknown"]
Role = Literal["upper","lower","outerwear","one_piece","footwear","hosiery","unknown"]
STYLES = ("casual","sporty","formal","smart_casual","classic","minimal","streetwear","vintage")

class ColourFact(old.Fact):
    values: tuple[Literal['black','white','grey','blue','navy','teal','green','olive','khaki','brown','tan','beige','red','orange','yellow','pink','purple','multicoloured','silver','gold'],...]=Field(max_length=4)

class PatternFact(old.Fact):
    values: tuple[Literal['plain','striped','checked','floral','graphic','patterned'],...]=Field(max_length=4)

class SleeveFact(old.Fact):
    values: tuple[Literal['sleeveless','short','elbow','three_quarter','long'],...]=Field(max_length=4)

class RollFact(old.Fact):
    values: tuple[Literal['rolled','not_rolled'],...]=Field(max_length=4)

class StyleFact(old.Fact):
    values: tuple[Literal['casual','sporty','formal','smart_casual','classic','minimal','streetwear','vintage'],...]=Field(max_length=4)


class Item(old.Item):
    category: Category
    category_alternatives: tuple[Category,...] = Field(max_length=4)
    role: Role
    unit: Literal["single","pair","footwear_pair","unresolved"]
    colours: ColourFact
    pattern: PatternFact
    sleeve_length: SleeveFact
    sleeve_state: RollFact
    style: StyleFact = Field(default_factory=lambda: StyleFact(state="unknown",values=()))

    @model_validator(mode="after")
    def style_values(self):
        if not set(self.style.values)<=set(STYLES):raise ValueError("Unsupported appearance style")
        return self


class Prediction(old.Prediction):
    version: Literal["outfit-review-observation-1.1.0"]
    items: tuple[Item,...] = Field(max_length=24)
    feet_observation: Literal["shoes_visible","socks_only_visible","bare_feet_visible","feet_out_of_frame","uncertain"] = "uncertain"


class Observation(old.Observation):
    version: Literal["outfit-review-observation-1.1.0"] = VERSION
    prediction: Prediction

    @model_validator(mode="after")
    def raw_binding(self):
        if parse_prediction(self.raw_response)!=self.prediction:raise ValueError("Prediction differs from raw source")
        return self


def parse_prediction(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError("Duplicate JSON field")
            result[key]=value
        return result
    value=json.loads(raw,object_pairs_hook=unique)
    if value.get('version')==old.VERSION:return old.parse_prediction(raw)
    return Prediction.model_validate_json(raw)


def parse_observation(raw):
    value=json.loads(raw)
    if value.get('version')=='outfit-review-observation-1.1.1':
        from .output_handling import Observation as NormalizedObservation
        return NormalizedObservation.model_validate_json(raw)
    return (old.Observation if value.get('version')==old.VERSION else Observation).model_validate_json(raw)


def issues(prediction):
    if prediction.version==old.VERSION:return old.issues(prediction)
    out=list(old.issues(prediction))
    for item in prediction.items:
        if item.category=='jersey' and item.role!='upper':out.append(f'{item.id}:category_role_conflict')
        if item.category=='socks':
            if item.role!='hosiery':out.append(f'{item.id}:category_role_conflict')
            if item.unit=='footwear_pair':out.append(f'{item.id}:socks_pair_confirmation_required')
            if item.sleeve_length.state!='unknown' or item.sleeve_state.state!='unknown':out.append(f'{item.id}:sleeve_not_applicable')
        if item.unit=='pair' and item.category not in ('socks','footwear','unknown'):out.append(f'{item.id}:invalid_pair')
    shoes=[i for i in prediction.items if i.category=='footwear']
    socks=[i for i in prediction.items if i.category=='socks']
    if len(socks)>1:out.append('socks_pair_grouping_required')
    state=prediction.feet_observation
    if state=='shoes_visible' and (not shoes or prediction.footwear_visibility not in ('visible','partial')):out.append('feet_observation_conflict')
    if state in ('socks_only_visible','bare_feet_visible','feet_out_of_frame') and (shoes or prediction.footwear_visibility in ('visible','partial')):out.append('feet_observation_conflict')
    if state=='socks_only_visible' and not socks:out.append('visible_socks_missing')
    if state=='bare_feet_visible' and socks:out.append('feet_observation_conflict')
    return tuple(dict.fromkeys(out))


PROMPT_VERSION='outfit-review-grounding-prompt-1.1.0'
from .model import SYSTEM_PROMPT as PREDECESSOR_PROMPT, USER_PROMPT
SYSTEM_PROMPT=PREDECESSOR_PROMPT+"""
This is observation version 1.1.0. Hosiery is represented explicitly:
socks are category socks, role hosiery, and are NOT shoes. A visibly worn pair
of socks uses unit pair. A jersey uses category jersey, role upper. Do not infer
athletic purpose or fabric from its name. footwear_visibility refers to shoes,
not socks. feet_observation describes only what is visible: shoes_visible,
socks_only_visible, bare_feet_visible, feet_out_of_frame, or uncertain.
Record clearly visible colours/patterns/sleeves instead of defaulting every
attribute to Unknown. Use uncertainty whenever the image cannot establish them.
Style is an optional visual appearance judgment, not verified material or fit;
use supported styles or Unknown. Do not guess unseen shoes. Identity uncertainty
is separate from a missing attribute. Keep every genuinely visible garment.
"""
