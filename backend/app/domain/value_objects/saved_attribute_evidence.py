"""Immutable origin of a saved label; never an owner-review or confidence claim."""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re

KEY = 'saved_attribute_sources_v1'
VERSION = 'saved-attribute-sources-1.0.0'
CONTRACT = 'saved_singleton_style_provisional_v1'
ORIGINS = ('unknown', 'owner_supplied', 'adapter_output', 'model_reported', 'synthetic')


def style_digest(value):
    if isinstance(value, str):
        value = [value]
    if isinstance(value, (list, tuple)) and all(isinstance(v, str) for v in value):
        value = sorted(set(re.sub(r'\s+', ' ', v.strip().casefold()) for v in value))
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class SavedAttributeEvidence:
    state: str = 'Absent'
    origin: str = 'unknown'
    contributor: str | None = None
    recorded_at: str | None = None
    value_sha256: str | None = None
    category: str | None = None
    media_id: str | None = None
    owner_id: str | None = None

    def __post_init__(self):
        if self.state not in ('Absent', 'Known', 'Malformed', 'Stale') or self.origin not in ORIGINS:
            raise ValueError('Invalid saved attribute evidence.')
        for key in ('contributor', 'recorded_at', 'value_sha256', 'category', 'media_id', 'owner_id'):
            value = getattr(self, key)
            if value is not None and (not isinstance(value, str) or len(value) > 200):
                raise ValueError('Invalid saved attribute source field.')

    def current(self, garment):
        return (self.state == 'Known' and self.owner_id == garment.user_id
                and self.category == garment.category and self.media_id == garment.preferred_media_id
                and self.value_sha256 == style_digest(garment.style_tags))


def source_record(attrs, owner, category, media, timestamp, origin, contributor):
    if origin not in ORIGINS:
        raise ValueError('Unapproved saved origin.')
    return {'version': VERSION, 'style': {'origin': origin, 'contributor': contributor,
            'recorded_at': timestamp, 'value_sha256': style_digest(attrs.get('style')),
            'category': category, 'media_id': media, 'owner_id': owner}}


def project_saved_attribute_evidence(raw, present, style, category, media, owner):
    if not present:
        return SavedAttributeEvidence()
    try:
        if not isinstance(raw, dict) or set(raw) != {'version', 'style'} or raw['version'] != VERSION:
            raise ValueError()
        entry = raw['style']
        if not isinstance(entry, dict) or set(entry) != {'origin', 'contributor', 'recorded_at', 'value_sha256', 'category', 'media_id', 'owner_id'}:
            raise ValueError()
        if (any(not isinstance(entry[k], str) or not entry[k] or len(entry[k]) > 200 for k in entry)
                or not re.fullmatch('[0-9a-f]{64}', entry['value_sha256'])
                or datetime.fromisoformat(entry['recorded_at'].replace('Z', '+00:00')).tzinfo is None):
            raise ValueError()
        result = SavedAttributeEvidence('Known', **entry)
        current = (entry['owner_id'] == owner and entry['category'] == category
                   and entry['media_id'] == media and entry['value_sha256'] == style_digest(style))
        return result if current else SavedAttributeEvidence('Stale', **entry)
    except (ValueError, TypeError, KeyError, AttributeError):
        return SavedAttributeEvidence('Malformed')
