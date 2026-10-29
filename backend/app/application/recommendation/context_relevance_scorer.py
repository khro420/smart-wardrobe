"""One prepared style objective, exact streaming ranking and immutable proof.

The compact kernel and reference stream retain their own eligibility/C paths.
Unknown relative candidates are never assigned an earned request-match score.
"""
from dataclasses import asdict, replace
from fractions import Fraction as F
import hashlib
import json

from app.application.recommendation.context_relevance_policy import ContextRelevancePolicy, PROFILE, POLICY_VERSION, CATALOGUE_VERSION, SCOPES
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.application.recommendation.preference_scorer import PreferenceScorer
from app.domain.value_objects.context_relevance import ratio, bounded_json, exact_text
from app.domain.value_objects.general_context_request import GeneralContextRequest
from app.domain.value_objects.recommendation_score import ComponentScore, ScoreEvidence, RecommendationScore
from app.domain.value_objects.compact_recommendation import Measure, CompactScore
from app.domain.value_objects.recommendation_refinement import RefinementError


def applies(request):
    if type(request) is not GeneralContextRequest:return False
    if request.context.bundle_id!='legacy_8_v1':
        from app.application.recommendation.context_bundle import ARCHIVES,ACTIVE_WAVE
        return request.context.situation.value in ARCHIVES[ACTIVE_WAVE]['targets']
    return request.context.situation.value in {row[0] for row in SCOPES}


def snapshot_hash(garment):
    return hashlib.sha256(json.dumps(asdict(garment),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def order_key(values, garment_key):
    return tuple(-x for x in values)+(garment_key,)


class PreparedRelativeFacts:
    def __init__(self,garments,request,preferences,policy=None):
        self.policy=policy or (ContextRelevancePolicy.load() if request.context.bundle_id=='legacy_8_v1' else ContextRelevancePolicy.load(bundle_id=request.context.bundle_id))
        self.resolution=self.policy.resolve(request)
        self.garments=tuple(garments)
        self.request,self.preferences=request,preferences
        self.objective=self.resolution.objective
        for preference in preferences.preferences:
            ratio(preference.importance)  # Fail before enumeration; do not restrict old profiles.
        self.mask=tuple(not (self.objective is not None and p.preference_type=='styles'
                            and tuple(p.values)==(self.objective.target,)) for p in preferences.preferences)
        self.denominator=sum((p.importance for p in preferences.preferences),F())
        ratio(self.denominator)
        mapper=GarmentEvidenceMapper()
        facts=[]
        for g in self.garments:
            style=mapper.classify(g).style
            source=g.saved_attribute_evidence
            admitted=(style.state=='Known' and len(style.values)==1
                and g.contextual_suitability.state!='Malformed' and g.contextual_suitability.review_state!='Malformed'
                and (source.state=='Absent' or source.current(g)))
            match=int(style.values[0]==self.objective.target) if admitted and self.objective else None
            facts.append((match,tuple(style.values),source.state,source.origin,g.contextual_suitability.review_state))
        self.facts=tuple(facts)
        self.by_id={g.garment_id:i for i,g in enumerate(self.garments)}
        from app.application.recommendation.context_relevance_verifier import PublicAlignmentFacts
        self.public_facts=PublicAlignmentFacts(self.garments,self.objective)

    def bounds(self,roles,indexes):
        if self.objective is None:return None
        matches=[self.facts[i][0] for role,i in zip(roles,indexes) if role!='outerwear']
        known=sum(m is not None for m in matches)
        low=F(sum(m for m in matches if m is not None),len(matches))
        return low,low+F(len(matches)-known,len(matches)),known,len(matches)

    def compact(self,roles,indexes,legacy):
        from app.application.recommendation.compact_scoring_facts import independent_preference
        bounds=self.bounds(roles,indexes)
        if bounds is None:return None,None
        low,high,known,count=bounds
        p,pdetails=independent_preference(self.preferences,legacy.preference,legacy.preference_details,self.mask)
        optimistic=(F(3,5)*high+F(1,5)*legacy.compatibility.value+F(1,5)*p.contribution,
                    high,legacy.compatibility.value,p.contribution)
        if low!=high:return None,(bounds,optimistic)
        r=Measure(low,'Available',known,count)
        score=CompactScore(r,legacy.compatibility,p,optimistic[0],(r,),pdetails)
        return score,(bounds,optimistic)

    def public(self,verified,legacy):
        from app.application.recommendation.request_match_scorer import RequestMatchScorer
        r=RequestMatchScorer.relative_component(verified,self.public_facts)
        if r.summary.value is None:raise ValueError('Unknown R cannot be a relative scored winner.')
        p=PreferenceScorer.independent_component(legacy.preference,self.preferences,self.objective)
        return RecommendationScore(r,legacy.compatibility,p,
            F(3,5)*r.contribution+F(1,5)*legacy.compatibility.contribution+F(1,5)*p.contribution,
            PROFILE,self.policy.policy_version,(F(3,5),F(1,5),F(1,5)))


class RelativeTracker:
    """Constant-size winner, baseline and strongest unresolved blocker state."""
    def __init__(self,facts,refinement_plan=None):
        self.facts=facts
        self.refinement_plan=refinement_plan
        self.skipped=dict(already_seen=0,below_floor_points=0,unresolved_below_floor=0)
        self.best_point=self.best_legacy=self.blocker=None
        self.passed=self.points=self.unresolved=0
        self.point_ties=self.legacy_ties=0

    def consider(self,roles,indexes,conditions,legacy,garment_key):
        self.passed+=1
        legacy_values=(legacy.total,*legacy.contributions)
        item=(order_key(legacy_values,garment_key),roles,indexes,conditions,legacy)
        if self.best_legacy is None or item[0][:-1]<self.best_legacy[0][:-1]:self.legacy_ties=1
        elif item[0][:-1]==self.best_legacy[0][:-1]:self.legacy_ties+=1
        if self.best_legacy is None or item[0]<self.best_legacy[0]:self.best_legacy=item
        point,info=self.facts.compact(roles,indexes,legacy)
        if info is None:return None,info
        bounds,values=info
        if self.refinement_plan is not None:
            from app.application.recommendation.refinement_selector import classify_remaining
            group=classify_remaining(self.refinement_plan,garment_key,bounds)
            if group in self.skipped:
                self.skipped[group]+=1
                return point,info
        if point is None:
            self.unresolved+=1
            blocker=(order_key(values,garment_key),roles,indexes,bounds,values)
            if self.blocker is None or blocker[0]<self.blocker[0]:self.blocker=blocker
        else:
            self.points+=1
            item=(order_key(values,garment_key),roles,indexes,conditions,point)
            if self.best_point is None or item[0][:-1]<self.best_point[0][:-1]:self.point_ties=1
            elif item[0][:-1]==self.best_point[0][:-1]:self.point_ties+=1
            if self.best_point is None or item[0]<self.best_point[0]:self.best_point=item
        return point,info

    @property
    def selected(self):return self.best_point if self.refinement_plan is not None else self.best_point or self.best_legacy

    @property
    def empty_refinement_status(self):
        if self.refinement_plan is None or not self.passed:return None
        if self.facts.objective is None:return 'RefinementUnavailable'
        if self.unresolved:return 'RefinementInsufficientEvidence'
        return 'RefinementExhausted' if self.refinement_plan.ordinal else 'RefinementInsufficientEvidence'

    @property
    def relative(self):return self.best_point is not None

    def proof(self,winner):
        objective=self.facts.objective
        certified=self.relative and (self.blocker is None or self.best_point[0]<self.blocker[0])
        selected=[]
        for member in winner.verified.candidate.members:
            g=member.garment
            match,styles,source_state,origin,review=self.facts.facts[self.facts.by_id[g.garment_id]]
            selected.append(dict(garment_id=g.garment_id,role=member.role,snapshot_sha256=snapshot_hash(g),
                styles=list(styles),match=match if member.role!='outerwear' else None,
                source_state=source_state,origin=origin,review_state=review))
        blocker=None
        if self.blocker:
            _,roles,indexes,bounds,values=self.blocker
            blocker=dict(key=[[role,self.facts.garments[i].garment_id] for role,i in zip(roles,indexes)],
                R_low=ratio(bounds[0]),R_high=ratio(bounds[1]),optimistic=[ratio(v) for v in values])
        data=dict(version='context-relevance-evidence-1.0.0',explanation_version='context-relevance-explanation-1.0.0',
            policy_version=self.facts.policy.policy_version,policy_sha256=self.facts.policy.policy_sha256,
            catalogue_version=self.facts.policy.catalogue_version,catalogue_sha256=self.facts.policy.catalogue_sha256,
            requested_profile=PROFILE,actual_profile=winner.score.profile_name,
            selection_mode='best_evidenced_with_coverage_v1' if self.relative else 'baseline_disclosed_v1',
            fallback_reason=None if self.relative else 'objective_unavailable' if objective is None else 'no_point_relative_candidate',
            objective=asdict(objective) if objective else None,
            coverage=dict(hard_passed=self.passed,point_candidates=self.points,unresolved_candidates=self.unresolved,
                objective_unavailable_candidates=self.passed if objective is None else 0,global_optimum_certified=bool(certified)),
            strongest_unresolved=blocker,selected_members=selected,
            winning_key=[list(v) for v in winner.verified.candidate.key],
            numeric_ties=self.point_ties if self.relative else self.legacy_ties,
            preference_denominator=ratio(self.facts.denominator),
            preferences=[dict(id=p.preference_id,kind=p.preference_type,values=[asdict(v) if hasattr(v,'__dataclass_fields__') else v for v in p.values],
                weight=ratio(p.importance),suppressed=self.relative and not keep) for p,keep in zip(self.facts.preferences.preferences,self.facts.mask)],
            relative_R=ratio(winner.score.request_match.contribution) if self.relative else None,
            score_components=[ratio(x.contribution) for x in (winner.score.request_match,winner.score.compatibility,winner.score.preference)],
            total=ratio(winner.score.total),weights=[ratio(w) for w in winner.score.weights])
        if self.facts.policy.bundle_id!='legacy_8_v1':
            from app.application.recommendation.context_bundle import ContextBundle
            from app.application.recommendation.context_constraint_compiler import compile_context
            bundle=ContextBundle.load(self.facts.policy.bundle_id)
            plan=compile_context(self.facts.policy.registry,self.facts.request)
            data.update(version='context-relevance-evidence-1.1.0',explanation_version='context-relevance-explanation-1.1.0',
                bundle_id=bundle.identifier,bundle_sha256=bundle.manifest_sha256,
                context_plan=dict(request=self.facts.request.to_dict(),bindings=[plan.binding.identifier,*[p.binding.identifier for _,p in plan.secondary]]))
        if self.refinement_plan is not None:
            if not self.relative or data['version']!='context-relevance-evidence-1.1.0':
                raise ValueError('Refinement requires an expanded ordinary point-relative result.')
            data.update(version='context-relevance-evidence-1.2.0',explanation_version='context-relevance-explanation-1.2.0',
                selection_scope_sha256=self.refinement_plan.selection_scope_sha256)
            data['coverage'].update(self.skipped)
        from app.application.recommendation.context_relevance_verifier import validate_evidence
        validate_evidence(data,winner.score,winner.verified.candidate)
        return bounded_json(data)


def reference_rank(engine,query,user,request,refinement_plan=None):
    """Public-object reference loop; no compact candidate/scoring facts."""
    from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
    from app.application.recommendation.preference_normalizer import PreferenceNormalizer
    from app.application.recommendation.request_match_scorer import RequestMatchScorer
    from app.application.recommendation.rule_based_compatibility_scorer import RuleBasedCompatibilityScorer
    from app.application.recommendation.rule_based_compatibility_policy import RuleBasedCompatibilityPolicy
    from app.application.recommendation.prepared_decision_policy import PreparedDecisionPolicy
    from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
    from app.domain.value_objects.ranking_outcome import RankingOutcome
    from app.domain.value_objects.scored_candidate import ScoredCandidate
    from app.domain.value_objects.compatibility_signature import STRUCTURES
    from app.domain.value_objects.context_relevance import RelativeEncodingLimit
    from app.application.recommendation.preference_normalizer import InvalidPreferenceData
    from app.application.recommendation.scoring_eligibility_gate import InvalidScoringInput
    session=None
    try:
        from app.application.recommendation.garment_retrieval_service import GarmentRetrievalService
        from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
        from app.application.recommendation.compact_exhaustive_scorer import SnapshotQuery
        actual=engine.engine if hasattr(engine,'engine') else engine
        if not actual.evaluator_factory().supports(request):return RankingOutcome('PolicyUnavailable')
        garments=GarmentRetrievalService(actual.structural_engine.retrieval.query).retrieve(user).garments
        if refinement_plan is not None:
            from app.application.recommendation.refinement_selector import filter_snapshot,check_category_conflicts
            from app.application.nlp.vocabulary import Vocabulary
            check_category_conflicts(request,refinement_plan.exclusions,Vocabulary.load())
            filtered=filter_snapshot(garments,refinement_plan.exclusions)
            garments=filtered.garments
        replay_engine=RequestCandidateEngine(SnapshotQuery(user,garments),evaluator_factory=actual.evaluator_factory)
        session=replay_engine.generate_candidates(user,request)
        if hasattr(engine,'session'):engine.session=session
        if session.result.status in ('PolicyUnavailable','ProcessingFailure','Interrupted'):return RankingOutcome(session.result.status)
        preferences=PreferenceNormalizer().normalize(user,query.get_active_preferences(user))
        facts=PreparedRelativeFacts(garments,request,preferences)
        tracker=RelativeTracker(facts,refinement_plan)
        gate=ScoringEligibilityGate(session,user,request)
        rscorer,pscorer=RequestMatchScorer(),PreferenceScorer()
        cscorer=RuleBasedCompatibilityScorer(RuleBasedCompatibilityPolicy.load())
        decision=PreparedDecisionPolicy(CompatibilityDecisionPolicy.load())
        structures={roles:name for name,roles in STRUCTURES.items()}
        winners={}
        for item in session:
            verified=gate.verify(item)
            roles=tuple(m.role for m in verified.candidate.members)
            indexes=tuple(facts.by_id[m.garment.garment_id] for m in verified.candidate.members)
            c=decision.apply(cscorer.score(verified),structures[roles])
            r,p=rscorer.score(verified),pscorer.score(verified,preferences)
            legacy=RecommendationScore(r,c,p,F(3,5)*r.contribution+F(1,5)*c.contribution+F(1,5)*p.contribution,
                'experimental_compatibility_decision_v1',decision.version,decision.weights)
            # Tracker receives independently computed public scalar/detail measures.
            from app.domain.value_objects.compact_recommendation import Measure
            compact=type('ReferenceScalar',(),dict(total=legacy.total,contributions=(r.contribution,c.contribution,p.contribution),
                preference=Measure(p.summary.value,p.summary.state,p.summary.observed,p.summary.possible),
                preference_details=tuple(Measure(d.value,d.state,d.observed,d.possible) for d in p.details),
                compatibility=type('C',(),dict(value=c.contribution))()))()
            point,_=tracker.consider(roles,indexes,None,compact,verified.candidate.key)
            chosen=ScoredCandidate(verified,facts.public(verified,legacy)) if point else ScoredCandidate(verified,legacy)
            if point is not None and (chosen.score.total,chosen.score.request_match.contribution,chosen.score.preference.contribution)!=(point.total,point.request.contribution,point.preference.contribution):
                raise ValueError('Reference scalar and independent public score disagree.')
            # Constant state: retain only current known winner and baseline winner.
            if tracker.best_point and tracker.best_point[2]==indexes:winners['point']=chosen
            if tracker.best_legacy[2]==indexes:winners['legacy']=ScoredCandidate(verified,legacy)
        result=session.result
        session.close();session=None
        if not result.complete:return RankingOutcome('ProcessingFailure')
        if tracker.selected is None:
            status=tracker.empty_refinement_status or result.status
            summary=None
            if refinement_plan is not None:
                from app.application.recommendation.refinement_selector import outcome_summary
                if not garments and filtered.excluded_garments:status='InsufficientStructure'
                summary=outcome_summary(refinement_plan,filtered,tracker,result.failed,result.unknown,status)
            return RankingOutcome(status,complete=status!='RefinementUnavailable',refinement_summary=summary)
        winner=winners['point' if tracker.relative else 'legacy']
        proof=tracker.proof(winner)
        summary=None
        if refinement_plan is not None:
            from app.application.recommendation.refinement_selector import outcome_summary
            summary=outcome_summary(refinement_plan,filtered,tracker,result.failed,result.unknown,'Selected')
        return RankingOutcome('Selected',winner,True,tracker.points if tracker.relative else tracker.passed,ranking_evidence=proof,refinement_summary=summary)
    except RefinementError as exc:return RankingOutcome(exc.status,diagnostics=(('refinement_reason',exc.reason),))
    except RelativeEncodingLimit:return RankingOutcome('ProfileUnavailable',diagnostics=(('ranking_reason','exact_encoding_budget_exceeded'),))
    except InvalidPreferenceData:return RankingOutcome('InvalidPreferenceData')
    except InvalidScoringInput:return RankingOutcome('InvalidScoringInput')
    except (KeyboardInterrupt,GeneratorExit):return RankingOutcome('Interrupted')
    except Exception:return RankingOutcome('ProcessingFailure')
    finally:
        if session is not None:
            try:session.close()
            except Exception:pass
