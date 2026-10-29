"""Session-bounded reuse of validated candidate-independent numeric summaries.

Pair evidence, structural checks, owner/snapshot binding and every decision/final
score validator remain independent. No garment, candidate or eligibility proof is
cached here. Original cached scorer remains the differential reference.
"""
from fractions import Fraction
from functools import lru_cache,partial
from itertools import combinations
from app.application.recommendation.cached_rule_based_compatibility_scorer import CachedRuleBasedCompatibilityScorer
from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore


class PreparedCompatibilityAggregation(CachedRuleBasedCompatibilityScorer):
    def __init__(self,policy=None,capacity=19900,aggregation_capacity=256):
        super().__init__(policy,capacity)
        if type(aggregation_capacity) is not int or not 0<=aggregation_capacity<=256:
            raise ValueError('Invalid aggregation cache capacity.')
        self._provenance=('policy_version:'+self.policy.version,'policy_hash:'+self.policy.hash)
        self._aggregate=lru_cache(maxsize=aggregation_capacity,typed=True)(partial(type(self)._summaries,self._provenance))

    @property
    def aggregation_cache_info(self):return self._aggregate.cache_info()

    @staticmethod
    def _summaries(provenance,colour_atoms,style_atoms):
        def mean(name,atoms):
            observed=sum(x[1] for x in atoms)
            value=sum((Fraction(*x[0]) for x in atoms),Fraction(0))/len(atoms) if observed==len(atoms) else None
            return ScoreEvidence(name,value,'Available' if value is not None else 'Unknown',observed,len(atoms))
        c,s=mean('colour_coordination',colour_atoms),mean('style_consistency',style_atoms)
        value=(c.value+s.value)/2 if c.value is not None and s.value is not None else None
        observed=c.observed+s.observed
        summary=ScoreEvidence('compatibility',value,'Available' if value is not None else 'Unknown',observed,c.possible+s.possible,
            provenance if value is not None else ('partial_evidence' if observed else 'missing_evidence',*provenance))
        return c,s,summary

    def evaluate(self,candidate):
        if not self.structure.is_structurally_valid(tuple(m.garment for m in candidate.members)):
            raise ValueError('Supported complete structural candidate required.')
        self.pair_cache.bind(candidate.members[0].garment.user_id,self.policy)
        prepared=tuple(self.evidence.classify(m.garment) for m in candidate.members)
        if len(prepared)==1:
            # Retain the original no-pair representation and constructors.
            return ComponentScore(ScoreEvidence('compatibility',None,'Unknown',reasons=('no_pair_relationships',*self._provenance)),
                (ScoreEvidence('colour_coordination',None,'NotApplicable'),ScoreEvidence('style_consistency',None,'NotApplicable')))
        colours,styles=[],[]
        for a,b in combinations(prepared,2):
            pair=self.pair_cache.pair(a,b,candidate.members[0].garment.user_id,self.policy)
            colours.append(pair.colour);styles.append(pair.style)
        def key(entries):
            return tuple((None if x.value is None else (x.value.numerator,x.value.denominator),x.observed) for x in entries)
        c,s,summary=self._aggregate(key(colours),key(styles))
        return ComponentScore(summary,(c,s,*colours,*styles))
