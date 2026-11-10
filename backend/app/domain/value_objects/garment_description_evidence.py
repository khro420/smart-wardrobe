"""New bounded immutable description channel; old ranking snapshots are unchanged."""
from dataclasses import dataclass
import hashlib
import json
import re
from fractions import Fraction
from datetime import datetime
from uuid import UUID
import unicodedata

KEY = 'garment_description_evidence_v1'
CONTRACT = 'garment-description-evidence-1.0.0'
UPDATE_CONTRACT = 'garment-description-update-1.0.0'
LIMIT = 32768
FIELDS = ('garment_name', 'category', 'primary_colour', 'secondary_colour',
          'colour_palette', 'style', 'pattern', 'material', 'silhouette',
          'neckline', 'sleeve_length', 'colour_temperature', 'colour_dominance',
          'descriptive_tags')
STATES = frozenset(('Known', 'KnownEmpty', 'Absent', 'Unspecified', 'Unsure',
                    'Unrecognized', 'Malformed', 'Conflicting', 'Stale', 'Inapplicable'))
ORIGINS = frozenset(('owner_selected', 'owner_reported_label', 'model_suggestion',
                     'measured_image', 'legacy_selected_unverified', 'derived_category'))
RESOURCE_HASHES = {
    'garment_description_vocabulary.v1.json': 'd97fedeb9417260443318a583e7fdb875e4d4386ae8611b3ee38877a44aef815',
    'model_vocabulary_registry.v1.json': '0036a2feaae9de18803d1da980136e53b3b487601d72ed25d0cb4acc6619e883',
    'description_evidence_policy.v1.json': '4c96997255aa22a1e0d82e7e77e721224a4390da0518c411fe70e2ccffbc1385',
}
FIELD_KEYS = frozenset(('state', 'canonical_values', 'possible_values', 'completeness',
                        'applicability', 'selected', 'suggestion', 'source_refs',
                        'binding', 'uncertainty_reasons'))
CHANNEL_KEYS = frozenset(('origin', 'value', 'source_digest', 'source_location',
                          'event_id', 'recorded_at', 'source_revision'))
BINDING_KEYS = frozenset(('category', 'media_id', 'field_revision', 'dependency_revisions'))
HEX = re.compile(r'^[0-9a-f]{64}$')
LOCATIONS = frozenset(['/recorded/' + f for f in FIELDS] +
                      [prefix + f + '/value' for prefix in ('/description_raw_suggestions_v1/visible_attributes/', '/fashionpedia_visible_attributes/')
                       for f in ('silhouette', 'neckline', 'sleeve_length', 'pattern')] +
                      ['/description_raw_suggestions_v1/flattened_silhouette'])


CANONICAL_ENUMS = {'category': ('short_sleeve_top', 'long_sleeve_top', 'short_sleeve_outwear', 'long_sleeve_outwear', 'vest', 'sling', 'shorts', 'trousers', 'skirt', 'short_sleeve_dress', 'long_sleeve_dress', 'vest_dress', 'sling_dress'), 'pattern': ('plain', 'abstract', 'cartoon', 'letters, numbers', 'camouflage', 'check', 'dot', 'fair isle', 'floral', 'geometric', 'paisley', 'stripe', 'houndstooth', 'herringbone', 'chevron', 'argyle', 'leopard', 'snakeskin', 'cheetah', 'peacock', 'zebra', 'giraffe', 'toile de jouy', 'plant'), 'style': ('casual', 'classic', 'formal', 'minimal', 'smart casual', 'sporty', 'streetwear', 'vintage', 'bohemian'), 'material': ('cotton', 'denim', 'leather', 'linen', 'silk', 'synthetic', 'wool'), 'silhouette': ('asymmetrical', 'symmetrical', 'peplum', 'circle', 'flare', 'fit and flare', 'trumpet', 'mermaid', 'balloon', 'bell', 'bell bottom', 'bootcut', 'peg', 'pencil', 'straight', 'a-line', 'tent', 'baggy', 'wide leg', 'high low', 'curved', 'tight', 'regular', 'loose', 'oversized'), 'neckline': ('collarless', 'asymmetric', 'crew', 'round', 'v-neck', 'surplice', 'oval', 'u-neck', 'sweetheart', 'queen anne', 'boat', 'scoop', 'square', 'plunging', 'keyhole', 'halter', 'crossover', 'choker', 'high', 'turtle', 'cowl', 'straight across', 'illusion', 'off-the-shoulder', 'one shoulder'), 'sleeve_length': ('sleeveless', 'short', 'elbow-length', 'wrist-length'), 'colour_temperature': ('warm', 'cool', 'neutral'), 'primary_colour': ('black', 'white', 'grey', 'navy', 'blue', 'red', 'green', 'yellow', 'orange', 'pink', 'purple', 'brown', 'beige', 'cream'), 'secondary_colour': ('black', 'white', 'grey', 'navy', 'blue', 'red', 'green', 'yellow', 'orange', 'pink', 'purple', 'brown', 'beige', 'cream')}
REASONS = frozenset(('missing', 'null', 'blank', 'unobserved_palette_mass', 'material_unsure',
 'unsupported_value', 'reserved_description_tag', 'invalid_or_oversize_source', 'bottom_field_inapplicable',
 'category_sleeve_conflict', 'unregistered_model_vocabulary', 'competing_legacy_field_tags', 'invalid_model_source',
 'invalid_stored_description', 'description_projection_over_budget', 'category_or_media_changed',
 'recorded_value_changed', 'primary_colour_changed', 'too_many_uncertainty_reasons', 'unknown_role'))


def validate_values(field, values):
    if field == 'colour_palette':
        if len(values) > 5: raise ValueError('Too many palette entries.')
        colours, total = set(), Fraction(0)
        for value in values:
            exact_keys(value, ('hex', 'coverage'))
            colour = value['hex']
            if not isinstance(colour, str) or re.fullmatch(r'#[0-9a-f]{6}', colour) is None or colour in colours:
                raise ValueError('Invalid canonical palette colour.')
            colours.add(colour)
            coverage = value['coverage']
            if coverage is not None:
                if not isinstance(coverage, str) or re.fullmatch(r'(?:0(?:\.[0-9]{1,6})?|1(?:\.0{1,6})?)', coverage) is None:
                    raise ValueError('Invalid canonical coverage.')
                total += Fraction(coverage)
        if total > 1: raise ValueError('Canonical palette exceeds one.')
        return
    if field not in ('style', 'material', 'descriptive_tags') and len(values) > 1:
        raise ValueError('Scalar description has multiple canonical values.')
    if field == 'colour_dominance':
        if any(type(v) is not bool for v in values): raise ValueError('Invalid canonical boolean.')
        return
    if any(not isinstance(v, str) or not v.strip() or len(v)>100 for v in values) or len(set(values)) != len(values):
        raise ValueError('Invalid canonical description values.')
    if field == 'garment_name':
        if any(unicodedata.normalize('NFC',v)!=v for v in values): raise ValueError('Noncanonical name.')
    elif field == 'descriptive_tags':
        if any(v.casefold().startswith(('rec:', 'owner_style_', 'saved_attribute_', 'garment_description_', 'contextual_suitability_', 'appearance_evidence_', 'automatic_')) for v in values):
            raise ValueError('Reserved declaration in descriptive values.')
    elif field in ('primary_colour','secondary_colour'):
        if any(v not in CANONICAL_ENUMS[field] and re.fullmatch(r'#[0-9a-f]{6}',v) is None for v in values): raise ValueError('Unsupported canonical colour.')
    elif any(v not in CANONICAL_ENUMS.get(field,()) for v in values):
        raise ValueError('Unsupported canonical description value.')


def encode(value):
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                          separators=(',', ':')).encode('utf-8')
    except RecursionError as exc:
        raise ValueError('Description nesting exceeds the encoding boundary.') from exc


def decode(value):
    try:
        return json.loads(value)
    except RecursionError as exc:
        raise ValueError('Description nesting exceeds the decoding boundary.') from exc


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def exact_keys(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError('Invalid description fields.')


def _text(value, maximum=100, nullable=False):
    if nullable and value is None:
        return
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError('Invalid description text.')


def _hash(value):
    if not isinstance(value, str) or HEX.fullmatch(value) is None:
        raise ValueError('Invalid description digest.')


def seal_field(record):
    """Integrity aid; this is not authentication or proof of attribute accuracy."""
    record['binding']['field_revision'] = ''
    record['binding']['field_revision'] = digest(record)
    return record


def validate_field(record):
    exact_keys(record, FIELD_KEYS)
    if record['state'] not in STATES or record['applicability'] not in ('applicable', 'inapplicable', 'unknown'):
        raise ValueError('Unknown description state/applicability.')
    if record['completeness'] not in ('complete_recorded_set', 'partial', 'unknown'):
        raise ValueError('Unknown description completeness.')
    for name, count in (('canonical_values', 20), ('possible_values', 20),
                        ('uncertainty_reasons', 8), ('source_refs', 4)):
        if type(record[name]) is not list or len(record[name]) > count:
            raise ValueError('Description collection exceeds limit.')
    for reason in record['uncertainty_reasons']:
        _text(reason, 100)
        if reason not in REASONS: raise ValueError('Unknown description reason.')
    for ref in record['source_refs']:
        exact_keys(ref, ('location', 'digest'))
        _text(ref['location'], 100)
        if ref['location'] not in LOCATIONS:
            raise ValueError('Unknown description source location.')
        _hash(ref['digest'])
    exact_keys(record['binding'], BINDING_KEYS)
    binding = record['binding']
    _text(binding['category'], 50, True)
    _text(binding['media_id'], 100, True)
    if type(binding['dependency_revisions']) is not dict or len(binding['dependency_revisions']) > 6:
        raise ValueError('Invalid description dependencies.')
    for name, value in binding['dependency_revisions'].items():
        if name not in FIELDS and name not in ('category', 'media_id'):
            raise ValueError('Unknown description dependency.')
        _hash(value)
    for name in ('selected', 'suggestion'):
        channel = record[name]
        if channel is None:
            continue
        exact_keys(channel, CHANNEL_KEYS)
        if channel['origin'] not in ORIGINS:
            raise ValueError('Unknown description origin.')
        if name == 'selected' and channel['origin'] == 'model_suggestion':
            raise ValueError('A model suggestion is not selected evidence.')
        if name == 'suggestion' and channel['origin'] != 'model_suggestion':
            raise ValueError('Invalid suggestion origin.')
        channel_value = channel['value']
        if channel_value is not None:
            if type(channel_value) is not list or len(channel_value) > 20:
                raise ValueError('Invalid description channel collection.')
            for item in channel_value:
                if type(item) is dict:
                    validate_values('colour_palette', [item])
                elif type(item) is not bool and (not isinstance(item, str) or len(item) > 100):
                    raise ValueError('Invalid description channel value.')
        _hash(channel['source_digest'])
        _text(channel['source_location'], 100)
        if channel['source_location'] not in LOCATIONS:
            raise ValueError('Unknown description source location.')
        for key in ('event_id', 'recorded_at', 'source_revision'):
            _text(channel[key], 100, True)
        event_fields = [channel[k] is not None for k in ('event_id', 'recorded_at', 'source_revision')]
        if any(event_fields) and not all(event_fields): raise ValueError('Incomplete owner event.')
        if all(event_fields):
            if str(UUID(channel['event_id'])) != channel['event_id']: raise ValueError('Noncanonical owner event ID.')
            if datetime.fromisoformat(channel['recorded_at']).utcoffset() is None: raise ValueError('Owner event needs timezone.')
            _hash(channel['source_revision'])
            if channel['origin'] not in ('owner_selected','owner_reported_label'): raise ValueError('Nonowner source cannot attest an owner event.')
    _hash(binding['field_revision'])
    copy = json.loads(encode(record))
    copy['binding']['field_revision'] = ''
    if digest(copy) != binding['field_revision']:
        raise ValueError('Description integrity mismatch.')


@dataclass(frozen=True)
class DescriptionField:
    payload: bytes

    def __post_init__(self):
        if type(self.payload) is not bytes or len(self.payload) > LIMIT:
            raise ValueError('Description field exceeds encoding limit.')
        validate_field(decode(self.payload))

    @classmethod
    def from_dict(cls, value):
        return cls(encode(value))

    def to_dict(self):
        return json.loads(self.payload)


@dataclass(frozen=True)
class GarmentDescriptionEvidence:
    payload: bytes

    def __post_init__(self):
        if type(self.payload) is not bytes or len(self.payload) > LIMIT:
            raise ValueError('Description exceeds encoding limit.')
        value = decode(self.payload)
        exact_keys(value, ('contract', 'normalizer_version', 'vocabulary_hash',
                           'registry_hash', 'subject', 'revision', 'fields'))
        if value['contract'] != CONTRACT or value['normalizer_version'] != 'description-normalizer-1.0.0':
            raise ValueError('Unsupported description version.')
        if value['vocabulary_hash'] != RESOURCE_HASHES['garment_description_vocabulary.v1.json'] or value['registry_hash'] != RESOURCE_HASHES['model_vocabulary_registry.v1.json']:
            raise ValueError('Unregistered description resource.')
        exact_keys(value['subject'], ('account_id', 'source_processing_item_id', 'garment_id'))
        _text(value['subject']['account_id'])
        _text(value['subject']['source_processing_item_id'], nullable=True)
        _text(value['subject']['garment_id'], nullable=True)
        _hash(value['revision'])
        exact_keys(value['fields'], FIELDS)
        for field, record in value['fields'].items():
            validate_field(record)
            validate_values(field, record['canonical_values'])
            validate_values(field, record['possible_values'])
            selected = record['selected']
            if selected is not None and selected['value'] is not None:
                if field == 'colour_palette':
                    validate_values(field, selected['value'])
                elif field == 'colour_dominance':
                    if any(type(v) is not bool for v in selected['value']): raise ValueError('Invalid recorded boolean channel.')
                elif any(not isinstance(v,str) for v in selected['value']):
                    raise ValueError('Invalid recorded text channel.')
                if selected['origin'] in ('owner_selected','owner_reported_label') and record['state']=='Known' and selected['value'] != record['canonical_values']:
                    raise ValueError('Selected channel and canonical values disagree.')
            if record['state']=='Known' and not record['canonical_values']: raise ValueError('Known description has no value.')
            if record['state']=='KnownEmpty' and (record['canonical_values'] or field not in ('style','material','descriptive_tags','colour_palette')): raise ValueError('Invalid empty-set state.')
            if record['state'] in ('Absent','Unspecified','Inapplicable') and record['canonical_values']: raise ValueError('Unavailable state has positive canonical values.')
        copy = json.loads(self.payload)
        copy['revision'] = ''
        if digest(copy) != value['revision']:
            raise ValueError('Description document integrity mismatch.')

    @classmethod
    def from_dict(cls, value):
        return cls(encode(value))

    def to_dict(self):
        return json.loads(self.payload)
