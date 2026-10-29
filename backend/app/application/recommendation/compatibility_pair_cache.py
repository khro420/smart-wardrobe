"""Bounded LRU of immutable exact pairs; never an eligibility or shared cache."""
from collections import OrderedDict
from dataclasses import dataclass,replace
from fractions import Fraction
from app.domain.value_objects.recommendation_score import ScoreEvidence
from app.domain.value_objects.rule_based_compatibility import PreparedCompatibilityEvidence
from app.application.recommendation.rule_based_compatibility_policy import RuleBasedCompatibilityPolicy

MAX_PAIR_CAPACITY=19900


@dataclass(frozen=True)
class PairEvidence:
    colour: ScoreEvidence
    style: ScoreEvidence

    def __post_init__(self):
        if not isinstance(self.colour,ScoreEvidence) or not isinstance(self.style,ScoreEvidence):
            raise ValueError("Immutable validated pair evidence required.")


@dataclass(frozen=True)
class PairCacheInfo:
    capacity: int
    size: int
    visits: int
    hits: int
    misses: int
    evictions: int
    high_water: int


@dataclass(frozen=True)
class _Entry:
    order: tuple[str,str]
    forward: PairEvidence
    reverse: PairEvidence | None = None


class CompatibilityPairCache:
    def __init__(self,policy,capacity=MAX_PAIR_CAPACITY):
        if not isinstance(policy,RuleBasedCompatibilityPolicy):
            raise ValueError("Validated policy required.")
        if type(capacity) is not int or not 0<=capacity<=MAX_PAIR_CAPACITY:
            raise ValueError("Pair capacity must be an integer between 0 and 19900.")
        self._policy=policy
        self._owner=None
        self._capacity=capacity
        self._entries=OrderedDict()
        self._prepared={}
        self._prefixes={}
        self._visits=self._hits=self._misses=self._evictions=self._high_water=0

    @property
    def info(self):
        return PairCacheInfo(self._capacity,len(self._entries),self._visits,self._hits,self._misses,self._evictions,self._high_water)

    def bind(self,user_id,policy):
        if not isinstance(user_id,str) or not user_id.strip() or policy!=self._policy:
            raise ValueError("Compatibility cache policy/owner mismatch.")
        if self._owner is None:
            self._owner=user_id
        elif self._owner!=user_id:
            raise ValueError("Compatibility cache cannot cross users.")

    def _register(self,item):
        if not isinstance(item,PreparedCompatibilityEvidence):
            raise ValueError("Frozen prepared evidence required.")
        previous=self._prepared.get(item.garment_id)
        if previous is not None:
            if previous is not item and previous!=item:
                raise ValueError("Conflicting prepared garment snapshot.")
        else:
            self._prepared[item.garment_id]=item
            self._prefixes[item.garment_id]=tuple(item.garment_id+":"+r for r in item.reasons)

    def _view(self,a,b,colour,style):
        label=a.garment_id+":"+b.garment_id
        reasons=self._prefixes[a.garment_id]+self._prefixes[b.garment_id]
        return PairEvidence(ScoreEvidence("colour:"+label,colour,"Available" if colour is not None else "Unknown",int(colour is not None),1,reasons),
                            ScoreEvidence("style:"+label,style,"Available" if style is not None else "Unknown",int(style is not None),1,reasons))

    def pair(self,a,b,user_id,policy):
        self.bind(user_id,policy)
        self._register(a);self._register(b)
        if a.garment_id==b.garment_id:
            raise ValueError("Distinct garment pair required.")
        order=(a.garment_id,b.garment_id)
        key=order if order[0]<order[1] else (order[1],order[0])
        self._visits+=1
        entry=self._entries.get(key)
        if entry is not None:
            self._hits+=1
            self._entries.move_to_end(key)
            if order==entry.order:
                return entry.forward
            if entry.reverse is None:
                view=self._view(a,b,entry.forward.colour.value,entry.forward.style.value)
                entry=replace(entry,reverse=view)
                self._entries[key]=entry
            return entry.reverse
        self._misses+=1
        colour=(Fraction(int(a.colour==b.colour or a.colour in policy.achromatic or b.colour in policy.achromatic))
                if a.colour_state==b.colour_state=="Known" else None)
        style=(Fraction(2*len(a.styles & b.styles),len(a.styles)+len(b.styles))
               if a.style_state==b.style_state=="Known" else None)
        view=self._view(a,b,colour,style)
        if self._capacity:
            if len(self._entries)==self._capacity:
                self._entries.popitem(last=False);self._evictions+=1
            self._entries[key]=_Entry(order,view)
            self._high_water=max(self._high_water,len(self._entries))
        return view
