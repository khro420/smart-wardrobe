"""Isolated exact exhaustive kernel. Not selected by any live factory."""
from app.application.recommendation.general_context_evaluator import GeneralContextEvaluator, EvaluatorSpecification, construct_evaluator
from dataclasses import asdict
from time import perf_counter
from threading import Lock
from app.application.recommendation.compact_candidate_stream import groups,enumerate_indexes,key,materialize
from app.application.recommendation.structural_policy import StructuralPolicy
from app.application.recommendation.compact_mandatory_verifier import CompactMandatoryFacts,CompactEligibilityVerifier,state_of,PASS,FAIL
from app.application.recommendation.compact_scoring_facts import CompactScoringFacts
from app.application.recommendation.garment_retrieval_service import GarmentRetrievalService
from app.application.recommendation.preference_normalizer import PreferenceNormalizer,InvalidPreferenceData
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.contextual_suitability_evaluator import ContextualSuitabilityEvaluator
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate,InvalidScoringInput
from app.application.recommendation.request_match_scorer import RequestMatchScorer
from app.application.recommendation.preference_scorer import PreferenceScorer
from app.application.recommendation.prepared_compatibility_aggregation import PreparedCompatibilityAggregation
from app.application.recommendation.prepared_decision_policy import PreparedDecisionPolicy
from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
from app.application.recommendation.rule_based_compatibility_policy import RuleBasedCompatibilityPolicy
from app.application.recommendation.scoring_policy import ScoringProfile
from app.domain.value_objects.compatibility_signature import STRUCTURES
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.domain.value_objects.request_candidate_evaluation import EvaluatedCandidate
from app.domain.value_objects.recommendation_score import RecommendationScore,ComponentScore,ScoreEvidence
from app.domain.value_objects.scored_candidate import ScoredCandidate
from app.domain.value_objects.ranking_outcome import RankingOutcome
from app.domain.value_objects.compact_recommendation import Measure
from app.shared_contracts.confirmed_garment_query import ConfirmedGarmentQuery
from app.domain.value_objects.context_relevance import RelativeEncodingLimit
from app.domain.value_objects.recommendation_refinement import RefinementError

DEFERRED='compatibility_deferred'
EXPERIMENTAL='experimental_compatibility_decision_v1'


class SnapshotQuery(ConfirmedGarmentQuery):
    """Read-only replay of an already acquired Phase 1 session, not persistence."""
    def __init__(self,user,garments):self.user,self.garments=user,tuple(garments)
    def get_confirmed_available_garments(self,user_id):
        if user_id!=self.user:raise InvalidScoringInput('Snapshot owner mismatch.')
        return self.garments
    def list_available_garment_ids(self,user_id):
        return [g.garment_id for g in self.get_confirmed_available_garments(user_id)]


def measure(public):
    return Measure(public.value,public.state,public.observed,public.possible)


def numeric_key(score):
    return (score.total,*score.contributions)


class CompactExhaustiveScorer:
    def __init__(self,query,preference_query,profile=EXPERIMENTAL,*,evaluator_type=RequestConstraintEvaluator,
                 audit=None,checkpoint=None,stream_factory=enumerate_indexes,pair_capacity=19900,aggregation_capacity=256,diagnostics=False,context_ranking=False):
        self.query,self.preference_query,self.profile=query,preference_query,profile
        self.evaluator_type,self.audit,self.checkpoint,self.stream_factory=evaluator_type,audit,checkpoint,stream_factory
        self.pair_capacity,self.aggregation_capacity=pair_capacity,aggregation_capacity
        self.instrument=diagnostics; self.timings={}; self.cache_statistics={};self.public_session=None
        self._lock=Lock()
        self.context_ranking=context_ranking

    def _event(self,stage,*args):
        if self.checkpoint is not None:self.checkpoint(stage,*args)

    def rank(self,user_id,request,refinement_plan=None):
        if not self._lock.acquire(blocking=False):return RankingOutcome('InvalidScoringInput')
        self.timings={};self.cache_statistics={};self.public_session=None
        experimental=self.profile==EXPERIMENTAL
        seen=scored=examined=failed=unknown=0; best=None; stream=None; diagnostics=()
        tracker=None;ranking_evidence=None;filtered=None
        basis={name:0 for name in ('Computed','PartiallyConventional','FullyConventional','NoPairReference')}
        coverage={name:{'examined':0,'available':0,'unknown':0,'zero':0,'no_pairs':0} for name in STRUCTURES}
        atomic_known=atomic_possible=compat_unknown=not_applicable=0
        def finish(status,winner=None,complete=False):
            if experimental:
                counts=tuple(('coverage:'+name,k+'='+str(v)) for name,values in sorted(coverage.items()) for k,v in sorted(values.items()))
                extra=(('accepted_examined',str(seen)),('numerically_scored',str(scored)),('compatibility_unknown',str(compat_unknown)),('compatibility_not_applicable',str(not_applicable)))
                extra=(*extra,*counts,*tuple(('decision_basis:'+name,str(n)) for name,n in basis.items()),('atomic_known',str(atomic_known)),('atomic_possible',str(atomic_possible)))
            else:extra=()
            count=tracker.points if tracker is not None and tracker.relative else scored
            summary=None
            if refinement_plan is not None and filtered is not None and tracker is not None:
                from app.application.recommendation.refinement_selector import outcome_summary
                summary=outcome_summary(refinement_plan,filtered,tracker,failed,unknown,status)
            return RankingOutcome(status,winner,complete,count,(*diagnostics,*extra),ranking_evidence,summary)
        try:
            start=perf_counter()
            if self.profile not in (DEFERRED,EXPERIMENTAL):return finish('ProfileUnavailable')
            try:
                raw_policy=RuleBasedCompatibilityPolicy.load() if experimental else None
                profile=CompatibilityDecisionPolicy.load() if experimental else ScoringProfile.load(DEFERRED)
            except (ValueError,TypeError,OSError):return finish('ProfileUnavailable')
            if experimental:
                diagnostics=(('compatibility_policy',raw_policy.version),('compatibility_policy_hash',raw_policy.hash),
                    ('scoring_profile_hash',profile.hash),('experimental','true'),('coverage_policy','all_mandatory_valid_candidates_use_explicit_decision'))
            if not isinstance(request,StructuredOutfitRequest):return finish('PolicyUnavailable')
            try:evaluator=construct_evaluator(self.evaluator_type)
            except (ValueError,TypeError):raise InvalidScoringInput('Unapproved evaluator type or bundle.')
            if not evaluator.supports(request):return finish('PolicyUnavailable')
            try:retrieved=GarmentRetrievalService(self.query).retrieve(user_id)
            except Exception:return finish('ProcessingFailure')
            garments=retrieved.garments
            if refinement_plan is not None:
                from app.application.recommendation.refinement_selector import filter_snapshot,check_category_conflicts
                from app.application.nlp.vocabulary import Vocabulary
                check_category_conflicts(request,refinement_plan.exclusions,Vocabulary.load())
                filtered=filter_snapshot(garments,refinement_plan.exclusions)
                garments=filtered.garments
                diagnostics=(*diagnostics,('excluded_garments',str(filtered.excluded_garments)),
                    ('structural_bound_before',str(filtered.structural_bound_before)),('structural_bound_after',str(filtered.structural_bound_after)))
            slots=groups(garments)
            if type(evaluator) not in (RequestConstraintEvaluator,SuitabilityRequestEvaluator,ContextualSuitabilityEvaluator,GeneralContextEvaluator):raise InvalidScoringInput('Unapproved evaluator type.')
            expected_count=(len(slots['upper'])*len(slots['lower'])+len(slots['one_piece']))*(1+len(slots['outerwear']))
            composition_order={roles:n for n,roles in enumerate(StructuralPolicy.load().compositions)}
            membership={role:frozenset(items) for role,items in slots.items()};previous_position=None
            preferences=PreferenceNormalizer().normalize(user_id,self.preference_query.get_active_preferences(user_id))
            diagnostics=(*diagnostics,*preferences.diagnostics)
            primary=CompactMandatoryFacts(garments,request,self.evaluator_type)
            independent=CompactEligibilityVerifier(user_id,garments,request,self.evaluator_type)
            facts=CompactScoringFacts(garments,request,preferences,raw_policy,profile.weights,experimental,self.pair_capacity,self.aggregation_capacity)
            if self.context_ranking:
                from app.application.recommendation.context_relevance_scorer import applies,PreparedRelativeFacts,RelativeTracker
                if not experimental:return finish('ProfileUnavailable')
                if getattr(request,'context',None) is not None and request.context.bundle_id!=getattr(self.evaluator_type,'bundle_id','legacy_8_v1'):return finish('ProfileUnavailable')
                if applies(request):tracker=RelativeTracker(PreparedRelativeFacts(garments,request,preferences),refinement_plan)
            if refinement_plan is not None and tracker is None:return finish('RefinementUnavailable')
            self.timings['preparation']=perf_counter()-start
            # Reconstructor is used only for audit or the completed winning item.
            public_engine = RequestCandidateEngine(SnapshotQuery(user_id,garments), **(
                {"evaluator_specification": self.evaluator_type} if type(self.evaluator_type) is EvaluatorSpecification
                else {"evaluator_factory": self.evaluator_type}))
            public_session=public_engine.generate_candidates(user_id,request)
            self.public_session=public_session
            gate=ScoringEligibilityGate(public_session,user_id,request)
            public_r,public_p=RequestMatchScorer(),PreferenceScorer()
            public_c=PreparedCompatibilityAggregation(raw_policy) if experimental else None
            public_decision=PreparedDecisionPolicy(profile) if experimental else None
            structures={roles:name for name,roles in STRUCTURES.items()}
            def reconstruct(roles,indexes,conditions,compact=None,relative_point=False):
                candidate=materialize(garments,roles,indexes)
                evaluation=public_session.evaluator.evaluate(candidate,request)
                expected=tuple((field,value,{1:'Pass',0:'Fail',-1:'Unknown'}[state],tuple(garments[i].garment_id for p,i in enumerate(indexes) if mask&(1<<p))) for field,value,state,mask in conditions)
                actual=tuple((c.field,c.value,c.state,c.evidence_ids) for c in evaluation.conditions)
                if actual!=expected:raise InvalidScoringInput('Public mandatory reconstruction mismatch.')
                if compact is None:return candidate,evaluation,None
                verified=gate.verify(EvaluatedCandidate(candidate,evaluation))
                r,p=public_r.score(verified),public_p.score(verified,preferences)
                c=public_decision.apply(public_c.score(verified),structures[roles]) if experimental else ComponentScore(ScoreEvidence('compatibility',None,'Unavailable'))
                public=RecommendationScore(r,c,p,sum(w*x.contribution for w,x in zip(profile.weights,(r,c,p))),profile.name,profile.version,profile.weights)
                if relative_point:
                    public=tracker.facts.public(verified,public)
                    r,p=public.request_match,public.preference
                if public.total!=compact.total:raise InvalidScoringInput('Public exact total mismatch.')
                if (measure(r.summary),measure(p.summary))!=(compact.request,compact.preference) or tuple(map(measure,r.details))!=compact.request_details or tuple(map(measure,p.details))!=compact.preference_details:
                    raise InvalidScoringInput('Public R/P reconstruction mismatch.')
                if experimental:
                    decision=c.decision; cc=compact.compatibility
                    if (measure(c.summary),tuple(map(measure,c.details[:2])),tuple(x.value for x in c.details if x.name.startswith(('colour:','style:'))),decision.basis,decision.value,decision.lower,decision.upper,decision.known_sum,decision.known_count,decision.pair_count)!=(cc.raw,(cc.colours,cc.styles),cc.atoms,cc.basis,cc.value,cc.lower,cc.upper,cc.known_sum,cc.known,cc.pairs):
                        raise InvalidScoringInput('Public compatibility reconstruction mismatch.')
                return candidate,evaluation,ScoredCandidate(verified,public)
            stream=iter(self.stream_factory(slots))
            while True:
                tick=perf_counter() if self.instrument else 0
                try:roles,indexes=next(stream)
                except StopIteration:break
                if self.instrument:self.timings['enumeration']=self.timings.get('enumeration',0)+perf_counter()-tick
                self._event('candidate',roles,indexes)
                if type(indexes) is not tuple or len(indexes)!=len(roles) or any(type(i) is not int or i not in membership[role] for role,i in zip(roles,indexes)):
                    raise InvalidScoringInput('Invalid structural stream membership.')
                position=(composition_order[roles],indexes)
                if previous_position is not None and position<=previous_position:raise InvalidScoringInput('Duplicate or out-of-order structural candidate.')
                previous_position=position
                tick=perf_counter() if self.instrument else 0
                conditions=primary.evaluate(roles,indexes); state=state_of(conditions);examined+=1
                if self.instrument:self.timings['mandatory']=self.timings.get('mandatory',0)+perf_counter()-tick
                compact=None
                if state==PASS:
                    tick=perf_counter() if self.instrument else 0
                    independent.verify(roles,indexes,conditions)
                    if self.instrument:self.timings['independent']=self.timings.get('independent',0)+perf_counter()-tick
                    seen+=1
                    tick=perf_counter() if self.instrument else 0
                    compact=facts.score(roles,indexes)
                    if self.instrument:self.timings['scoring_validation']=self.timings.get('scoring_validation',0)+perf_counter()-tick
                    if experimental:
                        decision=compact.compatibility; basis[decision.basis]+=1;atomic_known+=decision.known;atomic_possible+=len(decision.atoms)
                        row=coverage[structures[roles]];row['examined']+=1
                        if decision.raw.state=='NotApplicable':not_applicable+=1;row['no_pairs']+=1
                        elif decision.raw.value is None:compat_unknown+=1;row['unknown']+=1
                        else:row['available']+=1;row['zero']+=int(decision.raw.value==0)
                    scored+=1
                    tick=perf_counter() if self.instrument else 0
                    if tracker is not None:
                        compact,relative_info=tracker.consider(roles,indexes,conditions,compact,key(garments,roles,indexes))
                    else:
                        values=numeric_key(compact)
                        if best is None or values>best[0] or (values==best[0] and key(garments,roles,indexes)<key(garments,best[1],best[2])):
                            best=(values,roles,indexes,conditions,compact)
                    if self.instrument:self.timings['ranking']=self.timings.get('ranking',0)+perf_counter()-tick
                elif state==FAIL:failed+=1
                else:unknown+=1
                if self.audit is not None:
                    candidate,evaluation,public=reconstruct(roles,indexes,conditions,compact,tracker is not None and compact is not None)
                    self.audit({'key':candidate.key,'candidate_id':candidate.candidate_id,'evaluation':asdict(evaluation),
                        'verified':state==PASS,'score':asdict(public.score) if public else None,
                        **({'relative_bounds':relative_info} if tracker is not None and state==PASS else {})})
            self._event('before_close',examined,scored)
            close=getattr(stream,'close',None)
            if close:close()
            stream=None
            self._event('closed',examined,scored)
            if examined!=expected_count or examined!=scored+failed+unknown or scored!=seen:
                raise InvalidScoringInput('Incomplete exhaustive candidate ledger.')
            self.cache_statistics=facts.cache_info
            if tracker is not None:best=tracker.selected
            if experimental:diagnostics=(*diagnostics,('stream_examined',str(examined)),('stream_passed',str(scored)),('stream_failed',str(failed)),('stream_unknown',str(unknown)))
            if best is None:
                public_session.close()
                status='NoEligibleGarments' if not garments else 'InsufficientStructure' if not slots['one_piece'] and not (slots['upper'] and slots['lower']) else 'NoStructuralCandidates' if not examined else 'InsufficientEvidence' if unknown else 'NoMatchingCandidates'
                if refinement_plan is not None and tracker is not None:
                    status=tracker.empty_refinement_status or status
                    if not garments and filtered.excluded_garments:status='InsufficientStructure'
                return finish(status,complete=status!='RefinementUnavailable')
            tick=perf_counter()
            _,_,winner=reconstruct(best[1],best[2],best[3],best[4],tracker is not None and tracker.relative)
            if tracker is not None:ranking_evidence=tracker.proof(winner)
            self.timings['reconstruction']=perf_counter()-tick
            public_session.close()
            self._event('reconstructed',winner)
            return finish('Selected',winner,True)
        except RefinementError as exc:
            diagnostics=(*diagnostics,('refinement_reason',exc.reason))
            return finish(exc.status)
        except RelativeEncodingLimit:
            diagnostics=(*diagnostics,('ranking_reason','exact_encoding_budget_exceeded'))
            return finish('ProfileUnavailable')
        except InvalidPreferenceData:return finish('InvalidPreferenceData')
        except InvalidScoringInput:return finish('InvalidScoringInput')
        except (KeyboardInterrupt,GeneratorExit):return finish('Interrupted')
        except Exception:return finish('ProcessingFailure')
        finally:
            if stream is not None:
                try:
                    close=getattr(stream,'close',None)
                    if close:close()
                except Exception:pass
            if self.public_session is not None:
                try:self.public_session.close()
                except Exception:pass
            self._lock.release()
