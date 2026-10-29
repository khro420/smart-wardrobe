from tests.integration_source_guard import source_set, source_hash
"""Test-first full-stream differential oracle against a frozen application.

The reference includes all transitive application/config files, not a second
implementation of the intended formula. Each arm imports in a fresh process.
"""
import copy
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import zipfile
import pytest

BACKEND = Path(__file__).resolve().parents[1]
REFERENCE = BACKEND / "tests/fixtures/performance_reference"


def garment(identifier, category, **attributes):
    mapping = {"vest": ("top", 1), "trousers": ("bottom", 0),
               "vest_dress": ("dress", 0), "long_sleeve_outwear": ("outerwear", 2)}
    role, layer = mapping[category]
    return dict(garment_id=identifier, user_id="owner", status="available", category=category,
        name=identifier, preferred_media_id="synthetic-media", is_favourite=False, updated_at="time",
        structural_role=role, layering_index=layer, **attributes)


def preferences():
    return [dict(preference_id=str(i), user_id="owner", preference_type=kind,
                 value_json=json.dumps({"values": values}), weight="0.5")
            for i, (kind, values) in enumerate([
                ("colours", ["blue", "black"]), ("styles", ["vintage", "classic"]),
                ("garment_categories", [{"kind": "group", "value": "top"}]), ("formality", ["casual"])])]


def fixtures():
    base = [garment("t", "vest", primary_colour="blue", style_tags=["vintage"]),
            garment("b", "trousers", primary_colour="black", style_tags=["classic"]),
            garment("d", "vest_dress", primary_colour="#0000ff", style_tags=["vintage", "classic"]),
            garment("o", "long_sleeve_outwear", primary_colour="grey", style_tags=None)]
    output = []
    for supplied in ({}, {"style": "vintage"}, {"colours": ["blue", "black"]},
                     {"garment_categories": [{"kind": "group", "value": "top"}, {"kind": "category", "value": "vest"}]},
                     {"occasion": "campus"}, {"style": "sporty"}):
        for pref in ([], preferences()):
            output.append(dict(name=f"matrix-{len(output)}", garments=base, request=supplied, preferences=pref))
    tags = ["rec:v1:occasion:campus:allow", "rec:v1:formality:casual:allow"]
    for evidence in (tags, tags + ["rec:v1:occasion:campus:deny"], ["rec:v1:occasion:campus:deny"], ["rec:v1:formality:casual:invalid"]):
        rows = [dict(row, custom_tags=evidence) for row in base]
        output.append(dict(name=f"suitability-{len(output)}", garments=rows, preferences=preferences(), suitability=True,
            request={"occasion": "campus", "formality": "casual", "style": "vintage", "colours": ["blue"],
                     "garment_categories": [{"kind": "group", "value": "top"}]}))
    for fault in ("early", "late", "interrupt", "generator_exit", "close", "incomplete", "tampered"):
        output.append(dict(name=fault, garments=base, fault=fault, preferences=preferences()))
        if fault == "tampered": output[-1]["request"] = {"style": "vintage"}
    output.extend([dict(name="empty", garments=[]), dict(name="insufficient", garments=[base[0]]),
        dict(name="actual-persistence", garments=base, preferences=preferences(), persist=True),
        dict(name="jaccard-unpaired", garments=base, profile="three_component_experimental"),
        dict(name="jaccard-pair", garments=base[:2], profile="three_component_experimental"),
        dict(name="jaccard-unknown", garments=[dict(base[0], style_tags=None), base[1]], profile="three_component_experimental"),
        dict(name="unsupported-preference", garments=base, preferences=[dict(preference_id="u", user_id="owner",
             preference_type="style_note", value_json='{"value":"unrestricted prose"}')]),
        dict(name="duplicate-preference", garments=base, preferences=[preferences()[0], dict(preferences()[0], preference_id="duplicate")])])
    for seed in range(32):
        rng = random.Random(seed)
        rows = []
        for index in range(rng.randint(3, 12)):
            rows.append(garment(str(index), rng.choice(["vest", "trousers", "vest_dress", "long_sleeve_outwear"]),
                primary_colour=rng.choice([None, "blue", "black", "red", "#123456", "#bad!", "navy blue"]),
                style_tags=rng.choice([None, [], ["vintage"], ["classic"], ["unmapped"], ["vintage", "classic"]]),
                invalid_attributes=rng.choice([[], ["style_tags"], ["custom_tags"]])))
        rng.shuffle(rows)
        output.append(dict(name=f"seed-{seed}", garments=rows, preferences=preferences() if seed % 2 else [],
                           request=rng.choice([{}, {"style": "vintage"}, {"colours": ["blue"]}])))
    return output


def execute(tmp_path, variant, cases):
    source, output = tmp_path / "input.json", tmp_path / (variant + ".json")
    source.write_text(json.dumps(cases), encoding="utf-8")
    subprocess.run([sys.executable, "-B", str(BACKEND / "tests/performance_worker.py"),
        "--variant", variant, "--fixtures", str(source), "--output", str(output), "--trace"],
        cwd=BACKEND, check=True, capture_output=True, text=True)
    return [{k: v for k, v in row.items() if k != "timings"} for row in json.loads(output.read_text())]


@pytest.fixture(scope="module")
def baseline(tmp_path_factory):
    path = tmp_path_factory.mktemp("differential")
    cases = fixtures()
    return path, cases, execute(path, "original", cases)


@pytest.mark.parametrize("variant", ["key", "preferences", "constants", "combined"])
def test_complete_candidate_evidence_scores_winner_and_completion(baseline, variant):
    path, cases, expected = baseline
    assert execute(path, variant, cases) == expected


def test_oracle_covers_all_structures_and_three_states(baseline):
    _, _, expected = baseline
    roles, states = set(), set()
    for row in expected:
        for event in row["trace"]:
            if "mandatory" in event:
                roles.add(tuple(role for role, identifier in event["key"]))
                states.update(c["state"] for c in event["mandatory"]["conditions"])
    assert roles == {("upper", "lower"), ("one_piece",), ("upper", "lower", "outerwear"), ("one_piece", "outerwear")}
    assert states == {"Pass", "Fail", "Unknown"}
    by_name = {row["name"]: row for row in expected}
    for fault, status in (("early", "ProcessingFailure"), ("late", "ProcessingFailure"),
                          ("interrupt", "Interrupted"), ("generator_exit", "Interrupted"), ("close", "ProcessingFailure"),
                          ("incomplete", "ProcessingFailure"), ("tampered", "InvalidScoringInput")):
        assert by_name[fault]["outcome"]["status"] == status
        assert by_name[fault]["outcome"]["winner"] is None


def test_oracle_detects_numerical_eligibility_winner_and_completion_mutations(baseline):
    _, _, expected = baseline
    for field in ("score", "eligibility", "winner", "completion"):
        broken = copy.deepcopy(expected)
        row = next(r for r in broken if r["outcome"]["winner"] is not None)
        if field == "score": row["outcome"]["winner"]["score"]["total"] = {"fraction": [123, 456]}
        if field == "eligibility": row["trace"].pop()
        if field == "winner": row["outcome"]["winner"]["verified"]["evaluated"]["candidate"]["members"][0]["role"] = "invalid"
        if field == "completion": row["outcome"]["complete"] = False
        with pytest.raises(AssertionError): assert broken == expected


def test_frozen_reference_integrity_and_unchanged_transitive_dependencies():
    manifest = json.loads((REFERENCE / "manifest.json").read_text())
    allowed = {"app/application/recommendation/" + name + ".py" for name in
               ("candidate_ranker", "preference_scorer", "compatibility_scorer", "request_match_scorer", "recommendation_scorer", "recommendation_engine", "request_candidate_session")}
    with zipfile.ZipFile(REFERENCE / "app.zip") as archive:
        assert set(archive.namelist()) == set(manifest)
        for name, digest in manifest.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
            if name not in allowed:
                source_hash(name,digest)


@pytest.mark.parametrize("stage", ["total", "request", "compatibility", "preference", "identifier"])
def test_ranker_matches_frozen_reference_at_every_tie_level(stage):
    from dataclasses import replace
    from fractions import Fraction as F
    from app.application.recommendation.candidate_ranker import CandidateRanker
    from app.domain.value_objects.recommendation_score import ScoreEvidence, ComponentScore, RecommendationScore
    from app.domain.value_objects.scored_candidate import ScoredCandidate
    from tests.test_recommendation_scoring import verified
    from tests.test_structural_candidates import garment as snapshot
    with zipfile.ZipFile(REFERENCE / "app.zip") as archive:
        namespace = {}
        exec(compile(archive.read("app/application/recommendation/candidate_ranker.py"), "frozen-ranker", "exec"), namespace)
    old, new = namespace["CandidateRanker"](), CandidateRanker()
    first, second = verified([snapshot("a", "vest_dress"), snapshot("z", "vest_dress")])
    weights = (F(1), F(0), F(0)) if stage == "preference" else (F(0), F(0), F(1))
    a, b = (F(1, 2),) * 3, (F(1, 2),) * 3
    if stage == "total": a, b = (F(0), F(0), F(1)), (F(1), F(1), F(1, 2))
    if stage == "request": a = (F(1), F(0), F(1, 2))
    if stage == "compatibility": a = (F(1, 2), F(1), F(1, 2))
    if stage == "preference": a = (F(1, 2), F(1, 2), F(1))
    def scored(item, values):
        parts = tuple(ComponentScore(ScoreEvidence(n, v, "Available")) for n, v in zip("rcp", values))
        return ScoredCandidate(item, RecommendationScore(*parts, sum(w*v for w, v in zip(weights, values)), "synthetic", "synthetic", weights))
    x, y = scored(first, a), scored(second, b)
    for challenger, incumbent in ((x, None), (y, x), (x, y), (y, y), (x, x), (y, x)):
        assert new.better(challenger, incumbent) == old.better(challenger, incumbent)
    bad = replace(x, score=replace(x.score, profile_name="other"))
    for ranker in (old, new):
        with pytest.raises(ValueError): ranker.better(bad, x)


def test_preparation_is_snapshot_and_user_scoped_and_reuses_no_candidate_evidence():
    from app.application.recommendation.preference_scorer import PreferenceScorer
    from app.application.recommendation.preference_normalizer import PreferenceNormalizer
    from tests.test_recommendation_scoring import verified, pair
    from tests.test_preference_modelling import pref
    item = verified(pair())[0]
    normalizer, scorer = PreferenceNormalizer(), PreferenceScorer()
    blue = normalizer.normalize("owner", [pref("colours", ["blue"])])
    red = normalizer.normalize("owner", [pref("colours", ["red"])])
    first = scorer.score(item, blue)
    prepared = scorer._prepared
    assert scorer.score(item, blue) == first and scorer._prepared is prepared
    assert scorer.score(item, red).contribution == 0 and first.contribution == 1
    assert scorer._prepared is not prepared
    other = normalizer.normalize("other", [pref("colours", ["blue"], user="other")])
    with pytest.raises(ValueError): scorer.score(item, other)
    assert PreferenceScorer()._prepared is None
