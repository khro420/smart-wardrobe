"""Pure isolated two-pass policy. Inputs are complete already-admitted vectors.

This is not a route, engine, write draft, authenticated query or archive verifier.
Only the test composition currently supplies real engine and source certificates.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import hashlib
from app.domain.value_objects.attribute_conditions import encode
from app.application.recommendation.request_local_preference_evidence import OptionalEvaluation

PROFILE='request_local_bounded_preference_v1'
T_BUDGET=F(1,50)
COMPONENT_BUDGET=F(1,10)
MAX_CANDIDATES=38148  # Finite structural maximum for the existing 100-garment scope.

@dataclass(frozen=True)
class PrimaryRecord:
    key:tuple
    r:F
    c:F
    p:F
    t:F
    scope_hash:str
    certificate:bytes
    def __post_init__(self):
        if type(self.key) is not tuple or any(type(x) is not tuple or len(x)!=2 or any(type(v) is not str or not v for v in x) for x in self.key):raise ValueError('Invalid full candidate key.')
        roles=tuple(x[0] for x in self.key)
        if roles not in (('upper','lower'),('upper','lower','outerwear'),('one_piece',),('one_piece','outerwear')) or len({x[1] for x in self.key})!=len(self.key):raise ValueError('Invalid full candidate key.')
        if any(type(x) is not F or not 0<=x<=1 for x in (self.r,self.c,self.p,self.t)) or self.t!=F(3,5)*self.r+F(1,5)*self.c+F(1,5)*self.p:raise ValueError('Changed original exact score.')
        if type(self.scope_hash) is not str or len(self.scope_hash)!=64 or type(self.certificate) is not bytes or not self.certificate:raise ValueError('Missing isolated scope/score certificate.')
    @property
    def original_key(self):return (-self.t,-self.r,-self.c,-self.p,self.key)
    def identity(self):
        return hashlib.sha256(encode({'key':self.key,'r':str(self.r),'c':str(self.c),'p':str(self.p),'t':str(self.t),'scope':self.scope_hash,'certificate':self.certificate.hex()})).digest()

@dataclass(frozen=True)
class CompletedLedger:
    examined:int
    passed:int
    failed:int
    unknown:int
    complete:bool
    def __post_init__(self):
        if any(type(v) is not int or v<0 for v in (self.examined,self.passed,self.failed,self.unknown)) or self.complete is not True or self.examined!=self.passed+self.failed+self.unknown or self.examined>MAX_CANDIDATES:raise ValueError('A complete bounded mandatory ledger is required.')

@dataclass(frozen=True)
class PromotionComparison:
    primary:PrimaryRecord
    optional:OptionalEvaluation | None
    reasons:tuple

@dataclass(frozen=True)
class BoundedDecision:
    baseline:PrimaryRecord | None
    selected:PrimaryRecord | None
    mandatory:CompletedLedger
    optional_ledger:tuple
    scope_digest:str
    profile:str=PROFILE
    production_ready:bool=False

def bounded_rank(scope_factory,completion,optional_evaluator,*,resolution='Active',p2=False,c2=False,contextual=False,continuation=False):
    if any(x is not False for x in (p2,c2,contextual,continuation)):raise ValueError('Unsupported isolated profile combination.')
    if type(completion) is not CompletedLedger or resolution not in ('Active','ContradictedByHard','EntailedByHard','Absent'):raise ValueError('Invalid isolated scope/resolution.')
    if (resolution=='Absent')!=(optional_evaluator is None):raise ValueError('No-soft requests retain the original path.')
    baseline=None;seen=set();identities=[];first_ids={};scope=None
    for row in scope_factory():
        if type(row) is not PrimaryRecord or row.key in seen or len(seen)>=MAX_CANDIDATES:raise ValueError('Duplicate/unbounded primary scope.')
        seen.add(row.key);identities.append(row.identity());first_ids[row.key]=row.identity()
        if scope is None:scope=row.scope_hash
        if row.scope_hash!=scope:raise ValueError('Mixed source scopes.')
        if baseline is None or row.original_key<baseline.original_key:baseline=row
    if len(seen)!=completion.passed:raise ValueError('Incomplete first-pass primary scope.')
    original_digest=hashlib.sha256(b''.join(sorted(identities))).hexdigest()
    selected=None;second=set();second_ids=[];comparisons=[]
    for row in scope_factory():
        if type(row) is not PrimaryRecord or row.key in second or len(second)>=MAX_CANDIDATES:raise ValueError('Invalid second-pass scope.')
        if row.key not in first_ids or row.identity()!=first_ids[row.key]:raise ValueError('Primary source/score changed before optional evaluation.')
        second.add(row.key);second_ids.append(row.identity())
        optional=optional_evaluator(row.key) if optional_evaluator else None
        if optional is not None and (type(optional) is not OptionalEvaluation or optional.key!=row.key or optional.scope_hash!=row.scope_hash):raise ValueError('Foreign optional evidence scope.')
        reasons=[]
        if resolution!='Active':reasons.append('inactive_optional_intent')
        elif optional.support!=1:reasons.append('no_qualified_match')
        if baseline.t-row.t>T_BUDGET:reasons.append('T_loss_above_budget')
        if baseline.c-row.c>COMPONENT_BUDGET:reasons.append('C_loss_above_budget')
        if baseline.p-row.p>COMPONENT_BUDGET:reasons.append('P_loss_above_budget')
        if row.r<baseline.r:reasons.append('R_would_decrease')
        comparisons.append(PromotionComparison(row,optional,tuple(reasons)))
        if not reasons and (selected is None or row.original_key<selected.original_key):selected=row
    if len(second)!=completion.passed or second!=seen or hashlib.sha256(b''.join(sorted(second_ids))).hexdigest()!=original_digest:raise ValueError('Source/membership/score changed between passes.')
    return BoundedDecision(baseline,selected or baseline,completion,tuple(sorted(comparisons,key=lambda x:x.primary.key)),original_digest)
