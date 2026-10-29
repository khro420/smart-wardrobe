"""Server-only execution selection, independent of the scoring profile."""
from dataclasses import dataclass
from app.application.recommendation.rule_based_compatibility_policy import digest
from app.application.recommendation.compact_assistant_scorer import CompactAssistantScorer,execution_context

REFERENCE='reference'
COMPACT='compact_exhaustive'
DEFAULT_ENGINE=COMPACT
ENVIRONMENT_KEY='SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE'


@dataclass(frozen=True)
class AssistantExecutionSelection:
    engine: str = DEFAULT_ENGINE
    version: str = 'assistant-execution-selection-1.0.0'

    def __post_init__(self):
        if self.engine not in (REFERENCE,COMPACT) or self.version!='assistant-execution-selection-1.0.0':
            raise ValueError('Unknown Assistant execution configuration.')

    @property
    def provenance(self):
        implementation=CompactAssistantScorer.implementation if self.engine==COMPACT else 'retained-reference'
        value={'version':self.version,'engine':self.engine,'implementation':implementation}
        return {**value,'hash':digest(value)}

    def scorer(self,scoring,candidates,preferences,reference_factory):
        if self.engine==REFERENCE:
            return scoring.scorer(candidates,preferences,reference_factory)
        return CompactAssistantScorer(candidates,preferences,scoring.profile,context_ranking=scoring.context_ranking!='disabled')

    def context(self,scorer,candidates,engine,user_id,request,ranked):
        context=scorer.prepared_context if self.engine==COMPACT else execution_context(candidates.session,engine,user_id,request)
        if context is None:raise ValueError('Missing prepared execution context.')
        context.validate_winner(user_id,request,ranked)
        return context

    @property
    def refinement_implementation(self):
        return 'compact-refinement-1.0.0' if self.engine==COMPACT else 'reference-refinement-1.0.0'
