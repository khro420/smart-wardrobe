"""Versioned owner intent at ordinary Add/Edit; v1 review remains authoritative."""
from datetime import datetime
import hashlib
import hmac
import json
from types import SimpleNamespace

from fastapi import HTTPException
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.domain.value_objects.contextual_garment_evidence import KEY as REVIEW_KEY, project_contextual_evidence

KEY = 'owner_style_confirmation_v1'
CONTRACT = 'owner-style-confirmation-1.0.0'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def canonical_style(value):
    tags = [value] if isinstance(value, str) else value
    if not isinstance(tags, list) or len(tags) != 1 or not isinstance(tags[0], str):
        return None
    evidence = GarmentEvidenceMapper().classify(SimpleNamespace(
        garment_id='style-confirmation', style_tags=tuple(tags), invalid_attributes=(), primary_colour=None)).style
    return evidence.values[0] if evidence.state == 'Known' and len(evidence.values) == 1 else None


def candidate_revision(item, owner):
    return digest([owner, *[item[k] for k in ('id', 'job_id', 'detected_category', 'attributes_json',
                   'review_status', 'preferred_media_id', 'crop_media_id', 'vtoff_media_id')]])


def garment_revision(row):
    return digest([row[k] for k in ('id', 'user_id', 'category', 'style_tags', 'attributes_json',
                                   'additional_attributes', 'preferred_media_id', 'status', 'updated_at')])


def validate_action(action, revision, attrs, category):
    from app.domain.value_objects.requests import OwnerStyleConfirmation
    action = OwnerStyleConfirmation.model_validate(action)
    if not hmac.compare_digest(action.expected_revision, revision):
        raise HTTPException(409, 'Garment details changed. Reload before confirming the style.')
    style = canonical_style(attrs.get('style'))
    if category not in GARMENT_STRUCTURE or style is None or action.style != style:
        raise HTTPException(422, 'Confirm one supported style matching the saved value and category.')
    return style


def event(owner, entity, job, category, media, style, timestamp, source):
    return {'contract': CONTRACT, 'event': source, 'owner_id': owner, 'entity_id': entity,
            'job_id': job, 'category': category, 'media_id': media, 'style': style, 'confirmed_at': timestamp}


def pending_current(raw, item, owner, attrs=None, media=None):
    attrs = json.loads(item['attributes_json']) if attrs is None else attrs
    category = attrs.get('reviewed_category') or item['detected_category']
    style = canonical_style(attrs.get('style'))
    if not isinstance(raw, dict) or style is None or category not in GARMENT_STRUCTURE:
        return False
    try:
        timestamp = raw['confirmed_at']
        if not isinstance(timestamp, str) or datetime.fromisoformat(timestamp.replace('Z', '+00:00')).tzinfo is None:
            return False
        return raw == event(owner, item['id'], item['job_id'], category,
                            media or item['preferred_media_id'], style, timestamp, 'candidate_accept')
    except (KeyError, ValueError, TypeError):
        return False


def candidate_view(item, owner):
    attrs = json.loads(item['attributes_json'])
    return {'revision': candidate_revision(item, owner),
            'current': item['review_status'] == 'accepted' and pending_current(attrs.get(KEY), item, owner)}


def admit(attrs, confirmation):
    """Do not repair malformed declarations or create a second style authority."""
    raw = attrs.get(REVIEW_KEY)
    evidence = project_contextual_evidence(raw, REVIEW_KEY in attrs)
    if evidence.state == 'Malformed' or evidence.review_state == 'Malformed':
        raise HTTPException(422, 'Stored contextual evidence needs explicit repair before style confirmation.')
    raw = raw or {'schema_version': '1.0.0', 'style_review': None, 'occasion_overrides': {}}
    review = {'source': 'owner_review', 'styles': [confirmation['style']],
              'category': confirmation['category'], 'reviewed_at': confirmation['confirmed_at']}
    attrs[REVIEW_KEY] = {**raw, 'style_review': review}
    attrs[KEY] = {**confirmation, 'review_sha256': digest(review)}


def transfer(item, owner, attrs):
    pending = attrs.pop(KEY, None)
    if pending is None:
        return
    if not pending_current(pending, item, owner, attrs):
        raise HTTPException(409, 'Candidate style confirmation is stale. Review the candidate again.')
    admit(attrs, pending)


def require_consistent_mirror(row):
    try:
        attrs, mirror = json.loads(row['attributes_json']), json.loads(row['additional_attributes'])
        if not isinstance(attrs, dict) or not isinstance(mirror, dict):
            raise ValueError()
        for key in (REVIEW_KEY, KEY, 'style'):
            if (key in attrs) != (key in mirror) or attrs.get(key) != mirror.get(key):
                raise ValueError()
    except (ValueError, TypeError):
        raise HTTPException(422, 'Stored attribute evidence is inconsistent. Repair it before confirming the style.') from None


def garment_view(row, review_current):
    attrs = json.loads(row['attributes_json'])
    audit, raw = attrs.get(KEY), attrs.get(REVIEW_KEY)
    source = None
    if review_current and isinstance(audit, dict) and isinstance(raw, dict):
        if (audit.get('contract') == CONTRACT and audit.get('owner_id') == row['user_id']
                and audit.get('category') == row['category'] and audit.get('media_id') == row['preferred_media_id']
                and audit.get('event') in ('candidate_accept', 'garment_edit')
                and audit.get('review_sha256') == digest(raw.get('style_review'))):
            source = audit['event']
    return {'revision': garment_revision(row), 'current': review_current, 'source': source}
