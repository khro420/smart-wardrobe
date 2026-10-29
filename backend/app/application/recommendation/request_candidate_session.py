"""Filtered stream; partial candidates cannot certify successful completion."""
from dataclasses import replace
from app.domain.value_objects.request_candidate_evaluation import RequestGenerationResult, EvaluatedCandidate


class RequestProcessingError(RuntimeError):
    pass


class RequestCandidateSession:
    def __init__(self, structural_session, request, evaluator, result=None):
        self.structural_session = structural_session
        self.request = request
        self.evaluator = evaluator
        self._result = result or RequestGenerationResult()
        self._terminal = self._result.status not in ("Pending","Running")

    @property
    def result(self):
        return self._result

    @property
    def evidence_cache_size(self):
        return self.evaluator.mapper.cache_size if self.evaluator is not None else 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._terminal:
            raise StopIteration
        try:
            while True:
                try:
                    candidate = next(self.structural_session)
                except StopIteration:
                    structural = self.structural_session.result
                    if not structural.complete:
                        raise RequestProcessingError("Structural stream did not complete.")
                    if structural.status in ("NoEligibleGarments","InsufficientStructure","NoStructuralCandidates"):
                        status = structural.status
                    else:
                        status = "MatchingCandidates" if self._result.passed else "InsufficientEvidence" if self._result.unknown else "NoMatchingCandidates"
                    self._result = replace(self._result,status=status,complete=True)
                    self._terminal = True
                    raise StopIteration
                decision = self.evaluator.evaluate(candidate,self.request)
                field = {"Pass":"passed","Fail":"failed","Unknown":"unknown"}[decision.state]
                previous = self._result
                if type(previous) is RequestGenerationResult:
                    # Preserve every counter and diagnostic; validate every step.
                    examined = previous.examined+1
                    count = getattr(previous,field)+1
                    self._result = RequestGenerationResult(
                        status="Running", complete=previous.complete, examined=examined,
                        passed=count if field == "passed" else previous.passed,
                        failed=count if field == "failed" else previous.failed,
                        unknown=count if field == "unknown" else previous.unknown,
                        reason=previous.reason,
                    )
                else:
                    self._result = replace(previous,status="Running",examined=previous.examined+1,**{field:getattr(previous,field)+1})
                if decision.state == "Pass":
                    return EvaluatedCandidate(candidate,decision)
        except StopIteration:
            raise
        except BaseException as exc:
            self._terminal = True
            self._result = replace(self._result,status="ProcessingFailure" if isinstance(exc,Exception) else "Interrupted",complete=False,reason="request_stream_failed")
            try:
                self.structural_session.close()
            except Exception:
                pass
            if isinstance(exc,Exception):
                raise RequestProcessingError("Request evaluation failed; discard the incomplete stream.") from None
            raise

    def close(self):
        if not self._terminal:
            self._terminal = True
            self._result = replace(self._result,status="Interrupted",complete=False,reason="stream_not_exhausted")
            try:
                self.structural_session.close()
            except Exception:
                self._result = replace(self._result,status="ProcessingFailure",reason="stream_close_failed")
                raise RequestProcessingError("Request stream could not close safely.") from None

    def __enter__(self):
        return self

    def __exit__(self,exc_type,exc,traceback):
        self.close()
