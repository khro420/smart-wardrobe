"""Internal first-pass acquisition/scoring; no route/profile/environment registration."""
from dataclasses import asdict
from fractions import Fraction as F
from types import SimpleNamespace
import json
from app.application.recommendation.request_local_bounded_ranking import PrimaryRecord,CompletedLedger,bounded_rank
from app.application.recommendation.request_local_preference_evidence import PreparedLocalPreference
from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions
from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
from app.application.recommendation.request_match_scorer import RequestMatchScorer
from app.application.recommendation.preference_scorer import PreferenceScorer
from app.application.recommendation.preference_normalizer import PreferenceNormalizer
from app.application.recommendation.rule_based_compatibility_scorer import RuleBasedCompatibilityScorer
from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
from app.application.recommendation.decision_score_codec import score_to_json,score_from_json
from app.domain.value_objects.recommendation_score import RecommendationScore
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.domain.value_objects.attribute_conditions import encode,digest

class LocalSelectionUnavailable(ValueError):
    def __init__(self,completion,*,no_eligible=False):
        self.completion=completion
        self.status='NoEligibleGarments' if no_eligible else 'InsufficientEvidence' if completion.unknown else 'NoMatchingCandidates' if completion.examined else 'NoStructuralCandidates'
        super().__init__('No mandatory-eligible local candidate.')

class FrozenQuery:
    def __init__(self,owner,rows):self.owner,self.rows=owner,tuple(rows)
    def get_confirmed_available_garments(self,owner):
        if owner!=self.owner:raise ValueError('Foreign local query.')
        return self.rows

def public_scorers(owner,preferences):
    return RequestMatchScorer(),PreferenceScorer(),RuleBasedCompatibilityScorer(),CompatibilityDecisionPolicy.load(),PreferenceNormalizer().normalize(owner,preferences)

def public_score(verified,scorers):
    r,p,c,policy,prefs=scorers
    structure={('upper','lower'):'top_bottom',('upper','lower','outerwear'):'top_bottom_outerwear',('one_piece',):'dress',('one_piece','outerwear'):'dress_outerwear'}[tuple(m.role for m in verified.candidate.members)]
    components=(r.score(verified),policy.apply(c.score(verified),structure),p.score(verified,prefs))
    total=sum((w*x.contribution for w,x in zip(policy.weights,components)),F())
    return RecommendationScore(*components,total,policy.name,policy.version,policy.weights)

def first_selection(owner,wearer,intent,collection,preferences,policy,engine):
    request=StructuredOutfitRequest(**intent.to_dict()['mandatory_request'])
    optional=PreparedLocalPreference(intent,collection,policy,account_id=owner,wearer_scope=wearer.profile_id)
    hard=intent.hard
    prepared=PreparedAttributeConditions.prepare(hard.conditions,collection,policy) if hard else None
    independent=IndependentAttributeVerifier.prepare(hard.conditions,collection,policy) if hard else None
    query=FrozenQuery(owner,[r.snapshot for r in collection]);scores={}
    if engine=='compact_exhaustive':
        from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
        from app.infrastructure.persistence.recommendation_repository_adapter import encode as score_encode
        audit=[]
        outcome=CompactExhaustiveScorer(query,SimpleNamespace(get_active_preferences=lambda who:preferences),attribute_context=prepared,attribute_verifier=independent,audit=audit.append).rank(owner,request)
        if not outcome.complete:raise ValueError('Incomplete compact local scope.')
        for row in audit:
            if row['verified']:scores[tuple(tuple(m) for m in row['key'])]=score_from_json(score_encode(row['score']))
    elif engine!='reference':raise ValueError('Unsupported local engine.')
    stream=RequestCandidateEngine(query,attribute_context=prepared,attribute_verifier=independent).generate_candidates(owner,request)
    gate=ScoringEligibilityGate(stream,owner,request);scorers=public_scorers(owner,preferences);verified={}
    try:
        for item in stream:
            v=gate.verify(item);verified[v.candidate.key]=v
            if engine=='reference':scores[v.candidate.key]=public_score(v,scorers)
        count=stream.result
        completion=CompletedLedger(count.examined,count.passed,count.failed,count.unknown,count.complete)
    finally:stream.close()
    if set(scores)!=set(verified):raise ValueError('Compact/reference admission scope mismatch.')
    from app.application.recommendation.request_local_score_encoding import LocalScoreEncoding
    encoding=LocalScoreEncoding()
    rows=tuple(PrimaryRecord(k,s.request_match.contribution,s.compatibility.contribution,s.preference.contribution,s.total,optional.scope_hash,encoding.encode(s).encode()) for k,s in scores.items())
    decision=bounded_rank(lambda:iter(rows),completion,lambda key:optional.evaluate(verified[key]),resolution=intent.to_dict()['optional']['resolution']['state'])
    if decision.selected is None:raise LocalSelectionUnavailable(completion)
    return decision,verified[decision.selected.key].candidate,scores[decision.selected.key]

def decision_document(decision):
    def row(item):return {'key':[list(k) for k in item.key],'score':json.loads(item.certificate)}
    selected=next(x for x in decision.optional_ledger if x.primary==decision.selected)
    optional=selected.optional
    return {'baseline':row(decision.baseline),'selected':row(decision.selected),'mandatory':asdict(decision.mandatory),
        'scope_digest':decision.scope_digest,'promotable':[list(map(list,x.primary.key)) for x in decision.optional_ledger if not x.reasons],
        'optional_counts':{s:sum(x.optional.state==s for x in decision.optional_ledger) for s in ('Satisfied','Unsatisfied','Unverifiable')},
        'selected_optional':{'state':optional.state,'support':optional.support,'value':None if optional.value is None else str(optional.value),'lower':str(optional.lower),'upper':str(optional.upper),'ledger':[json.loads(x) for x in optional.ledger]},
        'explanation':'qualified_bounded_promotion' if decision.selected.key!=decision.baseline.key else 'original_baseline_retained'}
