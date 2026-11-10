"""Closed source-qualified product identities, separate from extracted attributes."""
from pathlib import Path
import hashlib,json,re
VERSION='verified-garment-subtypes-1.0.0'
SOURCE_VERSION='verified-garment-subtype-evidence-1.0.0'
EVENT_VERSION='garment-subtype-event-1.0.0'
PROFILE='verified_subtype_v1'
ENVIRONMENT_KEY='SMART_WARDROBE_VERIFIED_SUBTYPE_PROFILE'
PARENTS=('short_sleeve_top','long_sleeve_top')
VALUES=('t_shirt','polo_shirt','button_up_shirt','knit_top','blouse')
RESOURCE=Path(__file__).with_name('config')/'verified_garment_subtypes.v1.json'
RESOURCE_SHA256='7f5277a118ff6a80c8b4c3bff887ba114aec8e2101e64cc280c4f459100de868'
EVENT_FIELDS=frozenset('contract event_id owner_id subject_kind subject_id wearer_profile_id action_id ordinal prior_revision revision event_kind state subtype category media_id source_binding_sha256 registry_version registry_sha256 origin contributor recorded_at review_basis reason transfer_source unresolved_restriction'.split())
def encode(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(v):return hashlib.sha256(encode(v).encode()).hexdigest()
def _pairs(pairs):
    result={}
    for k,v in pairs:
        if k in result:raise ValueError('Duplicate subtype key.')
        result[k]=v
    return result
def decode(raw,limit=16384):
    if type(raw) is not str or len(raw.encode())>limit:raise ValueError('Subtype data exceeds bound.')
    return json.loads(raw,object_pairs_hook=_pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite subtype data.')))
def registry(value=None):
    if value is None:
        raw=RESOURCE.read_bytes()
        if len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=RESOURCE_SHA256:raise ValueError('Unregistered subtype vocabulary.')
        value=decode(raw.decode(),65536)
    if digest(value)!='d4975ffc53e0f1177e4e2c942e864c58d7c16ce470f4394d6c2165d5cf02605a':raise ValueError('Unregistered captured subtype vocabulary.')
    if value['contract']!=VERSION or value['model_emitters']!=[] or value['measured_emitters']!=[]:raise ValueError('Unsupported subtype emitter.')
    return value
def validate_event(event):
    if type(event) is not dict or set(event)!=EVENT_FIELDS or len(encode(event).encode())>16384:raise ValueError('Invalid subtype event fields.')
    if event['contract']!=EVENT_VERSION or event['registry_version']!=VERSION or event['registry_sha256']!=RESOURCE_SHA256:raise ValueError('Unregistered subtype event.')
    if event['revision']!=digest({k:v for k,v in event.items() if k!='revision'}):raise ValueError('Corrupt subtype event.')
    for field in ('event_id','owner_id','subject_id','wearer_profile_id','action_id','contributor','recorded_at'):
        if type(event[field]) is not str or not event[field] or len(event[field])>200:raise ValueError('Invalid subtype identity.')
    if event['subject_kind'] not in ('garment','processing_item') or event['contributor']!=event['owner_id']:raise ValueError('Invalid subtype source authority.')
    if type(event['ordinal']) is not int or event['ordinal']<1 or event['origin']!='owner_selected':raise ValueError('Invalid subtype source.')
    if event['event_kind'] not in ('owner_confirm','owner_unspecified','owner_correction','owner_category_resolution','system_transfer'):raise ValueError('Unknown subtype event kind.')
    if event['state'] not in ('Known','Unspecified','Inapplicable') or event['review_basis'] not in ('owner_review','synthetic_fixture_declaration'):raise ValueError('Invalid subtype review.')
    if event['state']=='Known':
        if event['subtype'] not in VALUES or event['category'] not in PARENTS:raise ValueError('Subtype not applicable.')
    elif event['subtype'] is not None:raise ValueError('Unqualified subtype must be null.')
    if event['state']=='Inapplicable' and event['category'] in PARENTS:raise ValueError('Subtype review still applicable.')
    if type(event['reason']) is not str or len(event['reason'])>500 or not event['reason'].strip():raise ValueError('Review reason required.')
    if event['unresolved_restriction'] not in (None,'blouse'):raise ValueError('Invalid retained restriction.')
    if not re.fullmatch('[0-9a-f]{64}',event['source_binding_sha256']):raise ValueError('Invalid subtype source binding.')
    return event
def binding(row,owner):
    row=dict(row);attrs=row.get('attributes') or decode(row.get('attributes_json') or '{}',1048576)
    category=row.get('category') or attrs.get('reviewed_category') or row.get('detected_category')
    description=attrs.get('garment_description_evidence_v1') or {}
    return digest({'contract':'subtype-current-source-binding-1.0.0','owner_id':owner,'subject_id':row['id'],'category':category,'media_id':row.get('preferred_media_id'),'reviewed_category':attrs.get('reviewed_category'),'garment_type':attrs.get('garment_type'),'layering_index':attrs.get('layering_index'),'category_evidence':description.get('fields',{}).get('category')})
def project(row,owner,events):
    row=dict(row);attrs=row.get('attributes') or decode(row.get('attributes_json') or '{}',1048576)
    category=row.get('category') or attrs.get('reviewed_category') or row.get('detected_category')
    result={'version':SOURCE_VERSION,'owner_id':owner,'subject_id':row['id'],'category':category,'media_id':row.get('preferred_media_id'),'state':'Absent' if category in PARENTS else 'Inapplicable','value':None,'revision':None,'source_binding_sha256':binding(row,owner),'events':events}
    previous=None
    for ordinal,event in enumerate(events,1):
        validate_event(event)
        if event['owner_id']!=owner or event['subject_id']!=row['id'] or event['ordinal']!=ordinal or event['prior_revision']!=previous:raise ValueError('Broken subtype owner/event chain.')
        previous=event['revision']
    if events:
        head=events[-1];result.update(state=head['state'],value=head['subtype'],revision=head['revision'])
        if head['source_binding_sha256']!=result['source_binding_sha256']:result.update(state='Stale',value=None)
        if head['unresolved_restriction'] and (result['state']!='Known' or result['value']!='blouse'):result.update(state='Stale',value=None)
    return result

def validate_source(value):
    if type(value) is not dict or set(value)!={'version','owner_id','subject_id','category','media_id','state','value','revision','source_binding_sha256','events'} or value['version']!=SOURCE_VERSION:raise ValueError('Invalid subtype source fields.')
    events=value['events'];previous=None
    if type(events) is not list or len(encode(value).encode())>262144:raise ValueError('Unbounded subtype source.')
    for ordinal,event in enumerate(events,1):
        validate_event(event)
        if event['owner_id']!=value['owner_id'] or event['subject_id']!=value['subject_id'] or event['ordinal']!=ordinal or event['prior_revision']!=previous:raise ValueError('Invalid subtype source chain.')
        previous=event['revision']
    if value['revision']!=previous:raise ValueError('Invalid subtype source revision.')
    if not events:
        expected='Absent' if value['category'] in PARENTS else 'Inapplicable'
        if value['state']!=expected or value['value'] is not None:raise ValueError('Unrecorded subtype cannot be qualified.')
    else:
        head=events[-1]
        current=head['source_binding_sha256']==value['source_binding_sha256'] and head['category']==value['category'] and head['media_id']==value['media_id']
        state=head['state'] if current else 'Stale';subtype=head['subtype'] if current else None
        if head['unresolved_restriction'] and (state!='Known' or subtype!='blouse'):state,subtype='Stale',None
        if (value['state'],value['value'])!=(state,subtype):raise ValueError('Subtype qualification mismatch.')
    return value
def decision(category,gender,source):
    validate_source(source)
    if source['category']!=category:raise ValueError('Subtype category mismatch.')
    if gender=='female':return 'Permit'
    if category in PARENTS:
        if source['state']!='Known':return 'Unknown'
        return 'Deny' if source['value']=='blouse' else 'Permit'
    if source['state']=='Stale' and any(e['subtype']=='blouse' or e['unresolved_restriction']=='blouse' for e in source['events']):return 'Unknown'
    return 'Permit'
