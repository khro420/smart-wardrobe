"""Versioned language companion; no eligibility, scoring or persistence changes."""
from dataclasses import replace
import re
from app.application.recommendation.attribute_request_pipeline import AttributeRequestPipeline
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.nlp.conversational_context_interpreter import ConversationalContextInterpreter,guard,load_language,PROFILE,RESOURCE_SHA256
from app.application.nlp.conversational_attribute_interpreter import ConversationalAttributeInterpreter
from app.application.nlp.request_field_extractor import UnsupportedMeaning,RequestFieldExtractor
from app.domain.value_objects.attribute_conditions import AttributeConditions,AttributeRequestError,conjoin,ROLES
from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest

ENVIRONMENT_KEY='SMART_WARDROBE_ASSISTANT_LANGUAGE_PROFILE'

def select_language(profile,description_policy,interpreter):
    if profile=='disabled':return interpreter,None
    if profile!=PROFILE or description_policy is None or getattr(interpreter,'bundle_id',None)!='context_18_v1':raise ValueError('Conversational language dependencies/profile unavailable.')
    selected=ConversationalContextInterpreter()
    return selected,ConversationalRequestPipeline(selected,description_policy)

class ConversationalRequestPipeline(AttributeRequestPipeline):
    def __init__(self,interpreter,description_policy):
        super().__init__(interpreter,description_policy,grammar=ConversationalAttributeInterpreter())
        self.original=AttributeRequestPipeline(GeneralContextInterpreter('context_18_v1'),description_policy)
    def language_capabilities(self):
        return {'version':'conversational-language-capabilities-1.0.0','enabled':True,'profile':PROFILE,'supplement_sha256':RESOURCE_SHA256,'interpreter_sha256':self.interpreter.hash,'examples':["I'm going out to eat.",'Going to the movies.','Need an outfit for uni.','I want a cotton shirt.'],'soft_requests':'Use saved preference settings; no request-local score.','alternative_requests':'Use the bound Suggest another outfit action; supported ordinary contexts or enabled pure garment requirements.'}
    def capabilities(self):
        value=super().capabilities()
        value['grammar_version']='conversational-attribute-grammar-1.1.3'
        from app.application.nlp.verified_subtype_interpreter import active
        if active():
            from app.domain.value_objects.verified_garment_subtype import registry,VALUES
            value['request_version']='attribute-conditions-2.0.0'
            value['verified_subtypes']=registry()
            from pathlib import Path
            from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
            active_policy=AttributeEvidencePolicy.load(Path(__file__).with_name('config')/'attribute_evidence_policy.v2.json')
            value.update(policy_version=active_policy.snapshot()['version'],policy_sha256=active_policy.sha256,supported_request_versions=['attribute-conditions-1.0.0','attribute-conditions-2.0.0'])
            value['fields'].append({'attribute':'verified_subtype','operators':['in'],'values':list(VALUES),'dynamic_domain':False,'source_requirements':'Owner-confirmed garment type','default_role':'upper','default_quantifier':'exists'})
        value['base_grammar_sha256']=self.original.grammar.sha256
        value['language_supplement_sha256']=RESOURCE_SHA256
        return value
    def interpret(self,text,typed_input=None):
        from app.application.nlp.garment_wording_guidance import check
        check(text)
        try:guard(text)
        except UnsupportedMeaning as e:raise AttributeRequestError('InvalidInput' if e.reason=='invalid_text' else 'UnsupportedRequest',e.reason) from e
        # Preserve old successful interpretations only when bindings and context agree.
        original_result=None
        try:original_result=self.original.interpret(text,typed_input)
        except AttributeRequestError:pass
        typed=AttributeConditions.from_dict(typed_input) if typed_input is not None else None
        try:parsed=self.grammar.parse(text)
        except AttributeRequestError as e:
            if e.reason in ('ambiguous_same_binding','incompatible_binding_scopes','conflicting_binding_role','nested_binding_negation'):raise AttributeRequestError('UnsupportedRequest','language_conflicting_request') from e
            raise
        combined=conjoin(parsed.conditions,typed)
        if combined:
            groups=combined.to_dict()['groups']
            for positive in (g for g in groups if g['quantifier']=='exists'):
                for negative in (g for g in groups if g['quantifier']=='none' and set(ROLES[positive['role']])<=set(ROLES[g['role']])):
                    if any(a['attribute']==b['attribute'] and a['operator']==b['operator'] and set(map(str,a['values']))<=set(map(str,b['values'])) for a in positive['conditions'] for b in negative['conditions']):raise AttributeRequestError('AttributeConflict','language_conflicting_request')
        remaining=parsed.remaining
        # Explicit supported name/tag literals have already been consumed at
        # their original offsets. Unbound quotes must not reach context rules
        # which would treat words inside the literal as commands or negation.
        if re.search(r'"(?:[^"\\]|\\.)*"',remaining):
            raise AttributeRequestError('UnsupportedRequest','language_unsupported_requirement')
        work=list(remaining)
        for pattern in self.interpreter.language['function_frames']:
            for m in re.finditer(pattern,remaining,re.I):work[m.start():m.end()]=' '*(m.end()-m.start())
        tokens=set(re.findall(r"[\w']+",''.join(work).lower()))
        pure=combined is not None and tokens<=RequestFieldExtractor.GLUE|{'any'}
        if pure:request=StructuredOutfitRequest()
        else:
            outcome=self.interpreter.interpret_masked(text,remaining)
            if outcome.status!='Supported':raise AttributeRequestError(outcome.status,outcome.reason)
            request=outcome.structured_request
        if original_result is not None:
            original_request,original_intent=original_result
            old_raw=self.original.grammar.parse(text)
            old_conditions=old_raw.conditions.to_dict() if old_raw.conditions else None
            new_conditions=parsed.conditions.to_dict() if parsed.conditions else None
            old_sid=getattr(getattr(original_request,'context',None),'situation',None)
            new_sid=getattr(getattr(request,'context',None),'situation',None)
            if old_conditions==new_conditions and getattr(old_sid,'value',None)==getattr(new_sid,'value',None):return original_result
        if combined is None:return request,None
        spans=[{'condition_id':cid,'source':source,'start':a,'end':b,'text':raw} for cid,source,a,b,raw in parsed.spans]
        if typed:
            index=parsed.conditions.condition_count if parsed.conditions else 0
            for g in typed.to_dict()['groups']:
                for c in g['conditions']:
                    index+=1;spans.append({'condition_id':f'c{index:02d}' if parsed.conditions else c['id'],'source':'typed','start':None,'end':None,'text':None})
        from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
        return request,AttributeIntent.capture(text,typed,combined,spans,self.grammar.sha256,AttributeEvidencePolicy.for_conditions(combined).sha256)
