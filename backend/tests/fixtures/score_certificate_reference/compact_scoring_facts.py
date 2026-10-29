"""Session-local immutable numeric facts, bounded memoization, exact composition."""
from collections import OrderedDict
from fractions import Fraction as F
from functools import lru_cache
from itertools import combinations
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.application.recommendation.rule_based_compatibility_evidence import RuleBasedCompatibilityEvidence
from app.application.recommendation.preference_scorer import PreferenceScorer
from app.domain.value_objects.compact_recommendation import Measure,CompactDecision,CompactScore,validate_measure,validate_total


def measured(value,state='Available',observed=0,possible=0):
    return validate_measure(Measure(value,state,observed,possible))


def request_summary(details):
    if not details:return measured(None,'NotApplicable')
    for item in details:validate_measure(item)
    return measured(sum((m.value for m in details),F(0))/len(details),
        'Partial' if any(m.state=='Partial' for m in details) else 'Available',
        sum(m.observed for m in details),sum(m.possible for m in details))


def preference_summary(weights,details):
    for item in details:validate_measure(item)
    if all(m.value is None for m in details):return measured(None,'Unknown',0,sum(m.possible for m in details))
    value=sum((w*m.contribution for w,m in zip(weights,details)),F(0))/sum(weights)
    return measured(value,'Available' if all(m.state=='Available' for m in details) else 'Partial',sum(m.observed for m in details),sum(m.possible for m in details))


def decision_facts(key):
    atoms=tuple(None if atom is None else F(*atom) for atom in key)
    pairs=len(atoms)//2
    if len(atoms)!=pairs*2 or pairs not in (0,1,3):raise ValueError('Invalid atomic count.')
    if not pairs:
        return CompactDecision(measured(None,'NotApplicable'),measured(None,'NotApplicable'),measured(None,'NotApplicable'),(),
            'NoPairReference',F(1,2),None,None,F(0),0,0)
    for atom in atoms:
        if atom is not None and (type(atom) is not F or not 0<=atom<=1):raise ValueError('Invalid exact atom.')
    def dimension(values):
        known=sum(v is not None for v in values)
        return measured(sum(values,F(0))/pairs if known==pairs else None,'Available' if known==pairs else 'Unknown',known,pairs)
    colour,style=dimension(atoms[:pairs]),dimension(atoms[pairs:])
    known=sum(v is not None for v in atoms); total=sum((v for v in atoms if v is not None),F(0)); count=len(atoms)
    lower,upper=total/count,(total+count-known)/count
    raw=measured((colour.value+style.value)/2 if known==count else None,'Available' if known==count else 'Unknown',known,count)
    result=CompactDecision(raw,colour,style,atoms,'Computed' if known==count else 'FullyConventional' if not known else 'PartiallyConventional',
        (lower+upper)/2,lower,upper,total,known,pairs)
    # Independent exact bounds, coverage and raw-state identities, identical to
    # the public decision validator. Immutable certificates can be reused only
    # for the same ordered atomic key within this session.
    if raw.observed!=known or raw.possible!=2*pairs or (known==count and raw.value!=lower):raise ValueError('Invalid decision coverage.')
    return result


class CompactScoringFacts:
    def __setattr__(self,name,value):
        if getattr(self,'_sealed',False) and name not in ('hits','misses','evictions'):
            raise AttributeError('Prepared scoring facts cannot be rebound.')
        object.__setattr__(self,name,value)

    def __delattr__(self,name):raise AttributeError('Prepared facts cannot be deleted.')

    def __init__(self, garments, request, preferences, raw_policy, weights, experimental, pair_capacity=19900, aggregation_capacity=256):
        garments,weights=tuple(garments),tuple(weights)
        if any(g.user_id!=preferences.user_id for g in garments):raise ValueError('Foreign scoring snapshot.')
        if type(pair_capacity) is not int or not 0<=pair_capacity<=19900 or type(aggregation_capacity) is not int or not 0<=aggregation_capacity<=256:
            raise ValueError('Invalid bounded cache capacity.')
        if len(weights)!=3 or any(type(w) is not F or not 0<=w<=1 for w in weights) or sum(weights)!=1:
            raise ValueError('Invalid immutable profile weights.')
        self.garments,self.request,self.preferences,self.policy,self.weights,self.experimental=tuple(garments),request,preferences,raw_policy,tuple(weights),experimental
        self.owner=preferences.user_id
        mapper=GarmentEvidenceMapper()
        self.styles=tuple(mapper.classify(g).style for g in garments) if request.style else ()
        self.request_fields=tuple(field for field in ('garment_categories','colours','style','occasion','formality') if getattr(request,field) is not None)
        original=PreferenceScorer(mapper)
        if preferences.preferences:
            allowed,_=original._prepare(preferences)
            self.preference_facts=tuple(tuple(original._fact(i,p,values,g) for g in garments) for i,(p,values) in enumerate(zip(preferences.preferences,allowed)))
        else:self.preference_facts=()
        self.preference_weights=tuple(p.importance for p in preferences.preferences)
        self.empty_preference=measured(None,'NoSupportedPreferences' if preferences.diagnostics else 'NoPreferences')
        raw_mapper=RuleBasedCompatibilityEvidence()
        self.raw=tuple(raw_mapper.classify(g) for g in garments) if experimental else ()
        self.pairs=OrderedDict(); self.pair_capacity=pair_capacity
        self.hits=self.misses=self.evictions=0
        self._request=lru_cache(maxsize=aggregation_capacity)(request_summary)
        self._preference=lru_cache(maxsize=aggregation_capacity)(preference_summary)
        self._decision=lru_cache(maxsize=aggregation_capacity)(decision_facts)
        self._total=lru_cache(maxsize=aggregation_capacity)(lambda values:sum((w*v for w,v in zip(weights,values)),F(0)))
        self._sealed=True

    def pair(self,a,b):
        key=(a,b)
        if key in self.pairs:
            self.hits+=1; self.pairs.move_to_end(key); return self.pairs[key]
        x,y=self.raw[a],self.raw[b]
        colour=F(int(x.colour==y.colour or x.colour in self.policy.achromatic or y.colour in self.policy.achromatic)) if x.colour_state==y.colour_state=='Known' else None
        style=F(2*len(x.styles&y.styles),len(x.styles)+len(y.styles)) if x.style_state==y.style_state=='Known' else None
        result=(colour,style)
        if any(v is not None and (type(v) is not F or not 0<=v<=1) for v in result):raise ValueError('Invalid pair facts.')
        self.misses+=1
        if self.pair_capacity:
            self.pairs[key]=result
            if len(self.pairs)>self.pair_capacity:self.pairs.popitem(last=False);self.evictions+=1
        return result

    def score(self,roles,indexes):
        base=tuple(i for role,i in zip(roles,indexes) if role!='outerwear')
        r_details=[]
        for field in self.request_fields:
            if field=='style':
                matched=sum(self.request.style in self.styles[i].values for i in base)
                known=sum(self.styles[i].state=='Known' for i in base)
                r_details.append(Measure(F(matched,len(base)),'Available' if known==len(base) else 'Partial',known,len(base)))
            else:r_details.append(Measure(F(1),'Available',1,1))
        r_details=tuple(r_details); r=self._request(r_details)
        p_details=[]
        for pref,table in zip(self.preferences.preferences,self.preference_facts):
            kind=pref.preference_type
            selected=base if kind=='styles' else indexes
            facts=tuple(table[i] for i in selected)
            if kind=='garment_categories':detail=Measure(F(int(any(x[0] for x in facts))),'Available',1,1)
            elif kind in ('colours','styles'):
                matched=sum(x[0] for x in facts); known=sum(x[1] for x in facts); n=len(facts)
                if kind=='colours' and matched:detail=Measure(F(1),'Available',known,n)
                elif not known and not matched:detail=Measure(None,'Unknown',0,n)
                else:detail=Measure(F(int(matched>0)) if kind=='colours' else F(matched,n),'Available' if known==n else 'Partial',known,n)
            else:
                states=tuple(zip(*(x[0] for x in facts)))
                if any(all(s=='Pass' for s in row) for row in states):detail=Measure(F(1),'Available',1,1)
                elif all(any(s=='Fail' for s in row) for row in states):detail=Measure(F(0),'Available',1,1)
                else:detail=Measure(None,'Unknown',0,1)
            p_details.append(detail)
        p_details=tuple(p_details)
        p=self._preference(self.preference_weights,p_details) if p_details else self.empty_preference
        c=None
        if self.experimental:
            pairs=tuple(self.pair(a,b) for a,b in combinations(indexes,2))
            atoms=tuple(pair[0] for pair in pairs)+tuple(pair[1] for pair in pairs)
            atom_key=tuple(None if v is None else (v.numerator,v.denominator) for v in atoms)
            c=self._decision(atom_key)
            if c.atoms!=atoms or c.pairs!=len(pairs):raise ValueError('Decision certificate mismatch.')
        values=(r.contribution,c.value if c else F(0),p.contribution)
        score=CompactScore(r,c,p,self._total(values),r_details,p_details)
        validate_total(score,self.weights)
        return score

    @property
    def cache_info(self):
        return {'pairs':len(self.pairs),'capacity':self.pair_capacity,'hits':self.hits,'misses':self.misses,'evictions':self.evictions,
            'aggregations':tuple(fn.cache_info()._asdict() for fn in (self._request,self._preference,self._decision,self._total))}
