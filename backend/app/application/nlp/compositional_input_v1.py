"""Additive token edits on the frozen 1.8 map; never an implicit legacy rewrite."""
import re
from app.application.nlp.natural_input_v1 import normalize as prior
from app.domain.value_objects.attribute_conditions import AttributeRequestError

VERSION='raw-normalized-span-map-2.0.0'

def normalize(raw):
    v=prior(raw);text=v['normalized_text'];mapping=v['character_map']
    edits=[{**e,'stage':'normalization_1_8'} for e in v['transformations']]
    def edit(pattern,replacement,rule):
        nonlocal text,mapping
        protected=[m.span() for m in re.finditer(r'"(?:[^"\\]|\\.)*"',text)]
        for m in reversed(list(re.finditer(pattern,text))):
            a,b=m.span()
            if any(a<y and b>x for x,y in protected):continue
            after=replacement(m) if callable(replacement) else replacement
            old=text[a:b]
            if old==after:continue
            points=mapping[a:b];start=min((x[0] for x in points),default=0);end=max((x[1] for x in points),default=start)
            edits.append({'stage':'composition_1_9','rule':rule,'raw_start':start,'raw_end':end,'raw_text':raw[start:end],
                'stage_start':a,'stage_end':b,'before':old,'after':after})
            newmap=[p[:] for p in points] if len(after)==b-a else [[start,end] for _ in after]
            text=text[:a]+after+text[b:];mapping=mapping[:a]+newmap+mapping[b:]
    edit(r'\bid (?=prefer\b|like\b)',"i'd ",'clause_subject_id')
    edit(r'\bim (?=going\b|heading\b)',"i'm ",'clause_subject_im')
    edit(r'\bthats\b',"that's",'relative_apostrophe')
    edit(r'\b(?:shirts|tops|skirts)\b',lambda m:{'shirts':'shirt','tops':'top','skirts':'skirt'}[m[0]],'closed_plural_alias')
    edit(r'^(?:hey|hi)(?:,)?\s+(?=(?:can|could|would) you\b|please\b|suggest\b|recommend\b)', '', 'polite_greeting')
    edit(r'^(?:can|could|would) you\s+(?=(?:please\s+)?(?:give|suggest|recommend|find)\b)', '', 'polite_modal')
    edit(r"(^|[,;]\s*|\b(?:and|but)\s+)please\s+(?=(?:i(?:'d)?|don't|do not|no|avoid|preferably)\b)",lambda m:m[1],'polite_clause_marker')
    if len(text)>500 or len(edits)>128:raise AttributeRequestError('EncodingLimitExceeded','compositional_normalization_budget')
    return {'version':VERSION,'original_text':raw,'normalized_text':text,'character_map':mapping,'transformations':edits}
