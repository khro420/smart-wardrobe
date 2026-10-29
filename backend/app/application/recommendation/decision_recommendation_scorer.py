"""Isolated versioned decision scoring; no live registration or persistence changes."""
from app.application.recommendation.recommendation_scorer import RecommendationScorer
from app.application.recommendation.rule_based_compatibility_policy import RuleBasedCompatibilityPolicy,RULES
from app.application.recommendation.cached_rule_based_compatibility_scorer import CachedRuleBasedCompatibilityScorer
from app.application.recommendation.rule_based_compatibility_scorer import RuleBasedCompatibilityScorer
from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy, CONFIG
from app.application.recommendation.compatibility_pair_cache import PairCacheInfo,MAX_PAIR_CAPACITY
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate,InvalidScoringInput
from app.application.recommendation.preference_normalizer import PreferenceNormalizer,InvalidPreferenceData
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.application.recommendation.request_match_scorer import RequestMatchScorer
from app.application.recommendation.preference_scorer import PreferenceScorer
from app.application.recommendation.candidate_ranker import CandidateRanker
from app.application.recommendation.exact_score_reuse import ExactScoreReuse
from app.domain.value_objects.recommendation_score import RecommendationScore
from app.domain.value_objects.scored_candidate import ScoredCandidate
from app.domain.value_objects.ranking_outcome import RankingOutcome
from app.domain.value_objects.compatibility_signature import STRUCTURES


class DecisionRecommendationScorer(RecommendationScorer):
    def __init__(self,candidate_engine,preference_query,policy_path=RULES,decision_path=CONFIG,capacity=MAX_PAIR_CAPACITY,cached=True):
        super().__init__(candidate_engine,preference_query)
        if type(capacity) is not int or not 0<=capacity<=MAX_PAIR_CAPACITY:
            raise ValueError("Invalid pair-cache capacity.")
        if type(cached) is not bool:
            raise ValueError("Explicit cache selection must be boolean.")
        self.policy_path,self.decision_path,self.cached=policy_path,decision_path,cached
        self.capacity=capacity

    def rank(self,user_id,request):
        return self.rank_with_cache_info(user_id,request)[0]

    def rank_with_cache_info(self,user_id,request):
        c_scorer=None
        session,best,seen,scored,unknown=None,None,0,0,0
        not_applicable=0
        diagnostics=()
        basis_counts={name:0 for name in ("Computed","PartiallyConventional","FullyConventional","NoPairReference")}
        atomic_known=atomic_possible=0
        coverage={name:{"examined":0,"available":0,"unknown":0,"zero":0,"no_pairs":0} for name in STRUCTURES}
        structures={roles:name for name,roles in STRUCTURES.items()}
        def finish(status,winner=None,complete=False):
            counts=tuple(("coverage:"+name,key+"="+str(value)) for name,values in sorted(coverage.items()) for key,value in sorted(values.items()))
            stream=(("accepted_examined",str(seen)),("numerically_scored",str(scored)),("compatibility_unknown",str(unknown)),("compatibility_not_applicable",str(not_applicable)))
            return (RankingOutcome(status,winner,complete,scored,(*diagnostics,*stream,*counts,*( ("decision_basis:"+name,str(count)) for name,count in basis_counts.items()),("atomic_known",str(atomic_known)),("atomic_possible",str(atomic_possible)))),
                    c_scorer.pair_cache.info if self.cached and c_scorer is not None else PairCacheInfo(self.capacity if self.cached else 0,0,0,0,0,0,0))
        try:
            try:
                policy=RuleBasedCompatibilityPolicy.load(self.policy_path)
                profile=CompatibilityDecisionPolicy.load(self.decision_path)
            except (ValueError,TypeError,OSError):
                return finish("ProfileUnavailable")
            diagnostics=(("compatibility_policy",policy.version),("compatibility_policy_hash",policy.hash),
                         ("scoring_profile_hash",profile.hash),("experimental","true"),
                         ("coverage_policy","all_mandatory_valid_candidates_use_explicit_decision"))
            session=self.candidate_engine.generate_candidates(user_id,request)
            if session.result.status in ("PolicyUnavailable","ProcessingFailure","Interrupted"):
                return finish(session.result.status)
            gate=ScoringEligibilityGate(session,user_id,request)
            preferences=PreferenceNormalizer().normalize(user_id,self.preference_query.get_active_preferences(user_id))
            diagnostics=(*diagnostics,*preferences.diagnostics)
            mapper=GarmentEvidenceMapper()
            r_scorer,p_scorer=RequestMatchScorer(mapper),PreferenceScorer(mapper)
            c_scorer=CachedRuleBasedCompatibilityScorer(policy,self.capacity) if self.cached else RuleBasedCompatibilityScorer(policy)
            ranker,reuse=CandidateRanker(),ExactScoreReuse()
            for item in session:
                verified=gate.verify(item)
                seen+=1
                raw=c_scorer.score(verified)
                structure=structures[tuple(m.role for m in verified.candidate.members)]
                c=profile.apply(raw,structure)
                decision=c.decision
                basis_counts[decision.basis]+=1
                atomic_known+=decision.known_count
                atomic_possible+=decision.atomic_count
                row=coverage[structures[tuple(m.role for m in verified.candidate.members)]]
                row["examined"]+=1
                if c.summary.state!="Available" or c.summary.value is None:
                    if c.summary.state=="NotApplicable":
                        not_applicable+=1
                    else:
                        unknown+=1
                        row["unknown"]+=1
                    row["no_pairs"]+=int("no_pair_relationships" in c.summary.reasons)
                else:
                    row["available"]+=1
                    row["zero"]+=int(c.summary.value==0)
                r,p=r_scorer.score(verified),p_scorer.score(verified,preferences)
                score=RecommendationScore(r,c,p,reuse.weighted(profile.weights,(r.contribution,c.contribution,p.contribution)),
                                          profile.name,profile.version,profile.weights)
                candidate=ScoredCandidate(verified,score)
                scored+=1
                if ranker.better(candidate,best):
                    best=candidate
            result=session.result
            if not result.complete:
                return finish("ProcessingFailure")
            session.close()  # A late close failure invalidates all provisional results.
            session=None
            diagnostics=(*diagnostics,("stream_examined",str(result.examined)),("stream_passed",str(result.passed)),
                         ("stream_failed",str(result.failed)),("stream_unknown",str(result.unknown)))
            if seen and (result.status!="MatchingCandidates" or result.passed!=seen):
                raise InvalidScoringInput("Complete candidate-stream count mismatch.")
            if best is None:
                return finish(result.status,complete=True)
            return finish("Selected",best,True)
        except InvalidPreferenceData:
            return finish("InvalidPreferenceData")
        except InvalidScoringInput:
            return finish("InvalidScoringInput")
        except (KeyboardInterrupt,GeneratorExit):
            return finish("Interrupted")
        except Exception:
            return finish("ProcessingFailure")
        finally:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass
