from fastapi import HTTPException
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
from app.domain.value_objects.attribute_conditions import AttributeRequestError


class CapturedPreferenceQuery:
    """One immutable, user-scoped read snapshot per ranking interaction."""
    def __init__(self, query,wearer=None):
        self.query, self.rows, self.wearer = query, None, wearer

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
    def __init__(self, interpreter, engine, preference_query, repository, scorer_factory=RecommendationScorer, *, scoring_profile=DEFERRED, execution_engine=DEFAULT_ENGINE,context_ranking_profile='disabled',refinement_profile='disabled',attribute_pipeline=None,preference_policy=None,attribute_preference_query=None,compatibility_policy=None,garment_refinement_profile='disabled'):
        self.interpreter, self.engine = interpreter, engine
        self.preference_query, self.repository = preference_query, repository
        self.scorer_factory = scorer_factory
        self.scoring_profile = scoring_profile
        self.execution_engine = execution_engine
        self.context_ranking_profile=context_ranking_profile
        self.refinement_profile=refinement_profile
        self.attribute_pipeline=attribute_pipeline
        self.preference_policy,self.attribute_preference_query=preference_policy,attribute_preference_query
        self.compatibility_policy=compatibility_policy
        from app.domain.value_objects.garment_only_refinement import PROFILE as GP
        if garment_refinement_profile not in ('disabled',GP):raise ValueError('Unknown garment continuation profile.')
        if garment_refinement_profile==GP:
            from app.application.recommendation.garment_only_refinement_policy import load
            load()
            if attribute_pipeline is None or scoring_profile!=DECISION:raise ValueError('Garment continuation requires B1 and decision scoring.')
        self.garment_refinement_profile=garment_refinement_profile

    def recommend(self, user_id, submission_key, request_text,refinement=None,*,wearer=None,attribute_conditions=None,preference_profile=None,compatibility_profile=None):
        if (not isinstance(user_id,str) or not user_id.strip() or not isinstance(submission_key,str)
                or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}",submission_key) is None
                or not isinstance(request_text,str) or not request_text.strip() or len(request_text)>500):
            return {"status":"InvalidInput","complete":False}
        stage, timings = "lookup", {}
        try:
            try:action=RefinementAction.parse(refinement) if refinement is not None else None
            except ValueError:return {'status':'InvalidInput','complete':False}
            attribute_options={}
            if attribute_conditions is not None:
                from app.domain.value_objects.attribute_conditions import AttributeConditions
                attribute_conditions=AttributeConditions.from_dict(attribute_conditions).to_dict()
                attribute_options={'attribute_conditions':attribute_conditions}
            if preference_profile is not None:attribute_options['preference_profile']=preference_profile
            if compatibility_profile is not None:attribute_options['compatibility_profile']=compatibility_profile
            start = perf_counter()
            if wearer is not None:
                prior=self.repository.find_assistant_submission(user_id,submission_key,request_text,action,wearer_profile_id=wearer.profile_id,**attribute_options)
            else:
                prior = (self.repository.find_assistant_submission(user_id,submission_key,request_text,action,**attribute_options)
                    if action is not None else self.repository.find_assistant_submission(user_id,submission_key,request_text,**attribute_options))
            timings["lookup_seconds"] = perf_counter()-start
            if prior is not None:
                return self._success(prior,True,timings)
            if compatibility_profile is not None:
                from app.domain.value_objects.palette_compatibility import PROFILE as C2,PaletteError
                if compatibility_profile!=C2 or self.compatibility_policy is None or wearer is None or self.attribute_pipeline is None or self.scoring_profile!=DECISION:
                    raise PaletteError('CompatibilityUnavailable','Explicit C2 requires its enabled dependency bundle.')
            if preference_profile is not None:
                from app.domain.value_objects.attribute_preferences import PROFILE,PreferenceError
                if preference_profile!=PROFILE or self.preference_policy is None or self.attribute_preference_query is None or wearer is None or self.attribute_pipeline is None:
                    raise PreferenceError('PreferenceUnavailable','Explicit P2 requests require its enabled dependency bundle.')
            if attribute_conditions is not None and self.attribute_pipeline is None:
                raise AttributeRequestError('AttributeUnavailable','attribute_profile_disabled')
            if action is not None and self.refinement_profile!='optional_refinement_v1' and self.garment_refinement_profile=='disabled':
                raise RefinementError('RefinementUnavailable','feature_disabled')
            if self.refinement_profile!='disabled' and self.refinement_profile!='optional_refinement_v1':
                raise ValueError('Invalid refinement profile.')
            if self.refinement_profile!='disabled' and (action is None or action.kind=='initial') and submission_key.startswith('refine:v1:'):
                raise RefinementError('RefinementUnavailable','reserved_step_key')
            try:
                selection = AssistantScoringSelection(self.scoring_profile,context_ranking=self.context_ranking_profile,preference_profile=preference_profile,compatibility_profile=compatibility_profile)
                execution = AssistantExecutionSelection(self.execution_engine)
            except (ValueError,TypeError) as error:
                log_failure("assistant", "configuration", "ProfileUnavailable", error)
                return {"status":"ProfileUnavailable","complete":False}
            from app.application.wardrobe import wearer_category_service as categories
            eligibility_scope=categories.capture(user_id,wearer.profile_id if wearer else None)
            source_query=eligibility_scope or self.engine.structural_engine.retrieval.query if hasattr(self.engine,'structural_engine') else None
            if action is not None and action.kind=='alternative':categories.check_parent(self.repository,user_id,action.parent_recommendation_id,eligibility_scope)
            from app.application.recommendation.garment_only_refinement_selection import is_garment
            if (action is None or action.kind=='initial') and submission_key.startswith('garment-refine:v1:'):raise RefinementError('RefinementUnavailable','reserved_step_key')
            stage = "interpretation"
            start = perf_counter()
            plan=None;draft=None;active_engine=self.engine;raw_preferences=None;garments=None
            preference_context=None;preference_snapshot_capture=None;preference_base_scope=None;compatibility_context=None
            attribute_intent=None;attribute_collection=None;attribute_context=None;attribute_verifier=None;attribute_base_scope=None
            if self.attribute_pipeline is None and hasattr(self.engine,'structural_engine'):
                garments=tuple(source_query.get_confirmed_available_garments(user_id))
                if len({g.garment_id for g in garments})>100:
                    return {'status':'WardrobeCapacityExceeded','complete':False}
                from app.application.recommendation.compact_exhaustive_scorer import SnapshotQuery
                from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
                active_engine=self._prepared_engine(garments,user_id)
            if action is not None and action.kind=='alternative':
                try:plan,request=self.repository.refinement_continuation(user_id,action.parent_recommendation_id,request_text,submission_key,wearer=wearer,**attribute_options)
                except LookupError:return {'status':'RefinementNotFound','complete':False}
                if is_garment(plan) and self.garment_refinement_profile=='disabled':raise RefinementError('RefinementUnavailable','garment_feature_disabled')
                attribute_intent=getattr(plan,'attribute_intent',None)
                if attribute_intent is not None and self.attribute_pipeline is None:
                    raise AttributeRequestError('AttributeUnavailable','attribute_profile_disabled')
                interpreted=None
            elif self.attribute_pipeline is not None:
                request,attribute_intent=self.attribute_pipeline.interpret(request_text,attribute_conditions)
                interpreted=None
            else:interpreted = self.interpreter.interpret(request_text)
            timings["nlp_seconds"] = perf_counter()-start
            if interpreted is not None and interpreted.status != "Supported":
                if interpreted.status in ("ProcessingFailure", "PersistenceFailure", "ProfileUnavailable", "Interrupted", "ProcessingError", "InvalidScoringInput", "InvalidPreferenceData"):
                    log_failure("assistant", stage, interpreted.status, reason="controlled_failure")
                return {"status":interpreted.status,"reason":interpreted.reason,"context_reason":interpreted.reason,"complete":False}
            if interpreted is not None:request = interpreted.structured_request
            categories.check_request(request,attribute_intent,eligibility_scope)
            if attribute_intent is not None or preference_profile is not None or compatibility_profile is not None:
                if wearer is None or not hasattr(self.engine,'structural_engine'):
                    raise AttributeRequestError('AttributeUnavailable','captured_wearer_and_strict_engine_required')
                captured_at=perf_counter()
                query=source_query
                try:attribute_collection=tuple(query.get_confirmed_garment_descriptions(user_id,self.attribute_pipeline.description_policy))
                except ValueError as exc:
                    if str(exc)=='DescriptionCapacityExceeded':return {'status':'WardrobeCapacityExceeded','complete':False}
                    raise
                garments=tuple(item.snapshot for item in attribute_collection)
                if attribute_intent is not None:attribute_context,attribute_verifier=self.attribute_pipeline.prepare(attribute_intent,attribute_collection,eligibility_scope.account_subtypes if eligibility_scope else ())
                timings['attribute_acquisition_preparation_seconds']=perf_counter()-captured_at
                active_engine=self._prepared_engine(garments,user_id,attribute_context=attribute_context,attribute_verifier=attribute_verifier)
            elif garments is None and hasattr(self.engine,'structural_engine'):
                garments=tuple(source_query.get_confirmed_available_garments(user_id))
                if len({g.garment_id for g in garments})>100:return {'status':'WardrobeCapacityExceeded','complete':False}
                active_engine=self._prepared_engine(garments,user_id)
            if compatibility_profile is not None:
                from app.application.recommendation.palette_compatibility_preparation import PreparedPaletteCompatibility
                compatibility_context=PreparedPaletteCompatibility(user_id,attribute_collection,self.compatibility_policy)
            if preference_profile is not None:
                from app.application.recommendation.attribute_preference_preparation import PreparedAttributePreferences
                preference_snapshot_capture=self.attribute_preference_query.capture(user_id,wearer)
                raw_preferences=preference_snapshot_capture.legacy_rows()
                preference_context=PreparedAttributePreferences(preference_snapshot_capture,attribute_collection,
                    conditions=attribute_intent.conditions if attribute_intent is not None else None,request=request,original_text=request_text)
            if self.refinement_profile=='optional_refinement_v1'  or attribute_intent is not None and self.context_ranking_profile!='disabled':
                from app.application.recommendation.refinement_policy import RefinementPolicy
                policy=RefinementPolicy.load()
                ordinary=isinstance(request,GeneralContextRequest) and request.context.bundle_id=='context_18_v1' and request.context.situation.value in policy.ordinary_situations
                if action is not None and not ordinary and not is_garment(plan):raise RefinementError('RefinementUnavailable','relative_ordinary_required')
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
                        if garments is None:garments=tuple(source_query.get_confirmed_available_garments(user_id))
                        if raw_preferences is None:raw_preferences=tuple(self.preference_query.get_active_preferences(user_id,wearer) if wearer is not None else self.preference_query.get_active_preferences(user_id))
                        gh,ph,rh=snapshot_digest(garments),preference_digest(user_id,raw_preferences),request_digest(request_text,request,exclusions)
                        contracts=dict(bundle=ContextBundle.load('context_18_v1').manifest_sha256,
                            policy=relative_policy.policy_sha256,objectives=relative_policy.catalogue_sha256,
                            evaluator=asdict(self.engine.evaluator_factory().specification),
                            compatibility=RuleBasedCompatibilityPolicy.load().hash,
                            decision=CompatibilityDecisionPolicy.load().hash,structure=StructuralPolicy.load().version,
                            refinement=policy.sha256,execution=execution.refinement_implementation)
                        if compatibility_context is not None:
                            contracts.update(palette_policy=compatibility_context.policy.hash,palette_descriptions=compatibility_context.collection_sha256)
                        scope=scope_digest(rh,gh,ph,contracts)
                        if plan is not None and plan.compatibility_scope_sha256!=scope:raise RefinementError('RefinementScopeChanged','ranking_scope_changed')
                        plan=plan or RefinementPlan(exclusions=exclusions,compatibility_scope_sha256=scope,wearer_profile_id=wearer.profile_id if wearer else None)
                        if compatibility_context is not None:
                            if plan.ordinal and (plan.compatibility_profile!=compatibility_profile or plan.palette_collection_sha256!=compatibility_context.collection_sha256):raise RefinementError('RefinementScopeChanged','palette_sources_or_mode_changed')
                            plan=replace(plan,compatibility_profile=compatibility_profile,palette_collection_sha256=compatibility_context.collection_sha256)
                        if attribute_intent is not None:
                            from app.domain.value_objects.attribute_selection_evidence import description_digest,subtype_digest,scope_digest as attribute_scope_digest
                            description_hash=description_digest(attribute_collection)
                            attribute_scope=attribute_scope_digest(user_id,wearer.profile_id,scope,attribute_intent,description_hash,subtype_digest(eligibility_scope.account_subtypes) if eligibility_scope and attribute_intent.to_dict()['version']=='assistant-attribute-intent-2.0.0' else None)
                            if plan.ordinal and (plan.description_collection_sha256!=description_hash or plan.attribute_scope_sha256!=attribute_scope):
                                raise RefinementError('RefinementScopeChanged','attribute_sources_or_intent_changed')
                            plan=replace(plan,attribute_intent=attribute_intent,description_collection_sha256=description_hash,attribute_scope_sha256=attribute_scope)
                            attribute_base_scope=scope
                        if preference_context is not None:
                            from app.domain.value_objects.attribute_preferences import digest as p2_digest
                            from app.domain.value_objects.attribute_preference_evidence import preference_scope
                            from app.domain.value_objects.attribute_selection_evidence import description_digest
                            dh=description_digest(attribute_collection);p2hash=p2_digest(preference_snapshot_capture.to_dict())
                            p2scope=preference_scope(preference_snapshot_capture,scope,gh,dh,rh)
                            if plan.ordinal and (plan.preference_profile!=preference_profile or plan.attribute_preference_sha256!=p2hash or plan.attribute_preference_scope_sha256!=p2scope):
                                raise RefinementError('RefinementScopeChanged','saved_preferences_changed_start_fresh')
                            plan=replace(plan,preference_profile=preference_profile,attribute_preference_sha256=p2hash,attribute_preference_scope_sha256=p2scope)
                            preference_base_scope=scope
                        draft=RefinementDraft(plan,action,gh,ph,rh)
                        active_engine=self._prepared_engine(garments,user_id,**({'attribute_context':attribute_context,'attribute_verifier':attribute_verifier} if attribute_context is not None else {}))
            from app.application.recommendation.garment_only_refinement_policy import applies as garment_applies,prepare as prepare_garment
            if self.garment_refinement_profile!='disabled' and garment_applies(request,attribute_intent):
                if raw_preferences is None:raw_preferences=tuple(self.preference_query.get_active_preferences(user_id,wearer))
                plan,draft,garment_scope=prepare_garment(plan,action,user_id,wearer,request_text,request,attribute_intent,garments,raw_preferences,attribute_collection,selection,execution,self.engine.evaluator_factory(),preference_snapshot_capture,compatibility_context,eligibility_scope)
                attribute_base_scope=preference_base_scope=garment_scope
            if action is not None and self.refinement_profile!='optional_refinement_v1' and not is_garment(plan):raise RefinementError('RefinementUnavailable','ordinary_feature_disabled')
            source_preferences=self.preference_query
            if wearer is not None:
                class ScopedPreferences:
                    def get_active_preferences(_,owner):
                        return self.preference_query.get_active_preferences(owner,wearer)
                source_preferences=ScopedPreferences()
            class PreparedPreferences:
                def get_active_preferences(_,owner):
                    if owner!=user_id:raise ValueError('Preference owner mismatch.')
                    return raw_preferences
            captured = CapturedPreferenceQuery(PreparedPreferences() if raw_preferences is not None else source_preferences,wearer)
            candidates = CapturedCandidateEngine(active_engine)
            if attribute_context is not None:active_engine.attribute_seen=plan.seen if plan is not None else ()
            if attribute_context is not None and plan is not None and plan.ordinal and execution.engine==REFERENCE and not is_garment(plan):
                from app.application.recommendation.attribute_condition_evaluator import AttributeRefinementCounterGuard
                from app.application.recommendation.context_relevance_scorer import PreparedRelativeFacts
                from app.application.recommendation.preference_normalizer import PreferenceNormalizer
                from types import MappingProxyType
                active_engine.attribute_counter_guard=AttributeRefinementCounterGuard(MappingProxyType({g.garment_id:i for i,g in enumerate(garments)}),
                    PreparedRelativeFacts(garments,request,PreferenceNormalizer().normalize(user_id,raw_preferences)),plan.root_R,frozenset(plan.seen))
            stage = "ranking"
            start = perf_counter()
            scorer = execution.scorer(selection,candidates,captured,self.scorer_factory,**({'preference_context':preference_context} if preference_context is not None else {}),**({'compatibility_context':compatibility_context} if compatibility_context is not None else {}))
            # Implicit initial requests retain legitimate disclosed fallback. Only
            # a successful point result is promoted to a root afterward.
            rank_plan=plan if action is not None or is_garment(plan) else None
            ranked = selection.rank(scorer,user_id,request,rank_plan)
            timings["ranking_seconds"] = perf_counter()-start
            if ranked.status != "Selected":
                if ranked.status in ("ProcessingFailure", "PersistenceFailure", "ProfileUnavailable", "Interrupted", "ProcessingError", "InvalidScoringInput", "InvalidPreferenceData"):
                    log_failure("assistant", stage, ranked.status, reason="controlled_failure")
                failed_ledger=getattr(getattr(scorer,'kernel',None),'attribute_ledger',None) or getattr(candidates.session,'attribute_ledger',None)
                rank_status='RefinementInsufficientEvidence' if ranked.status=='RefinementExhausted' and failed_ledger is not None and failed_ledger.unseen_unknown else ranked.status
                if is_garment(plan) and rank_status in ('GarmentRefinementExhausted','RefinementExhausted','RefinementInsufficientEvidence'):
                    rank_status='GarmentRefinementInsufficientEvidence' if failed_ledger is not None and failed_ledger.unseen_unknown or rank_status=='RefinementInsufficientEvidence' else 'GarmentRefinementExhausted'
                    if not plan.ordinal:rank_status='InsufficientEvidence' if rank_status=='GarmentRefinementInsufficientEvidence' else 'NoMatchingCandidates'
                from app.application.recommendation.subtype_remaining_evidence import could_matter
                subtype_unresolved=could_matter(eligibility_scope,user_id,request,attribute_intent,plan,self.engine.evaluator_factory,raw_preferences or ())
                if subtype_unresolved:
                    rank_status='GarmentRefinementInsufficientEvidence' if is_garment(plan) and plan.ordinal else 'RefinementInsufficientEvidence' if plan is not None and plan.ordinal else 'InsufficientEvidence'
                result = {"status":rank_status,"complete":False if subtype_unresolved else ranked.complete,"diagnostics":ranked.diagnostics,"timings":timings}
                if subtype_unresolved:result.update(reason='wearer_subtype_unresolved',message='Some garment types are not confirmed for this wearer. Review their garment type before trying again.')
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
                if failed_ledger is not None:
                    if failed_ledger.unseen_unknown:result['context_reason']='required_garment_description_unknown'
                    elif failed_ledger.counts['attribute_failed']:result['context_reason']='garment_description_mismatch'
                    if action is not None and rank_status!=ranked.status and isinstance(result.get('refinement_summary'),dict):result['refinement_summary']['reason']=rank_status
                return result
            if not ranked.complete or ranked.winner is None or ranked.scored_count<1 or captured.rows is None:
                log_failure("assistant", "validation", "ProcessingFailure", reason="incomplete_selection")
                return {"status":"ProcessingFailure","complete":False}
            score = ranked.winner.score
            if draft is not None and not is_garment(plan) and action is None and score.request_match.summary.name!='relative_style_alignment':draft=None;plan=None
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
            from app.application.nlp.garment_wording_guidance import capture as wording_capture
            wording=wording_capture(request_text,attribute_intent)
            if wording is not None:provenance['garment_wording']=wording
            attribute_write=None
            if attribute_intent is not None:
                from app.application.recommendation.refinement_verifier import snapshot_digest,preference_digest,request_digest,scope_digest
                from app.application.recommendation.attribute_selection_verifier import build_selection
                from app.domain.value_objects.attribute_selection_evidence import AttributeWriteDraft
                if attribute_base_scope is None:
                    attribute_base_scope=scope_digest(request_digest(request_text,request,()),snapshot_digest(garments),preference_digest(user_id,captured.rows),
                        {'scoring':selection.hash,'execution':execution.provenance,'evaluator':context.evaluator,'structure':context.structure_policy,'context_bundle':context.context_bundle})
                kernel=getattr(scorer,'kernel',None)
                ledger=getattr(kernel,'attribute_ledger',None) if kernel is not None else getattr(candidates.session,'attribute_ledger',None)
                if ledger is None:raise ValueError('Missing completed attribute admission ledger.')
                evidence=build_selection(attribute_intent,attribute_collection,attribute_context,attribute_verifier,ranked.winner.verified.candidate,
                    ledger.snapshot(),attribute_base_scope,wearer,eligibility_scope.account_subtypes if eligibility_scope else ())
                attribute_write=AttributeWriteDraft(evidence,attribute_base_scope)
            preference_write=None
            if preference_context is not None:
                from app.application.recommendation.refinement_verifier import snapshot_digest,preference_digest,request_digest,scope_digest
                from app.application.recommendation.attribute_preference_verifier import build as build_preference
                from app.domain.value_objects.attribute_selection_evidence import description_digest
                exclusions=plan.exclusions if plan is not None else action.excluded_categories if action else ()
                gh=snapshot_digest(garments);rh=request_digest(request_text,request,exclusions)
                if preference_base_scope is None:
                    preference_base_scope=scope_digest(rh,gh,preference_digest(user_id,captured.rows),
                        {'scoring':selection.hash,'execution':execution.provenance,'evaluator':context.evaluator,'structure':context.structure_policy,'context_bundle':context.context_bundle})
                preference_write=build_preference(preference_context,ranked.winner.verified,score,preference_base_scope,gh,description_digest(attribute_collection),rh,exclusions=exclusions)
            if ranked.ranking_evidence is not None:
                from app.domain.value_objects.context_relevance import read_proof
                from app.application.recommendation.context_relevance_verifier import validate_evidence
                evidence=read_proof(ranked.ranking_evidence)
                if compatibility_context is not None:
                    from app.application.recommendation.palette_compatibility_verifier import base_relative
                    evidence=base_relative(evidence)
                if draft is not None and evidence['version']=='context-relevance-evidence-2.0.0' and 'selection_scope_sha256' not in evidence:
                    evidence['selection_scope_sha256']=plan.selection_scope_sha256
                    evidence['coverage'].update(already_seen=0,below_floor_points=0,unresolved_below_floor=0)
                if draft is not None and evidence['version']=='context-relevance-evidence-1.1.0':
                    evidence.update(version='context-relevance-evidence-1.2.0',explanation_version='context-relevance-explanation-1.2.0',selection_scope_sha256=plan.selection_scope_sha256)
                    evidence['coverage'].update(already_seen=0,below_floor_points=0,unresolved_below_floor=0)
                if attribute_write is not None:
                    attribute_evidence=attribute_write.evidence.to_dict()
                    evidence.update(version='context-relevance-evidence-2.0.0' if preference_write else 'context-relevance-evidence-1.3.0',explanation_version='context-relevance-explanation-2.0.0' if preference_write else 'context-relevance-explanation-1.3.0',
                        attribute_scope_sha256=attribute_evidence['attribute_scope_sha256'],attribute_selection_sha256=attribute_write.evidence.sha256,
                        selection_scope_sha256=evidence.get('selection_scope_sha256',attribute_evidence['attribute_scope_sha256']))
                    for name in ('already_seen','below_floor_points','unresolved_below_floor'):evidence['coverage'].setdefault(name,0)
                if compatibility_context is not None:
                    from app.application.recommendation.palette_compatibility_selection import wrap_proof
                    evidence=wrap_proof(evidence,score)
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
            if 'context_relevance' in provenance and attribute_write is None and preference_write is None and compatibility_context is None:
                from app.application.recommendation.refinement_verifier import bounded_provenance
                bounded_provenance(provenance,draft=draft is not None)
            if draft is not None:
                provenance['preference_consistency']='full_strict_and_active_preferences_revalidated_under_write_lock'
                provenance['scorer_implementation']='garment-only-refinement-1.0.0' if is_garment(plan) else execution.refinement_implementation
                if ranked.refinement_summary:provenance['refinement_summary']=json.loads(ranked.refinement_summary)
            captured_gh=captured_ph=None
            if wearer is not None and garments is not None:
                from app.application.recommendation.refinement_verifier import snapshot_digest,preference_digest
                captured_gh=snapshot_digest(garments);captured_ph=preference_digest(user_id,captured.rows)
            compatibility_write=None
            if compatibility_context is not None:
                from app.application.recommendation.palette_compatibility_codec import build_archive
                compatibility_write=build_archive(compatibility_context,ranked.winner.verified,score,wearer,request_text,request,plan.exclusions if plan else action.excluded_categories if action else ())
            command = RecommendationWrite(user_id,"assistant",submission_key,json.dumps(asdict(request)),ranked.winner.verified.candidate,
                                          json.dumps(provenance),request_text,score,draft,wearer,captured_gh,captured_ph,attribute_write,preference_write,compatibility_write,eligibility_scope.eligibility if eligibility_scope else None)
            stage = "persistence"
            start = perf_counter()
            result,replayed = self.repository.persist_assistant(command)
            timings["persistence_seconds"] = perf_counter()-start
            return self._success(result,replayed,timings)
        except __import__('app.domain.value_objects.palette_compatibility',fromlist=['PaletteError']).PaletteError as error:
            return {'status':error.code,'complete':False,'reason':error.reason}
        except __import__('app.domain.value_objects.attribute_preferences',fromlist=['PreferenceError']).PreferenceError as error:
            return {'status':error.code,'complete':False,'reason':error.reason}
        except AttributeRequestError as error:
            return {'status':error.status,'complete':False,'reason':error.reason,'context_reason':error.reason}
        except RefinementError as error:
            return {'status':error.status,'complete':False,'refinement_summary':{'reason':error.reason}}
        except RelativeEncodingLimit:
            if locals().get('attribute_intent') is not None:
                return {'status':'EncodingLimitExceeded','complete':False,'reason':'attribute_proof_encoding_budget'}
            return {'status':'ProfileUnavailable','complete':False,'ranking_reason':'exact_encoding_budget_exceeded'}
        except PersistenceConflict:
            return {"status":"IdempotencyConflict","complete":False}
        except WardrobeChanged:
            return {"status":"WardrobeChanged","complete":False}
        except (KeyboardInterrupt,GeneratorExit) as error:
            log_failure("assistant", stage, "Interrupted", error)
            return {"status":"Interrupted","complete":False}
        except HTTPException:
            raise
        except Exception as error:
            log_failure("assistant", stage, "PersistenceFailure" if stage in ("lookup","persistence") else "ProcessingFailure", error)
            return {"status":"PersistenceFailure" if stage in ("lookup","persistence") else "ProcessingFailure","complete":False}

    def _prepared_engine(self,garments,user_id,*,attribute_context=None,attribute_verifier=None):
        from app.application.recommendation.compact_exhaustive_scorer import SnapshotQuery
        from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
        return RequestCandidateEngine(SnapshotQuery(user_id,garments),evaluator_factory=self.engine.evaluator_factory,
            attribute_context=attribute_context,attribute_verifier=attribute_verifier)

    @staticmethod
    def _success(record,replayed,timings):
        # Projection is read-only and uses the stored profile, never current config.
        record = with_scoring_display(record)
        # Retain legacy success fields at top level for existing consumers.
        return {**record,"status":"Selected","recommendation_status":record["status"],"complete":True,
                "replayed":replayed,"timings":timings,"recommendation":record}
