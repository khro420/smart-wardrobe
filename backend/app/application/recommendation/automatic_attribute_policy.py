"""Diagnostic-only automatic source registry. Every admission path is disabled."""
from dataclasses import dataclass
from types import MappingProxyType

from app.domain.value_objects.automatic_attribute_observation import (
    ATTRIBUTES, AutomaticAttributeObservation, validate_observation_binding,
    validate_observation_bundle, _hash,
)
from app.domain.value_objects.garment_description_evidence import digest

POLICY_VERSION = 'automatic-attribute-foundation-policy-1.0.0'
ATTRIBUTE_POLICIES = MappingProxyType({attribute:
    'owner_reported_only' if attribute=='material' else
    'existing_colour_policy_unchanged' if attribute=='primary_colour' else
    'automatic_admission_disabled' for attribute in sorted(ATTRIBUTES)})


@dataclass(frozen=True, slots=True)
class AutomaticSourceRegistration:
    """Source/mapping recognition only; never an approval of model reliability."""
    attribute: str
    kind: str
    producer_sha256: str
    mappings: tuple = ()  # (verbatim raw label, digest(canonical_values))
    required_quality: tuple = ()
    requires_mask: bool = True
    requires_confidence: bool = True

    def __post_init__(self):
        if self.attribute not in ATTRIBUTES or self.kind not in ('prediction','measurement'):
            raise ValueError('Unknown registered attribute/kind.')
        _hash(self.producer_sha256)
        if type(self.mappings) is not tuple or len(self.mappings)>256 or type(self.required_quality) is not tuple or len(self.required_quality)>16:
            raise ValueError('Bounded immutable registration required.')
        labels=set()
        for pair in self.mappings:
            if type(pair) is not tuple or len(pair)!=2 or type(pair[0]) is not str or not pair[0] or len(pair[0])>100 or pair[0] in labels:
                raise ValueError('Invalid registered mapping.')
            labels.add(pair[0]);_hash(pair[1])
        if any(type(k) is not str or not k or len(k)>48 for k in self.required_quality) or len(set(self.required_quality))!=len(self.required_quality):
            raise ValueError('Invalid quality requirements.')
        if type(self.requires_mask) is not bool or type(self.requires_confidence) is not bool:
            raise ValueError('Explicit registration requirements needed.')


@dataclass(frozen=True, slots=True)
class AutomaticSourceRegistry:
    entries: tuple = ()

    def __post_init__(self):
        if type(self.entries) is not tuple or len(self.entries)>32 or any(type(e) is not AutomaticSourceRegistration for e in self.entries):
            raise ValueError('Invalid or oversized source registry.')
        keys=[(e.attribute,e.kind,e.producer_sha256) for e in self.entries]
        if len(keys)!=len(set(keys)):raise ValueError('Duplicate source registration.')

    def find(self, observation):
        value=observation.to_dict()
        return next((e for e in self.entries if
            (e.attribute,e.kind,e.producer_sha256)==(value['attribute'],value['kind'],digest(value['producer']))),None)


DEFAULT_REGISTRY = AutomaticSourceRegistry()  # No approved automatic emitters.


@dataclass(frozen=True, slots=True)
class AutomaticEvidenceDiagnostic:
    structural_state: str
    binding_state: str
    registration_state: str
    observation_state: str
    reasons: tuple

    @property
    def source_authenticity(self):return 'unverified'

    @property
    def model_reliability(self):return 'not_validated'

    @property
    def automatic_admission(self):return False

    @property
    def mandatory_verdict(self):return 'Unknown'


def classify_observation(observation, *, context=None, binding=None, registry=DEFAULT_REGISTRY):
    """Never produces a B1 AttributeFact or calls a database/model/runtime."""
    if type(observation) is not AutomaticAttributeObservation or type(registry) is not AutomaticSourceRegistry:
        raise ValueError('Typed observation and registry required.')
    value=observation.to_dict();reasons=[];binding_state='unverified'
    if context is not None:
        try:
            validate_observation_binding(observation,context,binding)
            binding_state='matches_expected_context'
        except ValueError as error:
            binding_state='mismatch';reasons.append(str(error))
    elif binding is not None:raise ValueError('A binding requires independent expected context.')
    registration=registry.find(observation)
    registration_state='registered' if registration else 'unregistered'
    if registration is None:reasons.append('unregistered_source')
    else:
        if value['kind']=='prediction' and (value['raw_label'],digest(value['canonical_values'])) not in registration.mappings:
            reasons.append('unsupported_mapping')
        if registration.requires_mask and value['inputs']['mask'] is None:reasons.append('required_mask_missing')
        if registration.requires_confidence and value['kind']=='prediction' and value['confidence'] is None:reasons.append('required_confidence_missing')
        present={m['name'] for m in value['quality']['metrics']}
        if not set(registration.required_quality)<=present:reasons.append('required_quality_missing')
    if value['availability']!='available':reasons.append('extraction_'+value['availability'])
    elif value['mapping_state']=='unmapped':reasons.append('unmapped_prediction')
    reasons.extend(('source_authenticity_unverified','model_reliability_unvalidated',ATTRIBUTE_POLICIES[value['attribute']]))
    return AutomaticEvidenceDiagnostic('valid',binding_state,registration_state,value['availability'],tuple(reasons))


def compare_observation_claims(observations):
    """Report disagreements between comparable claims; never choose a winner.

    This does not establish that either source is genuine, reliable or current.
    """
    validate_observation_bundle(observations)
    if not observations:return 'Unknown'
    rows=[o.to_dict() for o in observations]
    keys={(r['owner_id'],r['processing_job_id'],r['processing_item_id'],r['attribute'],digest(r['inputs'])) for r in rows}
    if len(keys)!=1:raise ValueError('Incomparable observation claims.')
    available=[r for r in rows if r['availability']=='available' and r['mapping_state']=='mapped']
    if len({digest(r['canonical_values']) for r in available})>1:return 'Conflicting'
    return 'Unknown'  # Agreement is not qualification or negative completeness.
