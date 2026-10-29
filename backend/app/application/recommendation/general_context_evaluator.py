"""One context evaluator, configured by an immutable validated server bundle."""
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
from app.application.recommendation.context_policy_registry import ContextPolicyRegistry
from app.application.recommendation.context_constraint_compiler import compile_context
from app.application.recommendation.context_evidence_resolver import ContextEvidenceResolver
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.domain.value_objects.general_context_request import GeneralContextRequest
from app.domain.value_objects.request_candidate_evaluation import MandatoryCondition, RequestEvaluation


@dataclass(frozen=True)
class EvaluatorSpecification:
    registry_sha256: str
    taxonomy_sha256: str
    grammar_sha256: str
    version: str = 'general-evaluator-spec-1.0.0'
    bundle_id: str = 'legacy_8_v1'

    @classmethod
    def current(cls, bundle_id='legacy_8_v1'):
        registry = ContextPolicyRegistry.load(bundle_id=bundle_id)
        if bundle_id!='legacy_8_v1':
            from app.application.recommendation.context_bundle import ContextBundle
            return cls(registry.hash,registry.taxonomy_hash,ContextBundle.load(bundle_id).record['grammar_sha256'],bundle_id=bundle_id)
        grammar = Path(__file__).parents[1]/'nlp/config/context_grammar.v1.json'
        return cls(registry.hash, registry.taxonomy_hash, hashlib.sha256(grammar.read_bytes()).hexdigest())

    def construct(self):
        if type(self) is not EvaluatorSpecification or self.version != 'general-evaluator-spec-1.0.0':
            raise ValueError('Unapproved evaluator specification.')
        registry = ContextPolicyRegistry.load(bundle_id=self.bundle_id)
        if self != type(self).current(self.bundle_id):
            raise ValueError('Evaluator bundle mismatch.')
        return GeneralContextEvaluator(registry, self)


class GeneralContextEvaluator:
    def __init__(self, registry=None, specification=None):
        bundle_id=specification.bundle_id if specification is not None else registry.bundle_id if registry is not None else 'legacy_8_v1'
        actual = ContextPolicyRegistry.load(bundle_id=bundle_id)
        if registry is not None and registry != actual:
            raise ValueError('Unapproved registry instance.')
        self.registry = actual
        self.specification = specification or EvaluatorSpecification.current(bundle_id)
        if self.specification != EvaluatorSpecification.current(bundle_id):
            raise ValueError('Invalid evaluator bundle.')
        self.legacy = SuitabilityRequestEvaluator()
        self.minimum, self.mapper = self.legacy.minimum, self.legacy.mapper
        self.policy = actual
        self.resolver = ContextEvidenceResolver(self.legacy)
        self._prepared_request = None
        self._plan = None

    def plan(self, request):
        if request.context.grammar_sha256 != self.specification.grammar_sha256:
            raise ValueError('Unverified interpretation grammar.')
        if self._prepared_request != request:
            self._plan = compile_context(self.registry, request)
            self._prepared_request = request
        return self._plan

    def supports(self, request):
        if not isinstance(request, GeneralContextRequest):
            return self.legacy.supports(request)
        return self.plan(request).available and self.minimum.supports(request.minimum_request())

    def member_condition(self, garment, request, field):
        if not isinstance(request, GeneralContextRequest):
            return self.legacy.parser.parse(garment).state_for(field, getattr(request, field)), 'owner_declaration', None
        plan = self.plan(request)
        if not plan.available:
            raise ValueError('Unavailable contextual capability.')
        results=[self.resolver.resolve(garment,request,field,plan)]
        results.extend(self.resolver.resolve(garment,other,field,second) for other,second in plan.secondary)
        return next((result for state in ('Fail','Unknown','Pass') for result in results if result[0]==state))

    def evaluate(self, candidate, request):
        if not isinstance(request, GeneralContextRequest):
            return self.legacy.evaluate(candidate, request)
        if not self.supports(request):
            raise ValueError('Context policy unavailable.')
        conditions = list(self.minimum.evaluate(candidate, request.minimum_request()).conditions)
        for field in ('occasion', 'formality'):
            value = getattr(request, field)
            if value is None:
                continue
            members = [(m.garment.garment_id, self.member_condition(m.garment, request, field)[0]) for m in candidate.members]
            state = 'Fail' if any(s == 'Fail' for _, s in members) else 'Unknown' if any(s == 'Unknown' for _, s in members) else 'Pass'
            conditions.append(MandatoryCondition(field, value, state, tuple(gid for gid, s in members if s == state)))
        return RequestEvaluation(tuple(conditions))

    def summary(self, request):
        plan = self.plan(request)
        frame = request.context
        unavailable = []
        if not plan.available:
            names = ('role',) if plan.reason == 'unsupported_role' else ('dress_code', 'formality') if plan.reason == 'unsupported_dress_code' else ('venue', 'environment', 'soft_preferences', 'goals', 'companions') if plan.reason == 'unsupported_constraint' else ('situation',)
            unavailable = [name+': '+', '.join(getattr(frame, name).values) for name in names if getattr(frame, name).values]
        summary = {'version': 'general-context-explanation-1.0.0', 'situation': frame.situation.value,
                'label': next(s.label for s in self.registry.situations if s.identifier == frame.situation.value),
                'reason': plan.reason, 'assumptions': list(plan.assumptions),
                'dress_code': frame.dress_code.value, 'formality': frame.formality.value,
                'temporal': list(frame.temporal.values), 'available': plan.available,
                'unavailable_conditions': unavailable,
                'registry_sha256': self.registry.hash, 'taxonomy_sha256': self.registry.taxonomy_hash,
                'context': asdict(frame)}
        binding = self.registry.binding_for(frame.situation.value)
        if binding is not None and binding.declaration_source == 'legacy_exact_declarations_v1':
            summary.update(version='general-context-explanation-1.1.0', binding=binding.identifier,
                           policy_version=binding.policy_version, declaration_target=binding.declaration_target,
                           venue=frame.venue.value, companions=list(frame.companions.values),
                           policy_note=binding.unspecified_note if plan.available and request.formality is None else None,
                           limits_note=binding.limits_note)
        if binding is not None and binding.declaration_source == 'parent_negative_only_v1':
            missing = [name for name in binding.required_context if getattr(frame,name).state != 'Known']
            if binding.appearance_required and request.formality is None:
                missing.append('dress_code or requested formality')
            summary.update(version='general-context-explanation-1.2.0', binding=binding.identifier, policy_version=binding.policy_version,
                           declaration_target=binding.declaration_target, role=frame.role.value, venue=frame.venue.value,
                           parent_negative=binding.parent_negative, missing_context=missing,
                           policy_note=dict(binding.role_notes).get(frame.role.value) if plan.available and request.formality is None else None,
                           limits_note=binding.limits_note)
        if binding is not None and binding.identifier in ('campus_day_appearance_v1', 'shopping_appearance_v1', 'casual_outing_appearance_v1'):
            summary.update(version='general-context-explanation-1.3.0',
                           scope_note='Class is interpreted as ordinary academic attendance; no student role, lab, PE or uniform requirement is inferred.' if binding.declaration_target == 'campus' else 'Only ordinary '+('shopping' if binding.declaration_target == 'shopping' else 'casual outings')+' are supported; no specialised activity requirements are inferred.')
        if binding is not None and binding.evidence_contract == 'saved_singleton_style_provisional_v1':
            summary.update(version='general-context-explanation-1.4.0', evidence_contract=binding.evidence_contract)
        if self.specification.bundle_id!='legacy_8_v1' and binding is not None and binding.evidence_contract=='saved_singleton_style_provisional_v1':
            summary.update(version='general-context-explanation-2.0.0',bundle_id=self.specification.bundle_id,
                binding=binding.identifier if binding else None,policy_version=binding.policy_version if binding else None,
                venue=frame.venue.value,companions=list(frame.companions.values),facets=list(frame.facets.values),
                negative_scope=binding.parent_negative if binding else None,
                secondary_bindings=[second.binding.identifier for _,second in plan.secondary],
                policy_note=binding.unspecified_note if binding else None,limits_note=binding.limits_note if binding else None)
        return summary

    def explain(self, candidate, request):
        def condition(garment, field):
            result = self.member_condition(garment, request, field)
            proof = {'field': field, 'state': result[0], 'basis': result[1], 'rule': result[2]}
            binding = self.plan(request).binding
            if self.specification.bundle_id!='legacy_8_v1':
                proof['binding_results']=[dict(binding=p.binding.identifier,target=p.binding.declaration_target,negative_scope=p.binding.parent_negative,
                    state=(r:=self.resolver.resolve(garment,req,field,p))[0],basis=r[1],rule=r[2]) for req,p in ((request,self.plan(request)),*self.plan(request).secondary)]
            if binding.declaration_source == 'legacy_exact_declarations_v1':
                proof.update(declaration_target={'field': field, 'value': getattr(request, field)},
                             declaration_policy=self.legacy.policy.version,
                             supporting_declarations=[asdict(d) for d in self.legacy.parser.parse(garment).declarations
                                 if d.field == field and d.value == getattr(request, field)])
            if binding.declaration_source == 'parent_negative_only_v1':
                target = binding.parent_negative if field == 'occasion' else getattr(request,field)
                proof.update(declaration_target={'field':field,'value':getattr(request,field)},
                             negative_scope={'field':field,'value':target}, declaration_policy=self.legacy.policy.version,
                             supporting_declarations=[asdict(d) for d in self.legacy.parser.parse(garment).declarations if d.field == field and d.value == target],
                             parent_allow_is_not_child_permission=field == 'occasion')
            return proof
        def saved_source(garment):
            if self.plan(request).binding.evidence_contract != 'saved_singleton_style_provisional_v1':
                return {}
            review = garment.contextual_suitability
            style = self.mapper.classify(garment).style
            reviewed = (review.review_state == 'Known' and style.state == 'Known' and len(style.values) == 1
                        and review.reviewed_styles == style.values and review.reviewed_category == garment.category)
            return {'saved_attribute_evidence': asdict(garment.saved_attribute_evidence),
                    'style_verification': 'owner_reviewed_current' if reviewed else 'saved_unreviewed'}
        return {**self.summary(request), 'members': [
            {'garment_id': m.garment.garment_id, 'review': asdict(m.garment.contextual_suitability),
             **saved_source(m.garment),
             **({'appearance_observations':asdict(m.garment.appearance_evidence), 'appearance_current':m.garment.appearance_evidence.current(m.garment)}
                 if self.plan(request).binding.appearance_required else {}),
             'observed_styles': asdict(self.mapper.classify(m.garment).style), 'conditions': [
                condition(m.garment, field)
                for field in ('occasion', 'formality') if getattr(request, field) is not None]}
            for m in candidate.members]}


def evaluator_selector(evaluator):
    return evaluator.specification if type(evaluator) is GeneralContextEvaluator else type(evaluator)


def construct_evaluator(selector):
    from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
    from app.application.recommendation.contextual_suitability_evaluator import ContextualSuitabilityEvaluator
    if type(selector) is EvaluatorSpecification:
        return selector.construct()
    if selector not in (RequestConstraintEvaluator, SuitabilityRequestEvaluator, ContextualSuitabilityEvaluator):
        raise ValueError('Unapproved evaluator construction.')
    return selector()
