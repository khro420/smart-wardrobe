"""Paired opt-in interpretation and evaluation, never a scoring selection."""
import os
from app.application.nlp.contextual_nlp_interpreter import ContextualNLPInterpreter
from app.application.recommendation.contextual_suitability_evaluator import ContextualSuitabilityEvaluator


def contextual_selection():
    profile = os.getenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE', 'disabled')
    bundle_id=os.getenv('SMART_WARDROBE_ASSISTANT_CONTEXT_BUNDLE','legacy_8_v1')
    if bundle_id not in ('legacy_8_v1','context_18_v1') or bundle_id!='legacy_8_v1' and (profile!='general_context_v1' or os.getenv('SMART_WARDROBE_ASSISTANT_CONTEXT_RANKING_PROFILE')!='context_relevance_decision_v1'):
        raise ValueError('Invalid context expansion selection.')
    if profile == 'disabled':
        return None
    if (profile not in ('wedding_guest_v1', 'general_context_v1')
            or any(os.getenv('SMART_WARDROBE_' + flag, 'false').lower() != 'true'
                   for flag in ('ASSISTANT_ENABLED', 'ASSISTANT_SUITABILITY_ENABLED'))):
        raise ValueError('Invalid or incomplete contextual Assistant configuration.')
    if profile == "general_context_v1":
        from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
        from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
        specification = EvaluatorSpecification.current(bundle_id)
        specification.construct()
        return GeneralContextInterpreter(bundle_id), specification.construct
    # Validate the new policy before startup readiness.
    ContextualSuitabilityEvaluator()
    return ContextualNLPInterpreter(), ContextualSuitabilityEvaluator
