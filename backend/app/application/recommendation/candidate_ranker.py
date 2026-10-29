"""Top-one comparison without materialising or truncating candidate streams."""
from app.domain.value_objects.scored_candidate import ScoredCandidate


class CandidateRanker:
    def __init__(self):
        # One ranker per session. Retain the immutable incumbent, not an ID-only
        # cache that could conflate different candidates or scoring contexts.
        self._incumbent = None
        self._incumbent_key = None

    @staticmethod
    def key(item):
        if not isinstance(item,ScoredCandidate):
            raise ValueError("Scored candidate required.")
        score = item.score
        return (-score.total,-score.request_match.contribution,-score.compatibility.contribution,-score.preference.contribution,item.verified.candidate.key)

    def better(self,candidate,current):
        candidate_key = self.key(candidate)
        if current is not None and (candidate.verified.context_id,candidate.verified.request,candidate.verified.user_id) != (current.verified.context_id,current.verified.request,current.verified.user_id):
            raise ValueError("Cannot compare different scoring sessions.")
        if current is not None and (candidate.score.profile_name,candidate.score.policy_version,candidate.score.weights) != (current.score.profile_name,current.score.policy_version,current.score.weights):
            raise ValueError("Cannot compare different scoring profiles.")
        current_key = (self._incumbent_key if current is self._incumbent
                       else self.key(current)) if current is not None else None
        better = current is None or candidate_key < current_key
        self._incumbent = candidate if better else current
        self._incumbent_key = candidate_key if better else current_key
        return better
