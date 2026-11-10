"""Public-object reference coordinator for P2; original R/C producers are reused."""
from fractions import Fraction as F
from types import SimpleNamespace
from app.application.recommendation.attribute_preference_relative_facts import P2RelativeFacts,P2RelativeTracker,public_score,measure
from app.application.recommendation.context_relevance_scorer import applies
from app.application.recommendation.candidate_ranker import CandidateRanker
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate,InvalidScoringInput
from app.application.recommendation.preference_normalizer import InvalidPreferenceData
from app.application.recommendation.request_match_scorer import RequestMatchScorer
from app.application.recommendation.rule_based_compatibility_scorer import RuleBasedCompatibilityScorer
from app.application.recommendation.rule_based_compatibility_policy import RuleBasedCompatibilityPolicy
from app.application.recommendation.prepared_decision_policy import PreparedDecisionPolicy
from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
from app.domain.value_objects.recommendation_score import RecommendationScore
from app.domain.value_objects.scored_candidate import ScoredCandidate
from app.domain.value_objects.ranking_outcome import RankingOutcome
from app.domain.value_objects.compatibility_signature import STRUCTURES
from app.domain.value_objects.recommendation_refinement import RefinementError
from app.domain.value_objects.attribute_preferences import PreferenceError
from app.domain.value_objects.context_relevance import RelativeEncodingLimit


def reference_rank(engine,query,user,request,prepared,*,context_ranking=False,refinement_plan=None,audit=None):
    session=None
    try:
        from app.application.recommendation.garment_retrieval_service import GarmentRetrievalService
        from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
        from app.application.recommendation.compact_exhaustive_scorer import SnapshotQuery
        actual=engine.engine if hasattr(engine,'engine') else engine
        if not actual.evaluator_factory().supports(request):return RankingOutcome('PolicyUnavailable')
        garments=GarmentRetrievalService(actual.structural_engine.retrieval.query).retrieve(user).garments
        if user!=prepared.account_id or any(g.garment_id not in prepared.by_id or prepared.by_id[g.garment_id].snapshot!=g for g in garments):raise InvalidScoringInput('P2 strict collection mismatch.')
        rows=tuple(query.get_active_preferences(user))
        if rows!=prepared.snapshot.legacy_rows():raise InvalidPreferenceData('Captured P2 and P1 preference rows disagree.')
        prepared.bind_request(request)
        preferences=prepared.composed.legacy
        if refinement_plan is not None:
            from app.application.recommendation.refinement_selector import filter_snapshot,check_category_conflicts
            from app.application.nlp.vocabulary import Vocabulary
            check_category_conflicts(request,refinement_plan.exclusions,Vocabulary.load())
            filtered=filter_snapshot(garments,refinement_plan.exclusions);garments=filtered.garments
        replay=RequestCandidateEngine(SnapshotQuery(user,garments),evaluator_factory=actual.evaluator_factory,
            attribute_context=getattr(actual,'attribute_context',None),attribute_verifier=getattr(actual,'attribute_verifier',None))
        replay.attribute_seen=getattr(actual,'attribute_seen',())
        replay.attribute_counter_guard=getattr(actual,'attribute_counter_guard',None)
        session=replay.generate_candidates(user,request)
        if hasattr(engine,'session'):engine.session=session
        if session.result.status in ('PolicyUnavailable','ProcessingFailure','Interrupted'):return RankingOutcome(session.result.status)
        tracker=None
        if context_ranking and applies(request):tracker=P2RelativeTracker(P2RelativeFacts(garments,request,preferences,prepared),refinement_plan)
        from app.application.recommendation.garment_only_refinement_selection import is_garment,GarmentTracker
        if is_garment(refinement_plan):tracker=GarmentTracker(garments,refinement_plan)
        if refinement_plan is not None and tracker is None:return RankingOutcome('RefinementUnavailable')
        gate=ScoringEligibilityGate(session,user,request);rscorer=RequestMatchScorer()
        cscorer=RuleBasedCompatibilityScorer(RuleBasedCompatibilityPolicy.load())
        decision=PreparedDecisionPolicy(CompatibilityDecisionPolicy.load())
        structures={roles:name for name,roles in STRUCTURES.items()};ranker=CandidateRanker();best=None;winners={};scored=0
        for item in session:
            verified=gate.verify(item);roles=tuple(m.role for m in verified.candidate.members)
            c=decision.apply(cscorer.score(verified),structures[roles]);r=rscorer.score(verified)
            original_p=prepared.old_scorer.score(verified,preferences)
            original=RecommendationScore(r,c,original_p,F(3,5)*r.contribution+F(1,5)*c.contribution+F(1,5)*original_p.contribution,
                                         decision.name,decision.version,decision.weights)
            chosen=ScoredCandidate(verified,public_score(original,prepared.public(verified).score));scored+=1
            if tracker is not None:
                indexes=tuple(tracker.facts.by_id[m.garment.garment_id] for m in verified.candidate.members)
                scalar=SimpleNamespace(total=chosen.score.total,contributions=(r.contribution,c.contribution,chosen.score.preference.contribution),
                    preference=measure(chosen.score.preference.summary),preference_details=tuple(measure(d) for d in chosen.score.preference.details),
                    compatibility=SimpleNamespace(value=c.contribution),original_preference_score=SimpleNamespace(
                        preference=measure(original_p.summary),preference_details=tuple(measure(d) for d in original_p.details)))
                point,_=tracker.consider(roles,indexes,None,scalar,verified.candidate.key)
                base=chosen
                if point is not None and not is_garment(refinement_plan):
                    chosen=ScoredCandidate(verified,tracker.facts.public(verified,original))
                    if (chosen.score.total,chosen.score.request_match.contribution,chosen.score.preference.contribution)!=(point.total,point.request.contribution,point.preference.contribution):raise InvalidScoringInput('P2 reference public/scalar mismatch.')
                if tracker.best_point and tracker.best_point[2]==indexes:winners['point']=chosen
                if tracker.best_legacy and tracker.best_legacy[2]==indexes:winners['legacy']=base
            elif ranker.better(chosen,best):best=chosen
            if audit is not None:audit(chosen)
        result=session.result
        if not result.complete:return RankingOutcome('ProcessingFailure')
        session.close();session=None
        if tracker is not None:
            if tracker.selected is not None:best=winners['point' if tracker.relative else 'legacy']
            else:best=None
        if best is None:
            status=(tracker.empty_refinement_status if tracker is not None else None) or result.status
            if status=='MatchingCandidates':status='NoMatchingCandidates'
            return RankingOutcome(status,complete=status not in ('RefinementUnavailable','ProfileUnavailable','PolicyUnavailable','ProcessingFailure'))
        proof=tracker.proof(best) if tracker is not None else None
        summary=None
        if refinement_plan is not None:
            from app.application.recommendation.refinement_selector import outcome_summary
            summary=outcome_summary(refinement_plan,filtered,tracker,result.failed,result.unknown,'Selected')
        return RankingOutcome('Selected',best,True,tracker.points if tracker is not None and (tracker.relative or is_garment(refinement_plan)) else scored,
                              diagnostics=preferences.diagnostics,ranking_evidence=proof,refinement_summary=summary)
    except RefinementError as exc:return RankingOutcome(exc.status,diagnostics=(('refinement_reason',exc.reason),))
    except PreferenceError as exc:return RankingOutcome('InvalidPreferenceData' if exc.code=='PreferenceInvalid' else 'ProfileUnavailable',diagnostics=(('preference_reason',exc.reason),))
    except RelativeEncodingLimit:return RankingOutcome('ProfileUnavailable',diagnostics=(('preference_reason','exact_encoding_budget_exceeded'),))
    except InvalidPreferenceData:return RankingOutcome('InvalidPreferenceData')
    except InvalidScoringInput:return RankingOutcome('InvalidScoringInput')
    except (KeyboardInterrupt,GeneratorExit):return RankingOutcome('Interrupted')
    except Exception:return RankingOutcome('ProcessingFailure')
    finally:
        if session is not None:
            try:session.close()
            except Exception:pass
