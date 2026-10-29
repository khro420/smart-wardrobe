"""Immutable, request-scoped refinement intent; no account preference mutation."""
from dataclasses import dataclass
from uuid import UUID
from fractions import Fraction
import hashlib
import json

CATEGORY_VERSION = 'garment-category-exclusions-1.0.0'
REQUEST_VERSION = 'assistant-refinement-request-1.0.0'
POLICY_VERSION = 'recommendation-refinement-policy-1.0.0'
PROFILE = 'optional_refinement_v1'
CATEGORIES = tuple(sorted((
    'short_sleeve_top', 'long_sleeve_top', 'vest', 'sling',
    'short_sleeve_outwear', 'long_sleeve_outwear', 'shorts', 'trousers', 'skirt',
    'short_sleeve_dress', 'long_sleeve_dress', 'vest_dress', 'sling_dress',
)))
SHORTCUTS = (
    ('Dresses', tuple(c for c in CATEGORIES if c.endswith('_dress'))),
    ('Shorts', ('shorts',)), ('Trousers', ('trousers',)),
    ('Outerwear', tuple(c for c in CATEGORIES if c.endswith('_outwear'))),
)


class RefinementError(ValueError):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status, self.reason = status, reason


def canonical_categories(value):
    if type(value) is not list or len(value) > 13 or any(type(c) is not str or c not in CATEGORIES for c in value):
        raise ValueError('Use a list of canonical garment category IDs.')
    if len(set(value)) != len(value):
        raise ValueError('Duplicate excluded category.')
    return tuple(sorted(value))


def canonical_uuid(value):
    if type(value) is not str:
        raise ValueError('A canonical recommendation UUID is required.')
    try:
        valid = str(UUID(value)) == value
    except (ValueError, AttributeError):
        valid = False
    if not valid:
        raise ValueError('A canonical recommendation UUID is required.')
    return value


@dataclass(frozen=True)
class RefinementAction:
    kind: str
    excluded_categories: tuple[str, ...] = ()
    parent_recommendation_id: str | None = None

    def __post_init__(self):
        if self.kind == 'initial':
            if self.parent_recommendation_id is not None:
                raise ValueError('An initial action cannot name a parent.')
            canonical = canonical_categories(list(self.excluded_categories))
            object.__setattr__(self, 'excluded_categories', canonical)
        elif self.kind == 'alternative':
            if self.excluded_categories:
                raise ValueError('Changed exclusions require a fresh initial request.')
            canonical_uuid(self.parent_recommendation_id)
        else:
            raise ValueError('Unsupported refinement action.')

    @classmethod
    def parse(cls, raw):
        if type(raw) is not dict or raw.get('version') != REQUEST_VERSION:
            raise ValueError('Unsupported refinement request.')
        if raw.get('kind') == 'initial' and set(raw) == {'version', 'kind', 'excluded_categories'}:
            return cls('initial', canonical_categories(raw['excluded_categories']))
        if raw.get('kind') == 'alternative' and set(raw) == {'version', 'kind', 'parent_recommendation_id'}:
            return cls('alternative', parent_recommendation_id=canonical_uuid(raw['parent_recommendation_id']))
        raise ValueError('Invalid refinement action fields.')

    def to_dict(self):
        result = {'version': REQUEST_VERSION, 'kind': self.kind}
        if self.kind == 'initial':
            result['excluded_categories'] = list(self.excluded_categories)
        else:
            result['parent_recommendation_id'] = self.parent_recommendation_id
        return result


def step_key(root_id, ordinal):
    canonical_uuid(root_id)
    if type(ordinal) is not int or not 1 <= ordinal <= 9:
        raise ValueError('Alternative step must be 01 through 09.')
    return f'refine:v1:{root_id}:{ordinal:02d}'


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class RefinementPlan:
    """Trusted prepared selection, never parsed from a client request."""
    exclusions: tuple[str, ...] = ()
    root_id: str | None = None
    parent_id: str | None = None
    ordinal: int = 0
    root_R: Fraction | None = None
    root_total: Fraction | None = None
    seen: tuple = ()
    compatibility_scope_sha256: str = '0' * 64

    def __post_init__(self):
        from app.domain.value_objects.context_relevance import require_digest
        object.__setattr__(self,'exclusions',canonical_categories(list(self.exclusions)))
        require_digest(self.compatibility_scope_sha256)
        if type(self.ordinal) is not int or not 0 <= self.ordinal <= 9:
            raise ValueError('Invalid refinement ordinal.')
        if type(self.seen) is not tuple or len(self.seen)!=self.ordinal or len(set(self.seen))!=len(self.seen):
            raise ValueError('Invalid seen bases.')
        for signature in self.seen:
            if type(signature) is not tuple or tuple(x[0] for x in signature) not in (('one_piece',),('upper','lower')) or any(type(x) is not tuple or len(x)!=2 or type(x[1]) is not str or not x[1] for x in signature):
                raise ValueError('Invalid exact base signature.')
        if self.ordinal:
            canonical_uuid(self.root_id); canonical_uuid(self.parent_id)
            if any(type(v) is not Fraction or not 0<=v<=1 for v in (self.root_R,self.root_total)):
                raise ValueError('Original relative floor and total required.')
        elif self.parent_id is not None or self.root_R is not None or self.root_total is not None or self.root_id is not None:
            raise ValueError('Initial identity/floor must be allocated from its committed result.')

    @property
    def mode(self):
        return 'same_R_floor_base_distinct_v1' if self.ordinal else 'initial_permitted_optimum_v1'

    @property
    def selection_scope_sha256(self):
        from app.domain.value_objects.context_relevance import ratio
        return selection_digest(self.compatibility_scope_sha256,self.root_id,self.parent_id,self.ordinal,
                                self.mode,ratio(self.root_R),digest(self.seen),len(self.seen))


def selection_digest(scope,root,parent,ordinal,mode,floor,seen_hash,seen_count):
    return digest(dict(compatibility_scope_sha256=scope,root_id=root,parent_id=parent,
        ordinal=ordinal,mode=mode,root_R=floor,seen_sha256=seen_hash,seen_count=seen_count))


@dataclass(frozen=True)
class RefinementDraft:
    plan: RefinementPlan
    action: RefinementAction | None
    garment_snapshot_sha256: str
    preference_snapshot_sha256: str
    request_sha256: str

    def __post_init__(self):
        from app.domain.value_objects.context_relevance import require_digest
        if type(self.plan) is not RefinementPlan or self.action is not None and type(self.action) is not RefinementAction:
            raise ValueError('Typed refinement draft required.')
        for value in (self.garment_snapshot_sha256,self.preference_snapshot_sha256,self.request_sha256):require_digest(value)
        if self.plan.ordinal and (self.action is None or self.action.kind!='alternative' or self.action.parent_recommendation_id!=self.plan.parent_id):
            raise ValueError('Child draft/action mismatch.')
        if not self.plan.ordinal and self.action is not None and (self.action.kind!='initial' or self.action.excluded_categories!=self.plan.exclusions):
            raise ValueError('Initial draft/action mismatch.')
