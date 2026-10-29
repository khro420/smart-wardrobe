"""Before/corrected/public-reference every-candidate equality; frozen scores stay fixed."""
from pathlib import Path
from dataclasses import replace
import importlib.util,json,hashlib,random,os
import pytest
from app.application.nlp.nlp_interpreter import NLPInterpreter
from app.application.recommendation import compact_exhaustive_scorer as kernel
from app.application.recommendation.compact_scoring_facts import CompactScoringFacts
from app.application.recommendation.preference_normalizer import PreferenceNormalizer
from app.application.recommendation.rule_based_compatibility_policy import RuleBasedCompatibilityPolicy
from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
from app.application.recommendation.compact_candidate_stream import groups,enumerate_indexes
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from tests.test_compact_exhaustive import oracle_records,signature
from tests.test_rule_based_compatibility import g,Preferences
from tests.test_structural_candidates import Query
from tests.test_preference_modelling import pref

ROOT=Path(__file__).parent
manifest=json.loads((ROOT/'fixtures/score_certificate_sources.v1.json').read_text())
source=ROOT.parent/manifest['reference']['file']
assert hashlib.sha256(source.read_bytes()).hexdigest()==manifest['reference']['sha256']
spec=importlib.util.spec_from_file_location('score_certificate_frozen',source)
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
CASES=json.loads((ROOT/'fixtures/scoring_acceptance.v1.json').read_text())['cases']+[json.loads((ROOT/'fixtures/scoring_evidence_competition.v1.json').read_text())['case']]

def retain(case,profile,before,after,oracle):
    output=os.getenv('SMART_WARDROBE_CERTIFICATE_EVIDENCE')
    if not output:return
    encoded=lambda value:json.dumps(value,sort_keys=True,default=str,separators=(',',':'))
    digests=[hashlib.sha256(encoded(value).encode()).hexdigest() for value in (before,after,oracle)]
    assert len(set(digests))==1
    with Path(output).open('a') as f:f.write(json.dumps({'case':case,'profile':profile,'candidates':len(before),'sha256_before_after_oracle':digests,'records':before},default=str)+'\n')


@pytest.mark.parametrize('case',CASES,ids=lambda x:x['id'])
@pytest.mark.parametrize('profile',[kernel.DEFERRED,kernel.EXPERIMENTAL])
def test_every_frozen_candidate_before_after_and_public_fraction_oracle(monkeypatch,case,profile):
    rows=[g(n,c,colour,None if styles is None else tuple(styles)) for n,c,colour,styles in case['garments']]
    preferences=tuple(pref(p['type'],p['values'],'1',identifier=str(i)) for i,p in enumerate(case.get('preferences',[])))
    request=NLPInterpreter().interpret(case['text']).structured_request
    before=[];after=[]
    monkeypatch.setattr(kernel,'CompactScoringFacts',old.CompactScoringFacts)
    a=kernel.CompactExhaustiveScorer(Query(rows),Preferences(preferences),profile,audit=before.append).rank('owner',request)
    monkeypatch.setattr(kernel,'CompactScoringFacts',CompactScoringFacts)
    b=kernel.CompactExhaustiveScorer(Query(list(reversed(rows))),Preferences(preferences),profile,audit=after.append).rank('owner',request)
    assert before==after==list(oracle_records(rows,request,preferences,profile,None))
    assert signature(a)==signature(b) and b.complete
    retain(case['id'],profile,before,after,list(oracle_records(rows,request,preferences,profile,None)))

@pytest.mark.parametrize('state',['allow','deny','unknown','conflict','malformed'])
def test_suitability_and_changed_snapshot_three_way(monkeypatch,state):
    tags=('rec:v1:occasion:campus:allow',)
    other={'allow':tags,'deny':('rec:v1:occasion:campus:deny',),'unknown':(), 'conflict':tags+('rec:v1:occasion:campus:deny',),'malformed':tags+('rec:v1:occasion:campus:maybe',)}[state]
    rows=[g('t','vest','blue',('vintage',),custom_tags=tags),g('b','trousers','white',('vintage',),custom_tags=tags),g('d','vest_dress',None,None,custom_tags=other),g('o','long_sleeve_outwear','red',(),custom_tags=other)]
    request=StructuredOutfitRequest(occasion='campus')
    for current in (rows,[replace(x,primary_colour='#123456',style_tags=None) for x in rows]):
        records=[];results=[]
        for implementation in (old.CompactScoringFacts,CompactScoringFacts):
            monkeypatch.setattr(kernel,'CompactScoringFacts',implementation);audit=[]
            outcome=kernel.CompactExhaustiveScorer(Query(current),Preferences(),audit=audit.append,evaluator_type=SuitabilityRequestEvaluator).rank('owner',request)
            records.append(audit);results.append(signature(outcome))
        assert records[0]==records[1]==list(oracle_records(current,request,(),kernel.EXPERIMENTAL,SuitabilityRequestEvaluator))
        assert results[0]==results[1]
        retain('suitability-'+state+('-changed' if current is not rows else ''),kernel.EXPERIMENTAL,records[0],records[1],list(oracle_records(current,request,(),kernel.EXPERIMENTAL,SuitabilityRequestEvaluator)))

@pytest.mark.parametrize('capacity',[0,1,256])
def test_bound_reuse_immutability_and_all_pair_visits(capacity):
    rng=random.Random(20261022);styles=('classic','vintage','sporty','streetwear','minimal')
    rows=[g(str(i),('vest','trousers','long_sleeve_outwear')[i%3],rng.choice(('blue','white','red',None)),tuple(rng.sample(styles,rng.randint(0,4)))) for i in range(48)]
    rows=tuple(sorted(rows,key=lambda x:x.garment_id))
    preferences=PreferenceNormalizer().normalize('owner',(pref('styles',['vintage'],'1'),))
    request=StructuredOutfitRequest()
    current=CompactScoringFacts(rows,request,preferences,RuleBasedCompatibilityPolicy.load(),CompatibilityDecisionPolicy.load().weights,True,aggregation_capacity=capacity)
    previous=old.CompactScoringFacts(rows,request,preferences,RuleBasedCompatibilityPolicy.load(),CompatibilityDecisionPolicy.load().weights,True,aggregation_capacity=capacity)
    visits=0
    for roles,indexes in enumerate_indexes(groups(rows)):
        a=current.score(roles,indexes);b=previous.score(roles,indexes);assert a==b
        visits+=len(indexes)*(len(indexes)-1)//2
    assert current.hits+current.misses==previous.hits+previous.misses==visits
    assert current.cache_info['pairs']<=19900 and all(x['currsize']<=capacity for x in current.cache_info['aggregations'])
    assert current._score.cache_info().maxsize==capacity
    if capacity:assert current._score.cache_info().misses>capacity  # eviction exercised
    with pytest.raises(AttributeError):current.owner='foreign'
    with pytest.raises(AttributeError):current._score=None


def test_session_is_released_without_cyclic_gc():
    import weakref
    rows=(g('t','vest'),g('b','trousers'))
    preferences=PreferenceNormalizer().normalize('owner',())
    facts=CompactScoringFacts(rows,StructuredOutfitRequest(),preferences,RuleBasedCompatibilityPolicy.load(),CompatibilityDecisionPolicy.load().weights,True)
    score=facts.score(('upper','lower'),(0,1))
    ref=weakref.ref(facts)
    del facts
    assert ref() is None  # retained numeric score does not retain user/session facts
    assert score.compatibility.value==1
