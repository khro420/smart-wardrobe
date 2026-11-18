"""Bounded semantic frames with lossless original-source mapping.

Every residual word reaches the frozen Phase2O interpreter. Rules map complete
activity frames to existing situations; neither this module nor its resource
admits garments, supplies evidence, or changes contextual policies.
"""
from functools import lru_cache
from pathlib import Path
import json
import re
from . import context_intent as archived
from app.application.nlp.compositional_input_v1 import normalize as base_normalize
from app.application.nlp.natural_input_v1 import original_span
from app.domain.value_objects.attribute_conditions import AttributeRequestError, AttributeConditions, digest
from app.domain.value_objects.attribute_selection_evidence import AttributeIntent

GRAMMAR = 'mixed-semantic-context-language-1.0.0'
RESOURCE = Path(__file__).with_name('context_language_rules.v1.json')
HINTS = r'\b(?:seminar|team meeting|business presentation|workplace presentation|mall|being interviewed)\b'


def refuse(reason):
    raise AttributeRequestError('UnsupportedRequest', reason)


def identity():
    from app.shared_contracts.grammar_identity import semantic_fingerprint
    from .context_language_contract import GRAMMAR_SHA256
    actual = semantic_fingerprint((GRAMMAR.encode(), bytes.fromhex(archived.identity()), Path(__file__).read_bytes(), RESOURCE.read_bytes()))
    if actual != GRAMMAR_SHA256:
        raise ValueError('Unregistered semantic contextual grammar.')
    return actual


@lru_cache(maxsize=1)
def rules():
    raw = RESOURCE.read_bytes()
    if len(raw) > 65536:
        raise ValueError('Oversized contextual language resource.')
    value = json.loads(raw)
    if set(value) != {'version','scope','rules'} or value['version'] != 'bounded-context-paraphrases-1.0.0' or not 1 <= len(value['rules']) <= 64:
        raise ValueError('Unknown contextual language schema.')
    from app.application.recommendation.context_policy_registry import ContextPolicyRegistry
    registry = ContextPolicyRegistry.load(bundle_id='context_18_v1')
    result = []
    for item in value['rules']:
        if set(item) != {'id','situation','pattern','canonical'} or not registry.binding_for(item['situation']):
            raise ValueError('Unapproved contextual target.')
        result.append((item, re.compile(r'(?<!\w)(?:' + item['pattern'] + r')(?!\w)')))
    if len({item['id'] for item, _ in result}) != len(result):
        raise ValueError('Duplicate contextual rule.')
    return tuple(result)


def outside(text):
    return re.sub(r'"(?:[^"\\]|\\.)*"', lambda m: ' '*len(m[0]), text)


def contextual(raw):
    text = outside(base_normalize(raw)['normalized_text'])
    return archived.contextual(raw) or bool(re.search(HINTS, text)) or any(p.search(text) for _, p in rules())


def rewrite(raw):
    base = base_normalize(raw)
    text = base['normalized_text']
    mapping = base['character_map']
    locked = [False]*len(text)
    edits = [{**e, 'stage':'frozen_composition_1_9'} for e in base['transformations']]
    targets = set()

    def replace(a, b, after, rule, semantic=False):
        nonlocal text, mapping, locked
        if any(locked[a:b]):
            return
        before = text[a:b]
        if before == after:
            return
        points = mapping[a:b]
        start, end = min(p[0] for p in points), max(p[1] for p in points)
        edits.append({'stage':'semantic_context_1_0','rule':rule,'raw_start':start,'raw_end':end,'raw_text':raw[start:end],
                      'stage_start':a,'stage_end':b,'before':before,'after':after})
        text = text[:a] + after + text[b:]
        mapping = mapping[:a] + [[start,end] for _ in after] + mapping[b:]
        locked = locked[:a] + [semantic]*len(after) + locked[b:]

    def edit(pattern, replacement, rule):
        for m in reversed(list(re.finditer(pattern, outside(text)))):
            replace(m.start(), m.end(), m.expand(replacement), rule)

    # Fronted context is reordered only for this complete, finite request frame.
    front = re.fullmatch(r'for (?P<event>[^,;]{1,160}), (?P<request>(?:please )?(?:suggest|recommend|give me|help me (?:pick|choose)) (?:an? )?outfit)(?P<terminal>[.!?]*)', text)
    if front:
        old = text
        q, z = front.span('request')
        request_span = [min(p[0] for p in mapping[q:z]), max(p[1] for p in mapping[q:z])]
        a, b = front.span('event')
        tail = front.span('terminal')
        text = 'suggest an outfit for ' + front['event'] + front['terminal']
        mapping = [request_span[:] for _ in 'suggest an outfit '] + mapping[:4] + mapping[a:b] + mapping[tail[0]:tail[1]]
        locked = [False]*len(text)
        edits.append({'stage':'semantic_context_1_0','rule':'fronted_context_request','raw_start':0,'raw_end':len(raw),'raw_text':raw,'before':old,'after':text})
    edit(r'\b(?:tmr|tmrw)\b', 'tomorrow', 'explicit_tomorrow_abbreviation')
    edit(r'\b(?:tonite|2nite)\b', 'tonight', 'explicit_tonight_abbreviation')
    edit(r'\bw/ (?=(?:my )?(?:friends|classmates|colleagues)\b)', 'with ', 'bounded_companion_abbreviation')
    edit(r'^(?:hey|hi)(?: there)?[,!]? (?=(?:can|could|would) you|please|suggest|recommend|help me|any )', '', 'greeting')
    edit(r'^(?:can|could|would) you (?:please )?(?:help me )?(?:pick|choose) (?:an? )?outfit(?: to wear)? for ', 'suggest an outfit for ', 'polite_outfit_choice')
    edit(r'^what (?:should|can) i (?:put on|wear) for ', 'suggest an outfit for ', 'clothing_question')
    edit(r'^(?:any ideas|any suggestions)(?: on)? (?:what to wear|for (?:an? )?outfit) for ', 'suggest an outfit for ', 'clothing_ideas')
    edit(r"^i(?:'m| am) (?:not sure|unsure) what to wear for ", 'suggest an outfit for ', 'clothing_uncertainty')
    for item, pattern in rules():
        for m in reversed(list(pattern.finditer(outside(text)))):
            if any(locked[m.start():m.end()]):
                continue
            # Conservative event-negation guard: a negative activity never
            # becomes a positive event through a phrase replacement.
            prefix = re.split(r'[,;.!?]|\b(?:and|but)\b', text[:m.start()])[-1]
            if re.search(r"\b(?:not|never|no|don't|do not|won't|cannot|can't)\b", prefix):
                refuse('language_negated_event')
            replace(m.start(), m.end(), m.expand(item['canonical']), item['id'], True)
            targets.add(item['situation'])
    if len(targets) > 1:
        refuse('semantic_context_collision')
    if len(text) > 500 or len(edits) > 192 or len(mapping) != len(text):
        raise AttributeRequestError('EncodingLimitExceeded', 'semantic_context_budget')
    return {'version':'raw-semantic-context-map-1.0.0','original_text':raw,'normalized_text':text,
            'character_map':mapping,'transformations':edits}, targets


def compose(outer, inner):
    raw = outer['original_text']
    def interval(a,b):
        points = outer['character_map'][a:b]
        if points:
            return [min(p[0] for p in points), max(p[1] for p in points)]
        point = outer['character_map'][a-1][1] if a else 0
        return [point,point]
    mapping = [interval(a,b) for a,b in inner['character_map']]
    transforms = list(outer['transformations'])
    for e in inner['transformations']:
        a,b = interval(e['raw_start'],e['raw_end'])
        transforms.append({**e,'stage':'frozen_phase2o_after_semantics','raw_start':a,'raw_end':b,'raw_text':raw[a:b]})
    return {'version':'raw-semantic-context-map-1.0.0','original_text':raw,'normalized_text':inner['normalized_text'],
            'character_map':mapping,'transformations':transforms}


def document(raw):
    grammar = identity()
    check = outside(base_normalize(raw)['normalized_text'])
    if re.search(r'\b(?:my|our) (?:own )?wedding\b', check):
        refuse('semantic_context_scope_unavailable')
    if re.search(r'\bmall\b', check) and not re.search(r'\b(?:shopping|shop|buy|pick up|get (?:some|a few))\b', check):
        refuse('semantic_context_clarification')
    try:
        value = archived.document(raw)
        mapping = {**value['normalization'],'version':'raw-semantic-context-map-1.0.0'}
    except AttributeRequestError as original:
        mapping, targets = rewrite(raw)
        if not targets and mapping['normalized_text'] == base_normalize(raw)['normalized_text']:
            if re.search(HINTS, check):
                refuse('semantic_context_clarification')
            raise original
        value = archived.document(mapping['normalized_text'])
        if targets and value['request']['context']['situation']['values'] != sorted(targets):
            refuse('semantic_context_collision')
        mapping = compose(mapping, value['normalization'])
    if len(mapping['transformations']) > 384 or len(mapping['character_map']) != len(mapping['normalized_text']):
        raise AttributeRequestError('EncodingLimitExceeded', 'semantic_context_budget')
    hard = value['hard_intent']
    if hard:
        hard = AttributeIntent.capture(mapping['normalized_text'], None, AttributeConditions.from_dict(hard['conditions']), hard['spans'], grammar, hard['policy_sha256']).to_dict()
    optional = value['optional']
    context_spans = [{'slot':name,'value':slot['values'],'normalized_start':s['start'],'normalized_end':s['end'],**original_span(mapping,s['start'],s['end'])}
        for name,slot in value['request']['context'].items() if isinstance(slot,dict) and 'spans' in slot for s in slot['spans']]
    result = {**value,'version':'mixed-semantic-context-intent-1.0.0','grammar_version':GRAMMAR,'grammar_sha256':grammar,
              'base_contextual_grammar':archived.GRAMMAR,'normalization':mapping,'hard_intent':hard,
              'original_hard_spans':[{**s,**original_span(mapping,s['start'],s['end'])} for s in hard['spans']] if hard else [],
              'original_optional_spans':[{**s,**original_span(mapping,s['start'],s['end'])} for s in optional['spans']] if optional else [],
              'original_context_spans':context_spans}
    result.pop('revision')
    result['revision'] = digest(result)
    return result
