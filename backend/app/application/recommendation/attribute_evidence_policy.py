"""One-time field qualification over captured immutable B0 facts; no CV calls."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import unicodedata
import re
from types import MappingProxyType

from app.domain.value_objects.attribute_conditions import decode,encode,AttributeRequestError,RESERVED,ANCHORS
from app.domain.value_objects.garment_description_evidence import CANONICAL_ENUMS
from app.application.wardrobe.description_normalizer import qualified

VERSION='attribute-evidence-policy-1.0.0'
RESOURCE_SHA256='2f99aa41db6ee8b8dad20746599d459f9ab0b6fdb9d030dafb13f142021be0bf'
SEMANTIC_SHA256='85aa813be1add8563cdbb83144fb8f7205a5418b81362741ebfafd32392227cf'
MAP={'palette_colour':'colour_palette','palette_coverage':'colour_palette','descriptive_tag':'descriptive_tags'}
REVIEWED={'construction_collared':'collared_neckline','construction_structured':'structured_shape','construction_tailored':'tailored_cut'}
VISUAL=frozenset(('style','pattern','silhouette','neckline','sleeve_length','primary_colour','secondary_colour','palette_colour','palette_coverage','colour_temperature','colour_dominance'))


@dataclass(frozen=True)
class AttributeFact:
    state: str
    values: tuple = ()
    complete: bool = False
    applicability: str = 'applicable'
    source: str = 'unqualified_source'
    revision: str | None = None


@dataclass(frozen=True)
class ArchivedPrimaryClassifier:
    aliases: tuple

    def classify(self,value):
        if value is None or isinstance(value,str) and not value.strip():return AttributeFact('Missing')
        if type(value) is not str:return AttributeFact('Malformed')
        value=re.sub(r'\s+',' ',value.strip().casefold())
        if re.fullmatch(r'#[0-9a-f]{3}',value):value='#'+''.join(c*2 for c in value[1:])
        canonical=dict(self.aliases).get(value,ANCHORS.get(value))
        return AttributeFact('Known',(canonical,),True,source='legacy_named_identity') if canonical is not None else AttributeFact('Unrecognized')


@dataclass(frozen=True)
class AttributeEvidencePolicy:
    payload: bytes

    def __post_init__(self):
        value=decode(self.payload,65536)
        if value.get('version') not in (VERSION,'attribute-evidence-policy-2.0.0') or value.get('model_sources')!=[] or value.get('measured_sources')!=[]:
            raise AttributeRequestError('AttributeUnavailable','unapproved_source_policy')
        if hashlib.sha256(encode(value)).hexdigest()!=(SEMANTIC_SHA256 if value['version']==VERSION else '053baeb70814c4e23dea94e20663f225e85cad214aadb45fb6a8a887dc714e9b'):
            raise AttributeRequestError('AttributeUnavailable','unregistered_attribute_policy')

    @classmethod
    def load(cls,path=None):
        path=Path(path) if path else Path(__file__).with_name('config')/'attribute_evidence_policy.v1.json'
        try:
            with path.open('rb') as stream:raw=stream.read(65537)
        except OSError as exc:raise AttributeRequestError('AttributeUnavailable','missing_attribute_policy') from exc
        if hashlib.sha256(raw).hexdigest() not in (RESOURCE_SHA256,'772eb60118c333c87c58ec4d88ac39d6829b2d1df62db3ee3c37ac9f79cbefac'):raise AttributeRequestError('AttributeUnavailable','unregistered_attribute_policy')
        return cls(raw)

    @property
    def sha256(self):return RESOURCE_SHA256 if self.snapshot()['version']==VERSION else '772eb60118c333c87c58ec4d88ac39d6829b2d1df62db3ee3c37ac9f79cbefac'

    def snapshot(self):return decode(self.payload,65536)

    def primary_classifier(self):return ArchivedPrimaryClassifier(tuple(self.snapshot()['primary_aliases'].items()))

    @classmethod
    def for_conditions(cls,conditions):
        return cls.load(Path(__file__).with_name('config')/'attribute_evidence_policy.v2.json') if conditions and conditions.to_dict()['version']=='attribute-conditions-2.0.0' else cls.load()

    def subtype_fact(self,snapshot,source):
        from app.domain.value_objects.verified_garment_subtype import validate_source,PARENTS
        if source is None:return AttributeFact('Absent')
        value=source.to_dict() if hasattr(source,'to_dict') else source
        validate_source(value)
        if value['owner_id']!=snapshot.user_id or value['subject_id']!=snapshot.garment_id or value['category']!=snapshot.category or value['media_id']!=snapshot.preferred_media_id:raise ValueError('Wrong subtype member binding.')
        if snapshot.category not in PARENTS:return AttributeFact('Inapplicable',applicability='inapplicable')
        return AttributeFact(value['state'],(value['value'],) if value['state']=='Known' else (),value['state']=='Known',source='owner_confirmed_subtype',revision=value['revision'])

    def fact(self,snapshot,description,field,operator,legacy_primary):
        """Called once per captured member/primitive, never while enumerating."""
        if field=='garment_name':
            name=snapshot.name
            return AttributeFact('Known',(unicodedata.normalize('NFC',name),),True,source='legacy_named_identity') if isinstance(name,str) and name.strip() and len(name)<=100 else AttributeFact('Absent')
        if field=='category':
            return AttributeFact('Known',(snapshot.category,),True,source='legacy_named_identity') if snapshot.category in CANONICAL_ENUMS['category'] else AttributeFact('Unrecognized')
        if field=='primary_colour' and operator=='in':
            value=legacy_primary.classify(snapshot.primary_colour)
            return AttributeFact(value.state,tuple(value.values),value.state=='Known',source='legacy_named_identity')
        if field=='condition' or field in REVIEWED:
            evidence=snapshot.appearance_evidence
            if not evidence.current(snapshot):return AttributeFact('Stale' if evidence.state=='Known' else evidence.state)
            value=evidence.condition if field=='condition' else dict(evidence.features).get(REVIEWED[field])
            if value is None or value=='unknown':return AttributeFact('Absent')
            return AttributeFact('Known',(value,),True,source='dated_reviewed_observation',revision=evidence.reviewed_at)
        record=description['fields'][MAP.get(field,field)]
        source=record['selected']['origin'] if record['selected'] else 'unqualified_source'
        applicable=record['applicability']
        if field in VISUAL and (record['binding']['category']!=snapshot.category or record['binding']['media_id']!=snapshot.preferred_media_id):
            return AttributeFact('Stale',applicability=applicable,source=source,revision=record['binding']['field_revision'])
        if applicable=='inapplicable':return AttributeFact('Inapplicable',applicability=applicable)
        if not qualified(record):
            state=record['state'] if record['state'] not in ('Known','KnownEmpty') else 'Unqualified'
            return AttributeFact(state,applicability=applicable,source=source,revision=record['binding']['field_revision'])
        values=record['canonical_values']
        if field in ('palette_colour','palette_coverage'):
            values=tuple((v['hex'],v['coverage']) for v in values)
        elif field=='descriptive_tag':
            values=tuple(v for v in values if not v.casefold().startswith(RESERVED))
        else:values=tuple(values)
        return AttributeFact(record['state'],values,record['completeness']=='complete_recorded_set',applicable,source,record['binding']['field_revision'])
