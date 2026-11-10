"""P2 wrappers delegate unchanged R/C facts; they replace only preference utility."""
from dataclasses import asdict
from fractions import Fraction as F
import json
from app.domain.value_objects.attribute_preferences import PROFILE,DECISION,encode,digest,PreferenceError
from app.domain.value_objects.attribute_preference_evidence import ratio
from app.domain.value_objects.compact_recommendation import CompactScore,Measure,validate_total
from app.domain.value_objects.recommendation_score import RecommendationScore
from app.application.recommendation.context_relevance_scorer import PreparedRelativeFacts,RelativeTracker,snapshot_hash


def measure(value):return Measure(value.value,value.state,value.observed,value.possible)


def public_score(legacy,preference):
    r,c=legacy.request_match,legacy.compatibility
    result=RecommendationScore(r,c,preference,F(3,5)*r.contribution+F(1,5)*c.contribution+F(1,5)*preference.contribution,
                               PROFILE,DECISION,(F(3,5),F(1,5),F(1,5)))
    from app.application.recommendation.palette_compatibility_selection import profile_score
    return profile_score(result,p2=True)


class _ScoreIdentity:
    """Strong identity of the original, complete immutable numeric certificate.

    The original fact producer returns its independently validated CompactScore
    for every actual candidate. Identity implies equality of ALL immutable
    fields, including ordered C atoms, states, counts and request details. A
    fresh equal record merely misses; no partial numeric key can alias it.
    Keeping the object prevents id recycling while the entry is resident.
    """
    __slots__=('score',)
    def __init__(self,score):self.score=score
    def __hash__(self):return id(self.score)
    def __eq__(self,other):return type(other) is _ScoreIdentity and self.score is other.score


class P2CompactFacts:
    def __init__(self,original,prepared,garments):
        self.original,self.prepared,self.garments=original,prepared,tuple(garments)
        self.last=None

    def original_score(self,roles,indexes):
        if self.last is None or self.last[:2]!=(roles,indexes):self.last=(roles,indexes,self.original.score(roles,indexes))
        return self.last[2]

    def score(self,roles,indexes):
        legacy=self.original_score(roles,indexes)
        projection=self.prepared.compact_projection(self.garments,roles,indexes,legacy)
        key=('baseline_certificate',roles,_ScoreIdentity(legacy),projection.token)
        def build():
            p=projection.evaluation.score
            result=CompactScore(legacy.request,legacy.compatibility,projection.summary,
                F(3,5)*legacy.request.contribution+F(1,5)*legacy.compatibility.value+F(1,5)*p.contribution,
                legacy.request_details,projection.details)
            validate_total(result,(F(3,5),F(1,5),F(1,5)))
            return result
        return self.prepared.reuse_record(key,build)

    @property
    def cache_info(self):return self.original.cache_info


class P2RelativeFacts:
    def __init__(self,garments,request,preferences,prepared,compact_facts=None):
        self.original=PreparedRelativeFacts(garments,request,preferences)
        self.prepared,self.compact_facts=prepared,compact_facts
        prepared.bind_objective(self.original.objective)
        self.garments=tuple(garments)

    def __getattr__(self,name):return getattr(self.original,name)

    def compact(self,roles,indexes,legacy):
        bounds=self.original.bounds(roles,indexes)
        if bounds is None:return None,None
        original=self.compact_facts.original_score(roles,indexes) if self.compact_facts is not None else getattr(legacy,'original_preference_score',legacy)
        projection=self.prepared.compact_projection(self.garments,roles,indexes,original,relative=True)
        def build():
            p=projection.evaluation.score
            low,high,known,count=bounds
            optimistic=(F(3,5)*high+F(1,5)*legacy.compatibility.value+F(1,5)*p.contribution,high,legacy.compatibility.value,p.contribution)
            # Informational P upper is deliberately excluded from ranking bounds.
            if low!=high:return None,(bounds,optimistic)
            result=CompactScore(Measure(low,'Available',known,count),legacy.compatibility,projection.summary,optimistic[0],
                                (Measure(low,'Available',known,count),),projection.details)
            if self.compact_facts is not None:validate_total(result,(F(3,5),F(1,5),F(1,5)))
            return result,(bounds,optimistic)
        # The public reference uses mutable per-candidate scalar collaborators,
        # so it retains its original independent arithmetic path. Only the
        # compact producer's complete immutable certificates can be retained.
        if self.compact_facts is None:return build()
        key=('relative_certificate',roles,_ScoreIdentity(original),_ScoreIdentity(legacy),projection.token,bounds)
        return self.prepared.reuse_record(key,build)

    def public(self,verified,legacy):
        relative=self.original.public(verified,legacy)
        return public_score(relative,self.prepared.public(verified,relative=True).score)


class P2RelativeTracker(RelativeTracker):
    def proof(self,winner):
        """Same original R/coverage/Seen state, under a separate P2 proof reader."""
        facts=self.facts;objective=facts.objective;selected=[]
        for member in winner.verified.candidate.members:
            g=member.garment;match,styles,source_state,origin,review=facts.facts[facts.by_id[g.garment_id]]
            selected.append({'garment_id':g.garment_id,'role':member.role,'snapshot_sha256':snapshot_hash(g),'styles':list(styles),
                             'match':match if member.role!='outerwear' else None,'source_state':source_state,'origin':origin,'review_state':review})
        blocker=None
        if self.blocker:
            _,roles,indexes,bounds,values=self.blocker
            blocker={'key':[[role,facts.garments[i].garment_id] for role,i in zip(roles,indexes)],'R_low':ratio(bounds[0]),'R_high':ratio(bounds[1]),'optimistic':[ratio(v) for v in values]}
        ledger=facts.prepared.public(winner.verified,relative=self.relative).to_dict()
        data={'version':'context-relevance-evidence-2.0.0','explanation_version':'context-relevance-explanation-2.0.0',
            'policy_version':facts.policy.policy_version,'policy_sha256':facts.policy.policy_sha256,'catalogue_version':facts.policy.catalogue_version,'catalogue_sha256':facts.policy.catalogue_sha256,
            'requested_profile':'context_relevance_decision_v1','actual_profile':winner.score.profile_name,'preference_profile':PROFILE,
            'preference_snapshot_sha256':facts.prepared.snapshot.revision,'preference_ledger_sha256':digest(ledger),
            'selection_mode':'best_evidenced_with_coverage_v1' if self.relative else 'baseline_disclosed_v1',
            'fallback_reason':None if self.relative else 'objective_unavailable' if objective is None else 'no_point_relative_candidate',
            'objective':asdict(objective) if objective else None,
            'coverage':{'hard_passed':self.passed,'point_candidates':self.points,'unresolved_candidates':self.unresolved,
                        'objective_unavailable_candidates':self.passed if objective is None else 0,
                        'global_optimum_certified':bool(self.relative and (self.blocker is None or self.best_point[0]<self.blocker[0]))},
            'strongest_unresolved':blocker,'selected_members':selected,'winning_key':[list(v) for v in winner.verified.candidate.key],
            'numeric_ties':self.point_ties if self.relative else self.legacy_ties,'preference_denominator':ratio(facts.prepared.public(winner.verified,relative=self.relative).denominator),
            'relative_R':ratio(winner.score.request_match.contribution) if self.relative else None,
            'score_components':[ratio(x.contribution) for x in (winner.score.request_match,winner.score.compatibility,winner.score.preference)],
            'total':ratio(winner.score.total),'weights':[ratio(w) for w in winner.score.weights]}
        if facts.policy.bundle_id!='legacy_8_v1':
            from app.application.recommendation.context_bundle import ContextBundle
            from app.application.recommendation.context_constraint_compiler import compile_context
            bundle=ContextBundle.load(facts.policy.bundle_id);plan=compile_context(facts.policy.registry,facts.request)
            data.update(bundle_id=bundle.identifier,bundle_sha256=bundle.manifest_sha256,
                        context_plan={'request':facts.request.to_dict(),'bindings':[plan.binding.identifier,*[p.binding.identifier for _,p in plan.secondary]]})
        if self.refinement_plan is not None:
            data['selection_scope_sha256']=self.refinement_plan.selection_scope_sha256
            data['coverage'].update(self.skipped)
        raw=encode(data)
        if len(raw)>307200:raise PreferenceError('PreferenceCapacityExceeded','P2 relative proof exceeds its allocation.')
        return raw.decode('utf-8')
