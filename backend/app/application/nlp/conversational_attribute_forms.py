"""Closed exclusion/contrast frames. Every span addresses the original text.

No inferred fit synonyms, evidence, new attributes, or scoring live here.
"""
import re

from app.application.nlp.attribute_request_interpreter import AttributeInterpretation
from app.application.nlp.request_field_extractor import RequestFieldExtractor
from app.domain.value_objects.attribute_conditions import AttributeConditions, AttributeRequestError, CANONICAL_ENUMS

VERSION='conversational-bounded-attribute-forms-1.0.0'
DESCRIPTORS=(
    (r'stripe[\s-]+patterned|stripes','pattern','stripe'),
    (r'checked|checkered','pattern','check'),
    (r'polka[\s-]+dots?','pattern','dot'),
    (r'regular[\s-]+(?:fit|fitting)','silhouette','regular'),
    (r'short[\s-]+sleeve(?:d|s)?','sleeve_length','short'),
    (r'sleeveless','sleeve_length','sleeveless'),
)
NEGATIVE=re.compile(r"\s*(?:please\s+)?(?P<prefix>(?:i\s+)?(?:do\s+not|don['\u2019]?t)\s+(?:give\s+me|want(?:\s+to\s+wear)?|include)|no|avoid|anything\s+except)\s+(?:any\s+)?(?P<target>.+?)(?:\s*,?\s*please)?[.!?]*\s*",re.I)
CONTRAST=re.compile(r',\s*(?:but\s+)?not\s+|\s+instead\s+of\s+|(?:,\s*|\s+)but\s+no\s+',re.I)


def connector_spans(original):
    """License only connector tokens in a bounded frame, not arbitrary prose."""
    from app.application.nlp.conversational_context_interpreter import outside_literals
    if type(original) is not str or len(original)>500:return ()
    text=outside_literals(original)
    negative=NEGATIVE.fullmatch(text)
    if negative:
        return tuple(m.span() for m in re.finditer(r'\bexcept\b',text[:negative.end('prefix')],re.I))
    links=list(CONTRAST.finditer(text))
    if len(links)==1:
        return tuple((links[0].start()+m.start(),links[0].start()+m.end())
                     for m in re.finditer(r'\binstead\b',links[0].group(),re.I))
    return ()


def _merge(original,parts,remaining,grammar_hash):
    groups=[];spans=[];index=0;subtype=False
    for source_groups,source_spans in parts:
        for group in source_groups:
            conditions=[]
            for condition in group['conditions']:
                index+=1;cid=f'c{index:02d}';old=condition['id']
                conditions.append({**condition,'id':cid})
                subtype|=condition['attribute']=='verified_subtype'
                spans.extend((cid,src,a,b,original[a:b]) for prior,src,a,b,_ in source_spans if prior==old)
            groups.append({**group,'id':f'g{len(groups)+1:02d}','conditions':conditions})
    value={'version':'attribute-conditions-2.0.0' if subtype else 'attribute-conditions-1.0.0','groups':groups}
    return AttributeInterpretation(AttributeConditions.from_dict(value),remaining,tuple(spans),grammar_hash)


def _harmless(grammar,remaining):
    for pattern in grammar.language['function_frames']:remaining=re.sub(pattern,' ',remaining,flags=re.I)
    return set(re.findall(r"[\w']+",remaining.lower()))<=RequestFieldExtractor.GLUE|{'any'}


def parse_bounded(grammar,original):
    from app.application.nlp.conversational_context_interpreter import outside_literals
    text=outside_literals(original)
    # This is unsupported sleeve wording, not a request for three outfits.
    # Keep the canonical short/elbow-length/wrist-length meanings unchanged.
    if re.search(r'\bthree[\s-]+quarter[\s-]+sleeve(?:d|s)?\b',text,re.I):
        raise AttributeRequestError('UnsupportedAttributeValue','unsupported_sleeve_mapping')
    if re.search(r'\b(?:slim|relaxed)[\s-]+(?:fit|fitting)\b',text,re.I):
        raise AttributeRequestError('UnsupportedAttributeValue','unsupported_fit_mapping')
    if re.fullmatch(r"\s*(?:please\s+)?(?:(?:give\s+me|i\s+(?:need|want)|recommend|suggest)\s+)?something\s+(?:smart\s+casual|formal)[.!?]*\s*",text,re.I):
        raise AttributeRequestError('UnsupportedRequest','outfit_style_scope_required')

    negative=NEGATIVE.fullmatch(text)
    if negative:
        target=negative['target'].strip().lower()
        field=role=value=None
        if target in ('shorts','trousers','pants','skirt'):
            field,role,value='category','lower','trousers' if target=='pants' else target
        elif re.fullmatch(r'sleeveless\s+(?:clothes|clothing|garments)',target):
            field,role,value='sleeve_length','all_selected','sleeveless'
        else:
            material=re.sub(r'\s+(?:clothes|clothing|garments)$','',target)
            if material in CANONICAL_ENUMS['material']:field,role,value='material','all_selected',material
        if field:
            a,b=negative.span('target')
            condition={'id':'c01','attribute':field,'operator':'contains_any' if field=='material' else 'in','values':[value]}
            group={'id':'g01','role':role,'quantifier':'none','conditions':[condition]}
            spans=[('c01','nlp',a,b,original[a:b]),('c01','nlp',*negative.span('prefix'),original[slice(*negative.span('prefix'))])]
            return _merge(original,[([group],spans)],' '*len(original),grammar.sha256)
        known=any(target in values for values in CANONICAL_ENUMS.values())
        if 'except' in negative['prefix'].lower() or 'give' in negative['prefix'].lower() or re.fullmatch(r'[\w-]+',target) and not known:
            raise AttributeRequestError('UnsupportedAttributeValue','unsupported_exclusion_target')

    links=list(CONTRAST.finditer(text))
    if len(links)>1:raise AttributeRequestError('UnsupportedRequest','ambiguous_garment_reference')
    if not links:
        if re.search(r'\bones\b|\bone\b(?=\s*[.!?]*\s*$)',text,re.I):
            raise AttributeRequestError('UnsupportedRequest','ambiguous_garment_reference')
        return None
    link=links[0]
    # Existing unscoped scalar negation ("something casual, not sporty")
    # already has a registered meaning. It is not a pronoun/type contrast.
    scalar=text[link.end():].strip(' \t\r\n.!?')
    if 'instead' not in link.group().lower() and 'no' not in link.group().lower().split() and any(p.fullmatch(scalar) for p,_,_ in grammar.descriptors):
        return None
    left=grammar.parse(original[:link.start()])
    if left.conditions is None or not _harmless(grammar,left.remaining):
        raise AttributeRequestError('UnsupportedRequest','ambiguous_garment_reference')
    left_groups=left.conditions.to_dict()['groups']
    if len(left_groups)!=1 or left_groups[0]['quantifier']!='exists' or left_groups[0]['role'] not in ('upper','lower','one_piece','outerwear'):
        raise AttributeRequestError('UnsupportedRequest','ambiguous_garment_reference')
    right_text=original[link.end():];right_plain=text[link.end():]
    pronoun=re.fullmatch(r'\s*(?:an?\s+)?(?P<descriptor>.+?)\s+(?P<noun>ones?)\s*[.!?]*\s*',right_plain,re.I)
    if pronoun:
        a,b=pronoun.span('descriptor')
        matches={(field,value) for pattern,field,value in grammar.descriptors if pattern.fullmatch(right_plain,a,b)}
        if len(matches)!=1:raise AttributeRequestError('UnsupportedRequest','ambiguous_garment_reference')
        field,value=matches.pop()
        condition={'id':'c01','attribute':field,'operator':'contains_any' if field in ('style','material') else 'in','values':[value]}
        group={'id':'g01','role':left_groups[0]['role'],'quantifier':'none','conditions':[condition]}
        start,end=a+link.end(),b+link.end()
        spans=[('c01','nlp',start,end,original[start:end]),('c01','nlp',pronoun.start('noun')+link.end(),pronoun.end('noun')+link.end(),pronoun['noun'])]
        # Copy only the antecedent's category/type identity, never its adjectives.
        for category in left_groups[0]['conditions']:
            if category['attribute'] not in ('category','verified_subtype'):continue
            cid=f'c{len(group["conditions"])+1:02d}'
            group['conditions'].append({**category,'id':cid})
            spans.extend((cid,src,x,y,raw) for prior,src,x,y,raw in left.spans if prior==category['id'])
        right_groups,right_spans=[group],spans
    else:
        right=grammar.parse(right_text)
        if right.conditions is None or not _harmless(grammar,right.remaining):
            raise AttributeRequestError('UnsupportedRequest','ambiguous_garment_reference')
        right_groups=right.conditions.to_dict()['groups']
        if len(right_groups)!=1 or right_groups[0]['quantifier']!='exists':
            raise AttributeRequestError('UnsupportedRequest','ambiguous_garment_reference')
        if 'instead' in link.group().lower():
            if right_groups[0]['role']!=left_groups[0]['role']:
                raise AttributeRequestError('UnsupportedRequest','contrasting_garment_scope')
            for field in ('category','verified_subtype'):
                lhs=[c['values'] for c in left_groups[0]['conditions'] if c['attribute']==field]
                rhs=[c['values'] for c in right_groups[0]['conditions'] if c['attribute']==field]
                if lhs and rhs and lhs!=rhs:raise AttributeRequestError('UnsupportedRequest','contrasting_garment_scope')
        right_groups[0]['quantifier']='none'
        right_spans=[(cid,src,a+link.end(),b+link.end(),raw) for cid,src,a,b,raw in right.spans]
    return _merge(original,[(left_groups,left.spans),(right_groups,right_spans)],' '*len(original),grammar.sha256)
