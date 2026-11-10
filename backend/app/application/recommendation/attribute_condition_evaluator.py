"""Prepare member predicates once; candidate admission is table lookups only."""
from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType

from app.domain.value_objects.attribute_conditions import AttributeConditions,ROLES,ANCHORS,AttributeRequestError
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy


@dataclass(frozen=True)
class AttributeVerdict:
    state: str
    reason: str


def conjunction(states):
    return 'Fail' if 'Fail' in states else 'Unknown' if 'Unknown' in states else 'Pass'


def predicate(fact,field,operator,values):
    if fact.applicability!='applicable' or fact.state not in ('Known','KnownEmpty'):
        reasons={'Stale':'stale_description','Malformed':'malformed_description','Conflicting':'conflicting_description',
                 'Unsure':'unknown_material','Inapplicable':'inapplicable_role','Absent':'missing_description','Missing':'missing_description'}
        return AttributeVerdict('Unknown',reasons.get(fact.state,'unqualified_source'))
    if field in ('palette_colour','palette_coverage'):
        palette=fact.values
        def target(colour,raw):return raw==colour if colour.startswith('#') else ANCHORS.get(raw)==colour
        if operator=='coverage_ge':
            threshold=values[0];colour=threshold['colour'];minimum=Fraction(threshold['minimum'])
            lower=sum((Fraction(coverage) for raw,coverage in palette if coverage is not None and target(colour,raw)),Fraction(0))
            known_other=sum((Fraction(coverage) for raw,coverage in palette if coverage is not None and not target(colour,raw)),Fraction(0))
            # Any unclassified named colour may be the target family. Exact
            # non-target hex identity does not need named-family classification.
            if not colour.startswith('#'):
                known_other=sum((Fraction(coverage) for raw,coverage in palette if coverage is not None and raw in ANCHORS and not target(colour,raw)),Fraction(0))
            upper=1-known_other
            if fact.complete:upper=lower if all(raw in ANCHORS or colour.startswith('#') for raw,_ in palette) else upper
            state='Pass' if lower>=minimum else 'Fail' if upper<minimum else 'Unknown'
            return AttributeVerdict(state,'matched_recorded_value' if state=='Pass' else 'known_mismatch' if state=='Fail' else 'unclassified_palette_mass')
        known=[any(target(value,raw) for raw,_ in palette) for value in values]
        matched=all(known) if operator=='contains_all' else any(known)
        complete=fact.complete and (operator=='exact_hex' or all(raw in ANCHORS for raw,_ in palette))
    else:
        observed=fact.values
        matches=[value in observed for value in values]
        matched=all(matches) if operator=='contains_all' else any(matches)
        complete=fact.complete
    state='Pass' if matched else 'Fail' if complete else 'Unknown'
    return AttributeVerdict(state,'matched_recorded_value' if state=='Pass' else 'known_mismatch' if state=='Fail' else 'incomplete_recorded_set')


@dataclass(frozen=True)
class PreparedAttributeConditions:
    conditions: AttributeConditions
    groups: tuple
    rows: object
    verdicts: object
    applicable: object
    facts: object
    policy: AttributeEvidencePolicy

    @classmethod
    def prepare(cls,conditions,collection,policy,*,legacy_primary=None,subtype_sources=()):
        if type(conditions) is not AttributeConditions or type(policy) is not AttributeEvidencePolicy or len(collection)>100:
            raise AttributeRequestError('AttributeUnavailable','invalid_prepared_attribute_context')
        subtype_map={s.garment_id:s for s in subtype_sources}
        legacy_primary=legacy_primary or policy.primary_classifier()
        groups=conditions.to_dict()['groups'];rows={};verdicts={};applicable={};facts={}
        for item in collection:
            snapshot=item.snapshot;description=item.description.to_dict();gid=snapshot.garment_id
            if gid in rows:raise ValueError('Duplicate captured garment.')
            rows[gid]=item
            for group in groups:
                for condition in group['conditions']:
                    cid=condition['id'];field=condition['attribute'];op=condition['operator']
                    fact=policy.subtype_fact(snapshot,subtype_map.get(gid)) if field=='verified_subtype' else policy.fact(snapshot,description,field,op,legacy_primary)
                    facts[gid,cid]=fact
                    verdicts[gid,cid]=predicate(fact,field,op,condition['values'])
                    applicable[gid,cid]=fact.applicability!='inapplicable'
        frozen_groups=tuple((g['id'],ROLES[g['role']],g['quantifier'],tuple(c['id'] for c in g['conditions'])) for g in groups)
        return cls(conditions,frozen_groups,MappingProxyType(rows),MappingProxyType(verdicts),MappingProxyType(applicable),MappingProxyType(facts),policy)

    def evaluate_members(self,members):
        states=[]
        for _,roles,quantifier,ids in self.groups:
            member_states=[]
            for role,gid in members:
                if gid not in self.rows:raise ValueError('Uncaptured attribute member.')
                if role in roles and all(self.applicable[gid,cid] for cid in ids):
                    member_states.append(conjunction(tuple(self.verdicts[gid,cid].state for cid in ids)))
            if quantifier=='exists':state='Pass' if 'Pass' in member_states else 'Unknown' if 'Unknown' in member_states else 'Fail'
            elif quantifier=='none':state='Fail' if 'Pass' in member_states else 'Unknown' if 'Unknown' in member_states else 'Pass'
            else:state=conjunction(tuple(member_states)) if member_states else 'Fail'
            states.append(state)
        return conjunction(tuple(states))

    def evaluate(self,candidate):
        for member in candidate.members:
            if self.rows[member.garment.garment_id].snapshot!=member.garment:raise ValueError('Captured attribute snapshot mismatch.')
        return self.evaluate_members(tuple((m.role,m.garment.garment_id) for m in candidate.members))


class AttributeLedger:
    KEYS=('structural_examined','legacy_failed','legacy_unknown','attribute_failed','attribute_unknown','joint_passed')
    def __init__(self):
        self.counts=dict.fromkeys(self.KEYS,0);self.unseen_unknown=0
    def observe(self,legacy,attribute,*,seen=False):
        if legacy!='Fail' and attribute=='Unknown' and not seen:self.unseen_unknown+=1
        self.counts['structural_examined']+=1
        bucket=('legacy_failed' if legacy=='Fail' else 'attribute_failed' if attribute=='Fail' else
                'legacy_unknown' if legacy=='Unknown' else 'attribute_unknown' if attribute=='Unknown' else 'joint_passed')
        self.counts[bucket]+=1
        return conjunction((legacy,attribute))
    def snapshot(self):
        if self.counts['structural_examined']!=sum(self.counts[k] for k in self.KEYS[1:]):raise ValueError('Incomplete attribute ledger.')
        return dict(self.counts)


@dataclass(frozen=True)
class AttributeRefinementCounterGuard:
    """Negative eligibility proof only; never score/rank an attribute Unknown."""
    indexes: object
    relative_facts: object
    floor: Fraction
    seen: frozenset

    def ignores(self,members):
        base=tuple((role,gid) for role,gid in members if role!='outerwear')
        if base in self.seen:return True
        bounds=self.relative_facts.bounds(tuple(role for role,_ in members),tuple(self.indexes[gid] for _,gid in members))
        return bounds is not None and bounds[1]<self.floor
