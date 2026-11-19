"""Pure in-memory confirmation, no routes, database writes or wardrobe evidence.

Caller must supply server-authenticated ownership. A future endpoint must NOT
accept Authority from request JSON. This foundation exposes no HTTP endpoint.
"""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from .contract import Frozen, Short, Digest, Observation, Prediction, digest, issues


class Authority(Frozen):
    authenticated_user_id: Short
    image_owner_id: Short
    image_sha256: Digest

    @model_validator(mode="after")
    def owner(self):
        if self.authenticated_user_id != self.image_owner_id:
            raise ValueError("Image access denied")
        return self


class Correction(Frozen):
    operation: Literal["replace_item", "remove_item", "add_item", "review_relations", "select_target"]
    subject: Short
    reason: Annotated[str, Field(min_length=1, max_length=240)]


class Revision(Frozen):
    original_observation_sha256: Digest
    previous_revision_sha256: Digest
    actor_id: Short
    changes: tuple[Correction, ...] = Field(min_length=1, max_length=48)
    prediction: Prediction


class Review(Frozen):
    version: Literal["outfit-review-confirmation-1.0.0"] = "outfit-review-confirmation-1.0.0"
    owner_id: Short
    original: Observation
    revisions: tuple[Revision, ...] = Field(default=(), max_length=16)


def current(review: Review) -> Prediction:
    return review.revisions[-1].prediction if review.revisions else review.original.prediction


def _changes(before: Prediction, after: Prediction) -> set[tuple[str, str]]:
    a, b = {i.id: i for i in before.items}, {i.id: i for i in after.items}
    changes = {("remove_item", i) for i in a.keys() - b.keys()}
    changes |= {("add_item", i) for i in b.keys() - a.keys()}
    changes |= {("replace_item", i) for i in a.keys() & b.keys() if a[i] != b[i]}
    if (before.scene, before.people, before.target_person_id) != (after.scene, after.people, after.target_person_id):
        changes.add(("select_target", "scene"))
    if (before.layering, before.identity_questions, before.footwear_visibility) != (after.layering, after.identity_questions, after.footwear_visibility):
        changes.add(("review_relations", "scene"))
    return changes


def begin(observation: Observation, authority: Authority) -> Review:
    if observation.image.original_sha256 != authority.image_sha256:
        raise ValueError("Wrong image authority")
    return Review(owner_id=authority.image_owner_id, original=observation)


def _owner(review: Review, authority: Authority):
    if review.owner_id != authority.authenticated_user_id or review.original.image.original_sha256 != authority.image_sha256:
        raise ValueError("Review access denied")


def revise(review: Review, authority: Authority, expected_digest: str,
           prediction: Prediction, changes: tuple[Correction, ...]) -> Review:
    _owner(review, authority)
    verify(review)
    if digest(review) != expected_digest:
        raise ValueError("Stale review; reload before correcting")
    expected = _changes(current(review), prediction)
    actual = {(c.operation, c.subject) for c in changes}
    if not expected or expected != actual or len(actual) != len(changes):
        raise ValueError("Every actual change requires exactly one explicit user correction")
    revision = Revision(original_observation_sha256=digest(review.original), previous_revision_sha256=digest(review),
                        actor_id=authority.authenticated_user_id, changes=changes, prediction=prediction)
    return Review(owner_id=review.owner_id, original=review.original, revisions=review.revisions + (revision,))


def verify(review: Review) -> None:
    """Validate immutable links and exact correction coverage on deserialisation.

    Digests bind content, not authentication/signatures. Future persistence needs
    trusted server storage; an untrusted client cannot supply a verified Review.
    """
    prefix = Review(owner_id=review.owner_id, original=review.original)
    for revision in review.revisions:
        if (revision.actor_id != review.owner_id or revision.original_observation_sha256 != digest(review.original)
                or revision.previous_revision_sha256 != digest(prefix)):
            raise ValueError("Broken correction provenance")
        actual = {(c.operation, c.subject) for c in revision.changes}
        if actual != _changes(current(prefix), revision.prediction) or len(actual) != len(revision.changes) or not actual:
            raise ValueError("Unrecorded correction")
        prefix = Review(owner_id=review.owner_id, original=review.original, revisions=prefix.revisions + (revision,))


class Confirmation(Frozen):
    version: Literal["outfit-review-confirmation-1.0.0"] = "outfit-review-confirmation-1.0.0"
    review: Review
    review_sha256: Digest
    confirmed_by: Short
    basis: Literal["user_reviewed_visual_inventory_not_model_accuracy"] = "user_reviewed_visual_inventory_not_model_accuracy"

    @model_validator(mode="after")
    def checked(self):
        verify(self.review)
        if self.review_sha256 != digest(self.review) or self.confirmed_by != self.review.owner_id or confirmation_issues(self.review):
            raise ValueError("Invalid confirmation record")
        return self


def confirmation_issues(review: Review) -> list[str]:
    p = current(review)
    problems = list(issues(p))
    if any(c.operation == "select_target" for r in review.revisions for c in r.changes):
        problems = [i for i in problems if i != "user_target_selection_required"]
    if p.scene in ("unclear", "no_person") or not p.items:
        problems.append("no_reviewable_outfit")
    return problems


def confirm(review: Review, authority: Authority, expected_digest: str, *, inventory_reviewed: bool) -> Confirmation:
    _owner(review, authority)
    verify(review)
    if inventory_reviewed is not True or expected_digest != digest(review):
        raise ValueError("Explicit current-image inventory confirmation required")
    # Multi-person photos can be reviewed only after an explicit user target
    # selection; every retained item still has to belong to that target.
    problems = confirmation_issues(review)
    if problems:
        raise ValueError("Resolve observations before confirmation: " + ", ".join(problems))
    return Confirmation(review=review, review_sha256=digest(review), confirmed_by=authority.authenticated_user_id)


def provenance(review: Review) -> dict[str, str]:
    """Per item FIELD attribution; confirming unchanged AI labels is not accuracy."""
    verify(review)
    from .contract import Item
    fields = tuple(Item.model_fields)
    result = {f"{i.id}.{field}": "ai_prediction_user_reviewed" for i in review.original.prediction.items for field in fields}
    previous = review.original.prediction
    for r in review.revisions:
        a, b = {i.id: i for i in previous.items}, {i.id: i for i in r.prediction.items}
        for key in a.keys() - b.keys():
            result = {path: source for path, source in result.items() if not path.startswith(key + ".")}
        for key, item in b.items():
            for field in fields:
                if key not in a or getattr(a[key], field) != getattr(item, field):
                    result[f"{key}.{field}"] = "user_correction_not_model_verified"
        previous = r.prediction
    return result
