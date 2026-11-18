"""Standalone automatic observations. Integrity is NOT provenance or admission.

No producer, storage writer or recommendation path imports this foundation.
Owner assertions continue to use the existing B0 contract, never this envelope.
"""
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
import re
from uuid import UUID

from app.domain.value_objects.attribute_conditions import decode
from app.domain.value_objects.garment_description_evidence import (
    FIELDS, CANONICAL_ENUMS, encode, digest, exact_keys, validate_values,
)

CONTRACT = 'automatic-attribute-observation-1.0.0'
BINDING_CONTRACT = 'automatic-attribute-garment-binding-1.0.0'
MAX_BYTES = 4096
MAX_BUNDLE_BYTES = 32768
MAX_OBSERVATIONS = 14
ATTRIBUTES = frozenset(FIELDS) - {'garment_name'}
AVAILABILITY = frozenset(('available', 'disabled', 'assets_missing', 'failed', 'not_applicable'))
KEYS = frozenset(('contract', 'observation_id', 'owner_id', 'processing_job_id',
    'processing_item_id', 'attribute', 'kind', 'availability', 'failure_code',
    'raw_label', 'canonical_values', 'mapping_state', 'producer', 'inputs',
    'confidence', 'quality', 'predicted_at', 'recorded_at', 'source_revision',
    'observation_sha256'))
PRODUCER_KEYS = frozenset(('emitter_version', 'extractor_build_sha256', 'algorithm_version',
    'model_id', 'model_sha256', 'head_id', 'checkpoint_sha256', 'vocabulary_version',
    'vocabulary_sha256', 'mapping_version', 'mapping_sha256',
    'preprocessing_version', 'preprocessing_sha256'))
HEX = re.compile(r'[0-9a-f]{64}')
DECIMAL = re.compile(r'(?:0|[1-9][0-9]{0,8})(?:\.[0-9]{1,8})?')
NAME = re.compile(r'[a-z][a-z0-9_]{0,47}')


def _text(value, maximum=128):
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise ValueError('Invalid observation text.')


def _hash(value):
    if type(value) is not str or HEX.fullmatch(value) is None:
        raise ValueError('Invalid observation digest.')


def _one_of(value, choices):
    return type(value) is str and value in choices


def _uuid(value):
    if type(value) is not str or str(UUID(value)) != value or UUID(value).int == 0:
        raise ValueError('A canonical nonzero identity is required.')


def _timestamp(value):
    _text(value, 40)
    if re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z', value) is None:
        raise ValueError('An explicit UTC timestamp is required.')
    datetime.fromisoformat(value[:-1] + '+00:00')


def _decimal(value, *, unit_interval=False):
    if type(value) is not str or DECIMAL.fullmatch(value) is None:
        raise ValueError('A finite nonnegative decimal string is required.')
    if unit_interval and Fraction(value) > 1:
        raise ValueError('Confidence must be between zero and one.')


def _media(value):
    exact_keys(value, ('media_id', 'sha256'))
    _uuid(value['media_id']); _hash(value['sha256'])


def _inputs(value):
    exact_keys(value, ('source', 'crop', 'mask', 'analysed_pixels'))
    _media(value['source']); _media(value['crop'])
    if value['mask'] is not None:
        _media(value['mask'])
    pixels = value['analysed_pixels']
    exact_keys(pixels, ('sha256', 'width', 'height', 'colour_space', 'encoding'))
    _hash(pixels['sha256'])
    if any(type(pixels[k]) is not int or not 0 < pixels[k] <= 100000 for k in ('width', 'height')):
        raise ValueError('Invalid analysed dimensions.')
    if not _one_of(pixels['colour_space'], ('RGB', 'RGBA', 'BGR', 'GRAY')) or pixels['encoding'] != 'uint8-hwc-contiguous-v1':
        raise ValueError('Unregistered pixel representation.')


def _producer(value, *, prediction, available):
    exact_keys(value, PRODUCER_KEYS)
    for key in ('emitter_version', 'algorithm_version', 'preprocessing_version'):
        _text(value[key])
    for key in ('extractor_build_sha256', 'preprocessing_sha256'):
        _hash(value[key])
    optional = PRODUCER_KEYS - {'emitter_version', 'algorithm_version', 'preprocessing_version',
                                'extractor_build_sha256', 'preprocessing_sha256'}
    for key in optional:
        if value[key] is not None:
            (_hash if key.endswith('sha256') else _text)(value[key])
    if prediction and available and any(value[k] is None for k in optional):
        raise ValueError('Available predictions require model/head/checkpoint and mapping identities.')
    if not prediction and any(value[k] is not None for k in ('model_id', 'model_sha256', 'head_id', 'checkpoint_sha256')):
        raise ValueError('A measurement cannot impersonate a model prediction.')


def _quality(value):
    exact_keys(value, ('state', 'metrics'))
    if not _one_of(value['state'], ('available', 'partial', 'unavailable')) or type(value['metrics']) is not list or len(value['metrics']) > 16:
        raise ValueError('Invalid quality state or budget.')
    if (value['state'] == 'unavailable') != (not value['metrics']):
        raise ValueError('Quality availability must agree with metric presence.')
    names = set()
    for metric in value['metrics']:
        exact_keys(metric, ('name', 'value', 'unit', 'method_version'))
        if type(metric['name']) is not str or NAME.fullmatch(metric['name']) is None or metric['name'] in names:
            raise ValueError('Invalid or duplicate quality metric.')
        names.add(metric['name'])
        _decimal(metric['value']); _text(metric['unit'], 32); _text(metric['method_version'], 64)


def _source_revision(value):
    # IDs and receipt time distinguish observations, not the extraction content.
    return digest({k:v for k,v in value.items() if k not in
                   ('observation_id', 'recorded_at', 'source_revision', 'observation_sha256')})


def _validate(value, *, verify_integrity=True):
    exact_keys(value, KEYS)
    if value['contract'] != CONTRACT or not _one_of(value['attribute'], ATTRIBUTES):
        raise ValueError('Unknown automatic observation contract or attribute.')
    for key in ('observation_id', 'owner_id', 'processing_job_id', 'processing_item_id'):
        _uuid(value[key])
    if not _one_of(value['kind'], ('prediction', 'measurement')) or not _one_of(value['availability'], AVAILABILITY):
        raise ValueError('Unknown observation kind or availability.')
    available = value['availability'] == 'available'
    _producer(value['producer'], prediction=value['kind']=='prediction', available=available)
    _inputs(value['inputs']); _quality(value['quality']); _timestamp(value['recorded_at'])
    if type(value['canonical_values']) is not list or len(value['canonical_values']) > 20:
        raise ValueError('Invalid canonical value collection.')
    validate_values(value['attribute'], value['canonical_values'])
    if available:
        _timestamp(value['predicted_at'])
        if value['failure_code'] is not None or not _one_of(value['mapping_state'], ('mapped', 'unmapped')):
            raise ValueError('Available output cannot assert a failure.')
        if (value['mapping_state'] == 'mapped') != bool(value['canonical_values']):
            raise ValueError('Mapping state and canonical values disagree.')
        if value['kind'] == 'prediction':
            _text(value['raw_label'], 100)
        elif value['raw_label'] is not None:
            raise ValueError('Measurements have no raw model label.')
        if value['confidence'] is not None:
            if value['kind'] != 'prediction':
                raise ValueError('Measurements cannot assert classifier confidence.')
            exact_keys(value['confidence'], ('kind', 'value', 'calibration_id'))
            confidence = value['confidence']
            if not _one_of(confidence['kind'], ('softmax_top1', 'uncalibrated_score', 'calibrated_probability')):
                raise ValueError('Unknown confidence semantics.')
            _decimal(confidence['value'], unit_interval=True)
            if confidence['kind'] == 'calibrated_probability':
                _text(confidence['calibration_id'])
            elif confidence['calibration_id'] is not None:
                raise ValueError('Unexpected calibration claim.')
    else:
        if (value['canonical_values'] or value['mapping_state'] != 'not_available'
                or any(value[k] is not None for k in ('raw_label', 'confidence', 'predicted_at'))
                or value['quality'] != {'state':'unavailable', 'metrics':[]}):
            raise ValueError('Unavailable extraction cannot carry a positive observation.')
        if type(value['failure_code']) is not str or NAME.fullmatch(value['failure_code']) is None:
            raise ValueError('Unavailable extraction requires a bounded reason code.')
    if not verify_integrity:
        return
    _hash(value['source_revision']); _hash(value['observation_sha256'])
    if value['source_revision'] != _source_revision(value):
        raise ValueError('Observation source revision mismatch.')
    if value['observation_sha256'] != digest({**value, 'observation_sha256':''}):
        raise ValueError('Observation integrity mismatch.')


@dataclass(frozen=True, slots=True)
class AutomaticAttributeObservation:
    """Canonical immutable bytes; to_dict returns a detached copy, never trust."""
    payload: bytes

    def __post_init__(self):
        value = decode(self.payload, MAX_BYTES)
        _validate(value)
        object.__setattr__(self, 'payload', encode(value))

    @classmethod
    def from_dict(cls, value):
        _validate(value)  # Do not coerce caller tuples/subclasses into JSON arrays.
        return cls(encode(value))

    @classmethod
    def seal(cls, value):
        """Integrity-only builder for producer/test drafts; NOT an attestation."""
        exact_keys(value, KEYS)
        if value['source_revision'] != '' or value['observation_sha256'] != '':
            raise ValueError('Use from_dict to validate an already sealed observation.')
        _validate(value, verify_integrity=False)
        value = decode(encode(value), MAX_BYTES)
        value['source_revision'] = _source_revision(value)
        value['observation_sha256'] = digest({**value, 'observation_sha256':''})
        return cls.from_dict(value)

    def to_dict(self):
        return decode(self.payload, MAX_BYTES)

    @property
    def sha256(self):
        return self.to_dict()['observation_sha256']


BINDING_KEYS = frozenset(('contract', 'observation_sha256', 'owner_id', 'processing_job_id',
    'processing_item_id', 'garment_id', 'category', 'preferred_media_id', 'source_revision',
    'confirmed_at', 'binding_sha256'))


@dataclass(frozen=True, slots=True)
class GarmentObservationBinding:
    """Separate confirmation claims; no database or owner authority is created."""
    payload: bytes

    def __post_init__(self):
        value = decode(self.payload, MAX_BYTES); exact_keys(value, BINDING_KEYS)
        if value['contract'] != BINDING_CONTRACT or not _one_of(value['category'], CANONICAL_ENUMS['category']):
            raise ValueError('Unknown garment binding contract/category.')
        for k in ('owner_id', 'processing_job_id', 'processing_item_id', 'garment_id', 'preferred_media_id'):
            _uuid(value[k])
        for k in ('observation_sha256', 'source_revision', 'binding_sha256'):
            _hash(value[k])
        _timestamp(value['confirmed_at'])
        if value['binding_sha256'] != digest({**value, 'binding_sha256':''}):
            raise ValueError('Garment binding integrity mismatch.')
        object.__setattr__(self, 'payload', encode(value))

    @classmethod
    def from_dict(cls, value):
        return cls(encode(value))

    @classmethod
    def seal(cls, value):
        exact_keys(value, BINDING_KEYS)
        if value['binding_sha256'] != '':raise ValueError('Binding was already sealed.')
        return cls.from_dict({**value, 'binding_sha256':digest(value)})

    def to_dict(self):
        return decode(self.payload, MAX_BYTES)


@dataclass(frozen=True, slots=True)
class ObservationBindingContext:
    """Expected identities supplied by a future trusted caller, NOT by HTTP input.

    Equality with this context validates bindings, not emitter authenticity.
    No integrated producer supplies this context in the foundation phase.
    """
    owner_id: str
    processing_job_id: str
    processing_item_id: str
    inputs_sha256: str
    source_revision: str
    garment_id: str | None = None
    category: str | None = None
    preferred_media_id: str | None = None

    def __post_init__(self):
        for key in ('owner_id', 'processing_job_id', 'processing_item_id'):_uuid(getattr(self,key))
        _hash(self.inputs_sha256); _hash(self.source_revision)
        if self.garment_id is None:
            if self.category is not None or self.preferred_media_id is not None:
                raise ValueError('Processing-only context cannot claim garment bindings.')
        else:
            _uuid(self.garment_id); _uuid(self.preferred_media_id)
            if self.category not in CANONICAL_ENUMS['category']:raise ValueError('Invalid expected category.')


def validate_observation_binding(observation, context, binding=None):
    """Pure comparison with caller-owned expectations; raises on mismatches."""
    if type(observation) is not AutomaticAttributeObservation or type(context) is not ObservationBindingContext:
        raise ValueError('Typed observation and expected context required.')
    value = observation.to_dict()
    for key in ('owner_id', 'processing_job_id', 'processing_item_id'):
        if value[key] != getattr(context,key):raise ValueError('wrong_' + key)
    if digest(value['inputs']) != context.inputs_sha256:raise ValueError('wrong_media_binding')
    if value['source_revision'] != context.source_revision:raise ValueError('stale_source_revision')
    if context.garment_id is None:
        if binding is not None:raise ValueError('Unexpected garment binding.')
        return
    if type(binding) is not GarmentObservationBinding:raise ValueError('missing_confirmation_binding')
    garment = binding.to_dict()
    for key in ('owner_id', 'processing_job_id', 'processing_item_id', 'garment_id', 'category', 'preferred_media_id', 'source_revision'):
        if garment[key] != getattr(context,key):raise ValueError('wrong_confirmation_' + key)
    if garment['observation_sha256'] != observation.sha256:raise ValueError('wrong_confirmation_observation')


def validate_observation_bundle(observations):
    if type(observations) is not tuple or len(observations) > MAX_OBSERVATIONS:
        raise ValueError('Bounded immutable observation bundle required.')
    if any(type(o) is not AutomaticAttributeObservation for o in observations):raise ValueError('Invalid bundle member.')
    if len(encode([o.to_dict() for o in observations])) > MAX_BUNDLE_BYTES:raise ValueError('Observation bundle exceeds budget.')
    if len({o.to_dict()['observation_id'] for o in observations}) != len(observations):raise ValueError('Duplicate observation identity.')
