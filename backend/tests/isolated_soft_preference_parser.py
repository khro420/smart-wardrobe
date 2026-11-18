"""Explicitly test-only composition. This module is never imported by app runtime."""
from dataclasses import dataclass
from pathlib import Path
import re
from app.application.nlp.conversational_context_interpreter import ConversationalContextInterpreter,matching,outside_literals,fingerprint as legacy_fingerprint
from app.application.recommendation.conversational_request_pipeline import ConversationalRequestPipeline
from app.application.wardrobe.description_policy import DescriptionPolicy
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.domain.value_objects.request_local_preference import RequestLocalPreferenceIntent,IsolatedPreferenceError
from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
from app.domain.value_objects.garment_description_evidence import CANONICAL_ENUMS
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.domain.value_objects.attribute_conditions import encode
from app.shared_contracts.grammar_identity import semantic_fingerprint
from app.shared_contracts.isolated_soft_preference_grammar import GRAMMAR_VERSION,REGISTRY

# Closed existing role/category words, not names, images or guessed subtypes.
NOUNS={'trousers':('lower','trousers'),'pants':('lower','trousers'),'shorts':('lower','shorts'),'skirt':('lower','skirt'),
       'vest':('upper','vest'),'sling':('upper','sling'),'top':('upper',None),'shirt':('upper',None)}

def isolated_fingerprint():
    from app.domain.value_objects import request_local_preference as contract
    return semantic_fingerprint([GRAMMAR_VERSION.encode(),bytes.fromhex(legacy_fingerprint()),Path(__file__).read_bytes(),Path(contract.__file__).read_bytes(),
      encode({k:CANONICAL_ENUMS[k] for k in ('category','primary_colour')})])

@dataclass(frozen=True)
class IsolatedInterpretation:
    mandatory_request:object
    hard_intent:object
    local_intent:RequestLocalPreferenceIntent | None

class IsolatedSoftPreferenceParser:
    def __init__(self):self.base=ConversationalRequestPipeline(ConversationalContextInterpreter(),DescriptionPolicy.load())

    def interpret(self,text,*,preference_profile=None,compatibility_profile=None,contextual=False,continuation=False):
        normalized=matching(text);visible=outside_literals(normalized)
        if not re.search(r'\b(?:prefer|preferably)\b|\bwould\s+be\s+nice\b',visible):
            request,hard=self.base.interpret(text)
            return IsolatedInterpretation(request,hard,None)
        if preference_profile is not None or compatibility_profile is not None or contextual is not False or continuation is not False:
            raise IsolatedPreferenceError('SoftProfileUnavailable','P2/C2/context/continuation are not implemented for local wishes.')
        grammar=isolated_fingerprint()
        if grammar not in REGISTRY[GRAMMAR_VERSION]:raise ValueError('Changed/unregistered isolated parser implementation.')
        hard=None;request=StructuredOutfitRequest();binding={'kind':'explicit_role','group_id':None};spans=[]
        def span(target,a,b):return {'target':target,'start':a,'end':b,'text':text[a:b]}
        standalone=re.fullmatch(r"\s*(?P<marker>i'd\s+prefer)\s+(?P<wish>.+?)\s*[.!?]*\s*",normalized)
        nice=re.fullmatch(r'\s*(?P<wish>.+?)\s+(?P<marker>would\s+be\s+nice\s*,\s*but\s+anything\s+is\s+fine)\s*[.!?]*\s*',normalized)
        mixed=re.fullmatch(r'(?P<hard>.+?)\s*,\s*(?P<marker>preferably)\s+(?P<colour>[a-z]+)\s*[.!?]*\s*',normalized)
        if mixed:
            a,b=mixed.span('hard');masked=text[:b]+' '*(len(text)-b)
            request,old=self.base.interpret(masked)
            if type(request) is not StructuredOutfitRequest or any(getattr(request,k) is not None for k in ('occasion','style','colours','garment_categories','formality')) or old is None:
                raise IsolatedPreferenceError('SoftProfileUnavailable','A unique pure-B1 witness is required.')
            groups=old.conditions.to_dict()['groups']
            if len(groups)!=1 or groups[0]['role'] not in ('upper','lower') or groups[0]['quantifier']!='exists' or old.conditions.to_dict()['version']!='attribute-conditions-1.0.0':
                raise IsolatedPreferenceError('AmbiguousSoftBinding','Name one mandatory upper or lower witness.')
            role=groups[0]['role'];colour=mixed['colour']
            if colour not in CANONICAL_ENUMS['primary_colour']:raise IsolatedPreferenceError('UnsupportedSoftPreference','Use a supported named colour.')
            hard=AttributeIntent.capture(text,None,old.conditions,old.to_dict()['spans'],grammar,old.to_dict()['policy_sha256'])
            binding={'kind':'mandatory_group','group_id':groups[0]['id']}
            # The optional colour attaches to the actual source noun/condition
            # witness, not to another member with the same colour.
            source=next(s for s in old.to_dict()['spans'] if s['source']=='nlp')
            spans=[span('marker',*mixed.span('marker')),span('binding',source['start'],source['end']),span('s01',*mixed.span('colour'))]
            predicates=[{'id':'s01','attribute':'primary_colour','operator':'in','values':[colour]}]
        elif standalone or nice:
            frame=standalone or nice;wa,wb=frame.span('wish');words=normalized[wa:wb]
            names='|'.join(sorted(NOUNS,key=len,reverse=True));colours='|'.join(sorted(CANONICAL_ENUMS['primary_colour'],key=len,reverse=True))
            phrase=re.fullmatch(r'(?:(?:a|an)\s+)?(?:(?P<colour>'+colours+r')\s+)?(?P<noun>'+names+r')',words)
            if phrase is None:raise IsolatedPreferenceError('UnsupportedSoftPreference','One positive role/category/named-colour wish only; no residual conditions may be dropped.')
            role,category=NOUNS[phrase['noun']];predicates=[];spans=[span('marker',*frame.span('marker')),span('binding',wa+phrase.start('noun'),wa+phrase.end('noun'))]
            for field,value,part in [('primary_colour',phrase['colour'],'colour'),('category',category,'noun')]:
                if value is None:continue
                cid=f's{len(predicates)+1:02d}';predicates.append({'id':cid,'attribute':field,'operator':'in','values':[value]})
                spans.append(span(cid,wa+phrase.start(part),wa+phrase.end(part)))
            if not predicates:raise IsolatedPreferenceError('UnsupportedSoftPreference','A supported category or named colour is required.')
        else:raise IsolatedPreferenceError('UnsupportedSoftPreference','Unregistered soft frame, multiple wishes or unsupported modifier.')
        policy=AttributeEvidencePolicy.load()
        intent=RequestLocalPreferenceIntent.capture(text=text,request=request,hard=hard,grammar=grammar,role=role,predicates=predicates,binding=binding,spans=spans,policy=policy)
        return IsolatedInterpretation(request,hard,intent)
