"""Bounded immutable hard requirements, separate from historical requests/scores."""
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import re
import unicodedata

from app.domain.value_objects.garment_description_evidence import CANONICAL_ENUMS

VERSION = 'attribute-conditions-1.0.0'
SUBTYPE_VERSION='attribute-conditions-2.0.0'
MAX_BYTES = 32768
ROLES = {'all_selected': ('upper','lower','one_piece','outerwear'),
         'base': ('upper','lower','one_piece'), 'base_upper_body': ('upper','one_piece'),
         **{k:(k,) for k in ('upper','lower','one_piece','outerwear')}}
OPERATORS = {
 'in': ('category','primary_colour','secondary_colour','pattern','silhouette','neckline','sleeve_length','colour_temperature','condition'),
 'contains_any': ('style','material','palette_colour','descriptive_tag'),
 'contains_all': ('style','material','palette_colour','descriptive_tag'),
 'exact_text': ('garment_name','descriptive_tag'),
 'exact_hex': ('primary_colour','secondary_colour','palette_colour'),
 'coverage_ge': ('palette_coverage',),
 'bool_eq': ('colour_dominance','construction_collared','construction_structured','construction_tailored')}
FIELDS = frozenset(f for fields in OPERATORS.values() for f in fields)
DECIMAL = re.compile(r'^(?:0(?:\.[0-9]{1,6})?|1(?:\.0{1,6})?)$')
HEX = re.compile(r'^#[0-9a-f]{6}$')
RESERVED = ('rec:','owner_style_','saved_attribute_','garment_description_',
 'contextual_suitability_','appearance_evidence_','automatic_','neckline:','sleeve length:','silhouette:')
ANCHORS = {'#808080':'grey','#ffc0cb':'pink','#000080':'navy','#ffff00':'yellow',
 '#800080':'purple','#ffffff':'white','#000000':'black','#ffa500':'orange',
 '#f5f5dc':'beige','#ff0000':'red','#a52a2a':'brown','#008000':'green','#0000ff':'blue'}


class AttributeRequestError(ValueError):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status, self.reason = status, reason


def encode(value):
    try:
        return json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    except (RecursionError,TypeError,ValueError,UnicodeError) as exc:
        raise AttributeRequestError('InvalidInput','invalid_attribute_encoding') from exc


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def exact(value, keys):
    if type(value) is not dict or set(value)!=set(keys):
        raise AttributeRequestError('InvalidInput','exact_attribute_schema_required')


def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise AttributeRequestError('InvalidInput','duplicate_attribute_key')
        result[key]=value
    return result


def decode(payload,limit=MAX_BYTES):
    if type(payload) is not bytes or len(payload)>limit:
        raise AttributeRequestError('EncodingLimitExceeded','attribute_encoding_budget')
    try:
        return json.loads(payload,object_pairs_hook=_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(AttributeRequestError('InvalidInput','nonfinite_attribute_value')))
    except (RecursionError,ValueError,UnicodeError) as exc:
        if isinstance(exc,AttributeRequestError):raise
        raise AttributeRequestError('InvalidInput','invalid_attribute_json') from exc


def _value(field, op, value):
    if op=='bool_eq':
        if type(value) is not bool:raise AttributeRequestError('UnsupportedAttributeValue','strict_boolean_required')
        return value
    if op=='coverage_ge':
        exact(value,('colour','minimum'))
        colour,minimum=value['colour'],value['minimum']
        if (type(colour) is not str or colour not in ANCHORS.values() and HEX.fullmatch(colour) is None
            or type(minimum) is not str or DECIMAL.fullmatch(minimum) is None):
            raise AttributeRequestError('UnsupportedAttributeValue','unsupported_palette_threshold')
        return {'colour':colour,'minimum':minimum}
    if type(value) is not str or not value.strip() or len(value)>100:
        raise AttributeRequestError('UnsupportedAttributeValue','bounded_attribute_text_required')
    if op=='exact_hex':
        if HEX.fullmatch(value) is None:raise AttributeRequestError('UnsupportedAttributeValue','canonical_exact_hex_required')
        return value
    if op=='exact_text' or field=='descriptive_tag':
        if unicodedata.normalize('NFC',value)!=value or field=='descriptive_tag' and value.casefold().startswith(RESERVED):
            raise AttributeRequestError('UnsupportedAttributeValue','unsupported_literal_description')
        return value
    enums=CANONICAL_ENUMS.get(field,())
    if field=='verified_subtype':
        from app.domain.value_objects.verified_garment_subtype import VALUES
        enums=VALUES
    if field=='palette_colour':enums=tuple(ANCHORS.values())
    elif field=='condition':enums=('clean_intact','needs_attention')
    if value not in enums:
        raise AttributeRequestError('UnsupportedAttributeValue','unsupported_'+field)
    return value


def _validate(value):
    exact(value,('version','groups'))
    if value['version'] not in (VERSION,SUBTYPE_VERSION):
        raise AttributeRequestError('AttributeUnavailable','unsupported_attribute_contract')
    groups=value['groups']
    if type(groups) is not list or not 1<=len(groups)<=8:
        raise AttributeRequestError('InvalidInput','bounded_attribute_groups_required')
    group_ids=set();condition_ids=set();total_values=0;normalized=[]
    for group in groups:
        exact(group,('id','role','quantifier','conditions'))
        gid=group['id']
        if type(gid) is not str or re.fullmatch(r'g0[1-8]',gid) is None or gid in group_ids:
            raise AttributeRequestError('InvalidInput','unique_binding_id_required')
        group_ids.add(gid)
        if type(group['role']) is not str or group['role'] not in ROLES or type(group['quantifier']) is not str or group['quantifier'] not in ('exists','all_present','none'):
            raise AttributeRequestError('InvalidInput','unsupported_attribute_scope')
        if type(group['conditions']) is not list or not 1<=len(group['conditions'])<=16:
            raise AttributeRequestError('InvalidInput','nonempty_conditions_required')
        conditions=[];scalar_sets={}
        for condition in group['conditions']:
            exact(condition,('id','attribute','operator','values'))
            cid,field,op=condition['id'],condition['attribute'],condition['operator']
            if type(cid) is not str or re.fullmatch(r'c(?:0[1-9]|1[0-6])',cid) is None or cid in condition_ids:
                raise AttributeRequestError('InvalidInput','unique_condition_id_required')
            condition_ids.add(cid)
            subtype=field=='verified_subtype' and op=='in' and value['version']==SUBTYPE_VERSION
            if not subtype and (type(op) is not str or op not in OPERATORS or field not in OPERATORS[op]):
                raise AttributeRequestError('UnsupportedAttributeValue','unsupported_field_operator')
            values=condition['values']
            if type(values) is not list or not 1<=len(values)<=20 or op in ('exact_text','exact_hex','bool_eq','coverage_ge') and len(values)!=1:
                raise AttributeRequestError('InvalidInput','bounded_attribute_values_required')
            total_values+=len(values)
            values=[_value(field,op,v) for v in values]
            keys=[encode(v) for v in values]
            if len(set(keys))!=len(keys):raise AttributeRequestError('InvalidInput','duplicate_attribute_value')
            values=[v for _,v in sorted(zip(keys,values),key=lambda item:item[0])]
            conditions.append({**condition,'values':values})
            if op in ('in','exact_hex','bool_eq'):
                current=set(encode(v) for v in values)
                key=(field,op)
                scalar_sets[key]=scalar_sets.get(key,current)&current
        if group['quantifier']!='none' and any(not v for v in scalar_sets.values()):
            raise AttributeRequestError('AttributeConflict','same_member_scalar_conflict')
        normalized.append({**group,'conditions':sorted(conditions,key=lambda c:c['id'])})
    if len(condition_ids)>16 or total_values>64:
        raise AttributeRequestError('InvalidInput','attribute_collection_limit')
    for positive in normalized:
        if positive['quantifier']=='none':continue
        required={encode({k:c[k] for k in ('attribute','operator','values')}) for c in positive['conditions']}
        for negative in normalized:
            if negative['quantifier']!='none' or not set(ROLES[positive['role']])<=set(ROLES[negative['role']]):continue
            forbidden={encode({k:c[k] for k in ('attribute','operator','values')}) for c in negative['conditions']}
            if forbidden<=required:raise AttributeRequestError('AttributeConflict','required_forbidden_binding')
    result={'version':value['version'],'groups':sorted(normalized,key=lambda g:g['id'])}
    if len(encode(result))>MAX_BYTES:raise AttributeRequestError('EncodingLimitExceeded','attribute_encoding_budget')
    return result


@dataclass(frozen=True)
class AttributeConditions:
    payload: bytes

    def __post_init__(self):
        value=decode(self.payload)
        if encode(_validate(value))!=self.payload:
            raise AttributeRequestError('InvalidInput','noncanonical_attribute_conditions')

    @classmethod
    def from_dict(cls,value):
        if len(encode(value))>MAX_BYTES:raise AttributeRequestError('EncodingLimitExceeded','attribute_encoding_budget')
        return cls(encode(_validate(value)))

    def to_dict(self):return decode(self.payload)

    @property
    def sha256(self):return hashlib.sha256(self.payload).hexdigest()

    @property
    def condition_count(self):return sum(len(g['conditions']) for g in self.to_dict()['groups'])


def conjoin(first,second):
    if first is None:return second
    if second is None:return first
    groups=[];index=0
    for value in (first,second):
        for group in value.to_dict()['groups']:
            conditions=[]
            for condition in group['conditions']:
                index+=1;conditions.append({**condition,'id':f'c{index:02d}'})
            groups.append({**group,'id':f'g{len(groups)+1:02d}','conditions':conditions})
    return AttributeConditions.from_dict({'version':SUBTYPE_VERSION if any(v.to_dict()['version']==SUBTYPE_VERSION for v in (first,second)) else VERSION,'groups':groups})
