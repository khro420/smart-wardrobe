"""Versioned attribute intent/proof bytes, independent of legacy score codecs."""
from dataclasses import dataclass
import hashlib
import re
from app.domain.value_objects.attribute_conditions import AttributeConditions,AttributeRequestError,decode,encode,digest,exact

INTENT_VERSION='assistant-attribute-intent-1.0.0'
EVIDENCE_VERSION='attribute-selection-evidence-1.0.0'
MAX_INTENT=65536
MAX_EVIDENCE=196608
MAX_PROVENANCE=589824
INTENT_KEYS=('version','original_text','typed_input','conditions','spans','grammar_sha256','policy_sha256','intent_sha256')
EVIDENCE_KEYS=('version','intent','wearer_profile_id','strict_snapshot_sha256','description_collection_sha256',
 'attribute_scope_sha256','policy_snapshot','selected_evidence','decisions','coverage','revision')


def require_hash(value):
    if type(value) is not str or re.fullmatch(r'[0-9a-f]{64}',value) is None:raise ValueError('Invalid attribute digest.')


def subtype_digest(collection):
    return digest([s.to_dict() if hasattr(s,'to_dict') else s for s in sorted(collection,key=lambda s:s.garment_id if hasattr(s,'garment_id') else s['subject_id'])])

def scope_digest(account_id,wearer_profile_id,base_scope,intent,collection_hash,subtype_hash=None):
    if intent.to_dict()['version']=='assistant-attribute-intent-2.0.0':
        require_hash(subtype_hash)
        return digest({'version':'attribute-selection-scope-2.0.0','account_id':account_id,'wearer_profile_id':wearer_profile_id,'compatibility_scope_sha256':base_scope,'intent_sha256':intent.sha256,'description_collection_sha256':collection_hash,'subtype_collection_sha256':subtype_hash,'grammar_sha256':intent.to_dict()['grammar_sha256'],'policy_sha256':intent.to_dict()['policy_sha256']})
    return digest({'version':'attribute-selection-scope-1.0.0','account_id':account_id,'wearer_profile_id':wearer_profile_id,
        'compatibility_scope_sha256':base_scope,'intent_sha256':intent.sha256,'description_collection_sha256':collection_hash,
        'grammar_sha256':intent.to_dict()['grammar_sha256'],'policy_sha256':intent.to_dict()['policy_sha256']})


def description_digest(collection):
    return digest([{'garment_id':item.snapshot.garment_id,'description':item.description.to_dict()}
        for item in sorted(collection,key=lambda item:item.snapshot.garment_id)])


@dataclass(frozen=True)
class AttributeIntent:
    payload: bytes

    def __post_init__(self):
        value=decode(self.payload,MAX_INTENT);exact(value,INTENT_KEYS)
        if value['version'] not in (INTENT_VERSION,'assistant-attribute-intent-2.0.0') or type(value['original_text']) is not str or not value['original_text'].strip() or len(value['original_text'])>500:
            raise ValueError('Invalid immutable attribute intent.')
        conditions=AttributeConditions.from_dict(value['conditions'])
        if (value['version']=='assistant-attribute-intent-2.0.0')!=(conditions.to_dict()['version']=='attribute-conditions-2.0.0'):raise ValueError('Wrong attribute intent version.')
        if value['typed_input'] is not None:AttributeConditions.from_dict(value['typed_input'])
        for key in ('grammar_sha256','policy_sha256','intent_sha256'):require_hash(value[key])
        ids={c['id'] for g in conditions.to_dict()['groups'] for c in g['conditions']}
        if type(value['spans']) is not list or len(value['spans'])>128:raise ValueError('Invalid attribute spans.')
        for span in value['spans']:
            exact(span,('condition_id','source','start','end','text'))
            if span['condition_id'] not in ids or span['source'] not in ('nlp','typed'):raise ValueError('Invalid attribute span identity.')
            if span['source']=='typed':
                if any(span[k] is not None for k in ('start','end','text')):raise ValueError('Typed input has no invented text span.')
            elif (type(span['start']) is not int or type(span['end']) is not int or
                    not 0<=span['start']<span['end']<=len(value['original_text']) or value['original_text'][span['start']:span['end']]!=span['text']):
                raise ValueError('Attribute span does not address original text.')
        if ids!={span['condition_id'] for span in value['spans']}:raise ValueError('Missing attribute source span.')
        copy={**value,'intent_sha256':''}
        if digest(copy)!=value['intent_sha256']:raise ValueError('Attribute intent integrity mismatch.')

    @classmethod
    def capture(cls,text,typed,conditions,spans,grammar_hash,policy_hash):
        value=dict(version='assistant-attribute-intent-2.0.0' if conditions.to_dict()['version']=='attribute-conditions-2.0.0' else INTENT_VERSION,original_text=text,typed_input=typed.to_dict() if typed else None,
            conditions=conditions.to_dict(),spans=list(spans),grammar_sha256=grammar_hash,policy_sha256=policy_hash,intent_sha256='')
        value['intent_sha256']=digest(value)
        return cls(encode(value))

    @classmethod
    def from_dict(cls,value):return cls(encode(value))

    def to_dict(self):return decode(self.payload,MAX_INTENT)

    @property
    def sha256(self):return self.to_dict()['intent_sha256']

    @property
    def conditions(self):return AttributeConditions.from_dict(self.to_dict()['conditions'])


@dataclass(frozen=True)
class AttributeSelectionEvidence:
    payload: bytes

    def __post_init__(self):
        value=decode(self.payload,MAX_EVIDENCE)
        v2=value.get('version')=='attribute-selection-evidence-2.0.0'
        exact(value,(*EVIDENCE_KEYS,'subtype_collection_sha256','subtype_registry','selected_subtypes') if v2 else EVIDENCE_KEYS)
        if v2:
            from app.domain.value_objects.verified_garment_subtype import registry,validate_source
            registry(value['subtype_registry']);require_hash(value['subtype_collection_sha256'])
            if type(value['selected_subtypes']) is not list or len(value['selected_subtypes'])!=len(value['selected_evidence']):raise ValueError('Incomplete subtype selection.')
            for source in value['selected_subtypes']:validate_source(source)
        if value['version'] not in (EVIDENCE_VERSION,'attribute-selection-evidence-2.0.0'):raise ValueError('Unknown attribute selection evidence.')
        AttributeIntent.from_dict(value['intent'])
        for key in ('strict_snapshot_sha256','description_collection_sha256','attribute_scope_sha256','revision'):require_hash(value[key])
        if type(value['wearer_profile_id']) is not str:raise ValueError('Captured wearer required.')
        from app.domain.value_objects.recommendation_refinement import canonical_uuid
        canonical_uuid(value['wearer_profile_id'])
        if type(value['selected_evidence']) is not list or not 1<=len(value['selected_evidence'])<=3:raise ValueError('Bounded selected attribute evidence required.')
        for member in value['selected_evidence']:
            exact(member,('role','garment_id','description','appearance_evidence'))
            from app.domain.value_objects.garment_description_evidence import GarmentDescriptionEvidence
            document=GarmentDescriptionEvidence.from_dict(member['description']).to_dict()
            if document['subject']['garment_id']!=member['garment_id']:raise ValueError('Wrong selected description subject.')
        exact(value['decisions'],('identities','member_results'))
        if type(value['decisions']['identities']) is not list or len(value['decisions']['identities'])!=len(value['selected_evidence']):raise ValueError('Selected identity ledger mismatch.')
        if type(value['decisions']['member_results']) is not list or len(value['decisions']['member_results'])>48:raise ValueError('Attribute verdict ledger too large.')
        keys=('structural_examined','legacy_failed','legacy_unknown','attribute_failed','attribute_unknown','joint_passed')
        exact(value['coverage'],keys)
        if any(type(value['coverage'][k]) is not int or not 0<=value['coverage'][k]<=1000000 for k in keys):raise ValueError('Invalid attribute coverage.')
        if value['coverage']['joint_passed']<1 or value['coverage']['structural_examined']!=sum(value['coverage'][k] for k in keys[1:]):raise ValueError('Incomplete attribute coverage.')
        if digest({**value,'revision':''})!=value['revision']:raise ValueError('Attribute selection integrity mismatch.')

    @classmethod
    def from_dict(cls,value):return cls(encode(value))

    def to_dict(self):return decode(self.payload,MAX_EVIDENCE)

    @property
    def sha256(self):return self.to_dict()['revision']


@dataclass(frozen=True)
class AttributeWriteDraft:
    evidence: AttributeSelectionEvidence
    compatibility_scope_sha256: str

    def __post_init__(self):
        if type(self.evidence) is not AttributeSelectionEvidence:raise ValueError('Immutable attribute draft required.')
        require_hash(self.compatibility_scope_sha256)


def bounded_provenance(value):
    # Version-specific outer encoding; historical codecs remain unchanged.
    text=encode(value)
    attributes=value.get('attribute_selection')
    if attributes is None:raise ValueError('New provenance requires attribute evidence.')
    AttributeSelectionEvidence.from_dict(attributes)
    core={k:v for k,v in value.items() if k!='attribute_selection'}
    if len(encode(core))>360448 or len(text)>MAX_PROVENANCE:
        raise AttributeRequestError('EncodingLimitExceeded','attribute_provenance_budget')
    return text.decode('utf-8')
