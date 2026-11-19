"""Version dispatch reusing the original confirmation invariants and reader."""
import json
from typing import Literal
from pydantic import Field,model_validator
from . import confirmation as old
from . import observation_v11 as visual
from .output_handling import Observation as NormalizedObservation
from .contract import digest,Short

Authority=old.Authority
Correction=old.Correction
current=old.current


class Revision(old.Revision):
    prediction: visual.Prediction
    selected_target: Short|None=None


class Review(old.Review):
    version: Literal['outfit-review-confirmation-1.1.0']='outfit-review-confirmation-1.1.0'
    original: NormalizedObservation|visual.Observation
    revisions: tuple[Revision,...]=Field(default=(),max_length=16)


def changes(before,after):
    if before.version!=after.version:raise ValueError('Do not reinterpret a historical observation in place')
    result=set()
    ids={i.id for i in before.items}|{i.id for i in after.items}
    for id in ids:
        a=tuple(i for i in before.items if i.id==id);b=tuple(i for i in after.items if i.id==id)
        if a!=b:result.add(('replace_item' if a and b else 'remove_item' if a else 'add_item',id))
    result|={x for x in old._changes(before,after) if x[0] in ('select_target','review_relations')}
    if before.feet_observation!=after.feet_observation:result.add(('review_relations','scene'))
    return result


def begin(observation,authority):
    if observation.version==visual.old.VERSION:return old.begin(observation,authority)
    if observation.image.original_sha256!=authority.image_sha256:raise ValueError('Wrong image authority')
    return Review(owner_id=authority.image_owner_id,original=observation)


def _expected(before,after,selected):
    result=changes(before,after)
    if selected is not None:
        if selected!=after.target_person_id or selected not in {p.id for p in after.people}:raise ValueError('Invalid explicit target selection')
        result.add(('select_target','scene'))
    return result


def verify(review):
    if isinstance(review,old.Review) and not isinstance(review,Review):return old.verify(review)
    prefix=Review(owner_id=review.owner_id,original=review.original)
    for revision in review.revisions:
        if (revision.actor_id!=review.owner_id or revision.original_observation_sha256!=digest(review.original)
                or revision.previous_revision_sha256!=digest(prefix)):raise ValueError('Broken correction provenance')
        actual={(c.operation,c.subject) for c in revision.changes}
        if not actual or len(actual)!=len(revision.changes) or actual!=_expected(current(prefix),revision.prediction,revision.selected_target):raise ValueError('Unrecorded correction')
        prefix=Review(owner_id=review.owner_id,original=review.original,revisions=prefix.revisions+(revision,))


def revise(review,authority,expected_digest,prediction,corrections,selected_target=None):
    if not isinstance(review,Review):
        if selected_target is not None:raise ValueError('Explicit target assertion requires observation 1.1')
        return old.revise(review,authority,expected_digest,prediction,corrections)
    old._owner(review,authority);verify(review)
    if digest(review)!=expected_digest:raise ValueError('Stale review')
    actual={(c.operation,c.subject) for c in corrections}
    if not actual or len(actual)!=len(corrections) or actual!=_expected(current(review),prediction,selected_target):raise ValueError('Every correction must be recorded')
    revision=Revision(original_observation_sha256=digest(review.original),previous_revision_sha256=digest(review),actor_id=authority.authenticated_user_id,
                      changes=corrections,prediction=prediction,selected_target=selected_target)
    return Review(owner_id=review.owner_id,original=review.original,revisions=review.revisions+(revision,))


def confirmation_issues(review):
    if not isinstance(review,Review):return old.confirmation_issues(review)
    p=current(review);problems=list(visual.issues(p))
    if any(r.selected_target==p.target_person_id for r in review.revisions):problems=[x for x in problems if x!='user_target_selection_required']
    if p.scene in ('unclear','no_person') or not p.items:problems.append('no_reviewable_outfit')
    return problems


class Confirmation(old.Confirmation):
    version: Literal['outfit-review-confirmation-1.1.0']='outfit-review-confirmation-1.1.0'
    review: Review

    @model_validator(mode='after')
    def checked(self):
        verify(self.review)
        if self.review_sha256!=digest(self.review) or self.confirmed_by!=self.review.owner_id or confirmation_issues(self.review):raise ValueError('Invalid confirmation')
        return self


def confirm(review,authority,expected_digest,*,inventory_reviewed):
    if not isinstance(review,Review):return old.confirm(review,authority,expected_digest,inventory_reviewed=inventory_reviewed)
    old._owner(review,authority);verify(review)
    if inventory_reviewed is not True or expected_digest!=digest(review):raise ValueError('Explicit current inventory review required')
    if confirmation_issues(review):raise ValueError('Resolve the inventory before confirming')
    return Confirmation(review=review,review_sha256=digest(review),confirmed_by=authority.authenticated_user_id)


def parse_confirmation(raw):
    return (Confirmation if json.loads(raw).get('version')=='outfit-review-confirmation-1.1.0' else old.Confirmation).model_validate_json(raw)


def provenance(review):
    if not isinstance(review,Review):return old.provenance(review)
    verify(review);fields=tuple(visual.Item.model_fields)
    result={f'{i.id}.{field}':'ai_prediction_user_reviewed' for i in review.original.prediction.items for field in fields}
    before=review.original.prediction
    for revision in review.revisions:
        after=revision.prediction
        retained={i.id for i in after.items}
        result={k:v for k,v in result.items() if k.rsplit('.',1)[0] in retained}
        for item in after.items:
            originals=[i for i in before.items if i.id==item.id]
            scope_changed=len(originals)!=1 or any(getattr(originals[0],key)!=getattr(item,key) for key in ('region','unit','person_id'))
            for field in fields:
                if scope_changed:result[f'{item.id}.{field}']='user_scope_review_not_model_verified'
                elif getattr(originals[0],field)!=getattr(item,field):result[f'{item.id}.{field}']='user_correction_not_model_verified'
        before=after
    return result
