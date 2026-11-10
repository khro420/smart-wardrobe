"""One owned immutable B0 capture; no I/O or model calls during enumeration."""
from collections import OrderedDict
from dataclasses import dataclass
from fractions import Fraction as F
from types import MappingProxyType
from itertools import combinations
from app.application.recommendation.palette_compatibility_policy import PalettePolicy,encode
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.application.recommendation.rule_based_compatibility_evidence import RuleBasedCompatibilityEvidence
from app.domain.value_objects.palette_compatibility import STRUCTURES,PaletteError
from app.domain.value_objects.attribute_selection_evidence import description_digest

@dataclass(frozen=True)
class PaletteMemberFact:
    palette: tuple
    styles: frozenset
    style_known: bool
    state: str

class PreparedPaletteCompatibility:
    def __init__(self,user,collection,policy=None,*,archived=False):
        self.user=user;self.policy=policy or PalettePolicy.load();self.collection=tuple(collection)
        if len(self.collection)>100:raise PaletteError('CompatibilityCapacityExceeded','Too many strict palette members.')
        self.by_id={};facts={};legacy=None if archived else RuleBasedCompatibilityEvidence()
        bridge=self.policy.snapshot();attribute=AttributeEvidencePolicy(encode(bridge['attribute_policy']))
        for item in self.collection:
            g=item.snapshot
            if g.user_id!=user or g.garment_id in self.by_id:raise PaletteError('CompatibilityInvalid','Foreign or duplicate palette member.')
            self.by_id[g.garment_id]=item
            fact=attribute.fact(g,item.description.to_dict(),'palette_coverage','coverage_ge',None)
            palette=[]
            if fact.state in ('Known','KnownEmpty') and fact.source in ('owner_selected','owner_reported_label'):
                for colour,coverage in fact.values:
                    if colour in bridge['anchors'] and coverage is not None:palette.append((bridge['anchors'][colour],F(coverage)))
            if archived:
                import re
                aliases=bridge['style_aliases'];tags=g.style_tags
                normalized=tuple(re.sub(r'\s+',' ',v.strip().casefold()) for v in tags or ())
                styles=frozenset(aliases[v] for v in normalized if v in aliases)
                known=tags is not None and bool(styles) and 'style_tags' not in g.invalid_attributes and all(v in aliases for v in normalized)
            else:
                old=legacy.classify(g);styles=old.styles;known=old.style_state=='Known'
            facts[g.garment_id]=PaletteMemberFact(tuple(palette),styles,known,fact.state)
        self.by_id=MappingProxyType(self.by_id);self.facts=MappingProxyType(facts)
        self.collection_sha256=description_digest(self.collection)
        self._pairs=OrderedDict();self._aggregates=OrderedDict();self.pair_hits=self.pair_misses=0
        self.achromatic=frozenset(bridge['achromatic'])
    def _check(self,members):
        if tuple(role for role,_ in members) not in STRUCTURES or len({gid for _,gid in members})!=len(members) or any(gid not in self.by_id for _,gid in members):
            raise PaletteError('CompatibilityInvalid','Uncaptured C2 scoring member.')
    def public(self,verified):
        from app.domain.value_objects.scored_candidate import VerifiedScoringInput
        from app.application.recommendation.palette_compatibility_scorer import public_component
        if not isinstance(verified,VerifiedScoringInput) or verified.user_id!=self.user:raise PaletteError('CompatibilityInvalid','Independent owned gate required.')
        members=tuple((m.role,m.garment.garment_id) for m in verified.candidate.members);self._check(members)
        if any(self.by_id[m.garment.garment_id].snapshot!=m.garment for m in verified.candidate.members):raise PaletteError('CompatibilityInvalid','C2 snapshot changed inside action.')
        return public_component(self.facts,members,self.policy)
    def compact(self,garments,roles,indexes):
        from app.application.recommendation.palette_compatibility_scorer import compact_pair,compact_decision
        members=tuple((role,garments[i].garment_id) for role,i in zip(roles,indexes));self._check(members)
        if any(self.by_id[garments[i].garment_id].snapshot!=garments[i] for i in indexes):raise PaletteError('CompatibilityInvalid','C2 strict collection mismatch.')
        pairs=[]
        for (_,a),(_,b) in combinations(members,2):
            key=(a,b)
            if key in self._pairs:self.pair_hits+=1;value=self._pairs[key];self._pairs.move_to_end(key)
            else:
                self.pair_misses+=1;value=compact_pair(self.facts[a],self.facts[b],self.achromatic);self._pairs[key]=value
                if len(self._pairs)>19900:self._pairs.popitem(last=False)
            pairs.append(value)
        intervals=tuple(p[0] for p in pairs)+tuple(p[1] for p in pairs)
        if intervals not in self._aggregates:
            self._aggregates[intervals]=compact_decision(intervals,self.policy.hash)
            if len(self._aggregates)>256:self._aggregates.popitem(last=False)
        return self._aggregates[intervals]
