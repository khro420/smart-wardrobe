"""Synthetic offline fixtures; no independent fashion ratings are claimed."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace, FrozenInstanceError
from fractions import Fraction as F
import json
import pytest
from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
from app.application.recommendation.decision_recommendation_scorer import DecisionRecommendationScorer
from app.application.recommendation.decision_score_codec import score_from_json, score_to_json
from app.application.recommendation.rule_based_compatibility_scorer import RuleBasedCompatibilityScorer
from app.application.recommendation.cached_rule_based_compatibility_scorer import CachedRuleBasedCompatibilityScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
from app.domain.value_objects.recommendation_score import ComponentScore, RecommendationScore
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.domain.value_objects.compatibility_signature import STRUCTURES
from tests.test_rule_based_compatibility import g, candidate, Preferences
from tests.test_structural_candidates import Query
from tests.test_compatibility_pair_cache import signature
from tests.test_recommendation_persistence import store, connect


def rank(rows, request=None, prefs=(), cached=True, capacity=19900):
    return DecisionRecommendationScorer(RequestCandidateEngine(Query(rows)), Preferences(prefs),
                                        cached=cached, capacity=capacity).rank_with_cache_info("owner", request or StructuredOutfitRequest())


def decision(rows, cached=True, capacity=19900):
    raw = (CachedRuleBasedCompatibilityScorer(capacity=capacity) if cached else RuleBasedCompatibilityScorer()).evaluate(candidate(rows))
    structure = next(k for k, roles in STRUCTURES.items() if roles == tuple(m.role for m in candidate(rows).members))
    return CompatibilityDecisionPolicy.load().apply(raw, structure)


@pytest.mark.parametrize("colour", ["blue", "red", None, "#nothex", "#234567"])
@pytest.mark.parametrize("styles", [("classic",), ("sporty",), ("classic", "vintage"), None, (), ("unsupported",)])
@pytest.mark.parametrize("outer", [False, True])
def test_atomic_bounds_against_independent_arithmetic(colour, styles, outer):
    rows = [g("t", "vest", colour, styles), g("b", "trousers")]
    if outer: rows.append(g("o", "long_sleeve_outwear", "white", ("vintage",)))
    c = decision(rows)
    assert c == decision(rows, cached=False)
    atoms = [x for x in c.details if x.name.startswith(("colour:", "style:"))]
    known = [x.value for x in atoms if x.value is not None]
    lower = sum(known, F(0))/len(atoms)
    upper = lower+F(len(atoms)-len(known), len(atoms))
    assert c.decision.lower == lower and c.decision.upper == upper
    assert c.contribution == (lower+upper)/2
    assert c.decision.known_count == len(known)
    if len(known) == len(atoms): assert c.summary.value == c.contribution
    else: assert c.summary.value is None and c.summary.state == "Unknown"


def test_zero_unknown_no_pair_and_exact_weighted_arithmetic():
    zero = decision([g("t", "vest", "blue", ("classic",)), g("b", "trousers", "red", ("sporty",))])
    unknown = decision([g("t", "vest", None, None), g("b", "trousers", None, None)])
    dress = decision([g("d", "vest_dress")])
    assert zero.summary.value == zero.contribution == 0 and zero.decision.basis == "Computed"
    assert unknown.summary.value is None and unknown.contribution == F(1, 2)
    assert unknown.decision.basis == "FullyConventional" and (unknown.decision.lower, unknown.decision.upper) == (0, 1)
    assert dress.summary.state == "NotApplicable" and dress.contribution == F(1, 2)
    assert dress.decision.pair_count == dress.decision.atomic_count == 0
    assert dress.decision.lower is dress.decision.upper is None
    # Generic request / NoPreferences stay zero numerical contribution.
    result, _ = rank([g("d", "vest_dress")])
    score = result.winner.score
    assert score.total == F(1, 10)
    assert score.weights == (F(3, 5), F(1, 5), F(1, 5))
    assert score.request_match.contribution == score.preference.contribution == 0
    assert score.preference.summary.state == "NoPreferences"
    assert ComponentScore(unknown.summary, unknown.details).contribution == 0  # legacy unchanged
    with pytest.raises(FrozenInstanceError): dress.decision.value = F(1)
    with pytest.raises(FrozenInstanceError): dress.summary = zero.summary
    with pytest.raises(ValueError): replace(dress.decision, value=F(1))
    with pytest.raises(ValueError): replace(unknown.decision, known_count=1)
    with pytest.raises(ValueError): replace(score, total=F(0))
    with pytest.raises(ValueError):
        replace(dress.decision, raw=ComponentScore(replace(dress.summary, possible=1), dress.details))


@pytest.mark.parametrize("structure", list(STRUCTURES))
def test_every_structure_can_win_and_replay(structure):
    rows = [g("d", "vest_dress")] if structure.startswith("dress") else [g("t", "vest"), g("b", "trousers")]
    if structure.endswith("outerwear"): rows.append(g("o", "long_sleeve_outwear"))
    result, _ = rank(rows)
    assert result.complete and result.status == "Selected"
    # Layered wardrobes also generate the unlayered base; use direct measurement
    # for structure identity, and require stable ranking to consider every candidate.
    assert decision(rows).decision.structure == structure
    assert result.scored_count == (2 if structure.endswith("outerwear") else 1)
    assert score_from_json(score_to_json(result.winner.score)) == result.winner.score


@pytest.mark.parametrize("capacity", [0, 1, 2, 19900])
def test_complete_stream_cached_uncached_equivalence_with_unknowns(capacity):
    rows = [g("t", "vest"), g("b1", "trousers", "red", ("sporty",)),
            g("b2", "shorts", None, None), g("d", "vest_dress"), g("o", "long_sleeve_outwear")]
    old, _ = rank(rows, cached=False)
    new, info = rank(list(reversed(rows)), capacity=capacity)
    assert signature(old) == signature(new)
    assert new.status == "Selected" and new.scored_count == 6
    assert dict(new.diagnostics)["accepted_examined"] == "6"
    assert info.high_water <= capacity
    if capacity in (1, 2): assert info.evictions > 0


def test_dress_can_beat_zero_and_lose_to_one_without_coverage_tiebreak():
    dress = g("d", "vest_dress")
    low, _ = rank([g("t", "vest"), g("b", "trousers", "red", ("sporty",)), dress])
    high, _ = rank([g("t", "vest"), g("b", "trousers"), dress])
    assert low.winner.score.compatibility.decision.structure == "dress"
    assert high.winner.score.compatibility.decision.structure == "top_bottom"
    assert low.scored_count == high.scored_count == 2
    # Measured .5 and no-pair .5 are tied; stable key, not coverage, decides.
    tied, _ = rank([g("t", "vest"), g("b", "trousers", "red"), dress])
    assert tied.winner.verified.candidate.key == min(candidate([dress]).key, candidate([g("t", "vest"), g("b", "trousers", "red")]).key)


def test_annotation_removal_and_request_preference_independence():
    top, bottom = g("t", "vest"), g("b", "trousers", "red", ("sporty",))
    before, after = decision([top, bottom]), decision([replace(top, style_tags=None), bottom])
    assert before.contribution == 0 and after.contribution == F(1, 4)
    assert after.summary.value is None  # missing annotation can improve midpoint; limitation explicit
    from tests.test_preference_modelling import pref
    a, _ = rank([top, bottom])
    b, _ = rank([top, bottom], StructuredOutfitRequest(style="classic"), [pref("styles", ["classic"])])
    assert a.winner.score.compatibility == b.winner.score.compatibility
    assert a.winner.score.total != b.winner.score.total


@pytest.mark.parametrize("primary,expected", [(None, "InsufficientEvidence"), ("red", "NoMatchingCandidates")])
def test_mandatory_unknown_and_fail_never_gain_conventional_pass(primary, expected):
    result, info = rank([g("t", "vest", primary), g("b", "trousers", primary)], StructuredOutfitRequest(colours=("blue",)))
    assert result.status == expected and result.winner is None and result.scored_count == info.visits == 0


@pytest.mark.parametrize("failure", [RuntimeError("late"), KeyboardInterrupt()])
def test_failed_or_interrupted_stream_never_publishes_winner(failure):
    class Engine:
        def generate_candidates(self, user_id, request):
            session = RequestCandidateEngine(Query([g("d", "vest_dress")])).generate_candidates(user_id, request)
            original = session.structural_session._candidates
            def broken():
                yield next(original)
                raise failure
            session.structural_session._candidates = broken()
            return session
    for cached in (True, False):
        result = DecisionRecommendationScorer(Engine(), Preferences(), cached=cached).rank("owner", StructuredOutfitRequest())
        assert not result.complete and result.winner is None and result.scored_count == 1
        assert result.status in ("ProcessingFailure", "Interrupted")


def test_parallel_sessions_do_not_share_cache_or_gate_context():
    scorer = DecisionRecommendationScorer(RequestCandidateEngine(Query([g("t", "vest"), g("b", "trousers")])), Preferences())
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _: scorer.rank_with_cache_info("owner", StructuredOutfitRequest()), range(8)))
    assert len({x.winner.verified.context_id for x, _ in results}) == 8
    assert all(info.misses == 1 and info.hits == 0 for _, info in results)
    foreign, info = rank([replace(g("d", "vest_dress"), user_id="other")])
    assert foreign.status == "NoEligibleGarments" and info.visits == 0


def test_policy_failure_and_metadata_tampering(tmp_path):
    from app.application.recommendation.compatibility_decision_policy import EXPECTED
    path = tmp_path/"policy.json"
    path.write_text(json.dumps({**EXPECTED, "default_activation": True}), encoding="utf-8")
    with pytest.raises(ValueError): CompatibilityDecisionPolicy.load(path)
    result = DecisionRecommendationScorer(RequestCandidateEngine(Query([])), Preferences(), decision_path=path).rank("owner", StructuredOutfitRequest())
    assert result.status == "ProfileUnavailable"
    good, _ = rank([g("d", "vest_dress")])
    raw = json.loads(score_to_json(good.winner.score))
    for field, value in [("adapter_version", "legacy"), ("summary", {**raw["compatibility"]["summary"], "value": {"numerator": 1, "denominator": 2}})]:
        broken = {**raw, "compatibility": {**raw["compatibility"], field: value}}
        with pytest.raises(ValueError): score_from_json(json.dumps(broken))


def test_outerwear_can_win_and_missing_empty_malformed_remain_distinct():
    layered, _ = rank([g("t", "vest"), g("b", "trousers", "red", ("sporty",)),
                       g("o", "long_sleeve_outwear", "white", ("classic",))])
    assert layered.winner.score.compatibility.decision.structure == "top_bottom_outerwear"
    dress, _ = rank([g("d", "vest_dress"), g("o", "long_sleeve_outwear")])
    assert dress.winner.score.compatibility.decision.structure == "dress_outerwear"
    results = []
    for tags, invalid in [(None, ()), ((), ()), (None, ("style_tags",))]:
        c = decision([g("t", "vest", styles=tags, invalid_attributes=invalid), g("b", "trousers")])
        results.append(c)
        assert c.summary.value is None and c.decision.basis == "PartiallyConventional"
    assert len({x.decision for x in results}) == 3
    assert len({x.contribution for x in results}) == 1


def test_independent_gate_still_rejects_forged_pass_and_changed_snapshot():
    from app.domain.value_objects.request_candidate_evaluation import RequestEvaluation
    class Engine:
        def generate_candidates(self, user_id, request):
            session = RequestCandidateEngine(Query([g("t", "vest"), g("b", "trousers")])).generate_candidates(user_id, request)
            session.evaluator.evaluate = lambda *_: RequestEvaluation(())
            return session
    result = DecisionRecommendationScorer(Engine(), Preferences()).rank("owner", StructuredOutfitRequest(colours=("red",)))
    assert result.status == "InvalidScoringInput" and not result.complete and result.winner is None
    for cached in (True, False):
        class Conflicting:
            def generate_candidates(self, user_id, request):
                session = RequestCandidateEngine(Query([g("t", "vest"), g("b", "trousers")])).generate_candidates(user_id, request)
                original = session.structural_session._candidates
                def conflicting():
                    yield next(original)
                    yield candidate([g("t", "vest", "red"), g("b", "trousers")])
                session.structural_session._candidates = conflicting()
                return session
        result = DecisionRecommendationScorer(Conflicting(), Preferences(), cached=cached).rank("owner", StructuredOutfitRequest())
        assert result.status == "ProcessingFailure" and not result.complete and result.winner is None


def test_late_close_failure_never_publishes_and_policy_never_bypasses_availability():
    class Engine:
        def generate_candidates(self, user_id, request):
            session = RequestCandidateEngine(Query([g("d", "vest_dress")])).generate_candidates(user_id, request)
            def close(): raise RuntimeError("late close")
            session.close = close
            return session
    result = DecisionRecommendationScorer(Engine(), Preferences()).rank("owner", StructuredOutfitRequest())
    assert result.status == "ProcessingFailure" and result.winner is None and not result.complete
    result, _ = rank([replace(g("d", "vest_dress"), status="unavailable")])
    assert result.winner is None


@pytest.mark.parametrize("kind", ["dress", "complete", "partial", "unknown", "zero"])
def test_disposable_real_repository_preserves_raw_null_and_exact_replay(store, kind):
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    path, repository, command = store
    if kind != "dress":
        colour = None if kind == "unknown" else "blue"
        styles = None if kind in ("partial", "unknown") else '["classic"]'
        with connect(path) as conn:
            conn.execute("UPDATE garments SET category='vest',primary_colour=?,style_tags=?", (colour, styles))
            conn.execute("INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES('bitem','job','trousers',1,'media','media','{}','confirmed','now')")
            conn.execute("INSERT INTO garments(id,user_id,processing_item_id,preferred_media_id,name,category,primary_colour,style_tags,attributes_json,created_at,updated_at) VALUES('b','owner','bitem','media','Bottom','trousers',?,?,'{}','now','now')", ("red" if kind == "zero" else colour, '["sporty"]' if kind == "zero" else styles))
    scorer = DecisionRecommendationScorer(RequestCandidateEngine(SqliteConfirmedGarmentQuery()), Preferences())
    outcome = scorer.rank("owner", StructuredOutfitRequest())
    assert outcome.status == "Selected"
    score = outcome.winner.score
    written = repository.persist(replace(command, operation="assistant", request_text="Suggest an outfit", score=score,
                                        candidate=outcome.winner.verified.candidate,
                                        provenance_json=json.dumps({"experimental": True, "decision_policy": score.compatibility.decision.policy_hash})))
    assert (written["compatibility_score"] is None) == (kind in ("dress", "partial", "unknown"))
    if kind == "zero": assert written["compatibility_score"] == 0
    replay = score_from_json(json.dumps(written["score_metadata"]))
    assert replay == score
    assert replay.total == F(3, 5)*replay.request_match.contribution+F(1, 5)*replay.compatibility.decision.value+F(1, 5)*replay.preference.contribution
    assert repository.get("owner", written["id"])["score_metadata"] == written["score_metadata"]


@pytest.mark.parametrize("sql", [
    "UPDATE garments SET status='archived'",
    "UPDATE garments SET status='unavailable'",
    "UPDATE garments SET user_id='other'",
    "UPDATE processing_jobs SET user_id='other'",
    "UPDATE processing_items SET review_status='pending'",
    "UPDATE processing_items SET review_status='accepted'",
    "UPDATE processing_items SET review_status='rejected'",
    "UPDATE garments SET processing_item_id=NULL",
    "UPDATE garments SET processing_item_id='missing'",
    "DELETE FROM garments",
])
def test_actual_phase1_ineligibility_cannot_gain_a_no_pair_reference(store, sql):
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    with connect(store[0]) as conn: conn.execute(sql)
    for cached in (True, False):
        result, info = DecisionRecommendationScorer(RequestCandidateEngine(SqliteConfirmedGarmentQuery()),
                                                   Preferences(), cached=cached).rank_with_cache_info("owner", StructuredOutfitRequest())
        assert result.status == "NoEligibleGarments" and result.winner is None and result.scored_count == 0
        assert info.visits == 0
