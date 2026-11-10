"""Companion interpretation and one-time preparation; no score arithmetic."""
from dataclasses import replace
from copy import copy
import re
from app.domain.value_objects.attribute_conditions import AttributeConditions,AttributeRequestError,conjoin
from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest,GarmentCategoryConstraint
from app.domain.value_objects.general_context_request import GeneralContextRequest
from app.application.nlp.attribute_request_interpreter import AttributeRequestInterpreter
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions
from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier


class AttributeRequestPipeline:
    def __init__(self,interpreter,description_policy,*,grammar=None,policy=None):
        from app.application.recommendation.attribute_execution_selection import AttributeExecutionSelection,PROFILE
        AttributeExecutionSelection(PROFILE).validate_dependencies(description_policy,interpreter)
        self.interpreter=interpreter
        self.description_policy=description_policy
        self.grammar=grammar or AttributeRequestInterpreter()
        self.policy=policy or AttributeEvidencePolicy.load()

    def interpret(self,text,typed_input=None):
        typed=AttributeConditions.from_dict(typed_input) if typed_input is not None else None
        parsed=self.grammar.parse(text)
        # Preserve all already-supported positive core behavior. New detailed
        # clauses still use this branch's old request projection where equivalent.
        core=parsed.conditions is not None and all(g['quantifier']=='exists' and all(c['attribute'] in ('category','primary_colour','style') for c in g['conditions']) for g in parsed.conditions.to_dict()['groups'])
        if typed is None and (parsed.conditions is None or core):
            legacy=self.interpreter.interpret(text)
            if legacy.status=='Supported':return legacy.structured_request,None
            if parsed.conditions is None:raise AttributeRequestError(legacy.status,legacy.reason)
        combined=conjoin(parsed.conditions,typed)
        if combined is None:
            legacy=self.interpreter.interpret(text)
            if legacy.status!='Supported':raise AttributeRequestError(legacy.status,legacy.reason)
            return legacy.structured_request,None
        remaining=parsed.remaining
        if re.search(r'\b(?:and|for|with|at|in|on)\s*[.!?]*$',text,re.I):
            raise AttributeRequestError('UnsupportedRequest','incomplete_attribute_or_context_clause')
        # The pure-attribute command skeleton is finite. It never licenses an
        # unknown meaningful modifier, which remains for the old residual guard.
        skeleton=re.sub(r"\b(?:i\s+(?:want|would\s+like)|suggest|recommend|a|an|the|garment|outfit|something|with|and|please)\b",' ',remaining,flags=re.I)
        pure=re.fullmatch(r'[\s.!?,]*',skeleton) is not None
        if pure:
            request=StructuredOutfitRequest()
        else:
            context_interpreter=self.interpreter
            if parsed.conditions is not None and re.match(r'\s*(?:please\s+)?(?:suggest|recommend)\b',text,re.I):
                # The registered attribute/noun frame already established the
                # clothing command. Reuse the original forbidden-intent guard
                # without injecting synthetic characters into context spans.
                context_interpreter=copy(self.interpreter);context_interpreter.legacy=copy(self.interpreter.legacy)
                classifier=self.interpreter.legacy.classifier
                class AttributeCommand:
                    def classify(_,value):return classifier.classify(value+' outfit')
                context_interpreter.legacy.classifier=AttributeCommand()
            legacy=context_interpreter.interpret(remaining)
            if legacy.status!='Supported':raise AttributeRequestError(legacy.status,legacy.reason)
            request=legacy.structured_request
            if isinstance(request,GeneralContextRequest):request=replace(request,context=replace(request.context,original_text=text))
        # Only proven-equivalent positive singleton core clauses are lifted.
        changes={};colours=list(request.colours or ());categories=list(request.garment_categories or ())
        for group in combined.to_dict()['groups']:
            if group['quantifier']!='exists' or len(group['conditions'])!=1:continue
            c=group['conditions'][0]
            if len(c['values'])!=1:continue
            field,value=c['attribute'],c['values'][0]
            if field=='style' and c['operator']=='contains_any' and group['role']=='base':
                if request.style is not None and request.style!=value:raise AttributeRequestError('AttributeConflict','conflicting_explicit_style')
                changes['style']=value
            elif field=='primary_colour' and c['operator']=='in' and group['role']=='all_selected':
                if value not in colours:colours.append(value)
            elif field=='category' and c['operator']=='in' and group['role']=='all_selected':
                value=GarmentCategoryConstraint('category',value)
                if value not in categories:categories.append(value)
        if colours:changes['colours']=tuple(colours)
        if categories:changes['garment_categories']=tuple(categories)
        if changes:request=replace(request,**changes)
        spans=[]
        nlp_count=parsed.conditions.condition_count if parsed.conditions else 0
        for cid,source,start,end,raw in parsed.spans:
            spans.append({'condition_id':cid,'source':source,'start':start,'end':end,'text':raw})
        if typed:
            index=nlp_count
            for group in typed.to_dict()['groups']:
                for c in group['conditions']:
                    index+=1;cid=f'c{index:02d}' if parsed.conditions else c['id']
                    spans.append({'condition_id':cid,'source':'typed','start':None,'end':None,'text':None})
        intent=AttributeIntent.capture(text,typed,combined,spans,self.grammar.sha256,AttributeEvidencePolicy.for_conditions(combined).sha256)
        return request,intent

    def prepare(self,intent,collection,subtype_sources=()):
        policy=AttributeEvidencePolicy.for_conditions(intent.conditions)
        if intent.conditions.to_dict()['version']=='attribute-conditions-2.0.0':
            from app.application.nlp.verified_subtype_interpreter import active
            if not active():raise AttributeRequestError('AttributeUnavailable','verified_subtype_profile_disabled')
        return (PreparedAttributeConditions.prepare(intent.conditions,collection,policy,subtype_sources=subtype_sources),
                IndependentAttributeVerifier.prepare(intent.conditions,collection,policy,subtype_sources=subtype_sources))

    def capabilities(self):
        from app.domain.value_objects.attribute_conditions import OPERATORS,ROLES
        from app.domain.value_objects.attribute_selection_evidence import decode
        registry=decode(self.grammar.payload,65536)
        return {'version':'attribute-request-capabilities-1.0.0','enabled':True,'request_version':'attribute-conditions-1.0.0',
          'grammar_version':registry['version'],'grammar_sha256':self.grammar.sha256,'policy_version':'attribute-evidence-policy-1.0.0',
          'policy_sha256':self.policy.sha256,'fields':[{'attribute':field,'operators':[op for op,fields in OPERATORS.items() if field in fields],
            'values':[e['value'] for e in registry['entries'] if e['attribute']==field and e['status']=='Planned'],
            'dynamic_domain':field in ('garment_name','descriptive_tag','palette_coverage','primary_colour','secondary_colour','palette_colour'),
            'source_requirements':value['rule'],'default_role':'base_upper_body' if field in ('neckline','sleeve_length') else 'base' if field in ('silhouette','style') else 'all_selected',
            'default_quantifier':'exists'} for field,value in self.policy.snapshot()['fields'].items()],
          'roles':list(ROLES),'quantifiers':['exists','all_present','none'],
          'bounds':{'groups':8,'conditions':16,'values_per_condition':20,'values_total':64,'typed_bytes':32768,'intent_bytes':65536,'request_codepoints':500},
          'blocked_sources':['Unverified model suggestions','Unregistered automatic measurement provenance','Cream palette family without an exact anchor']}
