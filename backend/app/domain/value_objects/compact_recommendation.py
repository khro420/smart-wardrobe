"""Private experimental scalar records; public recommendation models stay intact."""
from fractions import Fraction as F
from typing import NamedTuple
from dataclasses import dataclass


class Measure(NamedTuple):
    value: F | None
    state: str
    observed: int = 0
    possible: int = 0

    @property
    def contribution(self):
        return self.value if self.value is not None else F(0)


@dataclass(frozen=True)
class CompactDecision:
    raw: Measure
    colours: Measure
    styles: Measure
    atoms: tuple
    basis: str
    value: F
    lower: F | None
    upper: F | None
    known_sum: F
    known: int
    pairs: int

    def __post_init__(self):
        for m in (self.raw,self.colours,self.styles):validate_measure(m)
        if type(self.atoms) is not tuple or type(self.pairs) is not int or self.pairs not in (0,1,3) or len(self.atoms)!=2*self.pairs:
            raise ValueError('Invalid compact relationship count.')
        if any(v is not None and (type(v) is not F or not 0<=v<=1) for v in self.atoms):raise ValueError('Invalid atomic score.')
        known=tuple(v for v in self.atoms if v is not None)
        if type(self.known) is not int or self.known!=len(known) or type(self.known_sum) is not F or self.known_sum!=sum(known,F(0)) or type(self.value) is not F:
            raise ValueError('Invalid atomic coverage.')
        if not self.pairs:
            if self.basis!='NoPairReference' or self.value!=F(1,2) or self.lower is not None or self.upper is not None or any(m!=Measure(None,'NotApplicable') for m in (self.raw,self.colours,self.styles)):
                raise ValueError('Invalid no-pair reference.')
            return
        M=len(self.atoms); L=self.known_sum/M; U=(self.known_sum+M-self.known)/M
        basis='Computed' if self.known==M else 'FullyConventional' if not self.known else 'PartiallyConventional'
        if type(self.lower) is not F or type(self.upper) is not F or (self.lower,self.upper,self.value,self.basis)!=(L,U,(L+U)/2,basis):raise ValueError('Invalid exact decision bounds.')
        expected=('Available',L) if self.known==M else ('Unknown',None)
        if (self.raw.observed,self.raw.possible)!=(self.known,M) or (self.raw.state,self.raw.value)!=expected:
            raise ValueError('Invalid raw compatibility state.')


class CompactScore(NamedTuple):
    request: Measure
    compatibility: CompactDecision | None
    preference: Measure
    total: F
    request_details: tuple
    preference_details: tuple

    @property
    def contributions(self):
        return (self.request.contribution, self.compatibility.value if self.compatibility else F(0), self.preference.contribution)


def validate_measure(value):
    if type(value) is not Measure or value.state not in ('Available','Partial','Unknown','NotApplicable','Unavailable','NoPreferences','NoSupportedPreferences'):
        raise ValueError('Invalid compact component state.')
    if value.value is not None and (not isinstance(value.value,F) or not 0 <= value.value <= 1):
        raise ValueError('Exact bounded component required.')
    if (value.state in ('Available','Partial')) != (value.value is not None):
        raise ValueError('Component state/value mismatch.')
    if any(type(x) is not int or x < 0 for x in (value.observed,value.possible)) or value.observed > value.possible:
        raise ValueError('Invalid component coverage.')
    return value


def validate_total(score, weights):
    """Exact independent cross-product equality; Python integers cannot overflow.

    No float conversion, denominator bound or approximate comparison. Fixed
    immutable weights are validated at session preparation, not caller input.
    """
    if type(score) is not CompactScore or type(score.total) is not F or not 0 <= score.total <= 1:
        raise ValueError('Invalid compact total.')
    validate_measure(score.request); validate_measure(score.preference)
    if score.compatibility is not None:
        if type(score.compatibility) is not CompactDecision:raise ValueError('Validated decision certificate required.')
        validate_measure(score.compatibility.raw)
    terms = tuple((w.numerator*v.numerator,w.denominator*v.denominator) for w,v in zip(weights,score.contributions))
    (a,b),(c,d),(e,f) = terms
    if score.total.numerator*(b*d*f) != score.total.denominator*(a*d*f+c*b*f+e*b*d):
        raise ValueError('Exact total mismatch.')
