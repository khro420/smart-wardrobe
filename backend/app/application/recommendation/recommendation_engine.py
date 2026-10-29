"""Independent structural-only engine with explicit, single-use completion."""
from dataclasses import replace
from app.application.recommendation.garment_retrieval_service import GarmentRetrievalService
from app.application.recommendation.candidate_generator import CandidateGenerator
from app.application.recommendation.mandatory_rule_evaluator import MandatoryRuleEvaluator
from app.domain.value_objects.candidate_generation_result import CandidateGenerationResult
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest


class CandidateProcessingError(RuntimeError):
    pass


class CandidateGenerationSession:
    """Yielded candidates are provisional until result.complete is true.

    Exhaustion certifies a complete structural stream; early exit/close never
    does. Context management records interruption even when a consumer breaks.
    """
    def __init__(self, candidates, result):
        self._candidates = iter(candidates)
        self._result = result
        self._terminal = result.status not in ("Pending", "Running")

    @property
    def result(self):
        return self._result

    def __iter__(self):
        return self

    def __next__(self):
        if self._terminal:
            raise StopIteration
        try:
            candidate = next(self._candidates)
        except StopIteration:
            self._terminal = True
            self._result = replace(self._result, status="StructuralCandidates" if self._result.candidate_count else "NoStructuralCandidates", complete=True)
            raise
        except BaseException as exc:
            self._terminal = True
            self._result = replace(self._result, status="ProcessingFailure" if isinstance(exc, Exception) else "Interrupted", complete=False, reason="candidate_stream_failed")
            if isinstance(exc, Exception):
                raise CandidateProcessingError("Structural generation failed; discard the incomplete stream.") from None
            raise
        previous = self._result
        if type(previous) is CandidateGenerationResult:
            # Fresh construction retains full validation; subclasses need replace.
            self._result = CandidateGenerationResult(
                status="Running", complete=previous.complete,
                candidate_count=previous.candidate_count+1, reason=previous.reason,
                exclusions=previous.exclusions, validity=previous.validity,
            )
        else:
            self._result = replace(previous, status="Running", candidate_count=previous.candidate_count+1)
        return candidate

    def close(self):
        if not self._terminal:
            self._terminal = True
            self._result = replace(self._result, status="Interrupted", complete=False, reason="stream_not_exhausted")
            close = getattr(self._candidates, "close", None)
            if close:
                close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()


class RecommendationEngine:
    def __init__(self, query, generator=None, evaluator=None):
        self.retrieval = GarmentRetrievalService(query)
        self.generator = generator or CandidateGenerator()
        self.evaluator = evaluator or MandatoryRuleEvaluator()

    def generate_homepage_candidates(self, user_id):
        return self._generate(user_id)

    def generate_nlp_candidates(self, user_id, request):
        if not isinstance(request, StructuredOutfitRequest):
            return CandidateGenerationSession((), CandidateGenerationResult("PolicyUnavailable", False, reason="structured_request_required"))
        if any(getattr(request, field) is not None for field in ("occasion", "style", "colours", "garment_categories", "formality")):
            return CandidateGenerationSession((), CandidateGenerationResult("PolicyUnavailable", False, reason="phase_3b_request_rules_not_implemented"))
        return self._generate(user_id)

    def _generate(self, user_id):
        try:
            retrieved = self.retrieval.retrieve(user_id)
            if not retrieved.garments:
                return CandidateGenerationSession((), CandidateGenerationResult("NoEligibleGarments", True, exclusions=retrieved.exclusions))
            if not self.generator.has_base(retrieved.garments):
                return CandidateGenerationSession((), CandidateGenerationResult("InsufficientStructure", True, exclusions=retrieved.exclusions))
            return CandidateGenerationSession(self.generator.enumerate(retrieved.garments, self.evaluator), CandidateGenerationResult("Pending", False, exclusions=retrieved.exclusions))
        except Exception:
            return CandidateGenerationSession((), CandidateGenerationResult("ProcessingFailure", False, reason="structural_generation_setup_failed"))
