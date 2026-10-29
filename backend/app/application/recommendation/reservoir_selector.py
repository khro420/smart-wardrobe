"""Uniform sampling over a complete structural stream, with O(1) sample memory."""
from dataclasses import dataclass
from secrets import randbelow
from app.domain.value_objects.outfit_candidate import OutfitCandidate


class IncompleteSelection(RuntimeError):
    pass


@dataclass(frozen=True)
class ReservoirSelection:
    candidate: OutfitCandidate | None
    count: int
    status: str


class ReservoirSelector:
    def __init__(self, random_below=None):
        self.random_below = random_below or randbelow

    def select(self, session):
        selected, count = None, 0
        try:
            for candidate in session:
                if not isinstance(candidate, OutfitCandidate):
                    raise IncompleteSelection("Invalid candidate stream.")
                count += 1
                if count == 1:
                    selected = candidate
                else:
                    draw = self.random_below(count)
                    if isinstance(draw, bool) or not isinstance(draw, int) or not 0 <= draw < count:
                        raise IncompleteSelection("Invalid random source.")
                    if draw == 0:
                        selected = candidate
            result = session.result
            if not result.complete or result.candidate_count != count:
                raise IncompleteSelection("Candidate stream did not complete consistently.")
            expected = ("StructuralCandidates",) if count else ("NoEligibleGarments", "InsufficientStructure", "NoStructuralCandidates")
            if result.status not in expected:
                raise IncompleteSelection("Unexpected terminal candidate status.")
            session.close()  # Even a late close failure invalidates the sample.
            return ReservoirSelection(selected, count, result.status)
        except BaseException:
            try:
                session.close()
            except BaseException:
                pass
            raise
