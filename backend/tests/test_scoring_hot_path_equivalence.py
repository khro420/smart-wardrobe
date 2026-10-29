from tests.integration_source_guard import source_set, source_hash
"""Completed 2A oracle remains independently executable; no live dependencies."""
import hashlib,json,subprocess,sys,zipfile
from pathlib import Path
import pytest
from tests.test_assistant_performance_equivalence import fixtures, BACKEND
REFERENCE=BACKEND / "tests/fixtures/performance_reference_2a"

def hot_path_cases():
    from tests.test_assistant_performance_equivalence import garment,preferences
    tags=["rec:v1:occasion:campus:allow","rec:v1:formality:casual:allow"]
    rows=[garment("t","vest",primary_colour="navy blue",style_tags=["vintage","unmapped"],custom_tags=tags),
          garment("b","trousers",primary_colour="blue",style_tags=[],custom_tags=tags),
          garment("d","vest_dress",primary_colour="#0000ff",style_tags=["vintage"],custom_tags=tags),
          garment("o","long_sleeve_outwear",primary_colour="#123456",style_tags=None,
                  custom_tags=["rec:v1:formality:casual:deny"])]
    pref=preferences()
    for row,weight in zip(pref,("0.13","0.27","0.41","0.19")):row["weight"]=weight
    pref[-1]["value_json"]=json.dumps({"values":["casual","smart_casual"]})
    requests=[{}, {"style":"vintage"},{"colours":["navy","blue"]},
        {"style":"vintage","colours":["blue"],"garment_categories":[{"kind":"group","value":"top"}]},
        {"occasion":"campus","formality":"casual","style":"vintage","colours":["blue"],
         "garment_categories":[{"kind":"group","value":"top"},{"kind":"category","value":"trousers"}]}]
    return fixtures()+[dict(name=f"mixed-partial-{i}",garments=rows,preferences=pref,request=request,suitability=True)
                       for i,request in enumerate(requests)]

def execute(path, variant, cases):
    source=path / "input.json";output=path / (variant+".json")
    source.write_text(json.dumps(cases))
    subprocess.run([sys.executable,"-B",str(BACKEND/"tests/performance_worker.py"),"--reference",str(REFERENCE),"--variant",variant,"--fixtures",str(source),"--output",str(output),"--trace"],check=True,capture_output=True)
    return [{k:v for k,v in row.items() if k!="timings"} for row in json.loads(output.read_text())]

@pytest.fixture(scope="module")
def oracle(tmp_path_factory):
    path=tmp_path_factory.mktemp("completed-2a");cases=hot_path_cases()
    return path,cases,execute(path,"original",cases)

@pytest.mark.parametrize("variant",["request","preference","prepared","combined"])
def test_exact_completed_2a_equivalence(oracle,variant):
    path,cases,expected=oracle
    assert execute(path,variant,cases)==expected

def test_completed_2a_reference_integrity():
    manifest=json.loads((REFERENCE/"manifest.json").read_text())
    current={p.relative_to(BACKEND).as_posix() for p in (BACKEND/"app").rglob("*") if p.suffix in (".py",".json")}
    source_set(current,manifest,{"app/application/recommendation/exact_score_reuse.py"})
    allowed={"app/application/recommendation/"+n+".py" for n in ("request_match_scorer","preference_scorer","recommendation_scorer","recommendation_engine","request_candidate_session")}
    with zipfile.ZipFile(REFERENCE/"app.zip") as archive:
        assert set(archive.namelist())==set(manifest)
        for name,digest in manifest.items():
            assert hashlib.sha256(archive.read(name)).hexdigest()==digest
            if name not in allowed: source_hash(name,digest)

def test_request_preparation_preserves_order_and_rejects_changed_snapshots():
    from dataclasses import replace
    from app.application.recommendation.request_match_scorer import RequestMatchScorer
    from tests.test_recommendation_scoring import verified,pair,five_fields
    scorer=RequestMatchScorer()
    item=verified(pair(),five_fields())[0]
    first=scorer.score(item)
    assert scorer.score(item)==first
    assert scorer.fact_misses==2 and scorer.fact_hits==2
    assert tuple(x.name for x in first.details)==("garment_categories","colours","style","occasion","formality")
    changed=pair();changed[0]=replace(changed[0],style_tags=("vintage","classic"))
    # Same request object and ID with changed attributes must never reuse a fact.
    other=verified(changed,item.request)[0]
    with pytest.raises(ValueError,match="Conflicting garment"):
        scorer.score(other)
    assert RequestMatchScorer()._style_facts=={}

def test_bounded_reuse_complete_keys_and_real_validation():
    from fractions import Fraction as F
    from dataclasses import FrozenInstanceError
    from app.application.recommendation.exact_score_reuse import ExactScoreReuse
    reuse=ExactScoreReuse()
    a=reuse.evidence("style",F(0),"Available",1,1,("known:a",))
    assert reuse.evidence("style",F(0),"Available",1,1,("known:a",)) is a
    for args in (("style",None,"Unknown",0,1,("missing:a",)),
                 ("style",F(0),"Partial",0,1,("missing:a",)),
                 ("style",F(0),"Available",1,1,("known:b",)),
                 ("style",F(0),"Available",1,2,("known:a",))):
        assert reuse.evidence(*args) != a
    with pytest.raises(FrozenInstanceError):a.value=F(1)
    with pytest.raises(ValueError):reuse.evidence("style",F(2),"Available")
    with pytest.raises(ValueError):reuse.evidence("style",None,"Available")
    for invalid in (0,False,0.0):
        with pytest.raises(ValueError):reuse.evidence("style",invalid,"Available",1,1,("known:a",))
    with pytest.raises(ValueError):reuse.component("invalid")
    for i in range(2000):reuse.evidence("style",F(i%2),"Available",1,1,(f"known:{i}",))
    assert reuse._evidence.cache_info().currsize<=256
    assert reuse._component.cache_info().currsize<=256
    weights=(F(7,10),F(0),F(3,10))
    assert reuse.weighted(weights,(F(1,2),F(0),F(1,4)))==F(17,40)
    unknown=reuse.evidence("style",None,"Unknown",0,2,("missing:a","malformed:b"))
    reversed_reasons=reuse.evidence("style",None,"Unknown",0,2,("malformed:b","missing:a"))
    assert reversed_reasons is not unknown and reversed_reasons!=unknown
    assert reuse.component(unknown,(a,)) is reuse.component(unknown,(a,))
    assert reuse.component(unknown,(a,unknown)) != reuse.component(unknown,(unknown,a))
    for i in range(600):
        reuse.weighted(weights,(F(i,600),F(0),F(0)))
        reuse.component(reuse.evidence("synthetic",F(i,600),"Available"))
    assert reuse._weighted.cache_info().currsize<=256
    assert reuse._component.cache_info().currsize<=256
    assert ExactScoreReuse()._evidence.cache_info().currsize==0

def test_preference_facts_reset_for_exact_snapshot_and_preserve_unknown_reasons():
    from app.application.recommendation.preference_scorer import PreferenceScorer
    from app.application.recommendation.preference_normalizer import PreferenceNormalizer
    from tests.test_recommendation_scoring import verified,pair
    from tests.test_preference_modelling import pref
    scorer=PreferenceScorer();item=verified(pair(second_styles=None))[0]
    norm=PreferenceNormalizer()
    first=norm.normalize("owner",[pref("styles",["vintage"])])
    value=scorer.score(item,first)
    assert scorer.score(item,first)==value
    assert scorer.fact_misses==2 and scorer.fact_hits==2
    assert value.details[0].reasons==("known:t","missing:b")
    second=norm.normalize("owner",[pref("styles",["classic"])])
    assert scorer.score(item,second).contribution==0
    assert scorer.fact_misses==4
    assert PreferenceScorer()._facts=={}

def test_every_candidate_still_runs_final_score_validation_and_both_mandatory_checks(monkeypatch):
    from app.domain.value_objects.recommendation_score import RecommendationScore
    from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
    from tests.test_candidate_ranking import rank
    from tests.test_structural_candidates import garment
    calls={"score":0,"mandatory":0}
    original=RecommendationScore.__post_init__
    evaluate=RequestConstraintEvaluator.evaluate
    def validate(self):
        calls["score"]+=1
        original(self)
    def mandatory(self,*args):
        calls["mandatory"]+=1
        return evaluate(self,*args)
    monkeypatch.setattr(RecommendationScore,"__post_init__",validate)
    monkeypatch.setattr(RequestConstraintEvaluator,"evaluate",mandatory)
    rows=[garment("t","vest"),garment("b","trousers"),garment("d","vest_dress"),garment("o","long_sleeve_outwear")]
    result=rank(rows)
    assert result.complete and result.scored_count==4
    assert calls=={"score":4,"mandatory":8}

@pytest.mark.parametrize("populated",[False,True])
def test_large_stream_exact_fingerprint_and_persisted_metadata(tmp_path,populated):
    from tests.test_assistant_performance_equivalence import garment,preferences
    rows=[]
    for category,count in (("vest",24),("trousers",24),("vest_dress",6),("long_sleeve_outwear",6)):
        rows.extend(garment(f"{category}-{i:04d}",category,primary_colour="blue",style_tags=["vintage"]) for i in range(count))
    source=tmp_path/"large.json"
    source.write_text(json.dumps([dict(name="large-synthetic",garments=rows,preferences=preferences() if populated else [],service=True)]))
    records=[]
    for variant in ("original","combined"):
        output=tmp_path/(variant+".json")
        subprocess.run([sys.executable,"-B",str(BACKEND/"tests/performance_worker.py"),"--reference",str(REFERENCE),"--variant",variant,"--fixtures",str(source),"--output",str(output),"--digest"],check=True,capture_output=True)
        row=json.loads(output.read_text())[0]
        records.append({k:v for k,v in row.items() if k!="timings"})
    assert records[0]==records[1]
    assert records[0]["scored_count"]==4074
    assert records[0]["transcript"]["events"]==12222
