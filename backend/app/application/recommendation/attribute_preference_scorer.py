"""Exact conservative soft utilities. No database, model, resource or normalization IO."""
from dataclasses import dataclass
from fractions import Fraction as F
from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore


@dataclass(frozen=True)
class Utility:
    lower: F
    upper: F
    state: str
    observed: int=0
    possible: int=0

    def __post_init__(self):
        if any(type(v) is not F for v in (self.lower,self.upper)) or not 0<=self.lower<=self.upper<=1:raise ValueError('Invalid exact preference interval.')
        if self.state not in ('Available','Partial','Unknown','NotApplicable','Masked'):raise ValueError('Unknown preference information state.')
        if not 0<=self.observed<=self.possible:raise ValueError('Invalid preference observation counts.')


def disjunction(states):
    return 'Pass' if 'Pass' in states else 'Unknown' if 'Unknown' in states else 'Fail'


def conjunction(states):
    return 'Fail' if 'Fail' in states else 'Unknown' if 'Unknown' in states else 'Pass'


def utility(liked_states,avoided_states):
    l=disjunction(liked_states) if liked_states else 'Pass'
    a=disjunction(avoided_states) if avoided_states else 'Fail'
    lower=F(int(l=='Pass' and a=='Fail'))
    upper=F(int(l!='Fail' and a!='Pass'))
    states=tuple(liked_states)+tuple(avoided_states)
    known=sum(s!='Unknown' for s in states)
    return Utility(lower,upper,'Available' if known==len(states) else 'Partial' if known else 'Unknown',known,len(states))


def mean(values):
    if not values:return Utility(F(0),F(0),'NotApplicable')
    return Utility(sum((v.lower for v in values),F())/len(values),sum((v.upper for v in values),F())/len(values),
                   'Available' if all(v.state=='Available' for v in values) else 'Unknown' if all(v.state=='Unknown' for v in values) else 'Partial',
                   sum(v.observed for v in values),sum(v.possible for v in values))


def weighted(values):
    denominator=sum((w for w,_ in values),F())
    if not denominator:return Utility(F(0),F(0),'NotApplicable')
    active=[v for _,v in values]
    state='Available' if all(v.state=='Available' for v in active) else 'NotApplicable' if all(v.state in ('NotApplicable','Masked') for v in active) else 'Unknown' if all(v.state in ('Unknown','NotApplicable','Masked') for v in active) else 'Partial'
    return Utility(sum((w*v.lower for w,v in values),F())/denominator,sum((w*v.upper for w,v in values),F())/denominator,state,
                   sum(v.observed for v in active),sum(v.possible for v in active))


def evidence(name,value):
    state='NotApplicable' if value.state=='Masked' else value.state
    return ScoreEvidence(name,value.lower if state in ('Available','Partial') else None,state,value.observed,value.possible)


def component(total,details,configured):
    if not configured:return ComponentScore(ScoreEvidence('preference',None,'NoPreferences'))
    return ComponentScore(evidence('preference',total),tuple(evidence(name,v) for name,v in details))


def from_legacy(detail,kind):
    if detail.state=='NotApplicable':return Utility(F(),F(),'NotApplicable',detail.observed,detail.possible)
    lower=detail.value if detail.value is not None else F()
    if detail.state=='Available' or lower==1:upper=lower
    elif kind=='styles' and detail.possible:upper=min(F(1),lower+F(detail.possible-detail.observed,detail.possible))
    else:upper=F(1)
    return Utility(lower,upper,detail.state if detail.state in ('Available','Partial','Unknown') else 'Unknown',detail.observed,detail.possible)
