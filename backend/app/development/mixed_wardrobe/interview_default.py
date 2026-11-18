"""An inferred evaluation setting, never an invented user/garment observation."""
from dataclasses import replace
from pathlib import Path
import json
import re
from . import context_language as previous
from . import context_intent as phase2o
from app.application.nlp.compositional_input_v1 import normalize
from app.application.nlp.compositional_request_v1 import CompositionalIntent
from app.application.nlp.normalized_request_v1 import base_parse
from app.application.nlp.natural_input_v1 import original_span
from app.domain.value_objects.attribute_conditions import AttributeRequestError, AttributeConditions, digest, encode
from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
from app.domain.value_objects.request_local_preference import resolution_for
from app.application.recommendation.attribute_preference_codec import restore_request
from app.application.recommendation.general_context_evaluator import EvaluatorSpecification, INTERVIEW_DEFAULT_SPEC

GRAMMAR = 'mixed-interview-default-intent-1.0.0'
MESSAGE = "This outfit was recommended using a default smart-casual style because no dress code was specified. If your interview requires a different dress code, start a new chat and include the required dress code in your request."


def identity():
    from app.shared_contracts.grammar_identity import semantic_fingerprint
    from .interview_default_contract import GRAMMAR_SHA256
    h=semantic_fingerprint((GRAMMAR.encode(),bytes.fromhex(previous.identity()),INTERVIEW_DEFAULT_SPEC.encode(),Path(__file__).read_bytes()))
    if h!=GRAMMAR_SHA256:raise ValueError('Unregistered interview-default interpretation.')
    return h


def contextual(raw):
    return bool(re.search(r'\binterview(?:s|ed|ing)?\b',previous.outside(normalize(raw)['normalized_text'])))


def _parse(text):
    """Recover the already syntax-validated interview before policy admission.

    Same frozen clause parsers as Phase2O; this does not append a fictional
    dress-code sentence, manufacture spans, or change an archived parser.
    """
    optional=None;work=text
    markers=list(re.finditer(r"(?:,\s*|\s+(?:and|but)\s+)(?P<marker>preferably(?:\s+(?:wearing|with))?|(?:i'd|i) prefer)\s+",text))
    if len(markers)>1:phase2o.refuse('multiple_compositional_preferences')
    if markers:
        m=markers[0];end=len(text.rstrip('.!? '));prefix="I'd prefer "
        p=CompositionalIntent.capture(prefix+text[m.end():end]).to_dict()
        if p['hard_intent'] or not p['optional']:phase2o.refuse('unsupported_compositional_preference')
        optional=p['optional']
        for s in optional['spans']:
            a,b=(m.start('marker'),m.end('marker')) if s['target']=='marker' else (m.end()+s['start']-len(prefix),m.end()+s['end']-len(prefix))
            s.update(start=a,end=b,text=text[a:b])
        work=text[:m.start()]+' '*(len(text)-m.start())
    try:parsed=base_parse(work)
    except AttributeRequestError as error:
        parsed=None
        for cut in re.finditer(r'\s*[,;]\s*|\s+but\s+',work):
            left,right=work[:cut.start()],work[cut.end():].strip()
            if not right or not phase2o.contextual(left) or phase2o.contextual(right):continue
            context=base_parse(left+' '*(len(work)-len(left)));hard=CompositionalIntent.capture(right).to_dict()
            if context['hard'] or 'context' not in context['request'] or hard['optional'] or 'context' in hard['request'] or not hard['hard_intent']:continue
            if any(hard['request'][k] is not None for k in ('occasion','style','colours','garment_categories','formality')):continue
            offset=work.find(right,cut.end());h=hard['hard_intent']
            for s in h['spans']:s.update(start=offset+s['start'],end=offset+s['end']);s['text']=text[s['start']:s['end']]
            parsed={**context,'hard':h};break
        if parsed is None:raise error
    if 'context' not in parsed['request'] or parsed['local']:phase2o.refuse('unsupported_mixed_context_combination')
    return parsed,optional


def document(raw):
    grammar=identity();inferred=False
    try:
        value=previous.document(raw)
    except AttributeRequestError as error:
        # Every other refusal (explicit codes, role ambiguity, negation,
        # unknown words) is preserved. Default only this precise missing field.
        if error.reason!='mixed_context_dress_code_required':raise
        inferred=True
        try:phase2o.document(raw)
        except AttributeRequestError as initial:
            if initial.reason=='mixed_context_dress_code_required':mapping=normalize(raw)
            else:
                outer,targets=previous.rewrite(raw)
                if targets and targets!={'professional.job_interview'}:phase2o.refuse('semantic_context_collision')
                mapping=previous.compose(outer,normalize(outer['normalized_text']))
        else:raise ValueError('Unexpected successful archived interview parse.')
        parsed,optional=_parse(mapping['normalized_text']);hard=parsed['hard']
        # A global explicit rejection of the default is a dress requirement,
        # not omission. Preserve narrower garment-specific exclusions intact.
        for group in hard['conditions']['groups'] if hard else []:
            if group['role']=='all_selected' and group['quantifier']=='none' and len(group['conditions'])==1:
                c=group['conditions'][0]
                if c['attribute']=='style' and c['operator'] in ('in','contains_any') and 'smart casual' in c['values']:
                    phase2o.refuse('unsupported_context_unsupported_dress_code')
        if hard:hard=AttributeIntent.capture(mapping['normalized_text'],None,AttributeConditions.from_dict(hard['conditions']),hard['spans'],grammar,hard['policy_sha256']).to_dict()
        if optional:
            positives=[g for g in hard['conditions']['groups'] if g['quantifier']=='exists' and g['role']==optional['role']] if hard else []
            if len(positives)==1:optional['binding']={'kind':'mandatory_group','group_id':positives[0]['id']}
            optional['resolution']=resolution_for(AttributeIntent.from_dict(hard) if hard else None,optional['role'],optional['binding'],optional['predicates'])
        value={'request':parsed['request'],'hard_intent':hard,'optional':optional,'normalization':mapping,
               'base_grammar_version':'conversational-compositional-grammar-1.9.0'}
    observed=restore_request(value['request']);frame=observed.context
    if frame.situation.value!='professional.job_interview' or frame.role.value not in ('candidate','interviewer'):phase2o.refuse('language_context_clarification')
    if inferred and (frame.dress_code.state!='Unspecified' or frame.formality.state!='Unspecified' or observed.formality is not None):
        raise ValueError('An explicit or unresolved code cannot use the default.')
    effective=replace(observed,formality='smart_casual') if inferred else observed
    spec=EvaluatorSpecification.current('context_18_v1',interview_default=inferred);evaluator=spec.construct()
    if not evaluator.supports(effective):phase2o.refuse('unsupported_context_'+evaluator.plan(effective).reason)
    mapping=value['normalization'];hard=value['hard_intent'];optional=value['optional']
    if hard:hard=AttributeIntent.capture(mapping['normalized_text'],None,AttributeConditions.from_dict(hard['conditions']),hard['spans'],grammar,hard['policy_sha256']).to_dict()
    default={'version':'interview-appearance-default-1.0.0','inferred':inferred,'origin':'approved_policy_default' if inferred else 'user_specified',
             'effective_formality':effective.formality,'verified_dress_code':False,'message':MESSAGE if inferred else None,
             'policy_binding':evaluator.plan(effective).binding.identifier,'policy_version':evaluator.plan(effective).binding.policy_version,
             'predicate':evaluator.plan(effective).predicate.identifier}
    result={**value,'version':'mixed-interview-default-intent-1.0.0','grammar_version':GRAMMAR,'grammar_sha256':grammar,
            'request':observed.to_dict(),'evaluation_request':effective.to_dict(),'interview_default':default,'hard_intent':hard,
            'original_hard_spans':[{**s,**original_span(mapping,s['start'],s['end'])} for s in hard['spans']] if hard else [],
            'original_optional_spans':[{**s,**original_span(mapping,s['start'],s['end'])} for s in optional['spans']] if optional else [],
            'original_context_spans':[{'slot':name,'value':slot['values'],**original_span(mapping,s['start'],s['end'])} for name,slot in observed.to_dict()['context'].items() if isinstance(slot,dict) and 'spans' in slot for s in slot['spans']]}
    result.pop('revision',None);result=json.loads(encode(result));result['revision']=digest(result)
    return result
