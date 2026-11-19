"""Read-only adapter to existing CPU semantic NLP; no recommender activation."""
from .contract import Frozen, Short
import json
from pydantic import Field
from typing import Annotated, Literal


class OccasionUnavailable(ValueError):
    pass


class Occasion(Frozen):
    version: Literal["outfit-review-occasion-1.0.0"] = "outfit-review-occasion-1.0.0"
    original_text: Annotated[str, Field(min_length=1, max_length=1600)]
    context: Short
    role: Short
    dress_code: Short | None
    formality: Short | None
    grammar: Short
    interpretation_sha256: str
    requirements: tuple[Annotated[str, Field(min_length=1, max_length=1600)], ...] = Field(max_length=24)
    inferred_dress_code: Literal[False] = False


def interpret(raw: str) -> Occasion:
    from app.development.mixed_wardrobe import semantic_appearance as existing
    from app.domain.value_objects.attribute_conditions import AttributeRequestError
    from app.development.mixed_wardrobe.semantic_model import ModelUnavailable
    if not isinstance(raw, str) or not raw.strip() or len(raw) > 1600:
        raise ValueError("Describe one supported occasion in at most 1600 characters.")
    try:
        document = existing.document(raw, existing.propose(raw))
    except ModelUnavailable:
        raise OccasionUnavailable("The local semantic NLP assets are unavailable. Complete existing semantic model setup first.") from None
    except AttributeRequestError:
        raise ValueError("The occasion or requirements could not be interpreted safely. Clarify the activity, participant role and any dress code.") from None
    # Crucially use ORIGINAL request, never interview evaluation_request/default.
    request = document["request"]
    if document["semantic_metadata"]["primary"] == "none":
        raise ValueError("State a supported occasion or activity, not only a clothing request.")
    context = request.get("context") or {}
    dress = context.get("dress_code", {})
    dress_code = dress.get("values", [None])[0] if dress.get("state") == "Known" else None
    requirements = []
    hard = document.get("hard_intent") or {}
    for group in (hard.get("conditions") or {}).get("groups", []):
        # Preserve whole groups, including quantifiers, OR and scoped negation;
        # the visual feedback adapter does not flatten them into new semantics.
        requirements.append("Required group: " + json.dumps(group, sort_keys=True, separators=(",", ":")))
    if request.get("garment_categories"):
        requirements.append("Required categories: " + json.dumps(request["garment_categories"], sort_keys=True))
    if document.get("optional"):
        requirements.append("Optional wish (not mandatory): " + json.dumps(document["optional"], sort_keys=True, separators=(",", ":")))
    return Occasion(original_text=raw, context=document["semantic_metadata"]["primary"],
                    role=document["semantic_metadata"]["role"], dress_code=dress_code,
                    formality=request.get("formality"), grammar=document["grammar_version"],
                    interpretation_sha256=document["revision"], requirements=tuple(requirements))
