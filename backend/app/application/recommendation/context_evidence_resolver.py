"""Resolve admitted observations without scores, defaults or model-confidence guesses."""
class ContextEvidenceResolver:
    def __init__(self, legacy):
        self.legacy = legacy
        self.mapper = legacy.mapper

    def resolve(self, garment, request, field, plan):
        evidence = garment.contextual_suitability
        declarations = self.legacy.parser.parse(garment)
        # Adapter for the existing v1 namespace; no inferred parent occasion.
        channels = {'wedding': evidence.wedding_decisions}
        professional = plan.binding.declaration_source == 'parent_negative_only_v1'
        ordinary_parent=plan.binding.declaration_source=='ordinary_parent_negative_v1'
        legacy_source = plan.binding.declaration_source == 'legacy_exact_declarations_v1'
        decisions = (tuple(d.decision for d in declarations.declarations if d.field == 'occasion' and d.value == plan.binding.parent_negative) if field == 'occasion' and (professional or ordinary_parent) else
                     channels[plan.binding.declaration_target] if field == 'occasion' and not legacy_source else
                     tuple(d.decision for d in declarations.declarations if d.field == field and d.value == getattr(request, field)))
        if 'deny' in decisions:
            return 'Fail', 'explicit_deny', None
        if declarations.source_state == 'Malformed' or field in declarations.malformed_fields or evidence.state == 'Malformed':
            return 'Unknown', 'malformed_declaration', plan.binding.unknown_rule
        if decisions and set(decisions) == {'allow'} and not ((professional or ordinary_parent) and field == 'occasion'):
            return 'Pass', 'explicit_declaration' if legacy_source or professional else 'explicit_allow', None
        if decisions and not ((professional or ordinary_parent) and field == 'occasion' and set(decisions) == {'allow'}):
            return 'Unknown', 'malformed_declaration', plan.binding.unknown_rule
        if professional and field == 'occasion' and plan.binding.appearance_required and garment.appearance_evidence.current(garment) and garment.appearance_evidence.condition == 'needs_attention':
            return 'Fail','recorded_condition_needs_attention','IP06'
        style = self.mapper.classify(garment).style
        valid = (evidence.review_state == 'Known' and style.state == 'Known'
                 and evidence.reviewed_category == garment.category
                 and evidence.reviewed_styles == style.values and len(style.values) == 1)
        if plan.binding.evidence_contract == 'saved_singleton_style_provisional_v1':
            source = garment.saved_attribute_evidence
            if evidence.review_state == 'Malformed':
                return 'Unknown', 'malformed_style_review', plan.binding.unknown_rule
            if source.state != 'Absent' and not source.current(garment):
                return 'Unknown', 'stale_or_malformed_saved_source', plan.binding.unknown_rule
            if style.state != 'Known' or len(style.values) != 1:
                return 'Unknown', 'insufficient_saved_style', plan.binding.unknown_rule
            if style.values[0] not in plan.predicate.value:
                return 'Unknown', 'uncovered_saved_style', plan.binding.unknown_rule
            return 'Pass', 'attribute_inference' if valid else 'saved_attribute_provisional', plan.predicate.identifier
        if not valid:
            return 'Unknown', 'insufficient_reviewed_attributes', plan.binding.unknown_rule
        if professional:
            return self._expression(garment, style.values, request, field, plan)
        allowed = plan.predicate.value if plan.predicate.operator == 'reviewed_style_in' else (plan.predicate.value,)
        if style.values[0] not in allowed:
            return 'Unknown', 'uncovered_reviewed_style' if legacy_source else 'insufficient_reviewed_attributes', plan.binding.unknown_rule
        return 'Pass', 'attribute_inference' if legacy_source else 'reviewed_attribute_inference', plan.predicate.identifier

    def _expression(self, garment, styles, request, field, plan):
        if field == 'formality':
            expected = ('casual',) if request.formality == 'casual' else ('smart casual',)
            return ('Pass','attribute_inference',plan.predicate.identifier) if styles == expected else ('Unknown','uncovered_reviewed_style',plan.binding.unknown_rule)
        from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
        role = {'top':'upper','bottom':'lower','dress':'one_piece','outerwear':'outerwear'}.get(GARMENT_STRUCTURE.get(garment.category,(None,None))[0])
        appearance = garment.appearance_evidence
        current = appearance.current(garment)
        if plan.binding.appearance_required and current and appearance.condition == 'needs_attention':
            return 'Fail','recorded_condition_needs_attention','IP06'
        def reduce(node):
            if node[0] in ('all','any'):
                states = tuple(reduce(child) for child in node[1])
                if node[0] == 'all':
                    return 'Fail' if 'Fail' in states else 'Unknown' if 'Unknown' in states else 'Pass'
                return 'Pass' if 'Pass' in states else 'Unknown' if 'Unknown' in states else 'Fail'
            if node[0] == 'reviewed_style_in':
                return 'Pass' if len(styles) == 1 and styles[0] in node[1] else 'Unknown'
            value = appearance.condition if node[1] == 'condition_observation' else dict(appearance.features).get(node[1])
            return 'Pass' if current and value == node[2] and type(value) is type(node[2]) else 'Unknown'
        tree = dict(plan.predicate.expressions).get(role)
        state = reduce(tree) if tree is not None else 'Unknown'
        return state,'attribute_inference' if state == 'Pass' else 'insufficient_reviewed_attributes',plan.predicate.identifier if state == 'Pass' else plan.binding.unknown_rule
