"""Finite attribute companion grammar. Offsets always address original text."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import re
import unicodedata

from app.domain.value_objects.attribute_conditions import (
    AttributeConditions,AttributeRequestError,VERSION,encode,decode,CANONICAL_ENUMS,ROLES)

GRAMMAR_VERSION='attribute-request-grammar-1.0.0'
GRAMMAR_SHA256='491455b531f5ec0b58d2791b89cb7adda41525d6e97f975d2d5c2de958a7c8a0'


def phrase(value):
    """Matching normalization only: no rewritten copy or shifted source offsets."""
    parts=re.split(r'[\s_\-]+',value)
    return r'(?<!\w)'+r'[\s_\-\u2010-\u2014]+'.join(re.escape(p) for p in parts)+r'(?!\w)'


@dataclass(frozen=True)
class AttributeInterpretation:
    conditions: AttributeConditions | None
    remaining: str
    spans: tuple
    grammar_sha256: str


class AttributeRequestInterpreter:
    def __init__(self,path=None):
        path=Path(path) if path else Path(__file__).with_name('config')/'attribute_grammar.v1.json'
        try:
            with path.open('rb') as stream:raw=stream.read(65537)
        except OSError as exc:raise AttributeRequestError('AttributeUnavailable','missing_attribute_grammar') from exc
        if len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=GRAMMAR_SHA256:
            raise AttributeRequestError('AttributeUnavailable','unregistered_attribute_grammar')
        value=decode(raw,65536)
        if value.get('version')!=GRAMMAR_VERSION:raise AttributeRequestError('AttributeUnavailable','unsupported_attribute_grammar')
        self.payload=raw
        self.entries=tuple(sorted(((re.compile(phrase(e['expression'])[:-6]+r's?(?!\w)' if e['expression'].endswith(' pattern') else phrase(e['expression']),re.I),e)
            for e in value['entries']),key=lambda pair:len(pair[1]['expression']),reverse=True))
        self.category_aliases=tuple((re.compile(phrase(alias),re.I),category)
            for category,aliases in value['category_aliases'].items() for alias in aliases)
        self.nouns=dict(value['role_nouns']);self.nouns['outfit']='all_selected'
        self.descriptors=tuple(sorted(((re.compile(phrase(v),re.I),field,v)
            for field in ('pattern','material','silhouette','neckline','style','primary_colour')
            for v in CANONICAL_ENUMS[field]),key=lambda entry:len(entry[2]),reverse=True))

    @property
    def sha256(self):return GRAMMAR_SHA256

    def parse(self,original):
        if type(original) is not str or not original.strip() or len(original)>500:
            raise AttributeRequestError('InvalidInput','bounded_original_request_required')
        occupied=[False]*len(original);groups=[];spans=[];condition_index=0
        frames=[]
        for m in re.finditer(r'\b(?:(every|all|no|a|an|the)\s+)?(top|shirt|dress|outerwear|trousers|pants|garment)s?\s+(?:must\s+have|with)\s+',original,re.I):
            stop=re.search(r'[.;!?]',original[m.end():])
            frames.append((m.start(),m.end(),m.end()+stop.start() if stop else len(original),self.nouns[m.group(2).lower()],
                'all_present' if (m.group(1) or '').lower() in ('all','every') else 'none' if (m.group(1) or '').lower()=='no' else 'exists',m.group(2).lower()=='garment'))
        def free(start,end):return not any(occupied[start:end])
        def consume(start,end):occupied[start:end]=[True]*(end-start)
        def negation(start):
            prefix=original[:start]
            match=re.search(r"(?<!\w)(?:do\s+not\s+include|don['\u2019]t\s+include|no|not|without|avoid|excluding)\s+(?:any\s+)?$",prefix,re.I)
            if not match:return None
            if re.search(r'\b(?:no|not|without|avoid|excluding)\s*$',prefix[:match.start()],re.I):
                raise AttributeRequestError('UnsupportedRequest','double_negation')
            return match
        def operation(field,value):
            return 'coverage_ge' if field=='palette_coverage' else 'exact_hex' if isinstance(value,str) and value.startswith('#') else 'bool_eq' if type(value) is bool else 'exact_text' if field in ('garment_name','descriptive_tag') else 'contains_any' if field in ('style','material','palette_colour') else 'in'
        def add(observations,start,end,role=None,quantifier=None,all_values=False):
            nonlocal condition_index
            if not free(start,end):return
            negative=negation(start)
            frame=next((f for f in reversed(frames) if f[1]<=start<f[2]),None)
            if frame is not None:
                if negative:
                    if frame[4]=='none' or any(g.get('_frame')==frame[0] for g in groups):
                        raise AttributeRequestError('UnsupportedRequest','nested_binding_negation')
                    # "a top with no cotton material" both requires a top
                    # and excludes cotton within that role. A lone exclusion
                    # must not become vacuously true on a dress-only outfit.
                    categories=[c for c in CANONICAL_ENUMS['category'] if
                        ('upper' if c.endswith('_top') or c in ('vest','sling') else 'one_piece' if c.endswith('_dress') else 'outerwear' if 'outwear' in c else 'lower') in ROLES[frame[3]]]
                    condition_index+=1;required_id=f'c{condition_index:02d}'
                    groups.append({'id':f'g{len(groups)+1:02d}','role':frame[3],'quantifier':'exists',
                        'conditions':[{'id':required_id,'attribute':'category','operator':'in','values':categories}],
                        '_frame':None})
                    spans.append((required_id,'nlp',frame[0],frame[1],original[frame[0]:frame[1]]))
                if role is None:
                    if not (frame[5] and frame[4]=='exists'):role=frame[3]
                elif role!=frame[3]:raise AttributeRequestError('UnsupportedRequest','conflicting_binding_role')
                quantifier=frame[4];consume(frame[0],frame[1])
            if negative:consume(negative.start(),negative.end());quantifier='none'
            conditions=[]
            for position,(field,value,a,b) in enumerate(observations):
                if all_values and position:
                    cid=conditions[0]['id'];conditions[0]['values'].append(value)
                    spans.append((cid,'nlp',a,b,original[a:b]));continue
                condition_index+=1;cid=f'c{condition_index:02d}'
                conditions.append({'id':cid,'attribute':field,'operator':'contains_all' if all_values else operation(field,value),'values':[value]})
                spans.append((cid,'nlp',a,b,original[a:b]))
                if negative:spans.append((cid,'nlp',negative.start(),negative.end(),original[negative.start():negative.end()]))
            field=observations[0][0]
            if role is None:
                role='all_selected' if quantifier=='none' else 'base_upper_body' if field in ('neckline','sleeve_length') else 'base' if field in ('silhouette','style') else 'all_selected'
                if re.search(r'\bsomething\s+(?:with\s+)?(?:a\s+)?$',original[:start],re.I):role='base'
            quantifier=quantifier or 'exists'
            every=re.search(r'\b(?:every|all)\s+(?:selected\s+)?$',original[:start],re.I)
            if every and negative is None:consume(every.start(),every.end());quantifier='all_present'
            existing=next((g for g in groups if frame is not None and g.get('_frame')==frame[0]),None)
            if existing is not None:
                common=set(ROLES[existing['role']])&set(ROLES[role])
                scope=next((key for key,values in ROLES.items() if set(values)==common),None)
                if scope is None:raise AttributeRequestError('UnsupportedRequest','incompatible_binding_scopes')
                existing['role']=scope;existing['conditions'].extend(conditions)
            else:groups.append({'id':f'g{len(groups)+1:02d}','role':role,'quantifier':quantifier,'conditions':conditions,'_frame':frame[0] if frame else None})
            consume(start,end)

        # Quoted text is a single literal domain, never scanned for commands or
        # descriptive keywords. JSON escapes preserve its original source span.
        quoted=re.compile(r'\bgarment\s+(named|tagged)\s+("(?:[^"\\]|\\.)*")',re.I)
        for match in quoted.finditer(original):
            try:value=json.loads(match.group(2))
            except ValueError as exc:raise AttributeRequestError('UnsupportedRequest','invalid_quoted_literal') from exc
            if unicodedata.normalize('NFC',value)!=value:raise AttributeRequestError('UnsupportedAttributeValue','noncanonical_literal')
            field='garment_name' if match.group(1).lower()=='named' else 'descriptive_tag'
            add([(field,value,match.start(2),match.end(2))],match.start(),match.end())

        for match in re.finditer(r'\bexact\s+(main|secondary|palette)\s+colou?r\s+(#[0-9a-fA-F]{6})\b',original,re.I):
            field={'main':'primary_colour','secondary':'secondary_colour','palette':'palette_colour'}[match.group(1).lower()]
            add([(field,match.group(2).lower(),match.start(2),match.end(2))],match.start(),match.end())
        threshold=re.compile(r'\bpalette\s+(#[0-9a-fA-F]{6}|[a-z]+)\s+coverage\s+at\s+least\s+(\d+(?:\.\d+)?)\b',re.I)
        for match in threshold.finditer(original):
            add([('palette_coverage',{'colour':match.group(1).lower(),'minimum':match.group(2)},match.start(),match.end())],match.start(),match.end())
        percentage=re.compile(r'\bat\s+least\s+(\d+(?:\.\d+)?)%\s+(#[0-9a-fA-F]{6}|[a-z]+)\s+in\s+the\s+palette\b',re.I)
        for match in percentage.finditer(original):
            from fractions import Fraction
            value=Fraction(match.group(1))/100
            if not 0<=value<=1 or value.denominator>1000000:
                raise AttributeRequestError('UnsupportedAttributeValue','percentage_precision')
            scaled=value*1000000
            if scaled.denominator!=1:raise AttributeRequestError('UnsupportedAttributeValue','percentage_precision')
            decimal=f'{scaled.numerator//1000000}.{scaled.numerator%1000000:06d}'
            add([('palette_coverage',{'colour':match.group(2).lower(),'minimum':decimal},match.start(),match.end())],match.start(),match.end())

        for field,suffix in (('material','material'),('style','style'),('palette_colour','in the colour palette')):
            vocabulary=CANONICAL_ENUMS['primary_colour' if field=='palette_colour' else field]
            choice='|'.join(re.escape(v) for v in sorted(vocabulary,key=len,reverse=True))
            for match in re.finditer(r'\bboth\s+('+choice+r')\s+and\s+('+choice+r')\s+'+phrase(suffix),original,re.I):
                add([(field,match.group(1).lower(),match.start(1),match.end(1)),(field,match.group(2).lower(),match.start(2),match.end(2))],match.start(),match.end(),all_values=True)

        # Field-qualified forms have explicit field identity and take priority
        # over a noun embedded in a canonical category expression.
        for pattern,entry in self.entries:
            for match in pattern.finditer(original):
                if not free(match.start(),match.end()):continue
                if entry['status']=='Blocked':raise AttributeRequestError('UnsupportedAttributeValue','blocked_'+entry['attribute'])
                add([(entry['attribute'],entry['value'],match.start(),match.end())],match.start(),match.end())

        # Licensed descriptor+noun frames bind the entire conjunction to one
        # actual member. A negative forbids that conjunction as a whole.
        noun_matches=[]
        for name,role in self.nouns.items():
            pattern=phrase(name) if name.endswith('s') or name=='something' else phrase(name)[:-6]+r's?(?!\w)'
            noun_matches.extend((m,role,None) for m in re.finditer(pattern,original,re.I))
        for pattern,category in self.category_aliases:
            noun_matches.extend((m,'upper' if category.endswith('_top') else 'outerwear' if 'outwear' in category else 'lower',category)
                for m in pattern.finditer(original))
        noun_matches.sort(key=lambda row:(row[0].start(),-(row[0].end()-row[0].start())))
        for noun,role,category in noun_matches:
            if not free(noun.start(),noun.end()):continue
            observations=[];cursor=noun.start()
            while True:
                found=[]
                for pattern,field,value in self.descriptors:
                    for match in pattern.finditer(original,0,cursor):
                        gap=original[match.end():cursor]
                        if free(match.start(),match.end()) and re.fullmatch(r'[\s,]*(?:and\s+)?',gap,re.I):
                            found.append((match,field,value))
                if not found:break
                match,field,value=max(found,key=lambda row:row[0].end()-row[0].start())
                observations.insert(0,(field,value,match.start(),match.end()));cursor=match.start()
            if category:observations.append(('category',category,noun.start(),noun.end()))
            if observations:
                previous=len(groups)
                both=re.search(r'\bboth\s+$',original[:cursor],re.I)
                all_values=both is not None and len({o[0] for o in observations})==1 and observations[0][0] in ('material','style','palette_colour')
                if all_values:consume(both.start(),both.end())
                outfit=noun.group().lower().removesuffix('s')=='outfit'
                add(observations,cursor,noun.end(),role=role,quantifier='all_present' if outfit else None,all_values=all_values)
                if len(groups)>previous:
                    if outfit:
                        # This noun also licenses the original command/context
                        # frame. Keep it verbatim while consuming its attributes.
                        occupied[noun.start():noun.end()]=[False]*(noun.end()-noun.start())
                    for c in groups[-1]['conditions']:
                        spans.append((c['id'],'nlp',noun.start(),noun.end(),original[noun.start():noun.end()]))

        if not groups:return AttributeInterpretation(None,original,(),self.sha256)
        # Only explicit same-garment language merges independent clauses.
        same=re.search(r'\bon\s+the\s+same\s+garment\b',original,re.I)
        if same:
            role_sets=[set({'all_selected':('upper','lower','one_piece','outerwear'),'base':('upper','lower','one_piece'),'base_upper_body':('upper','one_piece')}.get(g['role'],(g['role'],))) for g in groups]
            common=set.intersection(*role_sets)
            if not common or len({g['quantifier'] for g in groups})!=1:raise AttributeRequestError('UnsupportedRequest','ambiguous_same_binding')
            named=next((g['role'] for g in groups if set({'all_selected':('upper','lower','one_piece','outerwear'),'base':('upper','lower','one_piece'),'base_upper_body':('upper','one_piece')}.get(g['role'],(g['role'],)))==common),None)
            if named is None:raise AttributeRequestError('UnsupportedRequest','ambiguous_same_binding')
            groups=[{**groups[0],'role':named,'conditions':[c for g in groups for c in g['conditions']]}];consume(same.start(),same.end())
        # Remove connectors only where they directly introduce a recognized
        # consumed attribute span, leaving unknown modifiers visible.
        for match in re.finditer(r'\b(?:and\s+(?:i\s+)?want|and\s+(?:i\s+)?would\s+like|with)\s+(?:a\s+|an\s+)?',original,re.I):
            if match.end()<len(occupied) and occupied[match.end()]:consume(match.start(),match.end())
        remaining=''.join(' ' if used else char for char,used in zip(original,occupied))
        for group in groups:group.pop('_frame',None)
        # Longest-match scanning order is an implementation detail. Public
        # binding/condition IDs follow their original source order.
        starts={cid:min(s[2] for s in spans if s[0]==cid) for cid,_,_,_,_ in spans}
        groups.sort(key=lambda g:min(starts[c['id']] for c in g['conditions']))
        remap={};index=0
        for number,group in enumerate(groups,1):
            group['id']=f'g{number:02d}'
            group['conditions'].sort(key=lambda c:starts[c['id']])
            for c in group['conditions']:
                index+=1;old=c['id'];c['id']=f'c{index:02d}';remap[old]=c['id']
        spans=[(remap[cid],source,start,end,text) for cid,source,start,end,text in spans]
        conditions=AttributeConditions.from_dict({'version':VERSION,'groups':groups})
        return AttributeInterpretation(conditions,remaining,tuple(spans),self.sha256)
