"""Owner-edit projection of existing reserved tags; no eligibility or inference."""
import hashlib
import json
from types import SimpleNamespace

from app.application.recommendation.suitability_policy import SuitabilityPolicy
from app.application.recommendation.suitability_evidence_mapper import SuitabilityEvidenceParser
from app.application.nlp.vocabulary import Vocabulary


def tag_revision(row):
    # Content precondition, not a timestamp or a claim of annotation provenance.
    def member(raw):
        try:
            obj=json.loads(raw) if raw is not None else {}
        except (ValueError,TypeError):
            return ['malformed',raw]
        return ['present','custom_tags' in obj,obj.get('custom_tags')] if isinstance(obj,dict) else ['invalid',raw]
    basis=[row['id'],row['user_id'],row['custom_tags'],member(row['attributes_json']),member(row['additional_attributes'])]
    return '"tags-v1-'+hashlib.sha256(json.dumps(basis,sort_keys=True,separators=(',',':')).encode()).hexdigest()+'"'


def tag_edit_view(row,data):
    policy=SuitabilityPolicy.load()
    extra=data.get('additional_attributes')
    attrs={**(extra if isinstance(extra,dict) else {}),**(data['attributes'] if isinstance(data['attributes'],dict) else {})}
    raw=data['custom_tags'] if data['custom_tags'] is not None else attrs.get('custom_tags')
    tags=[raw] if isinstance(raw,str) else raw
    invalid=tags is not None and (not isinstance(tags,list) or any(not isinstance(t,str) or not t.strip() for t in tags))
    parser=SuitabilityEvidenceParser(policy)
    projected=None if tags is None or invalid else tuple(dict.fromkeys(t.strip() for t in tags))
    evidence=parser.parse(SimpleNamespace(garment_id=row['id'],custom_tags=projected,invalid_attributes=('custom_tags',) if invalid else ()))
    raw_tags=[] if tags is None or invalid else tags
    reserved=[];malformed=[]
    for index,text in enumerate(raw_tags):
        if not text.strip().casefold().startswith('rec:'):continue
        reserved.append(index)
        item=parser.parse(SimpleNamespace(garment_id=row['id']+':'+str(index),custom_tags=(text.strip(),),invalid_attributes=()))
        if item.malformed_fields:
            malformed.append({'index':index,'fields':list(item.malformed_fields)})
    declarations=[]
    for field in ('occasion','formality'):
        for value in policy.values(field):
            decisions={d.decision for d in evidence.declarations if d.field==field and d.value==value}
            state=evidence.state_for(field,value)
            declarations.append({'field':field,'value':value,'label':value.replace('_',' ').capitalize(),
                'choice':{'Pass':'allow','Fail':'deny','Unknown':'unknown'}[state],
                'state':state,'conflict':decisions=={'allow','deny'},'malformed':field in evidence.malformed_fields,
                'allow_tag':f'{policy.reserved_prefix}:{field}:{value}:allow',
                'deny_tag':f'{policy.reserved_prefix}:{field}:{value}:deny'})
    return {'version':policy.version,'revision':tag_revision(row),'editable':not invalid,
        'tags':raw_tags,'reserved_indices':reserved,'ordinary_tags':[t for i,t in enumerate(raw_tags) if i not in reserved],
        'declarations':declarations,'malformed':malformed,'source_state':evidence.source_state,
        'colour_names':sorted(Vocabulary.load().values['colours'])}
