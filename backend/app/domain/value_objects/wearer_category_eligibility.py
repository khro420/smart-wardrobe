"""Closed project policy and immutable evidence; no demographic inference."""
from dataclasses import dataclass
import hashlib,json,re
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE

POLICY_VERSION='wearer-category-policy-1.0.0'
EVIDENCE_VERSION='wearer-category-eligibility-evidence-1.0.0'
KEY='wearer_category_eligibility'
DENIED=('skirt','short_sleeve_dress','long_sleeve_dress','vest_dress','sling_dress')

def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(value):return hashlib.sha256(encode(value).encode()).hexdigest()

def validate_policy(value):
    if type(value) is not dict:raise ValueError('Unregistered wearer category policy.')
    version=value.get('version')
    if version==POLICY_VERSION:
        if set(value)!={'version','allowed'}:raise ValueError('Unregistered wearer category policy.')
    elif version=='wearer-category-policy-2.0.0':
        from app.domain.value_objects.verified_garment_subtype import VERSION,RESOURCE_SHA256
        if set(value)!={'version','allowed','subtype'} or value['subtype']!={'registry_version':VERSION,'registry_sha256':RESOURCE_SHA256,'male_denied':['blouse'],'male_relevant_unknown':'Unknown','female_generic_unknown':'Permit'}:raise ValueError('Unregistered subtype policy.')
    else:raise ValueError('Unregistered wearer category policy.')
    expected={'male':sorted(set(GARMENT_STRUCTURE)-set(DENIED)),'female':sorted(GARMENT_STRUCTURE)}
    if value['allowed']!=expected:raise ValueError('Unregistered category matrix.')
    return value

def validate_evidence(value,owner,profile_id,items=()):
    fields={'version','policy','policy_sha256','owner_id','profile_id','details_revision','gender_key','account_count','account_source_sha256','usable_ids','scope_sha256'}
    v2=type(value) is dict and value.get('version')=='wearer-category-eligibility-evidence-2.0.0'
    if v2:fields=fields|{'subtype_sources','subtype_registry','subtype_decisions'}
    if type(value) is not dict or set(value)!=fields or value['version'] not in (EVIDENCE_VERSION,'wearer-category-eligibility-evidence-2.0.0'):raise ValueError('Invalid wearer eligibility evidence.')
    validate_policy(value['policy'])
    if value['owner_id']!=owner or value['profile_id']!=profile_id or value['gender_key'] not in ('male','female'):raise ValueError('Wrong captured eligibility identity.')
    if value['policy_sha256']!=digest(value['policy']) or value['scope_sha256']!=digest({k:v for k,v in value.items() if k!='scope_sha256'}):raise ValueError('Corrupt eligibility digest.')
    if type(value['details_revision']) is not str or not re.fullmatch('[0-9a-f]{32,64}',value['details_revision']):raise ValueError('Missing profile-details revision.')
    ids=value['usable_ids']
    if type(ids) is not list or any(type(i) is not str or not i or len(i)>200 for i in ids) or ids!=sorted(set(ids)) or type(value['account_count']) is not int or not len(ids)<=value['account_count']<=100:raise ValueError('Invalid eligibility collection.')
    if type(value['account_source_sha256']) is not str or not re.fullmatch('[0-9a-f]{64}',value['account_source_sha256']):raise ValueError('Invalid eligibility source digest.')
    allowed=value['policy']['allowed'][value['gender_key']]
    if v2:
        from app.domain.value_objects import verified_garment_subtype as subtype
        subtype.registry(value['subtype_registry'])
        if value['policy']['version']!='wearer-category-policy-2.0.0':raise ValueError('Wrong subtype policy version.')
        sources=value['subtype_sources']
        if type(sources) is not list or len(sources)!=value['account_count']:raise ValueError('Incomplete subtype account source.')
        decisions={}
        for source in sources:
            subtype.validate_source(source);gid=source['subject_id']
            if source['owner_id']!=owner or gid in decisions:raise ValueError('Wrong subtype source owner.')
            decisions[gid]='Deny' if source['category'] not in allowed else subtype.decision(source['category'],value['gender_key'],source)
        if value['subtype_decisions']!=decisions or ids!=sorted(g for g,s in decisions.items() if s=='Permit'):raise ValueError('Corrupt captured subtype decisions.')
        for item in items:
            garment=item if isinstance(item,dict) else {'garment_id':item.garment.garment_id,'category':item.garment.category,'preferred_media_id':item.garment.preferred_media_id}
            source=next((s for s in sources if s['subject_id']==garment['garment_id']),None)
            if source is None or source['category']!=garment['category'] or source['media_id']!=garment.get('preferred_media_id'):raise ValueError('Wrong captured subtype member.')
    for item in items:
        gid=item['garment_id'] if isinstance(item,dict) else item.garment.garment_id
        category=item['category'] if isinstance(item,dict) else item.garment.category
        if gid not in ids or category not in allowed:raise ValueError('Selected member violates captured wearer eligibility.')
    return value

@dataclass(frozen=True)
class EligibilityWriteDraft:
    payload:str
    def __post_init__(self):
        value=json.loads(self.payload);validate_evidence(value,value['owner_id'],value['profile_id'])
        object.__setattr__(self,'payload',encode(value))
    def to_dict(self):return json.loads(self.payload)
