"""Closed clause algebra over existing B1 facts; every clause must be consumed."""
from dataclasses import dataclass
from pathlib import Path
import re
from app.application.nlp.compositional_input_v1 import normalize
from app.application.nlp.natural_input_v1 import original_span
from app.application.nlp.normalized_request_v1 import base_parse
from app.domain.value_objects.attribute_conditions import AttributeConditions,AttributeRequestError,encode,decode,digest,exact
from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.domain.value_objects.garment_description_evidence import CANONICAL_ENUMS
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.domain.value_objects.request_local_preference import resolution_for

GRAMMAR='conversational-compositional-grammar-1.9.0'
VERSION='compositional-request-intent-1.0.0'
ENVIRONMENT_KEY='SMART_WARDROBE_ASSISTANT_COMPOSITION_PROFILE'
PROFILE='bounded_compositional_input_v1'
MAX_INTENT=98304
COLOURS=tuple(CANONICAL_ENUMS['primary_colour'])
NOUNS={'shirt':('upper',None),'top':('upper',None),'trousers':('lower','trousers'),
       'shorts':('lower','shorts'),'skirt':('lower','skirt'),'jeans':('lower','trousers'),
       'vest':('upper','vest'),'sling':('upper','sling')}

def fingerprint():
    from app.shared_contracts.grammar_identity import semantic_fingerprint
    from app.application.nlp import compositional_input_v1
    from app.application.nlp.normalized_request_v1 import identity as frozen_normalization
    return semantic_fingerprint((GRAMMAR.encode(),bytes.fromhex(frozen_normalization()),Path(__file__).read_bytes(),Path(compositional_input_v1.__file__).read_bytes(),encode(COLOURS)))

def identity():
    from app.shared_contracts.compositional_grammar_registry import GRAMMAR_SHA256
    if fingerprint()!=GRAMMAR_SHA256:raise ValueError('Unregistered compositional grammar.')
    return GRAMMAR_SHA256

def refuse(reason='unsupported_compositional_clause'):
    raise AttributeRequestError('UnsupportedRequest',reason)

def parse(text,grammar):
    """Return complete request, conditions, normalized spans and one optional wish.

    Existing condition values are OR sets; groups/conditions remain conjunctive.
    A negative group negates its entire same-member conjunction.
    """
    groups=[];spans=[];optional=None;clauses=[];previous=None;request=StructuredOutfitRequest().to_dict()
    # Never split quoted text or interpret arbitrary literals as clause syntax.
    if '"' in text:refuse('compositional_literal_scope_unavailable')
    if re.search(r'\b(?:not too formal|less formal|more formal|flashy|stylish|comfy)\b',text):refuse('unmodeled_compositional_modifier')
    # Soft markers split even without a comma; connectors otherwise retain a
    # full clause. OR is handled inside one target, not by branch selection.
    cuts=list(re.finditer(r'\s*[,;]\s*|\s+\b(?:and|but|rather than|instead of)\b\s+|\s+(?=preferably\b)',text))
    parts=[];start=0;connector='start'
    for link in cuts:
        parts.append((start,link.start(),connector));connector=link[0].strip(' ,;');start=link.end()
    parts.append((start,len(text),connector))
    def add(source_groups,source_spans,negative=False):
        nonlocal previous
        added=[]
        for g in source_groups:
            conditions=[]
            for c in g['conditions']:
                cid=f'c{sum(len(x["conditions"]) for x in groups)+len(conditions)+1:02d}'
                conditions.append({**c,'id':cid})
                spans.extend({'condition_id':cid,'source':'nlp','start':a,'end':b,'text':text[a:b]} for old,a,b in source_spans if old==c['id'])
            group={**g,'id':f'g{len(groups)+1:02d}','quantifier':'none' if negative else g['quantifier'],'conditions':conditions}
            groups.append(group);added.append(group)
        if not negative and len(added)==1 and added[0]['quantifier']=='exists':previous=added[0]
        return added
    def target(phrase,a,negative=False,antecedent=None):
        # Closed OR sets: colours with one noun, or same-role category names.
        names='|'.join(sorted(NOUNS,key=len,reverse=True));colours='|'.join(COLOURS)
        phrase=re.sub(r'^(?:a|an|any)\s+','',phrase)
        # Prefix trim above must update the source offset, never invent spans.
        a=text.find(phrase,a)
        post=re.fullmatch(r'(?P<noun>'+names+r")\s+that(?:'s| is)\s+(?:either\s+)?(?P<left>"+colours+r')\s+or\s+(?P<right>'+colours+r')',phrase)
        pre=re.fullmatch(r'(?:either\s+)?(?P<left>'+colours+r')\s+or\s+(?P<right>'+colours+r')\s+(?P<noun>'+names+r')',phrase)
        choice=post or pre
        if choice:
            noun=choice['noun'];role,category=NOUNS[noun]
            if noun=='jeans':refuse('compositional_or_jeans_scope_unavailable')
            cs=[{'id':'c01','attribute':'primary_colour','operator':'in','values':sorted(set((choice['left'],choice['right'])))}]
            ss=[('c01',a+choice.start(p),a+choice.end(p)) for p in ('left','right')]
            if category:
                cs.append({'id':'c02','attribute':'category','operator':'in','values':[category]});ss.append(('c02',a+choice.start('noun'),a+choice.end('noun')))
            return [{'id':'g01','role':role,'quantifier':'exists','conditions':cs}],ss
        categories=re.fullmatch(r'(?P<left>trousers|shorts|skirt)\s+or\s+(?P<right>trousers|shorts|skirt)',phrase)
        if categories:
            cs=[{'id':'c01','attribute':'category','operator':'in','values':sorted(set((categories['left'],categories['right'])))}]
            return [{'id':'g01','role':'lower','quantifier':'exists','conditions':cs}],[('c01',a+categories.start(p),a+categories.end(p)) for p in ('left','right')]
        if ' or ' in phrase:refuse('ambiguous_compositional_or_scope')
        pronoun=re.fullmatch(r'(?P<colour>'+colours+r')\s+ones?',phrase)
        if pronoun:
            if antecedent is None:refuse('ambiguous_compositional_antecedent')
            cs=[{'id':'c01','attribute':'primary_colour','operator':'in','values':[pronoun['colour']]}]
            ss=[('c01',a+pronoun.start('colour'),a+pronoun.end('colour'))]
            # A pronoun retains category identity, not its former adjectives.
            for c in antecedent['conditions']:
                if c['attribute']=='category':
                    cid=f'c{len(cs)+1:02d}';cs.append({**c,'id':cid})
                    ss.extend((cid,s['start'],s['end']) for s in spans if s['condition_id']==c['id'])
            return [{'id':'g01','role':antecedent['role'],'quantifier':'exists','conditions':cs}],ss
        if negative and phrase in COLOURS:
            return [{'id':'g01','role':'all_selected','quantifier':'exists','conditions':[{'id':'c01','attribute':'primary_colour','operator':'in','values':[phrase]}]}],[('c01',a,a+len(phrase))]
        parsed=base_parse('I need '+phrase)
        if 'context' in parsed['request'] or any(parsed['request'][k] is not None for k in ('occasion','style','colours','garment_categories','formality')) or parsed['local'] is not None or parsed['hard'] is None:refuse('unrepresentable_compositional_target')
        hard=parsed['hard']
        ss=[]
        for s in hard['spans']:
            if s['source']!='nlp' or s['start']<7 or s['end']>7+len(phrase):refuse('invalid_compositional_target_span')
            ss.append((s['condition_id'],s['start']-7+a,s['end']-7+a))
        return hard['conditions']['groups'],ss
    for a,b,link in parts:
        raw=text[a:b];left=len(raw)-len(raw.lstrip());body=raw.strip().rstrip('.!?').strip();a+=left
        if not body:refuse('empty_compositional_clause')
        # Finite function words are licensed only at clause boundaries.
        prefix=re.match(r'(?:please\s+)?(?:(?:i (?:need|want)(?: to wear)?|give me|suggest|recommend|(?:i am |i\'m )?looking for|find me)\s+)?(?:please\s+)?',body)
        negative=re.match(r"(?:(?:i )?(?:do not|don't) (?:give me|want(?: to wear)?|include)|no|not|avoid|anything except)\s+(?:any\s+|anything\s+)?",body)
        soft=re.match(r"(?P<marker>(?:i'd|i) prefer|preferably)\s+",body)
        if body.endswith(' please'):body=body[:-7]
        if body.endswith(' instead'):
            if not groups or not any(g['quantifier']=='none' for g in groups):refuse('unbound_compositional_instead')
            body=body[:-8]
        start=a;kind='hard';binding=None
        if soft:
            if optional is not None:refuse('multiple_compositional_preferences')
            kind='optional';at=a+soft.end();wish=body[soft.end():]
            if soft['marker']=='preferably':
                if previous is None or wish not in COLOURS:refuse('ambiguous_compositional_soft_binding')
                role=previous['role'];binding={'kind':'mandatory_group','group_id':previous['id']}
                if role not in ('upper','lower'):refuse('ambiguous_compositional_soft_binding')
                predicates=[{'id':'s01','attribute':'primary_colour','operator':'in','values':[wish]}]
                os=[{'target':'marker','start':a,'end':a+soft.end('marker'),'text':text[a:a+soft.end('marker')]},
                    {'target':'binding','start':at,'end':at+len(wish),'text':wish},{'target':'s01','start':at,'end':at+len(wish),'text':wish}]
            else:
                gs,ss=target(wish,at)
                if len(gs)!=1 or gs[0]['role'] not in ('upper','lower') or gs[0]['quantifier']!='exists' or any(c['attribute'] not in ('category','primary_colour') or len(c['values'])!=1 for c in gs[0]['conditions']):refuse('unsupported_compositional_preference')
                role=gs[0]['role'];binding={'kind':'explicit_role','group_id':None};predicates=[]
                os=[{'target':'marker','start':a,'end':a+soft.end('marker'),'text':text[a:a+soft.end('marker')]},{'target':'binding','start':at,'end':at+len(wish),'text':wish}]
                for c in gs[0]['conditions']:
                    cid=f's{len(predicates)+1:02d}';predicates.append({**c,'id':cid})
                    os.extend({'target':cid,'start':x,'end':y,'text':text[x:y]} for old,x,y in ss if old==c['id'])
            optional={'role':role,'quantifier':'exists','predicates':predicates,'binding':binding,'spans':os}
        else:
            neg=negative is not None or link in ('instead of','rather than')
            if negative:at=a+negative.end();wish=body[negative.end():]
            else:
                at=a+prefix.end();wish=body[prefix.end():]
                if not wish:refuse('empty_compositional_target')
            # Existing complete neutral/context/style sentences retain their
            # original parser contract. Context cannot enter the P1/C1 proof.
            if not neg and not groups and optional is None and len(parts)==1:
                try:whole=base_parse(body)
                except AttributeRequestError:whole=None
                if whole is not None:
                    if 'context' in whole['request']:return whole['request'],whole['hard'],None,[{'kind':'context','start':a,'end':a+len(body),'text':body}]
                    if whole['local'] is None and whole['hard'] is None:return whole['request'],None,None,[{'kind':'ordinary','start':a,'end':a+len(body),'text':body}]
            gs,ss=target(wish,at,negative=neg,antecedent=previous)
            add(gs,ss,negative=neg);kind='negative' if neg else 'hard'
        clauses.append({'kind':kind,'connector':link,'start':start,'end':a+len(body),'text':text[start:a+len(body)]})
    conditions=AttributeConditions.from_dict({'version':'attribute-conditions-1.0.0','groups':groups}) if groups else None
    policy=AttributeEvidencePolicy.load()
    hard=AttributeIntent.capture(text,None,conditions,spans,grammar,policy.sha256) if conditions else None
    if optional:
        # Explicit upper/lower wishes may coexist with unrelated hard groups.
        # For a unique same-role positive witness, retain its existing conflict
        # and entailment semantics instead of promoting a conflicting wish.
        positives=[g for g in groups if g['quantifier']=='exists' and g['role']==optional['role']]
        if optional['binding']['kind']=='explicit_role' and len(positives)==1:optional['binding']={'kind':'mandatory_group','group_id':positives[0]['id']}
        optional['resolution']=resolution_for(hard,optional['role'],optional['binding'],optional['predicates'])
    return request,hard.to_dict() if hard else None,optional,clauses

def document(raw):
    grammar=identity();mapping=normalize(raw);request,hard,optional,clauses=parse(mapping['normalized_text'],grammar)
    value={'version':VERSION,'grammar_version':GRAMMAR,'grammar_sha256':grammar,'normalization':mapping,
        'request':request,'hard_intent':hard,'optional':optional,'clauses':clauses,
        'original_hard_spans':[{**s,**original_span(mapping,s['start'],s['end'])} for s in hard['spans']] if hard else [],
        'original_optional_spans':[{**s,**original_span(mapping,s['start'],s['end'])} for s in optional['spans']] if optional else [],'revision':''}
    value['revision']=digest(value);return value

@dataclass(frozen=True)
class CompositionalIntent:
    payload:bytes
    def __post_init__(self):
        v=decode(self.payload,MAX_INTENT)
        exact(v,('version','grammar_version','grammar_sha256','normalization','request','hard_intent','optional','clauses','original_hard_spans','original_optional_spans','revision'))
        if v!=document(v['normalization']['original_text']):raise ValueError('Compositional interpretation/provenance mismatch.')
    @classmethod
    def capture(cls,raw):return cls(encode(document(raw)))
    def to_dict(self):return decode(self.payload,MAX_INTENT)
    @property
    def raw(self):return self.to_dict()['normalization']['original_text']
    @property
    def normalized(self):return self.to_dict()['normalization']['normalized_text']
    @property
    def revision(self):return self.to_dict()['revision']
