"""One immutable wearer snapshot; source facts prepared before enumeration."""
from collections import OrderedDict
from dataclasses import dataclass,asdict
from fractions import Fraction as F
from types import MappingProxyType
from typing import NamedTuple
from app.domain.value_objects.compact_recommendation import Measure,CompactScore

from app.application.recommendation.attribute_preference_normalizer import compose
from app.application.recommendation.attribute_preference_scorer import Utility,utility,mean,weighted,component,from_legacy,conjunction
from app.application.recommendation.attribute_preference_masks import hard_mask,style_r_mask,legacy_request_mask
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.application.recommendation.attribute_condition_evaluator import predicate
from app.application.recommendation.preference_scorer import PreferenceScorer
from app.application.recommendation.suitability_evidence_mapper import SuitabilityEvidenceParser
from app.domain.value_objects.attribute_conditions import ROLES
from app.domain.value_objects.attribute_preferences import PreferenceError,encode,decode
from app.domain.value_objects.attribute_preference_evidence import ratio


def operation(axis,value):
    if axis=='palette_coverage':return 'coverage_ge'
    if axis=='colour_dominance':return 'bool_eq'
    if axis in ('primary_colour','secondary_colour','palette_colour') and type(value) is str and value.startswith('#'):return 'exact_hex'
    if axis in ('style','material','palette_colour','descriptive_tag'):return 'contains_any'
    return 'in'


def _proof(value):
    return None if value is None else (value['rule'],value['scope'],tuple(tuple(v) for v in value['conditions']))


def _u(value):
    return {'lower':ratio(value.lower),'upper':ratio(value.upper),'state':value.state,'observed':value.observed,'possible':value.possible}


@dataclass(frozen=True)
class PreferenceEvaluation:
    score: object
    total: Utility
    raw: Utility
    denominator: F
    rows: tuple
    snapshot_revision: str
    request_payload: bytes | None=None
    conditions_sha256: str | None=None
    objective_payload: bytes | None=None
    relative: bool=False
    original_text: str | None=None

    def to_dict(self):
        families=[]
        for family,importance,raw,effective,axes in self.rows:
            fields=[]
            for name,axis_weight,scope,axis_raw,axis_effective,proof in axes:
                fields.append({'axis':name,'importance':ratio(axis_weight),'scope':scope,'raw':_u(axis_raw),'effective':_u(axis_effective),
                               'mask':None if proof is None else {'rule':proof[0],'scope':proof[1],'conditions':[list(v) for v in proof[2]]}})
            families.append({'family':family,'importance':ratio(importance),'raw':_u(raw),'effective':_u(effective),'axes':fields})
        return {'contract':'attribute-preference-ledger-1.0.0','snapshot_revision':self.snapshot_revision,'configured_denominator':ratio(self.denominator),
                'request':decode(self.request_payload,65536) if self.request_payload is not None else None,'conditions_sha256':self.conditions_sha256,
                'objective':decode(self.objective_payload) if self.objective_payload is not None else None,'relative':self.relative,
                'original_text':self.original_text,
                'decision':ratio(self.total.lower),'effective':_u(self.total),'raw':_u(self.raw),'families':families}


class _CompactProjection(NamedTuple):
    evaluation: PreferenceEvaluation
    summary: Measure
    details: tuple
    token: object


class _CompactInputIdentity:
    """Hold the complete immutable original input without rehashing its fields.

    Reuse by identity is conservative: a fresh equal input misses. Retaining
    the complete original object prevents recycled identity from aliasing it.
    Reference scalar collaborators still use the full typed value key below.
    """
    __slots__=('value',)
    def __init__(self,value):self.value=value
    def __hash__(self):return id(self.value)
    def __eq__(self,other):return type(other) is _CompactInputIdentity and self.value is other.value


def _measure_key(value):
    # Python equates Fraction(1), 1 and True. A warm entry must not bypass the
    # original ScoreEvidence validation for a differently typed input.
    return (type(value.value),value.value,type(value.state),value.state,
            type(value.observed),value.observed,type(value.possible),value.possible)


class PreparedAttributePreferences:
    def __init__(self,snapshot,collection,*,conditions=None,objective=None,policy=None,request=None,original_text=None):
        self.snapshot=snapshot;self.composed=compose(snapshot);self.settings=self.composed.families()
        self.conditions,self.objective=conditions,objective
        self.snapshot_revision=snapshot.revision
        self._condition_hash=conditions.sha256 if conditions is not None else None
        self._request_payload=None;self._objective_payload=encode(asdict(objective)) if objective is not None else None
        self.original_text=original_text
        self._family_weights=MappingProxyType({family:F(s['importance']) for family,s in self.settings.items()})
        self._axis_weights=MappingProxyType({axis:F(a['importance']) for s in self.settings.values() if s['mode']=='override' for axis,a in s['axes'].items()})
        archive=snapshot.to_dict().get('archive')
        self.policy=policy or (AttributeEvidencePolicy(encode(archive['policy_snapshot']['archive_bridge']['attribute_policy'])) if archive is not None else AttributeEvidencePolicy.load())
        self.collection=tuple(collection)
        if len(self.collection)>100:raise PreferenceError('PreferenceCapacityExceeded','Too many strict description members.')
        self.account_id=snapshot.to_dict()['account_id'];self.by_id={};self.predicate_calls=0
        for item in self.collection:
            g=item.snapshot
            if g.user_id!=self.account_id or g.garment_id in self.by_id:raise PreferenceError('PreferenceInvalid','Conflicting strict preference collection.')
            self.by_id[g.garment_id]=item
        self.by_id=MappingProxyType(self.by_id)
        if archive is not None:
            from app.application.recommendation.attribute_preference_codec import archived_scorer
            self.old_scorer=archived_scorer(snapshot)
        else:self.old_scorer=PreferenceScorer()
        matching,_=self.old_scorer._prepare(self.composed.legacy)
        for i,(p,values) in enumerate(zip(self.composed.legacy.preferences,matching)):
            for item in self.collection:self.old_scorer._fact(i,p,values,item.snapshot)
        self._states={};self._applicable={};self._masks={};facts={};primary=self.policy.primary_classifier()
        descriptions={gid:item.description.to_dict() for gid,item in self.by_id.items()}
        formality=self.old_scorer.suitability
        for family,setting in self.settings.items():
            if setting['mode']=='inherit_p1':continue
            for axis,config in setting['axes'].items():
                aggregation='any' if axis in ('primary_colour','category') else 'mean'
                self._masks[axis]=_proof(hard_mask(axis,config,conditions,aggregation))
                for gid,item in self.by_id.items():
                    for polarity in ('liked','avoided'):
                        for index,value in enumerate(config[polarity]):
                            if axis=='formality':
                                state=formality.parse(item.snapshot).state_for('formality',value);applicable=True
                            else:
                                op=operation(axis,value);key=(gid,axis,op)
                                if key not in facts:facts[key]=self.policy.fact(item.snapshot,descriptions[gid],axis,op,primary)
                                fact=facts[key];state=predicate(fact,axis,op,[value]).state
                                applicable=fact.applicability!='inapplicable'
                            self._applicable[gid,axis]=applicable
                            self._states[gid,axis,polarity,index]=state
                            self.predicate_calls+=1
        self._states=MappingProxyType(self._states);self._applicable=MappingProxyType(self._applicable);self._masks=MappingProxyType(self._masks)
        # Intern exact prepared verdict vectors once. Equivalent numeric facts
        # can share aggregation, while the gate and selected source evidence
        # still validate each actual garment independently.
        classes={};member_classes={};member_utilities={}
        axes=tuple((axis,config) for setting in self.settings.values() if setting['mode']=='override' for axis,config in setting['axes'].items())
        for gid in self.by_id:
            signature=[]
            for axis,config in axes:
                liked=tuple(self._states[gid,axis,'liked',i] for i in range(len(config['liked'])))
                avoided=tuple(self._states[gid,axis,'avoided',i] for i in range(len(config['avoided'])))
                signature.append((axis,self._applicable.get((gid,axis),True),liked,avoided))
                if axis not in ('primary_colour','category','formality'):member_utilities[gid,axis]=utility(liked,avoided)
            vector=tuple(signature)
            member_classes[gid]=classes.setdefault(vector,len(classes))
        self._member_classes=MappingProxyType(member_classes)
        self._member_utilities=MappingProxyType(member_utilities)
        self._cache=OrderedDict();self.cache_hits=0;self.cache_misses=0
        # All additional conversion/projection/certificate records share one
        # action-owned bound. Keys and values contain immutable numeric facts;
        # candidate permission/source checks remain outside reuse.
        self._reuse=OrderedDict();self.reuse_hits=self.reuse_misses=self.reuse_evictions=0

        self.request=None;self._legacy_masks={}
        if request is not None:self.bind_request(request)

    def bind_request(self,request):
        if self.request is not None and self.request!=request:raise PreferenceError('PreferenceInvalid','Preference request changed inside one action.')
        if self.request==request:return
        self.request=request;self._cache.clear();self._reuse.clear()
        if self.original_text is None and getattr(request,'context',None) is not None:self.original_text=request.context.original_text
        self._request_payload=encode(request.to_dict())
        masks=dict(self._masks)
        for family,setting in self.settings.items():
            if setting['mode']=='inherit_p1':
                p=next(p for p in self.composed.legacy.preferences if p.preference_type==setting['legacy_type'])
                axis='primary_colour' if p.preference_type=='colours' else 'category' if p.preference_type=='garment_categories' else 'style' if p.preference_type=='styles' else 'formality'
                values=p.values
                if axis=='category':
                    values=tuple(v for c in p.values for v in (self.old_scorer.vocabulary.groups[c.value] if c.kind=='group' else (c.value,)))
                config={'scope':'base' if axis=='style' else 'all_selected','liked':list(values),'avoided':[]}
                self._legacy_masks[family]=_proof(legacy_request_mask(axis,config,request,self.old_scorer.vocabulary.groups))
            else:
                for axis,config in setting['axes'].items():
                    proof=legacy_request_mask(axis,config,request,self.old_scorer.vocabulary.groups)
                    if proof is not None:masks[axis]=_proof(proof)
        self._masks=MappingProxyType(masks)

    def bind_objective(self,objective):
        if self.objective is not None and self.objective!=objective:raise PreferenceError('PreferenceInvalid','Preference objective changed inside one action.')
        if self.objective!=objective:
            self.objective=objective
            self._objective_payload=encode(asdict(objective)) if objective is not None else None
            self._cache.clear();self._reuse.clear()

    def _axis(self,axis,config,members):
        selected=[gid for role,gid in members if role in ROLES[config['scope']] and self._applicable.get((gid,axis),True)]
        if not selected:return Utility(F(),F(),'NotApplicable')
        def values(gid,polarity):return tuple(self._states[gid,axis,polarity,i] for i in range(len(config[polarity])))
        if axis=='formality':
            liked=tuple(conjunction(tuple(self._states[gid,axis,'liked',i] for gid in selected)) for i in range(len(config['liked'])))
            avoided=tuple(conjunction(tuple(self._states[gid,axis,'avoided',i] for gid in selected)) for i in range(len(config['avoided'])))
            return utility(liked,avoided)
        if axis in ('primary_colour','category'):
            return utility(tuple(v for gid in selected for v in values(gid,'liked')),tuple(v for gid in selected for v in values(gid,'avoided')))
        return mean(tuple(self._member_utilities[gid,axis] for gid in selected))

    def reuse_record(self,key,build):
        try:result=self._reuse[key]
        except KeyError:
            self.reuse_misses+=1;result=build();self._reuse[key]=result
            if len(self._reuse)>256:self._reuse.popitem(last=False);self.reuse_evictions+=1
            return result
        except TypeError:
            # Preserve the original validation failure for malformed,
            # unhashable collaborators; they can never create a warm entry.
            return build()
        # FIFO needs no hit-time ordering or second key lookup. Only this new
        # derived cache changes eviction order; the original utility/pair LRUs
        # and their limits remain unchanged. Eviction always recomputes exactly.
        self.reuse_hits+=1;return result

    @property
    def reuse_cache_info(self):
        return {'entries':len(self._reuse),'capacity':256,'hits':self.reuse_hits,
                'misses':self.reuse_misses,'evictions':self.reuse_evictions}

    def _member_key(self,members):
        if not members or len(members)>3 or len({gid for _,gid in members})!=len(members) or any(gid not in self.by_id or role not in ('upper','lower','one_piece','outerwear') for role,gid in members):
            raise PreferenceError('PreferenceInvalid','Uncaptured preference scoring member.')
        return tuple((role,self._member_classes[gid]) for role,gid in members)

    def evaluate(self,members,legacy_component,*,relative=False):
        members=tuple(members)
        key=(self._member_key(members),legacy_component,relative)
        if key in self._cache:
            self.cache_hits+=1;self._cache.move_to_end(key);return self._cache[key]
        self.cache_misses+=1
        old={p.preference_type:d for p,d in zip(self.composed.legacy.preferences,legacy_component.details)}
        rows=[];weighted_effective=[];weighted_raw=[];details=[]
        for family,setting in self.settings.items():
            importance=self._family_weights[family];axis_rows=[]
            if setting['mode']=='inherit_p1':
                kind=setting['legacy_type'];raw=from_legacy(old[kind],kind);effective=raw
                p=next(p for p in self.composed.legacy.preferences if p.preference_type==kind)
                masked=relative and kind=='styles' and self.objective is not None and p.values==(self.objective.target,)
                proof=('duplicate_R_semantic_test_suppressed','base',()) if masked else self._legacy_masks.get(family)
                if proof is not None:effective=Utility(F(),F(),'Masked',raw.observed,raw.possible)
                axis_rows.append(('primary_colour' if kind=='colours' else 'style' if kind=='styles' else 'category' if kind=='garment_categories' else 'formality',F(1),'base' if kind=='styles' else 'all_selected',raw,effective,proof))
            else:
                raw_axes=[];effective_axes=[]
                for axis,config in setting['axes'].items():
                    axis_importance=self._axis_weights[axis];axis_raw=self._axis(axis,config,members);axis_effective=axis_raw
                    proof=self._masks[axis]
                    if relative and style_r_mask(axis,config,self.objective):proof=('duplicate_R_semantic_test_suppressed',config['scope'],())
                    if proof is not None and axis_raw.state!='NotApplicable':axis_effective=Utility(F(),F(),'Masked',axis_raw.observed,axis_raw.possible)
                    raw_axes.append((axis_importance,axis_raw));effective_axes.append((axis_importance,axis_effective))
                    axis_rows.append((axis,axis_importance,config['scope'],axis_raw,axis_effective,proof if axis_raw.state!='NotApplicable' else None))
                raw=weighted(raw_axes);effective=weighted(effective_axes)
            rows.append((family,importance,raw,effective,tuple(axis_rows)));weighted_effective.append((importance,effective));weighted_raw.append((importance,raw));details.append(('p2:'+family,effective))
        total=weighted(weighted_effective);raw=weighted(weighted_raw);denominator=sum((w for w,_ in weighted_effective),F())
        result=PreferenceEvaluation(component(total,details,bool(self.settings)),total,raw,denominator,tuple(rows),self.snapshot_revision,
            self._request_payload,self._condition_hash,self._objective_payload,relative,self.original_text)
        self._cache[key]=result
        if len(self._cache)>256:self._cache.popitem(last=False)
        return result

    def public(self,verified,*,relative=False):
        if verified.user_id!=self.account_id:raise PreferenceError('PreferenceInvalid','Preference scoring owner mismatch.')
        for member in verified.candidate.members:
            if self.by_id[member.garment.garment_id].snapshot!=member.garment:raise PreferenceError('PreferenceInvalid','Preference snapshot changed inside one action.')
        legacy=self.old_scorer.score(verified,self.composed.legacy)
        return self.evaluate(tuple((m.role,m.garment.garment_id) for m in verified.candidate.members),legacy,relative=relative)

    def compact_projection(self,garments,roles,indexes,legacy,*,relative=False):
        from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore
        members=tuple((role,garments[i].garment_id) for role,i in zip(roles,indexes))
        member_key=self._member_key(members)  # Execute for every actual candidate.
        if type(legacy) is CompactScore:
            key=('compact_projection',member_key,_CompactInputIdentity(legacy),relative)
        else:
            pairs=tuple(zip(self.composed.legacy.preferences,legacy.preference_details))
            key=('projection',member_key,_measure_key(legacy.preference),tuple(_measure_key(d) for _,d in pairs),relative)
        def build():
            pairs=tuple(zip(self.composed.legacy.preferences,legacy.preference_details))
            summary=legacy.preference
            details=tuple(ScoreEvidence(p.preference_type,d.value,d.state,d.observed,d.possible) for p,d in pairs)
            original=ComponentScore(ScoreEvidence('preference',summary.value,summary.state,summary.observed,summary.possible),details)
            evaluation=self.evaluate(members,original,relative=relative);score=evaluation.score
            def measured(value):return Measure(value.value,value.state,value.observed,value.possible)
            # A unique token refers to this complete checked immutable
            # evaluation. Eviction cannot recycle it while a key retains it.
            return _CompactProjection(evaluation,measured(score.summary),tuple(measured(d) for d in score.details),object())
        return self.reuse_record(key,build)

    def compact(self,garments,roles,indexes,legacy,*,relative=False):
        return self.compact_projection(garments,roles,indexes,legacy,relative=relative).evaluation
