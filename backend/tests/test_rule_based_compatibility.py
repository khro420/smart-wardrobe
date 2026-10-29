"""Synthetic arithmetic fixtures only; no human fashion-quality validation."""
from dataclasses import replace,FrozenInstanceError
from fractions import Fraction as F
from itertools import combinations,product
import json
import random
import pytest
from app.application.recommendation.rule_based_compatibility_policy import RuleBasedCompatibilityPolicy,RuleBasedScoringProfile,RULES,PROFILES
from app.application.recommendation.rule_based_compatibility_scorer import RuleBasedCompatibilityScorer
from app.application.recommendation.rule_based_compatibility_evidence import RuleBasedCompatibilityEvidence
from app.application.recommendation.rule_based_recommendation_scorer import RuleBasedRecommendationScorer
from app.application.recommendation.recommendation_scorer import RecommendationScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.recommendation_engine import RecommendationEngine
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest,GarmentCategoryConstraint
from app.domain.value_objects.rule_based_compatibility import PreparedCompatibilityEvidence
from tests.test_structural_candidates import garment,Query
from tests.test_recommendation_scoring import verified
from tests.test_preference_modelling import pref
from tests.test_recommendation_persistence import store

COLOURS=("black","white","grey","navy","blue","red","green","yellow","orange","pink","purple","brown","beige","cream")


def g(identifier,category,colour="blue",styles=("classic",),**kwargs):
    return replace(garment(identifier,category),primary_colour=colour,style_tags=styles,**kwargs)


def candidate(rows):
    return max(RecommendationEngine(Query(rows)).generate_homepage_candidates("owner"),key=lambda c:len(c.members))


class Preferences:
    def __init__(self,rows=()):self.rows=rows
    def get_active_preferences(self,user_id):return self.rows


def rank(rows,request=None,preferences=(),profile="rule_based_request_led",engine=None):
    return RuleBasedRecommendationScorer(engine or RequestCandidateEngine(Query(rows)),Preferences(preferences)).rank("owner",request or StructuredOutfitRequest(),profile)


@pytest.mark.parametrize("a,b",tuple(product(COLOURS,repeat=2)))
def test_all_fourteen_colour_truth_table(a,b):
    score=RuleBasedCompatibilityScorer().evaluate(candidate([g("t","vest",a),g("b","trousers",b)]))
    expected=F(int(a==b or a in {"black","white","grey"} or b in {"black","white","grey"}))
    assert score.details[0].value==expected
    assert score.summary.value==(expected+1)/2


@pytest.mark.parametrize("primary,expected",[(" Gray ","grey"),("navy blue","navy"),("#000","black"),("#FFFFFF","white"),("#a52a2a","brown"),("#234567",None),("#gggggg",None),(None,None),("",None)])
def test_primary_aliases_anchors_and_unknown(primary,expected):
    row=g("t","vest",primary,secondary_colour="black")
    assert RuleBasedCompatibilityEvidence().classify(row).colour==expected


def test_current_primary_precedence_over_palette_and_secondary():
    from app.shared_contracts.confirmed_garment_snapshot import GarmentPaletteEntry
    score=RuleBasedCompatibilityScorer().evaluate(candidate([g("t","vest","red",secondary_colour="black",colour_palette=(GarmentPaletteEntry("#000000"),)),g("b","trousers","blue")]))
    assert score.details[0].value==0


@pytest.mark.parametrize("styles,state",[(None,"Missing"),((),"Empty"),(("classic","unsupported"),"Unrecognized"),(("",),"Unrecognized")])
def test_incomplete_styles_are_not_repaired(styles,state):
    row=g("t","vest",styles=styles)
    mapper=RuleBasedCompatibilityEvidence();evidence=mapper.classify(row)
    assert evidence.style_state==state
    score=RuleBasedCompatibilityScorer().evaluate(candidate([row,g("b","trousers")]))
    assert score.summary.state=="Unknown" and score.summary.value is None
    assert score.summary.observed==1 and score.summary.possible==2
    if styles and "unsupported" in styles:assert "unsupported_style:unsupported" in evidence.reasons


def test_malformed_style_zero_and_single_dress_are_distinct():
    malformed=g("t","vest",styles=None,invalid_attributes=("style_tags",))
    assert RuleBasedCompatibilityEvidence().classify(malformed).style_state=="Malformed"
    zero=RuleBasedCompatibilityScorer().evaluate(candidate([g("t","vest","blue",("classic",)),g("b","trousers","red",("sporty",))]))
    assert zero.summary.state=="Available" and zero.summary.value==0
    dress=RuleBasedCompatibilityScorer().evaluate(candidate([g("d","vest_dress")]))
    assert dress.summary.value is None and dress.summary.state=="Unknown"
    assert all(x.state=="NotApplicable" for x in dress.details)
    assert dress.summary.possible==0


def test_dice_canonical_set_normalization_and_pattern_disabled():
    rows=[g("t","vest",styles=("minimalist","classic","classic")),g("b","trousers",styles=("minimal",))]
    scorer=RuleBasedCompatibilityScorer();c=scorer.evaluate(candidate(rows))
    assert c.details[1].value==F(2,3) and c.summary.value==F(5,6)
    assert RuleBasedCompatibilityScorer().evaluate(candidate([replace(x,pattern="unknown print") for x in reversed(rows)]))==c
    assert scorer.evidence.cache_size==2


@pytest.mark.parametrize("categories,expected,pairs",[(("vest","trousers"),F(1),1),(("vest","trousers","long_sleeve_outwear"),F(1),3),(("vest_dress",),None,0),(("vest_dress","long_sleeve_outwear"),F(1),1)])
def test_all_four_structures(categories,expected,pairs):
    c=RuleBasedCompatibilityScorer().evaluate(candidate([g(str(i),cat) for i,cat in enumerate(categories)]))
    assert c.summary.value==expected and c.summary.possible==pairs*2


def test_no_available_relationship_averaging():
    rows=[g("t","vest"),g("b","trousers"),g("o","long_sleeve_outwear",styles=None)]
    c=RuleBasedCompatibilityScorer().evaluate(candidate(rows))
    assert c.summary.value is None and c.summary.observed==4 and c.summary.possible==6
    assert c.details[0].value==1 and c.details[1].value is None


def test_mutable_inputs_frozen_evidence_and_session_snapshot_conflicts():
    styles=["classic"];reasons=["synthetic"]
    e=PreparedCompatibilityEvidence("x","blue","Known",styles,"Known",reasons)
    styles.append("sporty");reasons.clear()
    assert e.styles==frozenset(("classic",)) and e.reasons==("synthetic",)
    with pytest.raises(FrozenInstanceError):e.colour="red"
    with pytest.raises(AttributeError):e.styles.add("vintage")
    mapper=RuleBasedCompatibilityEvidence();row=g("x","vest");mapper.classify(row)
    with pytest.raises(ValueError,match="Conflicting"):mapper.classify(replace(row,primary_colour="red"))
    assert RuleBasedCompatibilityEvidence().classify(replace(row,primary_colour="red")).colour=="red"


def test_unknown_does_not_become_weighted_zero_and_consumes_full_stream():
    rows=[g("t","vest"),g("b","trousers"),g("d","vest_dress"),g("o","long_sleeve_outwear")]
    result=rank(rows)
    assert result.status=="InsufficientEvidence" and result.complete and result.winner is None
    d=dict(result.diagnostics)
    assert d["accepted_examined"]=="4" and d["compatibility_unknown"]=="1"
    assert result.scored_count==3 and d["reason"]=="compatibility_evidence_incomplete"
    normal=RecommendationScorer(RequestCandidateEngine(Query(rows)),Preferences()).rank("owner",StructuredOutfitRequest(),"compatibility_deferred")
    assert normal.status=="Selected"  # The live/deferred path still accepts dresses.


@pytest.mark.parametrize("profile,expected",[("rule_based_request_led",F(29,30)),("rule_based_balanced",F(19,20))])
def test_experimental_exact_weighted_total(profile,expected):
    rows=[g("t","vest",styles=("classic",)),g("b","trousers",styles=("classic","vintage"))]
    result=rank(rows,StructuredOutfitRequest(style="classic"),[pref("styles",["classic"])],profile)
    assert result.status=="Selected"
    score=result.winner.score
    assert score.request_match.summary.value==1 and score.compatibility.summary.value==F(5,6) and score.preference.summary.value==1
    assert expected==sum(w*v for w,v in zip(score.weights,(F(1),F(5,6),F(1))))
    assert score.total==expected and all(type(x) is F for x in score.weights)
    assert 0<=score.total<=1


def test_determinism_and_generic_request_does_not_invent_R_P():
    rows=[g("t","vest"),g("b1","trousers"),g("b2","trousers")]
    a,b=rank(rows),rank(list(reversed(rows)))
    assert a.winner.verified.candidate.key==b.winner.verified.candidate.key
    assert "b1" in str(a.winner.verified.candidate.key)
    assert a.winner.score.total==F(1,5)
    assert a.winner.score.request_match.summary.state=="NotApplicable"
    assert a.winner.score.preference.summary.state=="NoPreferences"


def test_C_request_and_preference_independence_and_mandatory_rejection():
    rows=[g("t","vest"),g("b","trousers")]
    generic=rank(rows);specific=rank(rows,StructuredOutfitRequest(style="classic"),[pref("colours",["blue"])])
    assert generic.winner.score.compatibility==specific.winner.score.compatibility
    assert rank(rows,StructuredOutfitRequest(colours=("red",))).status=="NoMatchingCandidates"
    assert rank(rows,StructuredOutfitRequest(occasion="campus")).status=="PolicyUnavailable"
    assert rank([replace(x,user_id="other") for x in rows]).status=="NoEligibleGarments"
    with pytest.raises(ValueError):RuleBasedCompatibilityScorer().score(candidate(rows))


def test_invalid_unavailable_policies_and_defaults(tmp_path):
    assert RuleBasedCompatibilityPolicy.load().achromatic==frozenset(("black","white","grey"))
    with pytest.raises(FrozenInstanceError):RuleBasedCompatibilityPolicy.load().version="changed"
    for name in ("rule_based_request_led","rule_based_balanced"):
        assert sum(RuleBasedScoringProfile.load(name).weights)==1
    for key,value in (("default_activation",True),("pattern_enabled",True),("approximate_hex_enabled",True),("internal_weights",["1","0"])):
        raw=json.loads(RULES.read_text(encoding="utf-8"));raw[key]=value
        path=tmp_path/'invalid.json';path.write_text(json.dumps(raw),encoding="utf-8")
        with pytest.raises(ValueError):RuleBasedCompatibilityPolicy.load(path)
    scorer=RuleBasedRecommendationScorer(RequestCandidateEngine(Query([])),Preferences(),policy_path=tmp_path/'missing.json')
    assert scorer.rank("owner",StructuredOutfitRequest(),"rule_based_request_led").status=="ProfileUnavailable"


def test_independent_reference_randomized_exhaustive_pairs():
    rng=random.Random(431)
    for _ in range(80):
        categories=rng.choice((("vest","trousers"),("vest","trousers","long_sleeve_outwear"),("vest_dress","long_sleeve_outwear")))
        rows=[g(str(i),cat,rng.choice(COLOURS),tuple(rng.sample(("classic","sporty","vintage"),rng.randint(1,3)))) for i,cat in enumerate(categories)]
        a=sum(F(int(x.primary_colour==y.primary_colour or bool({x.primary_colour,y.primary_colour}&{"black","white","grey"}))) for x,y in combinations(rows,2))
        b=sum(F(2*len(set(x.style_tags)&set(y.style_tags)),len(set(x.style_tags))+len(set(y.style_tags))) for x,y in combinations(rows,2))
        expected=(a+b)/(2*len(list(combinations(rows,2))))
        actual=RuleBasedCompatibilityScorer().evaluate(candidate(rows))
        assert actual.summary.value==expected


@pytest.mark.parametrize("failure,status",[(RuntimeError("late"),"ProcessingFailure"),(KeyboardInterrupt(),"Interrupted")])
def test_late_stream_failure_after_incumbent_never_selects(failure,status):
    class Engine:
        def generate_candidates(self,user_id,request):
            session=RequestCandidateEngine(Query([g("t","vest"),g("b","trousers")])).generate_candidates(user_id,request)
            original=session.structural_session._candidates
            def broken():
                yield next(original)
                raise failure
            session.structural_session._candidates=broken()
            return session
    result=rank([],engine=Engine())
    assert result.status==status and not result.complete and result.winner is None and result.scored_count==1


def test_late_close_failure_does_not_certify_success():
    class Engine:
        def generate_candidates(self,user_id,request):
            session=RequestCandidateEngine(Query([g("t","vest"),g("b","trousers")])).generate_candidates(user_id,request)
            def broken():raise RuntimeError("late close failure")
            session.close=broken
            return session
    result=rank([],engine=Engine())
    assert result.status=="ProcessingFailure" and not result.complete and result.winner is None


def test_actual_phase1_query_excludes_nonconfirmed_and_missing_links(store):
    from tests.test_recommendation_persistence import connect
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    path,_,_=store
    with connect(path) as conn:
        conn.execute("UPDATE garments SET primary_colour='blue',style_tags='[\"classic\"]'")
    query=SqliteConfirmedGarmentQuery()
    # Actual eligible dress is retrieved but remains non-numeric for pairwise C.
    assert RuleBasedRecommendationScorer(RequestCandidateEngine(query),Preferences()).rank("owner",StructuredOutfitRequest(),"rule_based_request_led").status=="InsufficientEvidence"
    for mutation in ("UPDATE processing_items SET review_status='accepted'","UPDATE processing_items SET review_status='pending'","UPDATE processing_items SET review_status='rejected'","UPDATE garments SET processing_item_id=NULL"):
        with connect(path) as conn:conn.execute(mutation)
        result=RuleBasedRecommendationScorer(RequestCandidateEngine(query),Preferences()).rank("owner",StructuredOutfitRequest(),"rule_based_request_led")
        assert result.status=="NoEligibleGarments"


def test_primary_fallback_projection_and_style_malformed_json(store):
    from tests.test_recommendation_persistence import connect
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    with connect(store[0]) as conn:
        conn.execute("UPDATE garments SET primary_colour=NULL,attributes_json=?,style_tags=?",(json.dumps({"primary_color":"navy blue","style":["classic"]}),"not-json"))
    row=SqliteConfirmedGarmentQuery().get_confirmed_available_garments("owner")[0]
    evidence=RuleBasedCompatibilityEvidence().classify(row)
    assert evidence.colour=="navy" and evidence.style_state=="Malformed"
    with connect(store[0]) as conn:conn.execute("UPDATE garments SET primary_colour='red'")
    changed=SqliteConfirmedGarmentQuery().get_confirmed_available_garments("owner")[0]
    assert RuleBasedCompatibilityEvidence().classify(changed).colour=="red"


@pytest.mark.parametrize("profile",["rule_based_request_led","rule_based_balanced"])
def test_full_stream_matches_independent_reference_and_tie_order(profile):
    rows=[g("t"+str(i),"vest",COLOURS[i+3],("classic",) if i%2 else ("classic","vintage")) for i in range(3)]
    rows += [g("b"+str(i),"trousers",COLOURS[i],("vintage",)) for i in range(3)]
    rows += [g("o"+str(i),"long_sleeve_outwear",COLOURS[i+6],("sporty",)) for i in range(2)]
    expected=[]
    for c in RecommendationEngine(Query(rows)).generate_homepage_candidates("owner"):
        pairs=list(combinations([m.garment for m in c.members],2))
        colour=sum(int(a.primary_colour==b.primary_colour or a.primary_colour in ("black","white","grey") or b.primary_colour in ("black","white","grey")) for a,b in pairs)
        style=sum((F(2*len(set(a.style_tags)&set(b.style_tags)),len(set(a.style_tags))+len(set(b.style_tags))) for a,b in pairs),F(0))
        value=(colour+style)/(2*len(pairs))
        expected.append((value,c.key))
    winner=sorted(expected,key=lambda x:(-x[0],x[1]))[0]
    result=rank(rows,profile=profile)
    assert result.status=="Selected" and result.scored_count==27
    assert result.winner.verified.candidate.key==winner[1]
    assert result.winner.score.compatibility.summary.value==winner[0]
    assert result.winner.score.total==RuleBasedScoringProfile.load(profile).weights[1]*winner[0]


def test_gate_independently_rejects_fabricated_mandatory_pass_and_foreign_candidate():
    from app.domain.value_objects.request_candidate_evaluation import RequestEvaluation
    class FabricatedPass:
        def generate_candidates(self,user_id,request):
            session=RequestCandidateEngine(Query([g("t","vest"),g("b","trousers")])).generate_candidates(user_id,request)
            session.evaluator.evaluate=lambda *_:RequestEvaluation(())
            return session
    result=rank([],StructuredOutfitRequest(colours=("red",)),engine=FabricatedPass())
    assert result.status=="InvalidScoringInput" and result.winner is None
    class Foreign:
        def generate_candidates(self,user_id,request):
            session=RequestCandidateEngine(Query([g("t","vest"),g("b","trousers")])).generate_candidates(user_id,request)
            foreign=[replace(g("t","vest"),user_id="other"),replace(g("b","trousers"),user_id="other")]
            foreign_candidate=max(RecommendationEngine(Query(foreign)).generate_homepage_candidates("other"),key=lambda c:len(c.members))
            session.structural_session._candidates=iter((foreign_candidate,))
            return session
    assert rank([],engine=Foreign()).status=="InvalidScoringInput"


def test_offline_coverage_and_weight_sensitivity_are_explicitly_synthetic():
    from scripts.evaluate_rule_based_compatibility import coverage_examples,weight_sensitivity
    report=coverage_examples()
    assert report["total_sessions"]==12 and report["blocked_sessions"]==8
    assert report["coverage_by_structure"]["dress"]["available"]==0
    assert report["coverage_by_structure"]["dress"]["no_pairs"]>0
    sensitivity=weight_sensitivity()
    assert "red-bottom" in str(sensitivity["rule_based_request_led"]["winner"])
    assert "black-bottom" in str(sensitivity["rule_based_balanced"]["winner"])
    assert sensitivity["rule_based_request_led"]["total"]=={"numerator":11,"denominator":50}
    assert sensitivity["rule_based_balanced"]["total"]=={"numerator":3,"denominator":10}



def test_measured_zero_is_rankable_and_unknown_profile_is_not():
    rows=[g("t","vest","blue",("classic",)),g("b","trousers","red",("sporty",))]
    result=rank(rows)
    assert result.status=="Selected" and result.winner.score.compatibility.summary.value==F(0)
    assert result.winner.score.total==F(0)
    assert rank(rows,profile="not-approved").status=="ProfileUnavailable"
    assert rank(rows,preferences=[pref(user="other")]).status=="InvalidPreferenceData"


def test_duplicate_policy_keys_and_profile_weight_changes_rejected(tmp_path):
    duplicate=tmp_path/"duplicate.json";duplicate.write_text('{"version":"one","version":"two"}',encoding="utf-8")
    with pytest.raises(ValueError,match="Duplicate"):RuleBasedCompatibilityPolicy.load(duplicate)
    raw=json.loads(PROFILES.read_text(encoding="utf-8"));raw["profiles"]["rule_based_request_led"]=["0.5","0.5","0"]
    invalid=tmp_path/"weights.json";invalid.write_text(json.dumps(raw),encoding="utf-8")
    with pytest.raises(ValueError):RuleBasedScoringProfile.load("rule_based_request_led",invalid)
