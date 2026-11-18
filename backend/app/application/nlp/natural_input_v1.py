"""Bounded deterministic text edits. Never used by historical parsers implicitly."""
import re
from app.domain.value_objects.attribute_conditions import AttributeRequestError

VERSION='raw-normalized-span-map-1.0.0'

def normalize(raw):
    if type(raw) is not str or not raw.strip() or len(raw)>500 or any(ord(c)<32 and c not in '\r\n\t' for c in raw):
        raise AttributeRequestError('InvalidInput','invalid_normalized_input')
    atoms=[(c,i,i+1) for i,c in enumerate(raw)];edits=[]
    def text():return ''.join(c for c,_,_ in atoms)
    def apply(pattern,replacement,rule,flags=0):
        nonlocal atoms
        value=text()
        protected=[(m.start(),m.end()) for m in re.finditer(r'"(?:[^"\\]|\\.)*"',value)]
        for match in reversed(list(re.finditer(pattern,value,flags))):
            a,b=match.span()
            if any(a<end and b>start for start,end in protected):continue
            before=value[a:b];after=replacement(match) if callable(replacement) else replacement
            if before==after:continue
            selected=atoms[a:b];start=min((x[1] for x in selected),default=atoms[a-1][2] if a else 0)
            end=max((x[2] for x in selected),default=start)
            edits.append({'rule':rule,'raw_start':start,'raw_end':end,'raw_text':raw[start:end],
                          'stage_start':a,'stage_end':b,'before':before,'after':after})
            mapped=[(c,start,end) for c in after]
            if len(before)==len(after):mapped=[(c,atoms[a+i][1],atoms[a+i][2]) for i,c in enumerate(after)]
            atoms[a:b]=mapped
    # Only double-quoted literal spans are protected; apostrophes are words.
    if raw.count('"')%2:raise AttributeRequestError('UnsupportedRequest','unclosed_literal')
    apply(r"[A-Z\u2018\u2019]+",lambda m:m[0].lower().replace('\u2018',"'").replace('\u2019',"'"),'case_apostrophe')
    apply(r'\s+',' ','spacing')
    apply(r'^ +| +$','','outer_spacing')
    # Abbreviations have closed lexical meanings, not fuzzy neighbours.
    aliases={'pls':'please','plz':'please','smth':'something','gimme':'give me','wanna':'want to',
             'dont':"don't",'cant':"can't",'wont':"won't",'isnt':"isn't",'gray':'grey',
             'pants':'trousers','trouser':'trousers','troussers':'trousers'}
    apply(r'\b('+ '|'.join(aliases)+r')\b',lambda m:aliases[m[0]],'closed_token_alias')
    # 'ur' can mean your/you are. Bare id/im/u are not globally expanded.
    outside=re.sub(r'"(?:[^"\\]|\\.)*"',' ',text())
    if re.search(r'\bur\b',outside):raise AttributeRequestError('UnsupportedRequest','ambiguous_normalized_contraction')
    apply(r'\b(can|could|would) u\b',lambda m:m[1]+' you','polite_you')
    apply(r'^(?:(hey|hi),? )?id (?=prefer\b|like\b)',lambda m:((m[1]+', ') if m[1] else '')+"i'd ",'subject_id')
    apply(r'^im (?=going\b|heading\b)',"i'm ",'subject_im')
    # Preserve all body words. A finite wrapper may be masked by the base parser.
    apply(r'^(hey|hi) (?=(?:can|could) you\b|please\b)',lambda m:m[1]+', ','polite_greeting_comma')
    # This boundary is legal only for a positive hard witness and one colour.
    colours='black|white|grey|navy|blue|red|green|yellow|orange|purple|pink|brown|beige'
    boundary=re.fullmatch(r'(i (?:need|want) [a-z -]+) preferably ('+colours+r')([.!?]*)',text())
    if boundary:
        if re.search(r'\b(?:and|or|with|but)\s*$',boundary[1]):
            raise AttributeRequestError('UnsupportedRequest','ambiguous_normalized_preference_boundary')
        at=boundary.end(1);raw_at=atoms[at-1][2]
        edits.append({'rule':'preferably_boundary','raw_start':raw_at,'raw_end':raw_at,'raw_text':'',
                      'stage_start':at,'stage_end':at,'before':'','after':','})
        atoms.insert(at,(',',raw_at,raw_at))
    apply(r'[.!?]+$', '.', 'terminal_punctuation')
    value=text()
    if len(value)>500:raise AttributeRequestError('EncodingLimitExceeded','normalized_input_too_long')
    if len(edits)>128:raise AttributeRequestError('EncodingLimitExceeded','too_many_normalization_edits')
    return {'version':VERSION,'original_text':raw,'normalized_text':value,
            'character_map':[[start,end] for _,start,end in atoms],'transformations':edits}

def original_span(document,start,end):
    if type(start) is not int or type(end) is not int or not 0<=start<end<=len(document['character_map']):
        raise ValueError('Invalid normalized source span.')
    entries=document['character_map'][start:end];a=min(x[0] for x in entries);b=max(x[1] for x in entries)
    if not a<b:raise ValueError('A source span cannot consist only of inserted punctuation.')
    return {'start':a,'end':b,'text':document['original_text'][a:b]}
