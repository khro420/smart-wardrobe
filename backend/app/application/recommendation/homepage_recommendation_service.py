"""Independent random Homepage flow: no NLP, preferences, scoring or chats."""
import json
import re
from time import perf_counter
from app.application.recommendation.reservoir_selector import ReservoirSelector
from app.domain.value_objects.recommendation_persistence import RecommendationWrite, PersistenceConflict, WardrobeChanged
from app.application.recommendation.failure_diagnostics import log_failure


def valid_submission_key(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}", value) is not None


class HomepageRecommendationService:
    def __init__(self, engine, repository, selector=None):
        self.engine = engine
        self.repository = repository
        self.selector = selector or ReservoirSelector()

    def recommend(self, user_id, submission_key):
        if not isinstance(user_id, str) or not user_id.strip() or not valid_submission_key(submission_key):
            return {"status": "InvalidInput", "complete": False}
        session, stage, timings = None, "lookup", {}
        try:
            start = perf_counter()
            prior = self.repository.find_homepage_submission(user_id, submission_key)
            timings["lookup_seconds"] = perf_counter() - start
            if prior is not None:
                return self._success(prior, True, timings)
            stage = "generation"
            start = perf_counter()
            session = self.engine.generate_homepage_candidates(user_id)
            timings["retrieval_setup_seconds"] = perf_counter() - start
            if session.result.status in ("ProcessingFailure", "Interrupted", "PolicyUnavailable"):
                status = session.result.status
                if status != "PolicyUnavailable":
                    log_failure("homepage", stage, status, reason="controlled_failure")
                session.close()
                session = None
                return {"status": status, "complete": False}
            start = perf_counter()
            selection = self.selector.select(session)
            session = None
            timings["enumeration_selection_seconds"] = perf_counter() - start
            if selection.candidate is None:
                return {"status": selection.status, "complete": True, "candidate_count": 0, "timings": timings}
            provenance = {
                "homepage_policy": "phase5b-1.0.0", "structure_policy": self.engine.generator.policy.version,
                "selection": "uniform_candidate_reservoir_v1", "candidate_count": selection.count,
                "validity": "approved_structural_policy_only", "compatibility_scoring": "not_applicable",
            }
            command = RecommendationWrite(user_id, "homepage", submission_key, "{}", selection.candidate, json.dumps(provenance))
            stage = "persistence"
            start = perf_counter()
            result, concurrent_replay = self.repository.persist_homepage(command)
            timings["persistence_seconds"] = perf_counter() - start
            # A concurrent request may have committed another draw first. Always
            # return its durable result; never substitute this provisional draw.
            return self._success(result, concurrent_replay, timings)
        except PersistenceConflict:
            return {"status": "IdempotencyConflict", "complete": False}
        except WardrobeChanged:
            return {"status": "WardrobeChanged", "complete": False}
        except (KeyboardInterrupt, GeneratorExit) as error:
            log_failure("homepage", stage, "Interrupted", error)
            return {"status": "Interrupted", "complete": False}
        except Exception as error:
            log_failure("homepage", stage, "PersistenceFailure" if stage in ("lookup", "persistence") else "ProcessingFailure", error)
            return {"status": "PersistenceFailure" if stage in ("lookup", "persistence") else "ProcessingFailure", "complete": False}
        finally:
            if session is not None:
                try:
                    session.close()
                except BaseException as error:
                    log_failure("homepage", "cleanup", "ProcessingFailure", error, reason="cleanup")

    @staticmethod
    def _success(result, replayed, timings):
        return {"status": "Selected", "complete": True, "replayed": replayed,
                "recommendation": result, "currently_eligible": bool(result["items"]) and all(i["currently_eligible"] for i in result["items"]),
                "timings": timings}
