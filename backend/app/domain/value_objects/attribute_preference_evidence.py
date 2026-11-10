"""Immutable bounded P2 evidence. Raw uncertainty is distinct from masked decision."""
from dataclasses import dataclass
from app.domain.value_objects.attribute_preferences import encode,decode,digest,exact,PreferenceError,PROFILE,DECISION,POLICY_HASH

EVIDENCE='attribute-preference-evidence-1.0.0'
LIMIT=344064
SCOPE_FIELDS=('legacy_base_scope_sha256','garment_snapshot_sha256','description_collection_sha256','request_sha256','preference_scope_sha256')


def preference_scope(snapshot,base,garments,descriptions,request):
    value=snapshot.to_dict()
    return digest({'contract':'attribute-preference-scope-1.0.0','account_id':value['account_id'],'wearer_id':value['wearer_id'],
        'snapshot_sha256':digest(value),'legacy_base_scope_sha256':base,'garment_snapshot_sha256':garments,
        'description_collection_sha256':descriptions,'request_sha256':request})


def ratio(value):
    if len(str(abs(value.numerator)))>4096 or len(str(value.denominator))>4096:raise PreferenceError('PreferenceCapacityExceeded','Exact preference ratio exceeds its bound.')
    return {'numerator':str(value.numerator),'denominator':str(value.denominator)}


def read_ratio(raw):
    from fractions import Fraction
    import re
    exact(raw,('numerator','denominator'))
    if any(type(raw[k]) is not str or len(raw[k])>4096 or re.fullmatch(r'0|[1-9][0-9]*',raw[k]) is None for k in raw) or raw['denominator']=='0':
        raise PreferenceError('PreferenceInvalid','Invalid exact preference ratio.')
    value=Fraction(int(raw['numerator']),int(raw['denominator']))
    if ratio(value)!=raw:raise PreferenceError('PreferenceInvalid','Noncanonical exact preference ratio.')
    return value


@dataclass(frozen=True)
class AttributePreferenceEvidence:
    payload: bytes

    def __post_init__(self):
        if type(self.payload) is not bytes:raise PreferenceError('PreferenceInvalid','Immutable preference evidence required.')
        v=decode(self.payload,LIMIT)
        exact(v,('contract','decision','policy','snapshot','scope','selected','ledger','revision'))
        if v['contract']!=EVIDENCE or v['decision']!=DECISION or v['policy']!=POLICY_HASH:raise PreferenceError('PreferenceInvalid','Unknown P2 evidence version.')
        from app.domain.value_objects.attribute_preferences import AttributePreferenceSnapshot
        snapshot=AttributePreferenceSnapshot.from_dict(v['snapshot'])
        from app.domain.value_objects.attribute_preferences import HASH
        exact(v['scope'],SCOPE_FIELDS)
        if any(type(h) is not str or not HASH.fullmatch(h) for h in v['scope'].values()):raise PreferenceError('PreferenceInvalid','Invalid captured P2 scope.')
        scope=v['scope']
        if scope['preference_scope_sha256']!=preference_scope(snapshot,scope['legacy_base_scope_sha256'],scope['garment_snapshot_sha256'],scope['description_collection_sha256'],scope['request_sha256']):
            raise PreferenceError('PreferenceInvalid','Captured P2 scope mismatch.')
        if type(v['selected']) is not list or not 1<=len(v['selected'])<=3 or len(encode(v['selected']))>147456:raise PreferenceError('PreferenceCapacityExceeded','Selected preference inputs exceed their bound.')
        if type(v['ledger']) is not dict or len(encode(v['ledger']))>65536:raise PreferenceError('PreferenceCapacityExceeded','Preference ledger exceeds its bound.')
        copy={**v,'revision':''}
        if digest(copy)!=v['revision']:raise PreferenceError('PreferenceInvalid','P2 evidence integrity mismatch.')

    @classmethod
    def from_dict(cls,value):return cls(encode(value))
    def to_dict(self):return decode(self.payload,LIMIT)


@dataclass(frozen=True)
class AttributePreferenceWriteDraft:
    evidence: AttributePreferenceEvidence

    def __post_init__(self):
        if type(self.evidence) is not AttributePreferenceEvidence or 'archive' not in self.evidence.to_dict()['snapshot']:
            raise PreferenceError('PreferenceInvalid','P2 writes require captured immutable archive inputs.')
