"""Differential oracle is the preserved uncached Phase3A code, not a rewritten formula."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace,FrozenInstanceError
from itertools import combinations,product
from fractions import Fraction as F
import pytest
from app.application.recommendation.compatibility_pair_cache import CompatibilityPairCache,MAX_PAIR_CAPACITY
from app.application.recommendation.cached_rule_based_compatibility_scorer import CachedRuleBasedCompatibilityScorer
from app.application.recommendation.cached_rule_based_recommendation_scorer import CachedRuleBasedRecommendationScorer
from app.application.recommendation.rule_based_compatibility_scorer import RuleBasedCompatibilityScorer
from app.application.recommendation.rule_based_recommendation_scorer import RuleBasedRecommendationScorer
from app.application.recommendation.rule_based_compatibility_policy import RuleBasedCompatibilityPolicy
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from tests.test_structural_candidates import Query
from tests.test_rule_based_compatibility import g,candidate,Preferences,COLOURS
from tests.test_recommendation_persistence import store,connect


def signature(outcome):
    w=outcome.winner
    # Only the gate-generated context nonce differs across independent runs.
    winner=(w.verified.evaluated,w.verified.request,w.verified.user_id,w.score) if w else None
    return outcome.status,winner,outcome.complete,outcome.scored_count,outcome.diagnostics


def differential(rows,request=None,capacity=MAX_PAIR_CAPACITY):
    request=request or StructuredOutfitRequest()
    original=RuleBasedRecommendationScorer(RequestCandidateEngine(Query(rows)),Preferences())
    cached=CachedRuleBasedRecommendationScorer(RequestCandidateEngine(Query(list(reversed(rows)))),Preferences(),capacity=capacity)
    a=original.rank("owner",request,"rule_based_request_led")
    b,info=cached.rank_with_cache_info("owner",request,"rule_based_request_led")
    assert signature(a)==signature(b)
    return b,info


@pytest.mark.parametrize("a,b",tuple(product(COLOURS,repeat=2)))
def test_full_colour_truth_table_matches_original(a,b):
    c=candidate([g("t","vest",a),g("b","trousers",b)])
    assert CachedRuleBasedCompatibilityScorer().evaluate(c)==RuleBasedCompatibilityScorer().evaluate(c)


@pytest.mark.parametrize("colour",["gray","navy blue","#fff","#000000","#234567","#broken",None])
@pytest.mark.parametrize("styles",[("classic","minimalist","classic"),None,(),("classic","unknown")])
def test_every_field_and_diagnostic_matches_original(colour,styles):
    rows=[g("t","vest",colour,styles),g("b","trousers",styles=("classic",)),g("o","long_sleeve_outwear",styles=None)]
    old,new=RuleBasedCompatibilityScorer(),CachedRuleBasedCompatibilityScorer()
    session=RequestCandidateEngine(Query(rows)).generate_candidates("owner",StructuredOutfitRequest())
    gate=ScoringEligibilityGate(session,"owner",StructuredOutfitRequest())
    for item in session:
        verified=gate.verify(item)
        assert old.score(verified)==new.score(verified)
    assert session.result.complete
    differential(rows)


def test_four_structures_and_complete_ordered_candidate_stream():
    rows=[g("t","vest"),g("b1","trousers"),g("b2","skirt"),g("d","vest_dress"),g("o","long_sleeve_outwear")]
    request=StructuredOutfitRequest()
    def collect(reverse,cached):
        session=RequestCandidateEngine(Query(list(reversed(rows)) if reverse else rows)).generate_candidates("owner",request)
        gate=ScoringEligibilityGate(session,"owner",request)
        scorer=CachedRuleBasedCompatibilityScorer() if cached else RuleBasedCompatibilityScorer()
        found=[]
        for item in session:
            v=gate.verify(item);found.append((v.candidate,v.evaluated.evaluation,scorer.score(v)))
        return found,session.result
    assert collect(False,False)==collect(True,True)
    result,info=differential(rows)
    assert result.status=="InsufficientEvidence" and result.winner is None
    assert dict(result.diagnostics)["accepted_examined"]=="6"
    assert info.hits>0 and info.misses>0


def test_reverse_order_preserves_labels_and_reasons_without_recalculation():
    scorer=CachedRuleBasedCompatibilityScorer();policy=scorer.policy
    a=scorer.evidence.classify(g("a","vest",styles=("classic","vintage")))
    b=scorer.evidence.classify(g("b","trousers",styles=("classic",)))
    forward=scorer.pair_cache.pair(a,b,"owner",policy)
    reverse=scorer.pair_cache.pair(b,a,"owner",policy)
    again=scorer.pair_cache.pair(b,a,"owner",policy)
    assert forward.style.value==reverse.style.value==F(2,3)
    assert forward.colour.value==reverse.colour.value==1
    assert reverse.colour.name=="colour:b:a"
    assert reverse.colour.reasons==tuple("b:"+x for x in b.reasons)+tuple("a:"+x for x in a.reasons)
    assert reverse is again
    assert scorer.pair_cache.info.visits==3 and scorer.pair_cache.info.hits==2 and scorer.pair_cache.info.misses==1
    with pytest.raises(FrozenInstanceError):forward.colour=reverse.colour
    with pytest.raises(FrozenInstanceError):forward.style.value=F(0)


def test_unknown_zero_malformed_and_no_pair_outputs_unchanged():
    for rows in ([g("d","vest_dress")],[g("t","vest","blue",("classic",)),g("b","trousers","red",("sporty",))],
                 [g("t","vest",styles=None,invalid_attributes=("style_tags",)),g("b","trousers")]):
        differential(rows)
    scorer=CachedRuleBasedCompatibilityScorer()
    c=candidate([g("t","vest",styles=None),g("b","trousers")])
    first=scorer.evaluate(c)
    assert scorer.evaluate(c)==first and first.summary.value is None
    assert scorer.pair_cache.info.hits==1


def test_conflicting_snapshot_policy_owner_and_context_cannot_reuse_cache():
    rows=[g("t","vest"),g("b","trousers")];c=candidate(rows)
    scorer=CachedRuleBasedCompatibilityScorer();scorer.evaluate(c)
    with pytest.raises(ValueError):scorer.evaluate(candidate([replace(rows[0],primary_colour="red"),rows[1]]))
    with pytest.raises(ValueError):scorer.evaluate(candidate([replace(r,user_id="other") for r in rows]))
    scorer.policy=replace(scorer.policy,hash="f"*64)
    with pytest.raises(ValueError,match="policy/owner"):scorer.evaluate(c)
    fresh=CachedRuleBasedCompatibilityScorer(scorer.policy)
    assert fresh.evaluate(c).summary.value==1
    scorer=CachedRuleBasedCompatibilityScorer()
    for index in range(2):
        request=StructuredOutfitRequest();session=RequestCandidateEngine(Query(rows)).generate_candidates("owner",request)
        gate=ScoringEligibilityGate(session,"owner",request);v=gate.verify(next(session))
        if index==0:scorer.score(v)
        else:
            with pytest.raises(ValueError,match="cross scoring sessions"):scorer.score(v)
        session.close()


@pytest.mark.parametrize("capacity",[0,1,2,19900])
def test_eviction_recomputes_exactly_and_preserves_ranking(capacity):
    rows=[g("t","vest"),g("b1","trousers","black"),g("b2","skirt","red",("vintage",)),g("b3","shorts","blue",("classic","vintage")),g("o","long_sleeve_outwear","red",("vintage",))]
    result,info=differential(rows,capacity=capacity)
    assert result.status=="Selected" and info.size<=capacity and info.high_water<=capacity
    if capacity in (1,2):assert info.evictions>0
    old,new=RuleBasedCompatibilityScorer(),CachedRuleBasedCompatibilityScorer(capacity=capacity)
    for index in (1,2,3,1,3,2):
        c=candidate([rows[0],rows[index]])
        assert old.evaluate(c)==new.evaluate(c)


def test_full_19900_capacity_saturation_without_candidate_truncation():
    # Pure pair-cache stress; these are not generated wardrobe outfit candidates.
    scorer=CachedRuleBasedCompatibilityScorer()
    prepared=[scorer.evidence.classify(g(str(i),"vest")) for i in range(201)]
    for a,b in combinations(prepared,2):
        assert scorer.pair_cache.pair(a,b,"owner",scorer.policy).style.value==1
    info=scorer.pair_cache.info
    assert info.visits==20100 and info.misses==20100 and info.size==19900 and info.evictions==200
    scorer.pair_cache.pair(prepared[0],prepared[1],"owner",scorer.policy)
    assert scorer.pair_cache.info.evictions==201


def test_parallel_sessions_and_exact_ties_have_no_shared_cache():
    rows=[g("t","vest"),g("b1","trousers"),g("b2","trousers"),g("o","long_sleeve_outwear")]
    coordinator=CachedRuleBasedRecommendationScorer(RequestCandidateEngine(Query(rows)),Preferences())
    def run(_):return coordinator.rank_with_cache_info("owner",StructuredOutfitRequest(),"rule_based_request_led")
    with ThreadPoolExecutor(4) as pool:outcomes=list(pool.map(run,range(8)))
    assert all(signature(a)==signature(outcomes[0][0]) and info==outcomes[0][1] for a,info in outcomes)
    assert all("b1" in str(a.winner.verified.candidate.key) for a,_ in outcomes)
    assert len({a.winner.verified.context_id for a,_ in outcomes})==8


@pytest.mark.parametrize("failure",[RuntimeError("late"),KeyboardInterrupt()])
def test_late_failure_after_repeated_candidate_has_identical_outcome(failure):
    class Engine:
        def generate_candidates(self,user_id,request):
            session=RequestCandidateEngine(Query([g("t","vest"),g("b","trousers")])).generate_candidates(user_id,request)
            original=session.structural_session._candidates
            def broken():
                first=next(original);yield first;yield first
                raise failure
            session.structural_session._candidates=broken()
            return session
    request=StructuredOutfitRequest()
    old=RuleBasedRecommendationScorer(Engine(),Preferences()).rank("owner",request,"rule_based_request_led")
    new,info=CachedRuleBasedRecommendationScorer(Engine(),Preferences()).rank_with_cache_info("owner",request,"rule_based_request_led")
    assert signature(old)==signature(new) and not new.complete and new.winner is None
    assert info.visits==2 and info.hits==1


def test_close_failure_and_mandatory_filtering_unchanged():
    class Engine:
        def generate_candidates(self,user_id,request):
            session=RequestCandidateEngine(Query([g("t","vest"),g("b","trousers")])).generate_candidates(user_id,request)
            def fail():raise RuntimeError("late close")
            session.close=fail;return session
    request=StructuredOutfitRequest()
    old=RuleBasedRecommendationScorer(Engine(),Preferences()).rank("owner",request,"rule_based_request_led")
    new=CachedRuleBasedRecommendationScorer(Engine(),Preferences()).rank("owner",request,"rule_based_request_led")
    assert signature(old)==signature(new) and new.status=="ProcessingFailure"
    result,info=differential([g("t","vest"),g("b","trousers")],StructuredOutfitRequest(colours=("red",)))
    assert result.status=="NoMatchingCandidates" and info.visits==0
    result,info=differential([replace(g("d","vest_dress"),user_id="other")])
    assert result.status=="NoEligibleGarments" and info.visits==0


@pytest.mark.parametrize("capacity",[-1,19901,True,None])
def test_capacity_is_an_explicit_bound(capacity):
    with pytest.raises(ValueError):CompatibilityPairCache(RuleBasedCompatibilityPolicy.load(),capacity)



def test_repeated_complete_candidate_references_do_not_change_counts():
    class Engine:
        def generate_candidates(self,user_id,request):
            session=RequestCandidateEngine(Query([g("t","vest"),g("b","trousers")])).generate_candidates(user_id,request)
            original=session.structural_session._candidates
            def repeated():
                first=next(original);yield first;yield first;yield first
            session.structural_session._candidates=repeated()
            return session
    req=StructuredOutfitRequest()
    old=RuleBasedRecommendationScorer(Engine(),Preferences()).rank("owner",req,"rule_based_request_led")
    new,info=CachedRuleBasedRecommendationScorer(Engine(),Preferences()).rank_with_cache_info("owner",req,"rule_based_request_led")
    assert signature(old)==signature(new) and new.scored_count==3
    assert info.visits==3 and info.hits==2 and info.misses==1


@pytest.mark.parametrize("mutation",[None,"UPDATE garments SET status='archived' WHERE id='garment'",
    "UPDATE garments SET status='unavailable' WHERE id='garment'",
    "UPDATE processing_items SET review_status='pending' WHERE id='item'",
    "UPDATE processing_items SET review_status='accepted' WHERE id='item'",
    "UPDATE processing_items SET review_status='rejected' WHERE id='item'",
    "UPDATE garments SET processing_item_id=NULL WHERE id='garment'",
    "UPDATE garments SET processing_item_id='missing' WHERE id='garment'",
    "UPDATE garments SET user_id='other' WHERE id='garment'",
    "UPDATE processing_jobs SET user_id='other'",
    "DELETE FROM garments WHERE id='garment'"])
def test_actual_phase1_adapter_eligibility_is_identical(store,mutation):
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    with connect(store[0]) as conn:
        conn.execute("UPDATE garments SET category='vest',primary_colour='blue',style_tags='[\"classic\"]'")
        conn.execute("INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES('bottom-item','job','trousers',1,'media','media','{}','confirmed','now')")
        conn.execute("INSERT INTO garments(id,user_id,processing_item_id,preferred_media_id,name,category,primary_colour,style_tags,attributes_json,created_at,updated_at) VALUES('bottom','owner','bottom-item','media','Bottom','trousers','blue','[\"classic\"]','{}','now','now')")
        if mutation:conn.execute(mutation)
    req=StructuredOutfitRequest()
    old=RuleBasedRecommendationScorer(RequestCandidateEngine(SqliteConfirmedGarmentQuery()),Preferences()).rank("owner",req,"rule_based_request_led")
    new,info=CachedRuleBasedRecommendationScorer(RequestCandidateEngine(SqliteConfirmedGarmentQuery()),Preferences()).rank_with_cache_info("owner",req,"rule_based_request_led")
    assert signature(old)==signature(new)
    if mutation:assert new.winner is None and info.visits==0
    else:assert new.status=="Selected" and info.visits==1


def test_cached_path_still_uses_independent_verifier_and_profile_two():
    from app.domain.value_objects.request_candidate_evaluation import RequestEvaluation
    class Engine:
        def generate_candidates(self,user_id,request):
            session=RequestCandidateEngine(Query([g("t","vest"),g("b","trousers")])).generate_candidates(user_id,request)
            session.evaluator.evaluate=lambda *_:RequestEvaluation(())
            return session
    req=StructuredOutfitRequest(colours=("red",))
    result,info=CachedRuleBasedRecommendationScorer(Engine(),Preferences()).rank_with_cache_info("owner",req,"rule_based_balanced")
    assert result.status=="InvalidScoringInput" and info.visits==0
    rows=[g("t","vest"),g("b1","trousers"),g("b2","shorts","red",("sporty",))]
    from tests.test_preference_modelling import pref
    prefs=[pref("styles",["sporty"])]
    req=StructuredOutfitRequest(style="classic")
    old=RuleBasedRecommendationScorer(RequestCandidateEngine(Query(rows)),Preferences(prefs)).rank("owner",req,"rule_based_balanced")
    new=CachedRuleBasedRecommendationScorer(RequestCandidateEngine(Query(rows)),Preferences(prefs)).rank("owner",req,"rule_based_balanced")
    assert signature(old)==signature(new)



def test_medium_complete_stream_every_candidate_matches_independent_oracle():
    from scripts.audit_compatibility_coverage import synthetic_wardrobe,OfflineQuery
    rows,_=synthetic_wardrobe(100,varied=True)
    request=StructuredOutfitRequest()
    session=RequestCandidateEngine(OfflineQuery(rows)).generate_candidates("synthetic-owner",request)
    gate=ScoringEligibilityGate(session,"synthetic-owner",request)
    original,cached=RuleBasedCompatibilityScorer(),CachedRuleBasedCompatibilityScorer()
    count=0
    for item in session:
        verified=gate.verify(item)
        assert original.score(verified)==cached.score(verified)
        count+=1
    assert session.result.complete and count==17710
    assert cached.pair_cache.info.visits==49700
    assert cached.pair_cache.info.misses==2500 and cached.pair_cache.info.hits==47200
