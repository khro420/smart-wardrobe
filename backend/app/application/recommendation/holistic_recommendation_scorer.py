"""Explicit experimental RecommendationScorer specialization; no live wiring.

Reuses Phase 4A gate, R/P scorers, exact score objects and CandidateRanker.
Separate orchestration preserves the completed Phase 4A constructor/profile
contracts. Completion/error behaviour is regression-tested against that pipeline.
"""
from app.application.recommendation.recommendation_scorer import RecommendationScorer
from app.application.recommendation.holistic_scoring_profile import HolisticScoringProfile,DEFAULT_HOLISTIC_PROFILES
from app.application.recommendation.compatibility_reference_policy import CompatibilityReferencePolicy
from app.application.recommendation.holistic_compatibility_scorer import HolisticCompatibilityScorer
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate,InvalidScoringInput
from app.application.recommendation.preference_normalizer import PreferenceNormalizer,InvalidPreferenceData
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.application.recommendation.request_match_scorer import RequestMatchScorer
from app.application.recommendation.preference_scorer import PreferenceScorer
from app.application.recommendation.candidate_ranker import CandidateRanker
from app.domain.value_objects.recommendation_score import RecommendationScore
from app.domain.value_objects.scored_candidate import ScoredCandidate
from app.domain.value_objects.ranking_outcome import RankingOutcome
from app.domain.value_objects.compatibility_signature import STRUCTURES


class HolisticRecommendationScorer(RecommendationScorer):
    def __init__(self,candidate_engine,preference_query,reference_policy=None,profile_path=DEFAULT_HOLISTIC_PROFILES,allow_synthetic=False):
        super().__init__(candidate_engine,preference_query)
        if reference_policy is not None and reference_policy.synthetic and not allow_synthetic:
            raise ValueError("Synthetic ratings may only be used by explicit test-fixture opt-in.")
        self.reference_policy = reference_policy
        self.profile_path = profile_path

    def rank(self,user_id,request,profile_name):
        session,best,count,diagnostics = None,None,0,()
        coverage = {name:{"examined":0,"reviewed":0,"unknown":0,"unavailable":0,"incomplete":0} for name in STRUCTURES}
        def finish(status,winner=None,complete=False):
            counts = tuple(("coverage:"+structure,key+"="+str(value)) for structure,values in sorted(coverage.items()) for key,value in sorted(values.items()))
            return RankingOutcome(status,winner,complete,count,(*diagnostics,*counts))
        try:
            try:
                profile = HolisticScoringProfile.load(profile_name,self.profile_path)
                policy = self.reference_policy or CompatibilityReferencePolicy.load()
            except (ValueError,OSError):
                return finish("ProfileUnavailable")
            diagnostics = (("reference_policy_version",policy.version),("reference_policy_hash",policy.hash),("synthetic_fixture",str(policy.synthetic).lower()),("unknown_numeric_contribution","0; experimental only, not proven incompatibility"))
            session = self.candidate_engine.generate_candidates(user_id,request)
            if session.result.status in ("PolicyUnavailable","ProcessingFailure","Interrupted"):
                return finish(session.result.status)
            gate = ScoringEligibilityGate(session,user_id,request)
            preferences = PreferenceNormalizer().normalize(user_id,self.preference_query.get_active_preferences(user_id))
            diagnostics = (*diagnostics,*preferences.diagnostics)
            mapper = GarmentEvidenceMapper()
            r_scorer,p_scorer,c_scorer = RequestMatchScorer(mapper),PreferenceScorer(mapper),HolisticCompatibilityScorer(policy,mapper)
            ranker = CandidateRanker()
            for item in session:
                verified = gate.verify(item)
                r,c,p = r_scorer.score(verified),c_scorer.score(verified,profile),p_scorer.score(verified,preferences)
                roles = tuple(member.role for member in verified.candidate.members)
                structure = next(name for name,expected in STRUCTURES.items() if roles == expected)
                current = coverage[structure]
                current["examined"] += 1
                current["reviewed" if c.summary.state == "Available" else "unavailable" if c.summary.state == "Unavailable" else "unknown"] += 1
                if "incomplete_or_malformed_evidence" in c.summary.reasons:
                    current["incomplete"] += 1
                score = RecommendationScore(r,c,p,sum(w*x.contribution for w,x in zip(profile.weights,(r,c,p))),profile.name,profile.version,profile.weights)
                candidate = ScoredCandidate(verified,score)
                count += 1
                if ranker.better(candidate,best):
                    best = candidate
            if not session.result.complete:
                return finish("ProcessingFailure")
            result = session.result
            session.close()
            session = None
            if best is None:
                return finish(result.status,complete=True)
            if result.status != "MatchingCandidates" or result.passed != count:
                raise InvalidScoringInput("Candidate completion count mismatch.")
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
