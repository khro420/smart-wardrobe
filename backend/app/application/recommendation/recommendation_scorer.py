"""Explicit Phase 4A coordinator, no live wiring or persistence side effects."""
from app.application.recommendation.scoring_policy import ScoringProfile
from app.application.recommendation.exact_score_reuse import ExactScoreReuse
from app.application.recommendation.preference_normalizer import PreferenceNormalizer,InvalidPreferenceData
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate,InvalidScoringInput
from app.application.recommendation.request_match_scorer import RequestMatchScorer
from app.application.recommendation.compatibility_scorer import CompatibilityScorer,ProfileUnavailable
from app.application.recommendation.preference_scorer import PreferenceScorer
from app.application.recommendation.candidate_ranker import CandidateRanker
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.domain.value_objects.recommendation_score import RecommendationScore
from app.domain.value_objects.scored_candidate import ScoredCandidate
from app.domain.value_objects.ranking_outcome import RankingOutcome


class RecommendationScorer:
    def __init__(self,candidate_engine,preference_query):
        self.candidate_engine = candidate_engine
        self.preference_query = preference_query

    def rank(self,user_id,request,profile_name):
        session,best,count,diagnostics = None,None,0,()
        try:
            try:
                profile = ScoringProfile.load(profile_name)
            except ValueError:
                return RankingOutcome("ProfileUnavailable")
            session = self.candidate_engine.generate_candidates(user_id,request)
            if session.result.status in ("PolicyUnavailable","ProcessingFailure","Interrupted"):
                return RankingOutcome(session.result.status)
            gate = ScoringEligibilityGate(session,user_id,request)
            preferences = PreferenceNormalizer().normalize(user_id,self.preference_query.get_active_preferences(user_id))
            diagnostics = preferences.diagnostics
            mapper = GarmentEvidenceMapper()  # Fresh cache, no uncalibrated classifier.
            request_scorer,compatibility_scorer,preference_scorer = RequestMatchScorer(mapper),CompatibilityScorer(mapper),PreferenceScorer(mapper)
            ranker = CandidateRanker()
            reuse = ExactScoreReuse()
            for item in session:
                verified = gate.verify(item)
                components = (request_scorer.score(verified),compatibility_scorer.score(verified,profile),preference_scorer.score(verified,preferences))
                total = reuse.weighted(profile.weights,tuple(c.contribution for c in components))
                score = RecommendationScore(*components,total,profile.name,profile.version,profile.weights)
                scored = ScoredCandidate(verified,score)
                count += 1
                if ranker.better(scored,best):
                    best = scored
            if not session.result.complete:
                return RankingOutcome("ProcessingFailure",scored_count=count,diagnostics=diagnostics)
            result = session.result
            session.close()  # A close error must not certify a final winner.
            session = None
            if best is None:
                return RankingOutcome(result.status,complete=True,diagnostics=diagnostics)
            if result.status != "MatchingCandidates" or result.passed != count:
                raise InvalidScoringInput("Stream result/accepted count mismatch.")
            return RankingOutcome("Selected",best,True,count,diagnostics)
        except InvalidPreferenceData:
            return RankingOutcome("InvalidPreferenceData",scored_count=count,diagnostics=diagnostics)
        except InvalidScoringInput:
            return RankingOutcome("InvalidScoringInput",scored_count=count,diagnostics=diagnostics)
        except ProfileUnavailable:
            return RankingOutcome("ProfileUnavailable",scored_count=count,diagnostics=diagnostics)
        except (KeyboardInterrupt,GeneratorExit):
            return RankingOutcome("Interrupted",scored_count=count,diagnostics=diagnostics)
        except Exception:
            return RankingOutcome("ProcessingFailure",scored_count=count,diagnostics=diagnostics)
        finally:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass
