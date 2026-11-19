"""Versioned, immutable observations. Structural validity is not visual truth.

The model supplies proposals, not verified garment facts. Contradictory proposals
remain available for review; nothing is silently merged, dropped or qualified.
"""
from hashlib import sha256
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

VERSION = "outfit-review-observation-1.0.0"
Short = Annotated[str, Field(min_length=1, max_length=80)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Coordinate = Annotated[int, Field(ge=0, le=1000)]
Category = Literal["top", "shirt", "t_shirt", "sweater", "jacket", "coat", "dress",
                   "skirt", "shorts", "trousers", "jeans", "footwear", "unknown"]
Role = Literal["upper", "lower", "outerwear", "one_piece", "footwear", "unknown"]
Visibility = Literal["visible", "partial", "not_visible", "unknown"]


class Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Box(Frozen):
    """0..1000 coordinates on the EXIF-oriented full image; never VTON fit/crop."""
    xyxy: tuple[Coordinate, Coordinate, Coordinate, Coordinate]

    @model_validator(mode="after")
    def area(self):
        if self.xyxy[0] >= self.xyxy[2] or self.xyxy[1] >= self.xyxy[3]:
            raise ValueError("Region must have positive area")
        return self

    def contains(self, other: "Box") -> bool:
        a, b, c, d = self.xyxy
        x, y, z, w = other.xyxy
        return a <= x and b <= y and c >= z and d >= w


class ImageIdentity(Frozen):
    original_sha256: Digest
    oriented_pixels_sha256: Digest
    width: Annotated[int, Field(ge=128, le=25000)]
    height: Annotated[int, Field(ge=128, le=25000)]
    coordinates: Literal["exif-oriented-full-image-1000-v1"] = "exif-oriented-full-image-1000-v1"

    @model_validator(mode="after")
    def bounded_resolution(self):
        if self.width * self.height > 25_000_000:
            raise ValueError("Image resolution exceeds observation bound")
        return self


class ModelRun(Frozen):
    """Filled by the trusted runner, never invented by the vision model."""
    model: Short
    revision: Short
    weights_sha256: Digest
    projector_sha256: Digest
    runtime: Short
    runtime_build: Short
    runtime_executable_sha256: Digest
    settings_sha256: Digest
    prompt_sha256: Digest
    run_id: Short
    generated_at: Short


class Fact(Frozen):
    state: Literal["observed", "uncertain", "unknown"]
    values: tuple[Short, ...] = Field(max_length=4)

    @model_validator(mode="after")
    def state_values(self):
        if (self.state == "unknown") != (not self.values):
            raise ValueError("Unknown has no values; observed/uncertain must name values")
        if len(set(self.values)) != len(self.values):
            raise ValueError("Repeated attribute values")
        return self


COLOURS = frozenset("black white grey blue navy teal green olive khaki brown tan beige red orange yellow pink purple multicoloured silver gold".split())
PATTERNS = frozenset("plain striped checked floral graphic patterned".split())
SLEEVES = frozenset(("sleeveless", "short", "elbow", "three_quarter", "long"))
ROLL = frozenset(("rolled", "not_rolled"))


class Person(Frozen):
    id: Short
    region: Box


class Item(Frozen):
    id: Short
    person_id: Short
    region: Box
    category: Category
    category_alternatives: tuple[Category, ...] = Field(max_length=4)
    role: Role
    visibility: Visibility
    unit: Literal["single", "footwear_pair", "unresolved"]
    colours: Fact
    pattern: Fact
    sleeve_length: Fact
    sleeve_state: Fact

    @model_validator(mode="after")
    def attributes(self):
        for name, allowed in (("colours", COLOURS), ("pattern", PATTERNS),
                              ("sleeve_length", SLEEVES), ("sleeve_state", ROLL)):
            fact = getattr(self, name)
            if not set(fact.values) <= allowed:
                raise ValueError(f"Unsupported {name}; keep unknown instead of fabricating a label")
            if name != "colours" and fact.state == "observed" and len(fact.values) > 1:
                raise ValueError("One observed value required; alternatives must be uncertain")
        return self


class Layer(Frozen):
    over: Short
    under: Short
    state: Literal["observed", "uncertain"]


class IdentityQuestion(Frozen):
    items: tuple[Short, Short]
    relation: Literal["possibly_same_garment", "possibly_one_footwear_pair"]


class Prediction(Frozen):
    """Small model-facing contract. No composition, brand or inferred body facts."""
    version: Literal["outfit-review-observation-1.0.0"]
    scene: Literal["single_person", "multiple_people", "no_person", "unclear"]
    people: tuple[Person, ...] = Field(max_length=8)
    target_person_id: Short | None
    footwear_visibility: Visibility
    items: tuple[Item, ...] = Field(max_length=24)
    layering: tuple[Layer, ...] = Field(max_length=32)
    identity_questions: tuple[IdentityQuestion, ...] = Field(max_length=24)


class Observation(Frozen):
    version: Literal["outfit-review-observation-1.0.0"] = VERSION
    image: ImageIdentity
    run: ModelRun
    raw_response: Annotated[str, Field(min_length=1, max_length=65536)]
    prediction: Prediction

    @model_validator(mode="after")
    def raw_binding(self):
        # A schema-valid wrapper cannot substitute a different parsed inventory.
        if parse_prediction(self.raw_response) != self.prediction:
            raise ValueError("Prediction does not match retained raw response")
        return self


def digest(value: Frozen) -> str:
    payload = json.dumps(value.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()


ROLE = {"top": "upper", "shirt": "upper", "t_shirt": "upper", "sweater": "upper",
        "jacket": "outerwear", "coat": "outerwear", "dress": "one_piece", "skirt": "lower",
        "shorts": "lower", "trousers": "lower", "jeans": "lower", "footwear": "footwear"}


def issues(p: Prediction) -> tuple[str, ...]:
    """Contract contradictions, not an image classifier or visual accuracy test."""
    out: list[str] = []
    people = {x.id: x for x in p.people}
    items = {x.id: x for x in p.items}
    if len(people) != len(p.people) or len(items) != len(p.items):
        out.append("duplicate_id")
    if p.scene == "no_person":
        if p.people or p.items or p.target_person_id is not None or p.footwear_visibility not in ("not_visible", "unknown"):
            out.append("no_person_inventory_conflict")
    elif p.scene == "unclear" or p.target_person_id not in people:
        out.append("target_selection_required")
    if p.scene == "single_person" and len(p.people) != 1:
        out.append("person_count_conflict")
    if p.scene == "multiple_people" and len(p.people) < 2:
        out.append("person_count_conflict")
    # Multiple people always require an explicit USER-selected target; the
    # model's favourite subject is not an authenticated user selection.
    if p.scene == "multiple_people":
        out.append("user_target_selection_required")
    for item in p.items:
        label = item.id
        if item.person_id != p.target_person_id or item.person_id not in people:
            out.append(f"{label}:wrong_person")
        elif not people[item.person_id].region.contains(item.region):
            out.append(f"{label}:region_outside_person")
        if item.visibility in ("not_visible", "unknown"):
            out.append(f"{label}:not_an_observed_item")
        if item.category_alternatives or item.unit == "unresolved":
            out.append(f"{label}:unresolved_identity")
        if item.category_alternatives and (item.category != "unknown" or len(set(item.category_alternatives)) < 2
                                          or len(set(item.category_alternatives)) != len(item.category_alternatives)
                                          or "unknown" in item.category_alternatives):
            # Retain internally inconsistent model proposals for user review,
            # just like category/role conflicts. Never silently repair them.
            out.append(f"{label}:invalid_category_alternatives")
        if item.category in ROLE and item.role != ROLE[item.category]:
            out.append(f"{label}:category_role_conflict")
        if item.unit == "footwear_pair" and item.category != "footwear":
            out.append(f"{label}:invalid_pair")
        if item.category == "footwear" and p.footwear_visibility not in ("visible", "partial"):
            out.append(f"{label}:footwear_visibility_conflict")
        if item.category in ("footwear", "skirt", "shorts", "trousers", "jeans") and (item.sleeve_length.state != "unknown" or item.sleeve_state.state != "unknown"):
            out.append(f"{label}:sleeve_not_applicable")
    shoes = [i for i in p.items if i.category == "footwear"]
    if len(shoes) > 1:
        out.append("footwear_pair_grouping_required")
    for n, first in enumerate(p.items):
        for second in p.items[n + 1:]:
            if first.region == second.region:
                out.append(f"{first.id},{second.id}:same_region_identity_review")
    if p.identity_questions:
        out.append("identity_review_required")
        for q in p.identity_questions:
            if len(set(q.items)) != 2 or any(i not in items for i in q.items):
                out.append("invalid_identity_reference")
    edges: dict[str, list[str]] = {}
    for layer in p.layering:
        if layer.over not in items or layer.under not in items or layer.over == layer.under:
            out.append("invalid_layer_reference")
        else:
            edges.setdefault(layer.over, []).append(layer.under)
    def cyclic(node: str, trail: frozenset[str]) -> bool:
        return node in trail or any(cyclic(child, trail | {node}) for child in edges.get(node, ()))
    if any(cyclic(node, frozenset()) for node in edges):
        out.append("cyclic_layers")
    return tuple(dict.fromkeys(out))


def parse_prediction(raw: str) -> Prediction:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result
    json.loads(raw, object_pairs_hook=unique)
    return Prediction.model_validate_json(raw)
