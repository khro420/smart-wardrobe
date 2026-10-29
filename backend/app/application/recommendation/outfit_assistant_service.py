"""Single-request Assistant integration; existing algorithms remain authoritative."""
from app.domain.value_objects.general_context_request import GeneralContextRequest
from app.application.recommendation.general_context_evaluator import GeneralContextEvaluator
from dataclasses import asdict
import hashlib
import json
import re
from time import perf_counter
from app.application.recommendation.recommendation_scorer import RecommendationScorer
from app.application.recommendation.assistant_scoring_selection import AssistantScoringSelection, DEFERRED, DECISION
from app.application.recommendation.assistant_execution_selection import AssistantExecutionSelection, REFERENCE, COMPACT, DEFAULT_ENGINE
from app.application.recommendation.scoring_display import with_scoring_display
from app.domain.value_objects.recommendation_persistence import RecommendationWrite, PersistenceConflict, WardrobeChanged
from app.application.recommendation.failure_diagnostics import log_failure
from app.domain.value_objects.contextual_outfit_request import ContextualOutfitRequest
from app.application.recommendation.contextual_suitability_evaluator import ContextualSuitabilityEvaluator
from app.domain.value_objects.context_relevance import RelativeEncodingLimit,bounded_json
from app.domain.value_objects.recommendation_refinement import RefinementAction,RefinementPlan,RefinementDraft,RefinementError


class CapturedPreferenceQuery:
    """One immutable, user-scoped read snapshot per ranking interaction."""
    def __init__(self, query):
        self.query, self.rows = query, None

    def get_active_preferences(self, user_id):
        if self.rows is not None:
            raise ValueError("Preference snapshot already consumed.")
        self.rows = tuple(self.query.get_active_preferences(user_id))
        return self.rows


class CapturedCandidateEngine:
    def __init__(self,engine):
        self.engine, self.session = engine, None

    def generate_candidates(self,user_id,request):
        self.session = self.engine.generate_candidates(user_id,request)
        return self.session


class OutfitAssistantService:
    def __init__(self, interpreter, engine, preference_query, repository, scorer_factory=RecommendationScorer, *, scoring_profile=DEFERRED, execution_engine=DEFAULT_ENGINE,context_ranking_profile='disabled',refinement_profile='disabled'):
        self.interpreter, self.engine = interpreter, engine
        self.preference_query, self.repository = preference_query, repository
        self.scorer_factory = scorer_factory
        self.scoring_profile = scoring_profile
        self.execution_engine = execution_engine
        self.context_ranking_profile=context_ranking_profile
        self.refinement_profile=refinement_profile

    def recommend(self, user_id, submission_key, request_text,refinement=None):
        if (not isinstance(user_id,str) or not user_id.strip() or not isinstance(submission_key,str)
                or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}",submission_key) is None
                or not isinstance(request_text,str) or not request_text.strip() or len(request_text)>500):
            return {"status":"InvalidInput","complete":False}
        stage, timings = "lookup", {}
        try:
            try:action=RefinementAction.parse(refinement) if refinement is not None else None
            except ValueError:return {'status':'InvalidInput','complete':False}
            start = perf_counter()
            prior = (self.repository.find_assistant_submission(user_id,submission_key,request_text,action)
                if action is not None else self.repository.find_assistant_submission(user_id,submission_key,request_text))
            timings["lookup_seconds"] = perf_counter()-start
            if prior is not None:
                return self._success(prior,True,timings)
            if action is not None and self.refinement_profile!='optional_refinement_v1':
                raise RefinementError('RefinementUnavailable','feature_disabled')
            if self.refinement_profile!='disabled' and self.refinement_profile!='optional_refinement_v1':
                raise ValueError('Invalid refinement profile.')
            if self.refinement_profile!='disabled' and (action is None or action.kind=='initial') and submission_key.startswith('refine:v1:'):
                raise RefinementError('RefinementUnavailable','reserved_step_key')
            try:
                selection = AssistantScoringSelection(self.scoring_profile,context_ranking=self.context_ranking_profile)
                execution = AssistantExecutionSelection(self.execution_engine)
            except (ValueError,TypeError) as error:
                log_failure("assistant", "configuration", "ProfileUnavailable", error)
                return {"status":"ProfileUnavailable","complete":False}
            stage = "interpretation"
            start = perf_counter()
            plan=None;draft=None;active_engine=self.engine;raw_preferences=None
            if action is not None and action.kind=='alternative':
                try:plan,request=self.repository.refinement_continuation(user_id,action.parent_recommendation_id,request_text,submission_key)
                except LookupError:return {'status':'RefinementNotFound','complete':False}
                interpreted=None
            else:interpreted = self.interpreter.interpret(request_text)
            timings["nlp_seconds"] = perf_counter()-start
            if interpreted is not None and interpreted.status != "Supported":
                if interpreted.status in ("ProcessingFailure", "PersistenceFailure", "ProfileUnavailable", "Interrupted", "ProcessingError", "InvalidScoringInput", "InvalidPreferenceData"):
                    log_failure("assistant", stage, interpreted.status, reason="controlled_failure")
                return {"status":interpreted.status,"reason":interpreted.reason,"context_reason":interpreted.reason,"complete":False}
            if interpreted is not None:request = interpreted.structured_request
            if self.refinement_profile=='optional_refinement_v1':
                from app.application.recommendation.refinement_policy import RefinementPolicy
                policy=RefinementPolicy.load()
                ordinary=isinstance(request,GeneralContextRequest) and request.context.bundle_id=='context_18_v1' and request.context.situation.value in policy.ordinary_situations
                if action is not None and not ordinary:raise RefinementError('RefinementUnavailable','relative_ordinary_required')
                if ordinary:
                    from app.application.recommendation.context_relevance_policy import ContextRelevancePolicy
                    relative_policy=ContextRelevancePolicy.load(bundle_id='context_18_v1')
                    resolution=relative_policy.resolve(request)
                    if action is not None and resolution.objective is None:raise RefinementError('RefinementUnavailable','relative_objective_required')
                    if resolution.objective is not None:
                        from dataclasses import replace
                        from app.application.recommendation.refinement_verifier import snapshot_digest,preference_digest,request_digest,scope_digest
                        from app.application.recommendation.context_bundle import ContextBundle
                        from app.application.recommendation.rule_based_compatibility_policy import RuleBasedCompatibilityPolicy
                        from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
                        from app.application.recommendation.structural_policy import StructuralPolicy
                        from app.application.recommendation.compact_exhaustive_scorer import SnapshotQuery
                        from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
                        from app.application.recommendation.refinement_selector import check_category_conflicts
                        exclusions=plan.exclusions if plan is not None else action.excluded_categories if action else ()
                        check_category_conflicts(request,exclusions,self.interpreter.vocabulary)
                        garments=tuple(self.engine.structural_engine.retrieval.query.get_confirmed_available_garments(user_id))
                        raw_preferences=tuple(self.preference_query.get_active_preferences(user_id))
                        gh,ph,rh=snapshot_digest(garments),preference_digest(user_id,raw_preferences),request_digest(request_text,request,exclusions)
                        contracts=dict(bundle=ContextBundle.load('context_18_v1').manifest_sha256,
                            policy=relative_policy.policy_sha256,objectives=relative_policy.catalogue_sha256,
                            evaluator=asdict(self.engine.evaluator_factory().specification),
                            compatibility=RuleBasedCompatibilityPolicy.load().hash,
                            decision=CompatibilityDecisionPolicy.load().hash,structure=StructuralPolicy.load().version,
                            refinement=policy.sha256,execution=execution.refinement_implementation)
                        scope=scope_digest(rh,gh,ph,contracts)
                        if plan is not None and plan.compatibility_scope_sha256!=scope:raise RefinementError('RefinementScopeChanged','ranking_scope_changed')
                        plan=plan or RefinementPlan(exclusions=exclusions,compatibility_scope_sha256=scope)
                        draft=RefinementDraft(plan,action,gh,ph,rh)
                        active_engine=RequestCandidateEngine(SnapshotQuery(user_id,garments),evaluator_factory=self.engine.evaluator_factory)
            class PreparedPreferences:
                def get_active_preferences(_,owner):
                    if owner!=user_id:raise ValueError('Preference owner mismatch.')
                    return raw_preferences
            captured = CapturedPreferenceQuery(PreparedPreferences() if raw_preferences is not None else self.preference_query)
            candidates = CapturedCandidateEngine(active_engine)
            stage = "ranking"
            start = perf_counter()
            scorer = execution.scorer(selection,candidates,captured,self.scorer_factory)
            # Implicit initial requests retain legitimate disclosed fallback. Only
            # a successful point result is promoted to a root afterward.
            rank_plan=plan if action is not None else None
            ranked = selection.rank(scorer,user_id,request,rank_plan)
            timings["ranking_seconds"] = perf_counter()-start
            if ranked.status != "Selected":
                if ranked.status in ("ProcessingFailure", "PersistenceFailure", "ProfileUnavailable", "Interrupted", "ProcessingError", "InvalidScoringInput", "InvalidPreferenceData"):
                    log_failure("assistant", stage, ranked.status, reason="controlled_failure")
                result = {"status":ranked.status,"complete":ranked.complete,"diagnostics":ranked.diagnostics,"timings":timings}
                if action is not None:result['refinement_summary']=json.loads(ranked.refinement_summary) if ranked.refinement_summary else {'reason':ranked.status,'excluded_categories':list(plan.exclusions) if plan else []}
                if isinstance(request, GeneralContextRequest):
                    explanation=GeneralContextEvaluator() if request.context.bundle_id=='legacy_8_v1' else self.engine.evaluator_factory()
                    summary = explanation.summary(request)
                    result["context_summary"] = summary
                    result["context_reason"] = summary["reason"] if ranked.status == "PolicyUnavailable" else "required_attribute_unknown" if ranked.status == "InsufficientEvidence" else "requirement_failed" if ranked.status == "NoMatchingCandidates" else "wardrobe_incomplete"
                if isinstance(request, ContextualOutfitRequest):
                    result['contextual_message'] = ('This wedding role or dress code is not supported. Start a new chat with a supported guest request.'
                        if ranked.status == 'PolicyUnavailable' else
                        'No outfit passed the wedding rules. Review the garment style evidence or your explicit suitability choices before starting a new chat.'
                        if ranked.status in ('InsufficientEvidence', 'NoMatchingCandidates') else
                        'No complete eligible outfit is available for this wedding request. Check your wardrobe before starting a new chat.') if ranked.status in ('PolicyUnavailable', 'InsufficientEvidence', 'NoMatchingCandidates', 'NoEligibleGarments', 'InsufficientStructure', 'NoStructuralCandidates') else None
                return result
            if not ranked.complete or ranked.winner is None or ranked.scored_count<1 or captured.rows is None:
                log_failure("assistant", "validation", "ProcessingFailure", reason="incomplete_selection")
                return {"status":"ProcessingFailure","complete":False}
            score = ranked.winner.score
            if draft is not None and action is None and score.profile_name!='context_relevance_decision_v1':draft=None;plan=None
            try:
                selection.validate(score)
            except (ValueError,TypeError,AttributeError,KeyError) as error:
                log_failure("assistant", "validation", "ProfileUnavailable", error)
                return {"status":"ProfileUnavailable","complete":False}
            preference_snapshot = [asdict(row) for row in captured.rows]
            context = execution.context(scorer,candidates,active_engine,user_id,request,ranked)
            preference_json = json.dumps(preference_snapshot,sort_keys=True,separators=(",",":"))
            provenance = {"assistant_policy":"phase5c-1.0.0","nlp_vocabulary":self.interpreter.vocabulary.version,
                "scoring_profile":score.profile_name,"scoring_policy":score.policy_version,
                "preference_consistency":"captured_at_ranking_read_not_commit_time",
                "preference_snapshot":preference_snapshot,"preference_snapshot_sha256":hashlib.sha256(preference_json.encode()).hexdigest(),
                "scored_count":ranked.scored_count,"diagnostics":ranked.diagnostics,
                "request_evaluator":context.evaluator,
                "suitability_policy":context.suitability_policy,
                "structure_policy":context.structure_policy,
                "mandatory_evaluation":asdict(ranked.winner.verified.evaluated.evaluation),
                "validity":"approved_minimum_mandatory_conditions_not_aesthetic_validation"}
            provenance["assistant_scoring_selection"] = {"version":selection.version,"profile":selection.profile,"hash":selection.hash}
            if ranked.ranking_evidence is not None:
                from app.domain.value_objects.context_relevance import read_proof
                from app.application.recommendation.context_relevance_verifier import validate_evidence
                evidence=read_proof(ranked.ranking_evidence)
                if draft is not None and evidence['version']=='context-relevance-evidence-1.1.0':
                    evidence.update(version='context-relevance-evidence-1.2.0',explanation_version='context-relevance-explanation-1.2.0',selection_scope_sha256=plan.selection_scope_sha256)
                    evidence['coverage'].update(already_seen=0,below_floor_points=0,unresolved_below_floor=0)
                validate_evidence(evidence,score,ranked.winner.verified.candidate,request)
                provenance['context_relevance']=evidence
            elif score.profile_name=='context_relevance_decision_v1':
                raise ValueError('Relative score requires immutable ranking evidence.')
            if isinstance(request, GeneralContextRequest):
                explanation_evaluator = GeneralContextEvaluator() if request.context.bundle_id=='legacy_8_v1' else self.engine.evaluator_factory()
                if explanation_evaluator.specification.registry_sha256 != context.context_bundle:
                    raise ValueError("Selected context and explanation bundle differ.")
                provenance["general_context"] = explanation_evaluator.explain(ranked.winner.verified.candidate, request)
                provenance["general_context_nlp_sha256"] = self.interpreter.hash
                provenance["context_bundle"] = context.context_bundle
            elif isinstance(request, ContextualOutfitRequest):
                provenance['contextual_wedding'] = ContextualSuitabilityEvaluator().explain(ranked.winner.verified.candidate, request)
                provenance['contextual_nlp_sha256'] = self.interpreter.hash
            elif hasattr(self.interpreter, 'legacy'):
                provenance['nlp_vocabulary'] = self.interpreter.legacy.vocabulary.version
                # Non-wedding evaluation delegates to the original policy. Keep
                # that effective evaluator explicit, and disclose the adapter.
                provenance['contextual_adapter'] = {'evaluator': context.evaluator, 'delegated': True}
                if context.evaluator in ('ContextualSuitabilityEvaluator', 'GeneralContextEvaluator'):
                    legacy = ContextualSuitabilityEvaluator().legacy
                    provenance['request_evaluator'] = type(legacy).__name__
                    provenance['suitability_policy'] = legacy.policy.version
            if selection.profile == DECISION:
                provenance.update(compatibility_decision_policy=score.compatibility.decision.policy_version,
                                  compatibility_decision_hash=score.compatibility.decision.policy_hash,
                                  scorer_implementation="prepared-decision-1.0.0")
            if execution.engine == COMPACT:
                provenance['assistant_execution_selection'] = execution.provenance
                if selection.profile == DECISION:
                    provenance['scorer_implementation'] = scorer.implementation
            if 'context_relevance' in provenance:
                from app.application.recommendation.refinement_verifier import bounded_provenance
                bounded_provenance(provenance,draft=draft is not None)
            if draft is not None:
                provenance['preference_consistency']='full_strict_and_active_preferences_revalidated_under_write_lock'
                provenance['scorer_implementation']=execution.refinement_implementation
                if ranked.refinement_summary:provenance['refinement_summary']=json.loads(ranked.refinement_summary)
            command = RecommendationWrite(user_id,"assistant",submission_key,json.dumps(asdict(request)),ranked.winner.verified.candidate,
                                          json.dumps(provenance),request_text,score,draft)
            stage = "persistence"
            start = perf_counter()
            result,replayed = self.repository.persist_assistant(command)
            timings["persistence_seconds"] = perf_counter()-start
            return self._success(result,replayed,timings)
        except RefinementError as error:
            return {'status':error.status,'complete':False,'refinement_summary':{'reason':error.reason}}
        except RelativeEncodingLimit:
            return {'status':'ProfileUnavailable','complete':False,'ranking_reason':'exact_encoding_budget_exceeded'}
        except PersistenceConflict:
            return {"status":"IdempotencyConflict","complete":False}
        except WardrobeChanged:
            return {"status":"WardrobeChanged","complete":False}
        except (KeyboardInterrupt,GeneratorExit) as error:
            log_failure("assistant", stage, "Interrupted", error)
            return {"status":"Interrupted","complete":False}
        except Exception as error:
            log_failure("assistant", stage, "PersistenceFailure" if stage in ("lookup","persistence") else "ProcessingFailure", error)
            return {"status":"PersistenceFailure" if stage in ("lookup","persistence") else "ProcessingFailure","complete":False}

    @staticmethod
    def _success(record,replayed,timings):
        # Projection is read-only and uses the stored profile, never current config.
        record = with_scoring_display(record)
        # Retain legacy success fields at top level for existing consumers.
        return {**record,"status":"Selected","recommendation_status":record["status"],"complete":True,
                "replayed":replayed,"timings":timings,"recommendation":record}
