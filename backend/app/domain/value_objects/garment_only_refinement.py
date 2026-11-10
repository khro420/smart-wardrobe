"""Separate pure-B1 continuation identity, reusing the bounded common plan fields."""
from dataclasses import dataclass
from fractions import Fraction
from app.domain.value_objects.recommendation_refinement import RefinementPlan,RefinementAction,canonical_uuid,digest
PROFILE='garment_only_refinement_v1'
KEY='garment_refinement'
VERSION='garment-only-refinement-evidence-1.0.0'

def step_key(root,ordinal):
    canonical_uuid(root)
    if type(ordinal) is not int or not 1<=ordinal<=9:raise ValueError('Invalid garment continuation step.')
    return f'garment-refine:v1:{root}:{ordinal:02d}'

@dataclass(frozen=True)
class GarmentRefinementPlan(RefinementPlan):
    def __post_init__(self):
        super().__post_init__()
        if self.attribute_intent is None or self.wearer_profile_id is None:raise ValueError('Captured B1 wearer required.')
        if self.ordinal and self.root_R!=Fraction(0):raise ValueError('Pure-B1 contribution floor must remain zero.')
    @property
    def mode(self):return 'garment_contribution_floor_base_distinct_v1'
    @property
    def selection_scope_sha256(self):
        return digest({'contract':VERSION,'common_selection':super().selection_scope_sha256})

@dataclass(frozen=True)
class GarmentRefinementDraft:
    plan:GarmentRefinementPlan
    action:RefinementAction|None
    garment_snapshot_sha256:str
    preference_snapshot_sha256:str
    request_sha256:str
    def __post_init__(self):
        from app.domain.value_objects.context_relevance import require_digest
        if type(self.plan) is not GarmentRefinementPlan:raise ValueError('Garment plan required.')
        for value in (self.garment_snapshot_sha256,self.preference_snapshot_sha256,self.request_sha256):require_digest(value)
        if self.action is not None and type(self.action) is not RefinementAction:raise ValueError('Typed action required.')
        if self.plan.ordinal:
            if self.action is None or self.action.kind!='alternative' or self.action.parent_recommendation_id!=self.plan.parent_id:raise ValueError('Child action mismatch.')
        elif self.action is not None and (self.action.kind!='initial' or self.action.excluded_categories!=self.plan.exclusions):raise ValueError('Root action mismatch.')
