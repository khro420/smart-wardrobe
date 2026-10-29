from app.application.recommendation.exact_score_reuse import ExactScoreReuse
from app.application.nlp.vocabulary import Vocabulary
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.application.recommendation.suitability_evidence_mapper import SuitabilityEvidenceParser
from app.domain.value_objects.scored_candidate import VerifiedScoringInput
from app.domain.value_objects.preference_snapshot import NormalizedPreferenceSet
from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore


class PreferenceScorer:
    @staticmethod
    def independent_component(original,preferences,objective):
        """New-profile mask only; retain the original positive-weight denominator."""
        from fractions import Fraction as F
        if objective is None or not preferences.preferences:return original
        keep=tuple(not (p.preference_type=='styles' and p.values==(objective.target,)) for p in preferences.preferences)
        if all(keep):return original
        details=tuple(d if k else ScoreEvidence(d.name,None,'NotApplicable',0,d.possible,('duplicate_R_semantic_test_suppressed',)) for d,k in zip(original.details,keep))
        active=tuple(d for d,k in zip(details,keep) if k)
        possible=sum(d.possible for d in details)
        if not active:summary=ScoreEvidence('preference',None,'NotApplicable',0,possible,('all_active_preferences_duplicate_R',))
        elif all(d.value is None for d in active):summary=ScoreEvidence('preference',None,'Unknown',0,possible)
        else:
            value=sum((p.importance*(d.value or F()) for p,d in zip(preferences.preferences,details)),F())/sum(p.importance for p in preferences.preferences)
            summary=ScoreEvidence('preference',value,'Available' if all(d.state=='Available' for d in active) else 'Partial',sum(d.observed for d in details),possible,('duplicate_R_semantic_test_suppressed_original_denominator',))
        return ComponentScore(summary,details)

    def __init__(self,mapper=None):
        self.mapper = mapper or GarmentEvidenceMapper()
        self._reuse = ExactScoreReuse()
        self.suitability = SuitabilityEvidenceParser()
        self.vocabulary = Vocabulary.load()
        self._prepared = None
        self._facts = {}
        self.fact_hits = self.fact_misses = 0
        self._empty = {state: ComponentScore(self._reuse.evidence("preference",None,state))
                       for state in ("NoPreferences","NoSupportedPreferences")}

    def _prepare(self, preferences):
        # NormalizedPreferenceSet and its nested values are immutable. Identity
        # scopes reuse to this exact user-owned snapshot; no cross-request cache.
        if self._prepared is None or self._prepared[0] is not preferences:
            self._facts.clear()
            self._weights = tuple(p.importance for p in preferences.preferences)
            facts = []
            for preference in preferences.preferences:
                if preference.preference_type == "garment_categories":
                    allowed = set()
                    for item in preference.values:
                        allowed.update(self.vocabulary.groups[item.value] if item.kind == "group" else (item.value,))
                    facts.append(frozenset(allowed))
                elif preference.preference_type in ("colours","styles"):
                    facts.append(frozenset(preference.values))
                else:
                    facts.append(None)
            self._prepared = (preferences,tuple(facts),sum(p.importance for p in preferences.preferences))
        return self._prepared[1:]

    def _fact(self, index, preference, matching_values, garment):
        """Immutable facts for this exact preference snapshot and garment.

        Values include diagnostics, not just matches. No candidate score is
        retained here. Snapshot conflicts still fail rather than use stale facts.
        """
        key = (index,garment.garment_id)
        cached = self._facts.get(key)
        if cached is not None:
            if cached[0] != garment:
                raise ValueError("Conflicting garment evidence in one session.")
            self.fact_hits += 1
            return cached[1]
        kind = preference.preference_type
        if kind == "garment_categories":
            fact = (garment.category in matching_values,)
        elif kind in ("colours","styles"):
            evidence = getattr(self.mapper.classify(garment),"colour" if kind == "colours" else "style")
            fact = (not matching_values.isdisjoint(evidence.values),evidence.state == "Known",
                    evidence.state.lower()+":"+garment.garment_id)
        else:
            evidence = self.suitability.parse(garment)
            fact = (tuple(evidence.state_for("formality",value) for value in preference.values),
                    evidence.source_state.lower()+":"+garment.garment_id)
        self._facts[key] = (garment,fact)
        self.fact_misses += 1
        return fact

    def score(self,verified,preferences):
        if not isinstance(verified,VerifiedScoringInput) or not isinstance(preferences,NormalizedPreferenceSet) or preferences.user_id != verified.user_id:
            raise ValueError("Verified user-scoped scoring inputs required.")
        if not preferences.preferences:
            state = "NoSupportedPreferences" if preferences.diagnostics else "NoPreferences"
            return self._empty[state]
        prepared, denominator = self._prepare(preferences)
        members = verified.candidate.members
        details = []
        for index,(preference, matching_values) in enumerate(zip(preferences.preferences,prepared)):
            kind,values = preference.preference_type,preference.values
            if kind == "garment_categories":
                match = any(self._fact(index,preference,matching_values,item.garment)[0] for item in members)
                detail = self._reuse.evidence(kind,self._reuse.fraction(int(match)),"Available",1,1)
            elif kind in ("colours","styles"):
                selected = [item for item in members if kind == "colours" or item.role != "outerwear"]
                evidence = [self._fact(index,preference,matching_values,item.garment) for item in selected]
                matched = sum(item[0] for item in evidence)
                known = sum(item[1] for item in evidence)
                reasons = tuple(item[2] for item in evidence)
                if kind == "colours" and matched:
                    detail = self._reuse.evidence(kind,self._reuse.fraction(1),"Available",known,len(evidence),reasons)
                elif known == 0 and matched == 0:
                    detail = self._reuse.evidence(kind,None,"Unknown",0,len(evidence),reasons)
                else:
                    value = self._reuse.fraction(int(matched>0)) if kind == "colours" else self._reuse.fraction(matched,len(evidence))
                    detail = self._reuse.evidence(kind,value,"Available" if known == len(evidence) else "Partial",known,len(evidence),reasons)
            else:
                evidence = [self._fact(index,preference,matching_values,item.garment) for item in members]
                states = tuple(zip(*(item[0] for item in evidence)))
                reasons = tuple(item[1] for item in evidence)
                if any(all(state == "Pass" for state in row) for row in states):
                    detail = self._reuse.evidence(kind,self._reuse.fraction(1),"Available",1,1,reasons)
                elif all(any(state == "Fail" for state in row) for row in states):
                    detail = self._reuse.evidence(kind,self._reuse.fraction(0),"Available",1,1,reasons)
                else:
                    detail = self._reuse.evidence(kind,None,"Unknown",0,1,reasons)
            details.append(detail)
        value = self._reuse.preference(self._weights,tuple(detail.value for detail in details),denominator)
        if all(detail.value is None for detail in details):
            return ComponentScore(self._reuse.evidence("preference",None,"Unknown",0,sum(x.possible for x in details)),tuple(details))
        return ComponentScore(self._reuse.evidence("preference",value,"Available" if all(x.state == "Available" for x in details) else "Partial",sum(x.observed for x in details),sum(x.possible for x in details)),tuple(details))
