from dataclasses import dataclass
from app.domain.value_objects.scored_candidate import ScoredCandidate


@dataclass(frozen=True)
class RankingOutcome:
    status: str
    winner: ScoredCandidate | None = None
    complete: bool = False
    scored_count: int = 0
    diagnostics: tuple[tuple[str,str], ...] = ()
    ranking_evidence: str | None = None
    refinement_summary: str | None = None

    def __post_init__(self):
        if self.refinement_summary is not None:
            import json
            if type(self.refinement_summary) is not str or len(self.refinement_summary)>8192 or type(json.loads(self.refinement_summary)) is not dict:
                raise ValueError('Invalid bounded refinement outcome summary.')
        complete_states = ("Selected","NoMatchingCandidates","InsufficientEvidence","NoEligibleGarments","InsufficientStructure","NoStructuralCandidates","RefinementExhausted","RefinementInsufficientEvidence")
        if self.status not in (*complete_states,"PolicyUnavailable","ProfileUnavailable","InvalidPreferenceData","InvalidScoringInput","ProcessingFailure","Interrupted","RefinementUnavailable","RefinementConflict","RefinementScopeChanged","RefinementLimitReached") or not isinstance(self.complete,bool) or self.complete != (self.status in complete_states):
            raise ValueError("Invalid ranking completion state.")
        if (self.status == "Selected") != isinstance(self.winner,ScoredCandidate) or (self.status != "Selected" and self.winner is not None):
            raise ValueError("Only a completed selection may contain a winner.")
        if isinstance(self.scored_count,bool) or not isinstance(self.scored_count,int) or self.scored_count < 0:
            raise ValueError("Invalid scored count.")
        if self.status == "Selected" and self.scored_count == 0:
            raise ValueError("Selection requires at least one scored candidate.")
        if not isinstance(self.diagnostics,(list,tuple)) or any(not isinstance(x,(tuple,list)) or len(x) != 2 or any(not isinstance(y,str) for y in x) for x in self.diagnostics):
            raise ValueError("Invalid ranking diagnostics.")
        object.__setattr__(self,"diagnostics",tuple(tuple(x) for x in self.diagnostics))
        if self.ranking_evidence is not None:
            from app.domain.value_objects.context_relevance import read_proof
            if self.status!='Selected' or type(read_proof(self.ranking_evidence)) is not dict:
                raise ValueError('Ranking evidence requires a completed selection.')
