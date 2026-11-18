"""Additive contextual composition; archived grammar 1.9 is never rewritten."""
from pathlib import Path
import re
from app.application.nlp.compositional_input_v1 import normalize
from app.application.nlp.compositional_request_v1 import CompositionalIntent, identity as base_identity
from app.application.nlp.normalized_request_v1 import base_parse
from app.application.nlp.natural_input_v1 import original_span
from app.domain.value_objects.attribute_conditions import AttributeRequestError, digest
from app.domain.value_objects.request_local_preference import resolution_for

GRAMMAR = 'mixed-contextual-composition-1.0.0'


def identity():
    from app.shared_contracts.grammar_identity import semantic_fingerprint
    from .context_contract import GRAMMAR_SHA256
    actual = semantic_fingerprint((GRAMMAR.encode(), bytes.fromhex(base_identity()), Path(__file__).read_bytes()))
    if actual != GRAMMAR_SHA256:
        raise ValueError('Unregistered mixed contextual grammar.')
    return actual


def contextual(raw):
    from app.application.nlp.conversational_context_interpreter import ConversationalContextInterpreter, outside_literals
    text = outside_literals(normalize(raw)['normalized_text'])
    return any(pattern.search(text) for _, pattern in ConversationalContextInterpreter().anchors)


def refuse(reason):
    raise AttributeRequestError('UnsupportedRequest', reason)


def document(raw):
    mapping = normalize(raw)
    text = mapping['normalized_text']
    # Only one explicit, positive, role-bound wish; no implicit colour target.
    markers = list(re.finditer(r"(?:,\s*|\s+(?:and|but)\s+)(?P<marker>preferably(?:\s+(?:wearing|with))?|(?:i'd|i) prefer)\s+", text))
    optional = None
    work = text
    if len(markers) > 1:
        refuse('multiple_compositional_preferences')
    if markers:
        m = markers[0]
        end = len(text.rstrip('.!? '))
        wish = text[m.end():end]
        prefix = "I'd prefer "
        parsed = CompositionalIntent.capture(prefix + wish).to_dict()
        if parsed['hard_intent'] or parsed['request'].get('context') or not parsed['optional']:
            refuse('unsupported_compositional_preference')
        optional = parsed['optional']
        for span in optional['spans']:
            if span['target'] == 'marker':
                a, b = m.start('marker'), m.end('marker')
            else:
                a, b = m.end() + span['start'] - len(prefix), m.end() + span['end'] - len(prefix)
            if not 0 <= a < b <= len(text):
                refuse('invalid_contextual_preference_span')
            span.update(start=a, end=b, text=text[a:b])
        work = text[:m.start()] + ' ' * (len(text) - m.start())
    # A full existing parse is preferred. Only an explicit clause boundary
    # licenses separate context + compositional hard clauses after a refusal.
    try:
        parsed = base_parse(work)
    except AttributeRequestError as error:
        cuts = list(re.finditer(r'\s*[,;]\s*|\s+but\s+', work))
        recovered = None
        for cut in cuts:
            left, right = work[:cut.start()], work[cut.end():].strip()
            if not right or not contextual(left) or contextual(right):
                continue
            context_part = base_parse(left + ' ' * (len(work) - len(left)))
            hard_part = CompositionalIntent.capture(right).to_dict()
            if context_part['hard'] or 'context' not in context_part['request'] or hard_part['optional'] or 'context' in hard_part['request'] or not hard_part['hard_intent']:
                continue
            if any(hard_part['request'][k] is not None for k in ('occasion', 'style', 'colours', 'garment_categories', 'formality')):
                continue
            shift = work.find(right, cut.end())
            hard = hard_part['hard_intent']
            for span in hard['spans']:
                span.update(start=shift + span['start'], end=shift + span['end'])
                span['text'] = text[span['start']:span['end']]
            recovered = {**context_part, 'hard': hard}
            break
        if recovered is None:
            raise error
        parsed = recovered
    if 'context' not in parsed['request'] or parsed['local']:
        refuse('unsupported_mixed_context_combination')
    hard = parsed['hard']
    if hard:
        from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
        from app.domain.value_objects.attribute_conditions import AttributeConditions
        hard = AttributeIntent.capture(text, None, AttributeConditions.from_dict(hard['conditions']), hard['spans'], identity(), hard['policy_sha256']).to_dict()
    if optional:
        positives = [g for g in hard['conditions']['groups'] if g['quantifier'] == 'exists' and g['role'] == optional['role']] if hard else []
        if len(positives) == 1:
            optional['binding'] = {'kind': 'mandatory_group', 'group_id': positives[0]['id']}
        from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
        # Only conditions are needed by conflict resolution; the original
        # archived hard-intent bytes remain intact in the new outer envelope.
        bound = AttributeIntent.from_dict(hard) if hard else None
        optional['resolution'] = resolution_for(bound, optional['role'], optional['binding'], optional['predicates'])
    from app.application.recommendation.attribute_preference_codec import restore_request
    from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
    request = restore_request(parsed['request'])
    evaluator = EvaluatorSpecification.current('context_18_v1').construct()
    if not evaluator.supports(request):
        plan = evaluator.plan(request)
        reason = plan.reason
        if reason == 'required_context_missing':
            binding = evaluator.registry.binding_for(request.context.situation.value)
            if binding and request.context.role.state != 'Known' and 'role' in binding.required_context:
                refuse('language_context_clarification')
            if binding and binding.appearance_required and request.formality is None:
                refuse('mixed_context_dress_code_required')
            refuse('language_context_clarification')
        refuse('unsupported_context_' + reason)
    context_spans = [
        {'slot': name, 'value': slot['values'], 'normalized_start': s['start'], 'normalized_end': s['end'], **original_span(mapping, s['start'], s['end'])}
        for name, slot in parsed['request']['context'].items() if isinstance(slot, dict) and 'spans' in slot
        for s in slot['spans']
    ]
    value = {'version': 'mixed-contextual-intent-1.0.0', 'grammar_version': GRAMMAR, 'grammar_sha256': identity(),
             'base_grammar_version': 'conversational-compositional-grammar-1.9.0', 'normalization': mapping,
             'request': parsed['request'], 'hard_intent': hard, 'optional': optional,
             'original_hard_spans': [{**s, **original_span(mapping, s['start'], s['end'])} for s in hard['spans']] if hard else [],
             'original_optional_spans': [{**s, **original_span(mapping, s['start'], s['end'])} for s in optional['spans']] if optional else [],
             'original_context_spans': context_spans}
    value['revision'] = digest(value)
    return value
