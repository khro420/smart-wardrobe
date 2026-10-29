"""Opt-in W01-W05, with declarations authoritative and absent evidence distinct."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.domain.value_objects.contextual_outfit_request import ContextualOutfitRequest
from app.domain.value_objects.request_candidate_evaluation import MandatoryCondition, RequestEvaluation

POLICY = Path(__file__).with_name('config') / 'wedding_guest_suitability.v1.json'


class WeddingPolicy:
    def __init__(self):
        raw = POLICY.read_bytes()
        data = json.loads(raw)
        if (data['version'] != 'wedding-guest-suitability-1.0.0' or data['default_activation'] is not False
                or data['rules'] != {'W01': {'dress_code': None, 'reviewed_style': 'smart casual'},
                    'W02': {'dress_code': 'smart_casual', 'reviewed_style': 'smart casual'},
                    'W03': {'dress_code': 'casual', 'reviewed_style': 'casual'}}):
            raise ValueError('Unsupported contextual policy.')
        self.version, self.hash = data['version'], hashlib.sha256(raw).hexdigest()


class ContextualSuitabilityEvaluator:
    def __init__(self):
        self.legacy = SuitabilityRequestEvaluator()
        self.minimum, self.mapper = self.legacy.minimum, self.legacy.mapper
        self.policy = WeddingPolicy()

    def supports(self, request):
        if not isinstance(request, ContextualOutfitRequest):
            return self.legacy.supports(request)
        return (request.context.role in ('guest', 'unspecified')
                and request.formality in (None, 'casual', 'smart_casual')
                and self.minimum.supports(request.minimum_request()))

    def member_condition(self, garment, request, field):
        if not isinstance(request, ContextualOutfitRequest):
            state = self.legacy.parser.parse(garment).state_for(field, getattr(request, field))
            return state, 'owner_declaration', None
        evidence = garment.contextual_suitability
        legacy = self.legacy.parser.parse(garment)
        relevant = tuple(d.decision for d in legacy.declarations
                         if d.field == field and d.value == getattr(request, field)) if field == 'formality' else ()
        decisions = evidence.wedding_decisions if field == 'occasion' else relevant
        if 'deny' in decisions:
            return 'Fail', 'explicit_deny', None
        # A corrupt reserved collection blocks inference for either condition.
        malformed = (legacy.source_state == 'Malformed' or field in legacy.malformed_fields
                     or evidence.state == 'Malformed')
        if malformed:
            return 'Unknown', 'malformed_declaration', 'W04'
        if decisions == ('allow',) or set(decisions) == {'allow'}:
            return 'Pass', 'explicit_allow', None
        style = self.mapper.classify(garment).style
        valid = (evidence.review_state == 'Known' and style.state == 'Known'
                 and evidence.reviewed_category == garment.category
                 and evidence.reviewed_styles == style.values
                 and len(style.values) == 1)
        expected = 'casual' if request.formality == 'casual' else 'smart casual'
        if not valid or style.values != (expected,):
            return 'Unknown', 'insufficient_reviewed_attributes', 'W04'
        rule = 'W03' if request.formality == 'casual' else 'W02' if request.formality == 'smart_casual' else 'W01'
        return 'Pass', 'reviewed_attribute_inference', rule

    def evaluate(self, candidate, request):
        if not isinstance(request, ContextualOutfitRequest):
            return self.legacy.evaluate(candidate, request)
        if not self.supports(request):
            raise ValueError('Contextual policy unavailable.')
        conditions = list(self.minimum.evaluate(candidate, request.minimum_request()).conditions)
        for field in ('occasion', 'formality'):
            value = getattr(request, field)
            if value is None:
                continue
            members = [(m.garment.garment_id, self.member_condition(m.garment, request, field)[0]) for m in candidate.members]
            state = 'Fail' if any(s == 'Fail' for _, s in members) else 'Unknown' if any(s == 'Unknown' for _, s in members) else 'Pass'
            conditions.append(MandatoryCondition(field, value, state, tuple(gid for gid, s in members if s == state)))
        return RequestEvaluation(tuple(conditions))

    def explain(self, candidate, request):
        return {'version': self.policy.version, 'policy_sha256': self.policy.hash,
                'context': asdict(request.context), 'members': [
                    {'garment_id': member.garment.garment_id,
                     'review': asdict(member.garment.contextual_suitability),
                     'conditions': [{'field': field, 'state': result[0], 'basis': result[1], 'rule': result[2]}
                         for field in ('occasion', 'formality') if getattr(request, field) is not None
                         for result in [self.member_condition(member.garment, request, field)]]}
                    for member in candidate.members]}
