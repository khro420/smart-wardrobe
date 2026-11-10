"""Bounded immutable P2 settings and captured inputs, separate from P1 DTOs."""
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import re
import unicodedata
from uuid import UUID

from app.domain.value_objects.attribute_conditions import ANCHORS, RESERVED, ROLES
from app.domain.value_objects.garment_description_evidence import CANONICAL_ENUMS
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot

DOCUMENT = 'attribute-preferences-document-1.0.0'
UPDATE = 'attribute-preferences-update-1.0.0'
SNAPSHOT = 'attribute-preference-snapshot-1.0.0'
TYPE = 'descriptive_preferences_v1'
SOURCE = 'owner_p2_v1'
PROFILE = 'attribute_preference_decision_v2'
DECISION = 'attribute-preference-decision-2.0.0'
POLICY_HASH = 'c3046bdbbb1dfbfbeef8b9ff4e2e79aab0ecedfdbcfcc3572741efb5e356984c'
POLICY_SEMANTIC_HASH = 'b11e122750254d7725d267342cae7775e31562ddc8a130d59ed39f2d08907360'
LIMIT = 32768
HASH = re.compile(r'^[0-9a-f]{64}$')
DECIMAL = re.compile(r'^(?:0(?:\.[0-9]{1,6})?|1(?:\.0{1,6})?)$')
AXES = {'colour': ('primary_colour','secondary_colour','palette_colour','palette_coverage','colour_temperature','colour_dominance'),
        'styles': ('style',), 'garment_categories': ('category',), 'formality': ('formality',),
        **{k:(k,) for k in ('pattern','material','silhouette','neckline','sleeve_length','descriptive_tag')}}
DEFAULT_SCOPE = {a: ('base_upper_body' if a in ('neckline','sleeve_length') else 'base' if a in ('style','silhouette') else 'all_selected') for axes in AXES.values() for a in axes}


class PreferenceError(ValueError):
    def __init__(self, code, reason, status=422):
        super().__init__(reason)
        self.code, self.reason, self.status = code, reason, status


def encode(value):
    try:
        return json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    except (ValueError,TypeError,RecursionError,UnicodeError) as exc:
        raise PreferenceError('PreferenceInvalid','Invalid preference encoding.') from exc


def _pairs(pairs):
    value={}
    for key,item in pairs:
        if key in value: raise PreferenceError('PreferenceInvalid','Duplicate JSON key.')
        value[key]=item
    return value


def decode(raw, limit=LIMIT):
    try:
        if not isinstance(raw,(str,bytes)) or len(raw.encode('utf-8') if isinstance(raw,str) else raw)>limit:
            raise PreferenceError('PreferenceCapacityExceeded','Preference encoding exceeds its bound.')
        return json.loads(raw,object_pairs_hook=_pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except PreferenceError:
        raise
    except (ValueError,TypeError,RecursionError,UnicodeError) as exc:
        raise PreferenceError('PreferenceInvalid','Invalid preference JSON.') from exc


def digest(value): return hashlib.sha256(encode(value)).hexdigest()


def exact(value, keys):
    if type(value) is not dict or set(value)!=set(keys):
        raise PreferenceError('PreferenceInvalid','Unknown or missing preference fields.')


def uuid(value):
    try:
        if type(value) is not str or str(UUID(value))!=value: raise ValueError()
    except (ValueError,TypeError,AttributeError) as exc:
        raise PreferenceError('PreferenceInvalid','A canonical wearer/action UUID is required.') from exc
    return value


def weight(value):
    if type(value) is not str or not DECIMAL.fullmatch(value):
        raise PreferenceError('PreferenceInvalid','Use an exact importance decimal from zero to one, up to six places.')
    return Fraction(value)


def validate_value(axis, value):
    if axis=='colour_dominance':
        if type(value) is not bool: raise PreferenceError('PreferenceInvalid','Dominance must be true or false.')
        return
    if axis=='palette_coverage':
        exact(value,('colour','minimum'));validate_value('palette_colour',value['colour']);weight(value['minimum']);return
    if type(value) is not str or not value.strip() or len(value)>100 or unicodedata.normalize('NFC',value)!=value:
        raise PreferenceError('PreferenceInvalid','Use bounded canonical preference text.')
    if axis=='descriptive_tag':
        if value.casefold().startswith(RESERVED): raise PreferenceError('PreferenceInvalid','Reserved declarations are not descriptive preferences.')
        return
    if axis in ('primary_colour','secondary_colour','palette_colour'):
        if re.fullmatch(r'#[0-9a-f]{6}',value): return
        if value not in CANONICAL_ENUMS['primary_colour'] or axis=='palette_colour' and value=='cream':
            raise PreferenceError('PreferenceUnsupportedValue','This colour channel has no registered value.')
        return
    if axis=='formality':
        if value not in ('casual','smart_casual'): raise PreferenceError('PreferenceUnsupportedValue','This formality target is unavailable.')
        return
    if value not in CANONICAL_ENUMS.get(axis,()): raise PreferenceError('PreferenceUnsupportedValue','Use a supported canonical preference value.')


def validate_families(families):
    if type(families) is not dict or not set(families)<=set(AXES): raise PreferenceError('PreferenceInvalid','Unknown preference family.')
    total=0
    for family,record in families.items():
        if type(record) is not dict or record.get('mode') not in ('inherit_p1','override','disabled'): raise PreferenceError('PreferenceInvalid','Unknown family mode.')
        if record['mode']!='override': exact(record,('mode',));continue
        exact(record,('mode','importance','axes'));weight(record['importance'])
        if type(record['axes']) is not dict or not set(record['axes'])<=set(AXES[family]): raise PreferenceError('PreferenceInvalid','Unknown or duplicate scoped axis.')
        for axis,settings in record['axes'].items():
            exact(settings,('scope','importance','liked','avoided'));weight(settings['importance'])
            if settings['scope'] not in ROLES: raise PreferenceError('PreferenceInvalid','Unknown garment role scope.')
            all_values=[]
            for polarity in ('liked','avoided'):
                values=settings[polarity]
                if type(values) is not list: raise PreferenceError('PreferenceInvalid','Preference values must be arrays.')
                for value in values: validate_value(axis,value)
                all_values.extend(encode(v) for v in values)
            if len(all_values)> (20 if axis=='descriptive_tag' else 32) or len(set(all_values))!=len(all_values):
                raise PreferenceError('PreferenceInvalid','Liked and avoided values must be distinct, disjoint and bounded.')
            total+=len(all_values)
    if total>320: raise PreferenceError('PreferenceCapacityExceeded','Too many configured preference values.')


def validate_document(value):
    exact(value,('contract','families','last_action'))
    if value['contract']!=DOCUMENT: raise PreferenceError('PreferenceInvalid','Unknown preference document version.')
    validate_families(value['families'])
    action=value['last_action']
    if action is not None:
        exact(action,('action_id','input_digest','prior_revision','legacy_digest'));uuid(action['action_id'])
        if any(type(action[k]) is not str or not HASH.fullmatch(action[k]) for k in ('input_digest','prior_revision','legacy_digest')):
            raise PreferenceError('PreferenceInvalid','Invalid preference action digest.')


@dataclass(frozen=True)
class PreferenceDocument:
    payload: bytes

    def __post_init__(self):
        if type(self.payload) is not bytes: raise PreferenceError('PreferenceInvalid','Immutable preference bytes required.')
        value=decode(self.payload)
        validate_document(value)
        if self.payload!=encode(value):raise PreferenceError('PreferenceInvalid','Stored preference document is not canonical; no repair was performed.')

    @classmethod
    def from_dict(cls,value): return cls(encode(value))
    def to_dict(self): return decode(self.payload)


@dataclass(frozen=True)
class AttributePreferenceSnapshot:
    payload: bytes

    def __post_init__(self):
        if type(self.payload) is not bytes: raise PreferenceError('PreferenceInvalid','Immutable preference snapshot required.')
        v=decode(self.payload,131072)
        fields=('contract','account_id','wearer_id','document','legacy','legacy_digest','revision','policy')
        exact(v,(*fields,'archive') if 'archive' in v else fields)
        if v['contract']!=SNAPSHOT or type(v['account_id']) is not str or not v['account_id']: raise PreferenceError('PreferenceInvalid','Invalid preference snapshot identity.')
        uuid(v['wearer_id'])
        if v['document'] is not None: PreferenceDocument.from_dict(v['document'])
        if type(v['legacy']) is not list or len(v['legacy'])>16 or len(encode(v['legacy']))>65536: raise PreferenceError('PreferenceCapacityExceeded','Legacy preference capture exceeds its bound.')
        for row in v['legacy']:
            exact(row,('preference_id','user_id','preference_type','value_json','weight','source','is_active'))
            item=PreferenceSnapshot(**row)
            if item.user_id!=v['account_id'] or not item.is_active or item.preference_type==TYPE: raise PreferenceError('PreferenceInvalid','Legacy preference ownership/sentinel mismatch.')
        if v['legacy_digest']!=digest(v['legacy']) or v['revision']!=digest({'legacy':v['legacy'],'document':v['document']}): raise PreferenceError('PreferenceInvalid','Preference snapshot revision mismatch.')
        if v['policy']!=POLICY_HASH: raise PreferenceError('PreferenceInvalid','Unregistered preference policy.')
        if 'archive' in v:
            exact(v['archive'],('policy_snapshot','normalized_legacy'))
            if digest(v['archive']['policy_snapshot'])!=POLICY_SEMANTIC_HASH:raise PreferenceError('PreferenceInvalid','Unregistered archived preference resources.')
            if type(v['archive']['normalized_legacy']) is not dict:raise PreferenceError('PreferenceInvalid','Missing archived normalized preference evidence.')

    @classmethod
    def from_dict(cls,value): return cls(encode(value))
    def to_dict(self): return decode(self.payload,131072)
    @property
    def revision(self): return self.to_dict()['revision']
    def legacy_rows(self): return tuple(PreferenceSnapshot(**v) for v in self.to_dict()['legacy'])
