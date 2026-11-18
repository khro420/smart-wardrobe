"""Experimental immutable local intent. Not a legacy request, score or write draft."""
from dataclasses import dataclass
import re
from app.domain.value_objects.attribute_conditions import encode,decode,digest,exact,AttributeRequestError
from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.domain.value_objects.garment_description_evidence import CANONICAL_ENUMS
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.shared_contracts.isolated_soft_preference_grammar import GRAMMAR_VERSION,PROFILE,REGISTRY

CONTRACT='request-local-preference-intent-1.0.0'
class IsolatedPreferenceError(ValueError):
    def __init__(self,code,reason):self.code,self.reason=code,reason;super().__init__(reason)

def resolution_for(hard,role,binding,predicates):
    if binding['kind']=='explicit_role':
        if binding['group_id'] is not None:raise ValueError('Explicit role has no hard-group identifier.')
        return {'state':'Active','proof':[]}
    if binding['kind']!='mandatory_group' or hard is None:raise ValueError('Missing hard witness.')
    groups=hard.conditions.to_dict()['groups']
    selected=[g for g in groups if g['id']==binding['group_id']]
    if len(selected)!=1 or selected[0]['role']!=role or selected[0]['quantifier']!='exists':raise ValueError('Ambiguous hard witness.')
    proofs=[];entailed=[];conflict=[]
    for p in predicates:
        same=[c for c in selected[0]['conditions'] if c['attribute']==p['attribute'] and c['operator']=='in']
        yes=any(set(c['values'])<=set(p['values']) for c in same)
        no=any(set(c['values']).isdisjoint(p['values']) for c in same)
        entailed.append(yes);conflict.append(no)
        proofs.extend({'optional_id':p['id'],'hard_id':c['id'],'relation':'disjoint' if set(c['values']).isdisjoint(p['values']) else 'entailed'}
                      for c in same if set(c['values']).isdisjoint(p['values']) or set(c['values'])<=set(p['values']))
    state='ContradictedByHard' if any(conflict) else 'EntailedByHard' if all(entailed) else 'Active'
    return {'state':state,'proof':proofs if state!='Active' else []}

@dataclass(frozen=True)
class RequestLocalPreferenceIntent:
    payload:bytes

    def __post_init__(self):
        v=decode(self.payload);exact(v,('contract','profile','grammar_version','grammar_sha256','source_kind','original_text','mandatory_request','hard_intent','optional','qualification_policy_sha256','revision'))
        if (v['contract'],v['profile'],v['grammar_version'])!=(CONTRACT,PROFILE,GRAMMAR_VERSION) or v['grammar_sha256'] not in REGISTRY[GRAMMAR_VERSION]:raise ValueError('Unregistered isolated grammar/intent.')
        if v['source_kind'] not in ('nlp','isolated_typed_fixture') or type(v['original_text']) is not str or not v['original_text'].strip() or len(v['original_text'])>500:raise ValueError('Invalid original local request.')
        request=v['mandatory_request'];exact(request,('intent','occasion','style','colours','garment_categories','formality'))
        q=StructuredOutfitRequest(**request)
        if any(getattr(q,k) is not None for k in ('occasion','style','colours','garment_categories','formality')):raise IsolatedPreferenceError('SoftProfileUnavailable','Only pure non-contextual B1/neutral requests are isolated here.')
        hard=AttributeIntent.from_dict(v['hard_intent']) if v['hard_intent'] is not None else None
        if hard and (hard.to_dict()['original_text']!=v['original_text'] or hard.to_dict()['grammar_sha256']!=v['grammar_sha256']):raise ValueError('Hard intent lost original text/grammar binding.')
        o=v['optional'];exact(o,('role','quantifier','predicates','binding','spans','resolution'))
        if o['role'] not in ('upper','lower') or o['quantifier']!='exists':raise IsolatedPreferenceError('UnsupportedSoftPreference','Unsupported optional scope.')
        ps=o['predicates']
        if type(ps) is not list or not 1<=len(ps)<=2:raise IsolatedPreferenceError('UnsupportedSoftPreference','Exactly one bounded conjunctive wish is supported.')
        fields=[]
        for index,p in enumerate(ps,1):
            exact(p,('id','attribute','operator','values'));field=p['attribute'];fields.append(field)
            if p['id']!=f's{index:02d}' or field not in ('category','primary_colour') or p['operator']!='in' or type(p['values']) is not list or len(p['values'])!=1 or type(p['values'][0]) is not str or p['values'][0] not in CANONICAL_ENUMS[field]:raise IsolatedPreferenceError('UnsupportedSoftPreference','Only canonical category/named primary colour are supported.')
            if field=='category' and {'top':'upper','bottom':'lower','dress':'one_piece','outerwear':'outerwear'}[GARMENT_STRUCTURE[p['values'][0]][0]]!=o['role']:raise ValueError('Category/role mismatch.')
        if len(fields)!=len(set(fields)):raise ValueError('Duplicate optional axis.')
        exact(o['binding'],('kind','group_id'))
        if hard is not None and (o['binding']['kind']!='mandatory_group' or len(hard.conditions.to_dict()['groups'])!=1):raise ValueError('A unique hard witness must retain its anchor.')
        if hard is None and o['binding']['kind']!='explicit_role':raise ValueError('Unbound optional hard witness.')
        expected=resolution_for(hard,o['role'],o['binding'],ps)
        if o['resolution']!=expected:raise ValueError('Unproven soft conflict/entailment.')
        if type(o['spans']) is not list or len(o['spans'])>32:raise ValueError('Invalid local source spans.')
        targets={'marker','binding',*(p['id'] for p in ps)};covered=set()
        for span in o['spans']:
            exact(span,('target','start','end','text'));covered.add(span['target'])
            if span['target'] not in targets:raise ValueError('Foreign optional span.')
            if v['source_kind']=='isolated_typed_fixture':
                if any(span[k] is not None for k in ('start','end','text')):raise ValueError('Fixture input cannot invent NLP spans.')
            elif (type(span['start']) is not int or type(span['end']) is not int or not 0<=span['start']<span['end']<=len(v['original_text']) or v['original_text'][span['start']:span['end']]!=span['text']):raise ValueError('Local span does not address original text.')
        if not {p['id'] for p in ps}<=covered or v['source_kind']=='nlp' and not {'marker','binding'}<=covered:raise ValueError('Missing optional source/binding span.')
        if type(v['qualification_policy_sha256']) is not str or not re.fullmatch('[0-9a-f]{64}',v['qualification_policy_sha256']):raise ValueError('Missing source policy.')
        if v['revision']!=digest({**v,'revision':''}):raise ValueError('Changed local intent.')

    @classmethod
    def capture(cls,*,text,request,hard,grammar,role,predicates,binding,spans,policy,source_kind='nlp'):
        value={'contract':CONTRACT,'profile':PROFILE,'grammar_version':GRAMMAR_VERSION,'grammar_sha256':grammar,'source_kind':source_kind,'original_text':text,
         'mandatory_request':request.to_dict(),'hard_intent':hard.to_dict() if hard else None,
         'optional':{'role':role,'quantifier':'exists','predicates':predicates,'binding':binding,'spans':spans,'resolution':resolution_for(hard,role,binding,predicates)},
         'qualification_policy_sha256':policy.sha256,'revision':''}
        value['revision']=digest(value);return cls(encode(value))
    def to_dict(self):return decode(self.payload)
    @property
    def revision(self):return self.to_dict()['revision']
    @property
    def hard(self):
        value=self.to_dict()['hard_intent'];return AttributeIntent.from_dict(value) if value else None
