"""C2 recorded-fraction intervals. No alteration of the C1 decision contract."""
from dataclasses import dataclass, field
from fractions import Fraction as F
from app.domain.value_objects.recommendation_score import ComponentScore

PROFILE='recorded_palette_compatibility_v1'
POLICY='recorded-palette-compatibility-1.0.0'
DECISION='recorded-palette-decision-1.0.0'
EVIDENCE='recorded-palette-evidence-1.0.0'
PROFILES={(False,False):'recorded_palette_p1_decision_v1',
          (False,True):'recorded_palette_context_p1_decision_v1',
          (True,False):'recorded_palette_p2_decision_v1',
          (True,True):'recorded_palette_context_p2_decision_v1'}
WEIGHTS=(F(3,5),F(1,5),F(1,5))
STRUCTURES={('upper','lower'):('top_bottom',1),('upper','lower','outerwear'):('top_bottom_outerwear',3),
            ('one_piece',):('dress',0),('one_piece','outerwear'):('dress_outerwear',1)}


class PaletteError(ValueError):
    def __init__(self,code,reason,status=422):
        super().__init__(reason);self.code,self.reason,self.status=code,reason,status


@dataclass(frozen=True)
class Interval:
    lower: F
    upper: F
    def __post_init__(self):
        if type(self.lower) is not F or type(self.upper) is not F or not 0<=self.lower<=self.upper<=1:
            raise ValueError('Exact bounded palette interval required.')
    @property
    def point(self):return self.lower==self.upper


@dataclass(frozen=True)
class PaletteDecision:
    raw: ComponentScore
    structure: str
    atoms: tuple
    policy_hash: str
    policy_version: str=POLICY

    def __post_init__(self):
        pairs=dict(STRUCTURES.values()).get(self.structure)
        if pairs is None or type(self.raw) is not ComponentScore or type(self.atoms) is not tuple or len(self.atoms)!=2*pairs:
            raise ValueError('Invalid C2 structure/atomic evidence.')
        if self.policy_version!=POLICY or type(self.policy_hash) is not str or len(self.policy_hash)!=64 or any(c not in '0123456789abcdef' for c in self.policy_hash):
            raise ValueError('Invalid C2 policy identity.')
        if any(type(a) is not tuple or len(a)!=2 or type(a[0]) is not str or type(a[1]) is not Interval for a in self.atoms):
            raise ValueError('Invalid C2 interval atom.')
        if len({name for name,_ in self.atoms})!=len(self.atoms):raise ValueError('Duplicate C2 atoms.')
        if pairs and (any(not name.startswith('colour:') for name,_ in self.atoms[:pairs]) or any(not name.startswith('style:') for name,_ in self.atoms[pairs:])):
            raise ValueError('Ordered colour/style C2 atoms required.')
        if pairs and tuple(name[7:] for name,_ in self.atoms[:pairs])!=tuple(name[6:] for name,_ in self.atoms[pairs:]):
            raise ValueError('C2 pair identity mismatch.')
        expected_state='NotApplicable' if not pairs else 'Available' if self.known_count==self.atomic_count else 'Unknown'
        expected_value=self.lower if expected_state=='Available' else None
        if (self.raw.summary.state,self.raw.summary.value,self.raw.summary.observed,self.raw.summary.possible)!=(expected_state,expected_value,self.known_count,self.atomic_count):
            raise ValueError('C2 raw coverage/state mismatch.')
        if len(self.raw.details)!=2+len(self.atoms):raise ValueError('Complete C2 raw ledger required.')
        for detail,(name,bounds) in zip(self.raw.details[2:],self.atoms):
            if (detail.name,detail.value,detail.state,detail.observed,detail.possible)!=(name,bounds.lower if bounds.point else None,'Available' if bounds.point else 'Unknown',int(bounds.point),1):
                raise ValueError('Raw C2 atom disagrees with interval.')
        for detail,name,axis in zip(self.raw.details[:2],('colour_coordination','style_consistency'),(self.atoms[:pairs],self.atoms[pairs:])):
            known=sum(b.point for _,b in axis)
            value=sum((b.lower for _,b in axis),F())/pairs if pairs and known==pairs else None
            state='NotApplicable' if not pairs else 'Available' if known==pairs else 'Unknown'
            if (detail.name,detail.value,detail.state,detail.observed,detail.possible)!=(name,value,state,known,pairs):raise ValueError('C2 dimension mismatch.')

    @property
    def pair_count(self):return len(self.atoms)//2
    @property
    def atomic_count(self):return len(self.atoms)
    @property
    def known_count(self):return sum(b.point for _,b in self.atoms)
    @property
    def known_sum(self):return sum((b.lower for _,b in self.atoms if b.point),F())
    @property
    def lower(self):return sum((b.lower for _,b in self.atoms),F())/len(self.atoms) if self.atoms else None
    @property
    def upper(self):return sum((b.upper for _,b in self.atoms),F())/len(self.atoms) if self.atoms else None
    @property
    def value(self):return (self.lower+self.upper)/2 if self.atoms else F(1,2)
    @property
    def basis(self):return 'NoPairReference' if not self.atoms else 'Computed' if self.known_count==len(self.atoms) else 'FullyConventional' if not self.known_count else 'PartiallyConventional'


@dataclass(frozen=True,kw_only=True)
class PaletteCompatibilityComponent(ComponentScore):
    decision: PaletteDecision
    adapter_version: str=field(default='recorded-palette-component-1.0.0',init=False)
    def __post_init__(self):
        super().__post_init__()
        if type(self.decision) is not PaletteDecision or (self.summary,self.details)!=(self.decision.raw.summary,self.decision.raw.details):
            raise ValueError('C2 component must retain actual raw evidence.')
    @property
    def contribution(self):return self.decision.value


@dataclass(frozen=True)
class CompactPaletteDecision:
    raw: object
    colours: object
    styles: object
    intervals: tuple
    policy_hash: str
    def __post_init__(self):
        from app.domain.value_objects.compact_recommendation import validate_measure,Measure
        for m in (self.raw,self.colours,self.styles):validate_measure(m)
        if type(self.intervals) is not tuple or len(self.intervals) not in (0,2,6) or any(type(b) is not Interval for b in self.intervals):raise ValueError('Invalid compact C2 intervals.')
        if type(self.policy_hash) is not str or len(self.policy_hash)!=64 or any(c not in '0123456789abcdef' for c in self.policy_hash):raise ValueError('Invalid compact C2 policy.')
        for actual,axis in ((self.colours,self.intervals[:self.pairs]),(self.styles,self.intervals[self.pairs:]),(self.raw,self.intervals)):
            count=len(axis);known=sum(b.point for b in axis)
            value=sum((b.lower for b in axis),F())/count if count and known==count else None
            expected=Measure(value,'NotApplicable' if not count else 'Available' if known==count else 'Unknown',known,count)
            if actual!=expected:raise ValueError('Compact C2 raw evidence mismatch.')
    @property
    def atoms(self):return tuple(b.lower if b.point else None for b in self.intervals)
    @property
    def pairs(self):return len(self.intervals)//2
    @property
    def known(self):return sum(b.point for b in self.intervals)
    @property
    def known_sum(self):return sum((b.lower for b in self.intervals if b.point),F())
    @property
    def lower(self):return sum((b.lower for b in self.intervals),F())/len(self.intervals) if self.intervals else None
    @property
    def upper(self):return sum((b.upper for b in self.intervals),F())/len(self.intervals) if self.intervals else None
    @property
    def value(self):return (self.lower+self.upper)/2 if self.intervals else F(1,2)
    @property
    def basis(self):return 'NoPairReference' if not self.intervals else 'Computed' if self.known==len(self.intervals) else 'FullyConventional' if not self.known else 'PartiallyConventional'


@dataclass(frozen=True)
class PaletteWriteDraft:
    payload: bytes
    collection_sha256: str
    def __post_init__(self):
        if type(self.payload) is not bytes or len(self.payload)>131072:raise PaletteError('CompatibilityCapacityExceeded','C2 selected archive exceeds128KiB.')
        if type(self.collection_sha256) is not str or len(self.collection_sha256)!=64 or any(c not in '0123456789abcdef' for c in self.collection_sha256):raise ValueError('C2 collection digest required.')
