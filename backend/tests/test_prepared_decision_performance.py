"""Differential against untouched 3C-2 plus independent exact arithmetic checks."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace,FrozenInstanceError
from fractions import Fraction as F
import json
import pytest
from app.application.recommendation.prepared_decision_policy import PreparedDecisionPolicy
from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
from app.application.recommendation.decision_recommendation_scorer import DecisionRecommendationScorer
from app.application.recommendation.prepared_decision_scorer import PreparedDecisionRecommendationScorer
from app.application.recommendation.cached_rule_based_compatibility_scorer import CachedRuleBasedCompatibilityScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.decision_score_codec import score_to_json,score_from_json
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
from app.domain.value_objects.recommendation_score import ComponentScore,ScoreEvidence,RecommendationScore
from app.domain.value_objects.compatibility_decision import CompatibilityDecision
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.domain.value_objects.compatibility_signature import STRUCTURES
from tests.test_rule_based_compatibility import g,candidate,Preferences
from tests.test_structural_candidates import Query
from tests.test_compatibility_pair_cache import signature
from tests.test_recommendation_persistence import store,connect


def run(rows,request=None,capacity=19900,cached=True,prefs=()):
    req=request or StructuredOutfitRequest()
    old=DecisionRecommendationScorer(RequestCandidateEngine(Query(rows)),Preferences(prefs),capacity=capacity,cached=cached)
    new=PreparedDecisionRecommendationScorer(RequestCandidateEngine(Query(list(reversed(rows)))),Preferences(prefs),capacity=capacity,cached=cached)
    a,ac=old.rank_with_cache_info("owner",req);b,bc=new.rank_with_cache_info("owner",req)
    assert signature(a)==signature(b) and ac==bc
    if b.winner:
        assert score_to_json(a.winner.score)==score_to_json(b.winner.score)
        assert score_from_json(score_to_json(b.winner.score))==b.winner.score
    return b,bc


@pytest.mark.parametrize("colour",["blue","red",None,"#234567","#nothex"])
@pytest.mark.parametrize("styles",[("classic",),("sporty",),("classic","vintage"),None,(),("unsupported",)])
@pytest.mark.parametrize("structure",list(STRUCTURES))
def test_every_atomic_field_bound_diagnostic_and_structure(colour,styles,structure):
    rows=([g("d","vest_dress",colour,styles)] if structure.startswith("dress") else
          [g("t","vest",colour,styles),g("b","trousers")])
    if structure.endswith("outerwear"):rows.append(g("o","long_sleeve_outwear","white",None))
    c=candidate(rows);raw=CachedRuleBasedCompatibilityScorer().evaluate(c)
    old=CompatibilityDecisionPolicy.load().apply(raw,structure)
    prepared=PreparedDecisionPolicy(CompatibilityDecisionPolicy.load())
    for _ in range(2):
        new=prepared.apply(raw,structure)
        assert old==new
        if new.decision.pair_count:
            atoms=[x.value for x in new.details if x.name.startswith(("colour:","style:"))]
            L=sum((x for x in atoms if x is not None),F(0))/len(atoms)
            U=L+F(sum(x is None for x in atoms),len(atoms))
            assert (new.decision.lower,new.decision.upper,new.contribution)==(L,U,(L+U)/2)
        else:assert new.contribution==F(1,2) and new.summary.state=="NotApplicable"
    run(rows)


@pytest.mark.parametrize("capacity",[0,1,2,19900])
@pytest.mark.parametrize("cached",[False,True])
def test_mixed_dress_missing_zero_ties_and_pair_eviction(capacity,cached):
    rows=[g("t","vest"),g("b0","trousers","red",("sporty",)),g("b1","shorts",None,None),
          g("b2","skirt","red"),g("d","vest_dress"),g("o","long_sleeve_outwear")]
    result,cache=run(rows,capacity=capacity,cached=cached)
    assert result.scored_count==8 and result.status=="Selected"
    if cached and capacity in (1,2):assert cache.evictions>0


def test_arithmetic_cache_bounded_eviction_and_original_constructor_validation():
    original=CompatibilityDecisionPolicy.load();new=PreparedDecisionPolicy(original,capacity=2)
    # Pure arithmetic stress: exact synthetic atomic values, no garment-quality claim.
    def raw(i):
        a,b=F(0),F(i,301)
        return ComponentScore(ScoreEvidence("compatibility",(a+b)/2,"Available",2,2),
            (ScoreEvidence("colour:a:b",a,"Available",1,1),ScoreEvidence("style:a:b",b,"Available",1,1)))
    for i in (*range(301),0,300,1):assert new.apply(raw(i),"top_bottom")==original.apply(raw(i),"top_bottom")
    assert new.cache_info.currsize==2 and new.cache_info.misses>301
    c=raw(5);new.apply(c,"top_bottom")
    invalid=replace(c,summary=replace(c.summary,value=F(1)))
    with pytest.raises(ValueError):new.apply(invalid,"top_bottom")  # hit still validates actual raw evidence
    with pytest.raises(FrozenInstanceError):new.weights=(F(1),F(0),F(0))
    with pytest.raises(FrozenInstanceError):new.hash="f"*64
    with pytest.raises(ValueError):PreparedDecisionPolicy(replace(original,hash="f"*64))


def test_new_objects_preserve_diagnostics_when_only_numeric_facts_recur():
    policy=PreparedDecisionPolicy(CompatibilityDecisionPolicy.load())
    a=CachedRuleBasedCompatibilityScorer().evaluate(candidate([g("a","vest"),g("b","trousers")]))
    b=CachedRuleBasedCompatibilityScorer().evaluate(candidate([g("c","vest"),g("d","trousers")]))
    x,y=policy.apply(a,"top_bottom"),policy.apply(b,"top_bottom")
    assert policy.cache_info.hits==1 and x.contribution==y.contribution
    assert x.decision.raw==a and y.decision.raw==b and x!=y


def test_original_validation_and_independent_gate_run_for_every_candidate(monkeypatch):
    counts={"decision":0,"score":0,"gate":0}
    for cls,name,key in [(CompatibilityDecision,"__post_init__","decision"),(RecommendationScore,"__post_init__","score"),(ScoringEligibilityGate,"verify","gate")]:
        original=getattr(cls,name)
        def wrap(self,*a,_original=original,_key=key,**kw):
            counts[_key]+=1;return _original(self,*a,**kw)
        monkeypatch.setattr(cls,name,wrap)
    rows=[g("t","vest"),g("b","trousers"),g("d","vest_dress"),g("o","long_sleeve_outwear")]
    result=PreparedDecisionRecommendationScorer(RequestCandidateEngine(Query(rows)),Preferences()).rank("owner",StructuredOutfitRequest())
    assert result.scored_count==4 and counts=={"decision":4,"score":4,"gate":4}


@pytest.mark.parametrize("primary,expected",[(None,"InsufficientEvidence"),("red","NoMatchingCandidates")])
def test_mandatory_unknown_and_fail(primary,expected):
    result,info=run([g("t","vest",primary),g("b","trousers",primary)],StructuredOutfitRequest(colours=("blue",)))
    assert result.status==expected and result.winner is None and info.visits==0


@pytest.mark.parametrize("fields",[{}, {"style":"classic"}, {"colours":("blue",)},
                                   {"style":"classic","colours":("blue",)}])
def test_nonzero_request_and_preferences_preserve_exact_ranking(fields):
    from tests.test_preference_modelling import pref
    rows=[g("t","vest"),g("b","trousers","red",("sporty",)),g("d","vest_dress"),g("o","long_sleeve_outwear","white")]
    result,_=run(rows,StructuredOutfitRequest(**fields),prefs=[pref("styles",["classic"])])
    assert result.status=="Selected" and result.winner.score.preference.contribution>0


def test_parallel_and_user_isolation():
    rows=[g("t","vest"),g("b","trousers"),g("d","vest_dress")]
    scorer=PreparedDecisionRecommendationScorer(RequestCandidateEngine(Query(rows)),Preferences())
    with ThreadPoolExecutor(4) as pool:outcomes=list(pool.map(lambda _:scorer.rank_with_cache_info("owner",StructuredOutfitRequest()),range(8)))
    assert len({a.winner.verified.context_id for a,_ in outcomes})==8
    assert all(signature(a)==signature(outcomes[0][0]) and info.misses==1 for a,info in outcomes)
    result,info=run([replace(g("d","vest_dress"),user_id="other")])
    assert result.winner is None and info.visits==0


@pytest.mark.parametrize("failure",[RuntimeError("late"),KeyboardInterrupt()])
def test_late_failure_and_interruption(failure):
    class Engine:
        def generate_candidates(self,user,request):
            session=RequestCandidateEngine(Query([g("d","vest_dress")])).generate_candidates(user,request)
            original=session.structural_session._candidates
            def broken():
                yield next(original);raise failure
            session.structural_session._candidates=broken();return session
    a=DecisionRecommendationScorer(Engine(),Preferences()).rank("owner",StructuredOutfitRequest())
    b=PreparedDecisionRecommendationScorer(Engine(),Preferences()).rank("owner",StructuredOutfitRequest())
    assert signature(a)==signature(b) and not b.complete and b.winner is None


def test_changed_snapshot_close_failure_policy_unavailable_and_forged_pass(tmp_path):
    from app.domain.value_objects.request_candidate_evaluation import RequestEvaluation
    for variant in ("snapshot","close","forged"):
        class Engine:
            def generate_candidates(self,user,request):
                session=RequestCandidateEngine(Query([g("t","vest"),g("b","trousers")])).generate_candidates(user,request)
                if variant=="snapshot":
                    original=session.structural_session._candidates
                    def changed():
                        yield next(original);yield candidate([g("t","vest","red"),g("b","trousers")])
                    session.structural_session._candidates=changed()
                elif variant=="close":
                    def close():raise RuntimeError("close")
                    session.close=close
                else:session.evaluator.evaluate=lambda *_:RequestEvaluation(())
                return session
        request=StructuredOutfitRequest(colours=("red",)) if variant=="forged" else StructuredOutfitRequest()
        a=DecisionRecommendationScorer(Engine(),Preferences()).rank("owner",request)
        b=PreparedDecisionRecommendationScorer(Engine(),Preferences()).rank("owner",request)
        assert signature(a)==signature(b) and b.winner is None and not b.complete
    path=tmp_path/"invalid.json";path.write_text('{}',encoding="utf-8")
    result=PreparedDecisionRecommendationScorer(RequestCandidateEngine(Query([])),Preferences(),decision_path=path).rank("owner",StructuredOutfitRequest())
    assert result.status=="ProfileUnavailable"


@pytest.mark.parametrize("kind",["dress","complete","partial","unknown","zero"])
def test_disposable_persistence_and_completed_history_restore_identical_decisions(store,kind,monkeypatch):
    import tests.test_compatibility_decision as reference_test
    from app.infrastructure.persistence.chat_history_query_adapter import SqliteChatHistoryQuery
    monkeypatch.setattr(reference_test,"DecisionRecommendationScorer",PreparedDecisionRecommendationScorer)
    reference_test.test_disposable_real_repository_preserves_raw_null_and_exact_replay(store,kind)
    with connect(store[0]) as conn:
        row=conn.execute("SELECT chat_id,id FROM recommendations WHERE recommendation_type='assistant'").fetchone()
    history=SqliteChatHistoryQuery(store[0]).get("owner",row["chat_id"])
    record=store[1].get("owner",row["id"])
    assert history["read_only"] and history["recommendation"]["score_metadata"]==record["score_metadata"]
    score=score_from_json(json.dumps(record["score_metadata"]))
    assert (score.compatibility.summary.value is None)==(kind in ("dress","partial","unknown"))


def test_current_live_service_rejects_direct_or_signature_adapted_activation():
    from types import SimpleNamespace
    from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
    class Interpreter:
        def interpret(self,_):return SimpleNamespace(status="Supported",structured_request=StructuredOutfitRequest())
    class Repository:
        def find_assistant_submission(self,*_):return None
        def persist_assistant(self,*_):raise AssertionError("No unapproved production write")
    engine=RequestCandidateEngine(Query([g("d","vest_dress")]))
    direct=OutfitAssistantService(Interpreter(),engine,Preferences(),Repository(),scorer_factory=PreparedDecisionRecommendationScorer,execution_engine="reference")
    assert direct.recommend("owner","key","Suggest an outfit")["status"]=="ProcessingFailure"
    class SignatureOnlyAdapter:
        def __init__(self,engine,prefs):self.scorer=PreparedDecisionRecommendationScorer(engine,prefs)
        def rank(self,user,request,profile):return self.scorer.rank(user,request)
    adapted=OutfitAssistantService(Interpreter(),engine,Preferences(),Repository(),scorer_factory=SignatureOnlyAdapter,execution_engine="reference")
    assert adapted.recommend("owner","key","Suggest an outfit")["status"]=="ProfileUnavailable"
