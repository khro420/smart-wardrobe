"""Synthetic exhaustive semantic comparisons, not fashion-quality validation."""
from dataclasses import asdict,replace,FrozenInstanceError
from fractions import Fraction as F
from itertools import product
import random
import pytest
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer,DEFERRED,EXPERIMENTAL
from app.application.recommendation.compact_candidate_stream import groups,enumerate_indexes,materialize
from app.application.recommendation.compact_mandatory_verifier import CompactMandatoryFacts,CompactEligibilityVerifier
from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
from app.application.recommendation.recommendation_scorer import RecommendationScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate,InvalidScoringInput
from app.application.recommendation.request_match_scorer import RequestMatchScorer
from app.application.recommendation.preference_scorer import PreferenceScorer
from app.application.recommendation.preference_normalizer import PreferenceNormalizer
from app.application.recommendation.prepared_compatibility_aggregation import PreparedCompatibilityAggregation
from app.application.recommendation.prepared_decision_policy import PreparedDecisionPolicy
from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
from app.application.recommendation.compatibility_scorer import CompatibilityScorer
from app.application.recommendation.scoring_policy import ScoringProfile
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.domain.value_objects.recommendation_score import RecommendationScore
from app.domain.value_objects.request_candidate_evaluation import EvaluatedCandidate
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest,GarmentCategoryConstraint
from app.domain.value_objects.compact_recommendation import CompactScore,Measure,validate_total
from app.domain.value_objects.compatibility_signature import STRUCTURES
from tests.test_rule_based_compatibility import g,Preferences
from tests.test_structural_candidates import Query
from tests.test_preference_modelling import pref


def reference(rows,structured,preferences,profile,evaluator):
    engine=RequestCandidateEngine(Query(rows),evaluator_factory=evaluator)
    scorer=AggregatedDecisionRecommendationScorer(engine,Preferences(preferences)) if profile==EXPERIMENTAL else RecommendationScorer(engine,Preferences(preferences))
    return scorer.rank('owner',structured) if profile==EXPERIMENTAL else scorer.rank('owner',structured,profile)


def signature(outcome):
    return (outcome.status,outcome.complete,outcome.scored_count,outcome.diagnostics,
        None if not outcome.winner else (outcome.winner.verified.candidate.key,asdict(outcome.winner.verified.evaluated.evaluation),asdict(outcome.winner.score)))


def oracle_records(rows,structured,preferences,profile,evaluator,user='owner'):
    engine=RequestCandidateEngine(Query(rows),evaluator_factory=evaluator)
    session=engine.generate_candidates(user,structured); gate=ScoringEligibilityGate(session,user,structured)
    prefs=PreferenceNormalizer().normalize(user,preferences)
    rs,ps,cs=RequestMatchScorer(),PreferenceScorer(),PreparedCompatibilityAggregation()
    policy=CompatibilityDecisionPolicy.load() if profile==EXPERIMENTAL else ScoringProfile.load(profile)
    decision=PreparedDecisionPolicy(policy) if profile==EXPERIMENTAL else None
    names={v:k for k,v in STRUCTURES.items()}
    try:
        for candidate in session.structural_session:
            evaluation=session.evaluator.evaluate(candidate,structured); score=None
            if evaluation.state=='Pass':
                verified=gate.verify(EvaluatedCandidate(candidate,evaluation))
                r,p=rs.score(verified),ps.score(verified,prefs)
                c=decision.apply(cs.score(verified),names[tuple(m.role for m in candidate.members)]) if decision else CompatibilityScorer().score(verified,policy)
                score=RecommendationScore(r,c,p,sum((w*x.contribution for w,x in zip(policy.weights,(r,c,p))),F(0)),policy.name,policy.version,policy.weights)
            yield {'key':candidate.key,'candidate_id':candidate.candidate_id,'evaluation':asdict(evaluation),'verified':score is not None,'score':asdict(score) if score else None}
    finally:session.close()


@pytest.mark.parametrize('profile',[DEFERRED,EXPERIMENTAL])
@pytest.mark.parametrize('structured',[StructuredOutfitRequest(),StructuredOutfitRequest(style='classic'),StructuredOutfitRequest(colours=('blue',)),StructuredOutfitRequest(garment_categories=(GarmentCategoryConstraint('group','top'),GarmentCategoryConstraint('category','vest')))])
@pytest.mark.parametrize('preferences',[(),(pref('colours',['blue']),),(pref('colours',['blue']),pref('styles',['vintage']),pref('garment_categories',[{'kind':'group','value':'dress'}]))])
def test_every_candidate_and_complete_outcome(profile,structured,preferences):
    rows=[g('t1','vest'),g('t2','short_sleeve_top','red',('sporty',)),g('b1','trousers','blue',None),g('b2','shorts',None,()),g('d','vest_dress','white',('vintage','classic')),g('o','long_sleeve_outwear','#123456',('unrecognized',))]
    actual=[]; kernel=CompactExhaustiveScorer(Query(list(reversed(rows))),Preferences(preferences),profile,audit=actual.append,pair_capacity=1,aggregation_capacity=1)
    result=kernel.rank('owner',structured)
    assert signature(result)==signature(reference(rows,structured,preferences,profile,None))
    assert actual==list(oracle_records(rows,structured,preferences,profile,None))
    assert kernel.cache_statistics['pairs']<=1


@pytest.mark.parametrize('seed',range(20))
def test_random_complete_candidate_evidence(seed):
    rng=random.Random(seed)
    rows=[g(str(i),category,rng.choice(('blue','red','white',None,'#182a46')),rng.choice((('classic',),('vintage',),('classic','vintage'),None,(),('bad',)))) for i,category in enumerate(('vest','vest','trousers','trousers','vest_dress','vest_dress','long_sleeve_outwear','long_sleeve_outwear'))]
    structured=StructuredOutfitRequest(style=rng.choice((None,'classic','vintage')),colours=rng.choice((None,('red',),('blue','white'))))
    actual=[]; result=CompactExhaustiveScorer(Query(rows),Preferences(),audit=actual.append).rank('owner',structured)
    assert signature(result)==signature(reference(rows,structured,(),EXPERIMENTAL,None))
    assert actual==list(oracle_records(rows,structured,(),EXPERIMENTAL,None))


def test_independent_expected_products_and_stable_ids():
    rows=[g('t','vest'),g('b','trousers'),g('d','vest_dress'),g('o','long_sleeve_outwear')]
    candidates=[materialize(rows,r,i).key for r,i in enumerate_indexes(groups(rows))]
    assert candidates==[(('upper','t'),('lower','b')),(('upper','t'),('lower','b'),('outerwear','o')),(('one_piece','d'),),(('one_piece','d'),('outerwear','o'))]
    assert len(candidates)==len(set(candidates))==4


@pytest.mark.parametrize('profile',[DEFERRED,EXPERIMENTAL])
def test_reused_instance_does_not_reuse_owner_request_or_snapshot_facts(profile):
    rows=[g('t','vest'),g('b','trousers')]
    query,preferences=Query(rows),Preferences((pref('colours',['blue']),))
    kernel=CompactExhaustiveScorer(query,preferences,profile)
    first=kernel.rank('owner',StructuredOutfitRequest(style='classic'))
    assert first.status=='Selected'
    assert kernel.rank('owner',StructuredOutfitRequest(style='vintage')).status=='NoMatchingCandidates'
    # Same IDs, another owner, changed evidence and preferences: no old cache fact
    # or verifier context may survive the next preparation.
    query.rows=[replace(row,user_id='other',primary_colour='red',style_tags=('sporty',)) for row in rows]
    preferences.rows=(pref('colours',['red'],user='other'),)
    actual=kernel.rank('other',StructuredOutfitRequest(style='sporty'))
    engine=RequestCandidateEngine(Query(query.rows))
    reference_scorer=AggregatedDecisionRecommendationScorer(engine,preferences) if profile==EXPERIMENTAL else RecommendationScorer(engine,preferences)
    expected=reference_scorer.rank('other',StructuredOutfitRequest(style='sporty')) if profile==EXPERIMENTAL else reference_scorer.rank('other',StructuredOutfitRequest(style='sporty'),profile)
    assert signature(actual)==signature(expected)
    assert all(member.garment.user_id=='other' for member in actual.winner.verified.candidate.members)
    assert kernel.rank('owner',StructuredOutfitRequest()).status=='InvalidPreferenceData'
    preferences.rows=()
    assert kernel.rank('owner',StructuredOutfitRequest()).status=='NoEligibleGarments'


@pytest.mark.parametrize('profile',[DEFERRED,EXPERIMENTAL])
def test_simultaneous_reuse_of_same_instance_is_rejected(profile):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    entered,release=Event(),Event()
    def checkpoint(stage,*_):
        if stage=='candidate':
            entered.set()
            if not release.wait(10):raise RuntimeError('Synthetic barrier timeout')
    kernel=CompactExhaustiveScorer(Query([g('t','vest'),g('b','trousers')]),Preferences(),profile,checkpoint=checkpoint)
    with ThreadPoolExecutor(max_workers=1) as pool:
        running=pool.submit(kernel.rank,'owner',StructuredOutfitRequest())
        try:
            assert entered.wait(10)
            rejected=kernel.rank('owner',StructuredOutfitRequest(style='sporty'))
            assert rejected.status=='InvalidScoringInput' and rejected.winner is None and not rejected.complete
        finally:release.set()
        assert running.result(timeout=10).status=='Selected'


@pytest.mark.parametrize('occasion',['campus','work','casual_outing','shopping','dinner','party','date','travel'])
def test_suitability_opt_in_all_fields(occasion):
    # Actual reserved syntax comes from the existing policy, not a new convention.
    from app.application.recommendation.suitability_policy import SuitabilityPolicy
    policy=SuitabilityPolicy.load()
    tags=(f'rec:v1:occasion:{occasion}:allow','rec:v1:formality:casual:allow')
    rows=[g('t','vest',custom_tags=tags),g('b','trousers',custom_tags=tags),g('o','long_sleeve_outwear',custom_tags=tags)]
    structured=StructuredOutfitRequest(occasion=occasion,formality='casual',style='classic',colours=('blue',),garment_categories=(GarmentCategoryConstraint('group','top'),))
    actual=[]; result=CompactExhaustiveScorer(Query(rows),Preferences(),evaluator_type=SuitabilityRequestEvaluator,audit=actual.append).rank('owner',structured)
    assert signature(result)==signature(reference(rows,structured,(),EXPERIMENTAL,SuitabilityRequestEvaluator))
    assert actual==list(oracle_records(rows,structured,(),EXPERIMENTAL,SuitabilityRequestEvaluator))


@pytest.mark.parametrize('rows',[[],[g('t','vest')],[g('d','vest_dress')],[g('t','vest'),g('b','trousers')]])
@pytest.mark.parametrize('structured',[StructuredOutfitRequest(),StructuredOutfitRequest(occasion='exercise'),StructuredOutfitRequest(style='sporty')])
def test_empty_incomplete_unavailable(rows,structured):
    for profile in (DEFERRED,EXPERIMENTAL):
        assert signature(CompactExhaustiveScorer(Query(rows),Preferences(),profile).rank('owner',structured))==signature(reference(rows,structured,(),profile,None))


@pytest.mark.parametrize('stage',['candidate','before_close','closed','reconstructed'])
@pytest.mark.parametrize('exception',[RuntimeError,KeyboardInterrupt])
def test_late_failure_never_returns_winner(stage,exception):
    def fail(current,*args):
        if current==stage:raise exception()
    result=CompactExhaustiveScorer(Query([g('t','vest'),g('b','trousers')]),Preferences(),checkpoint=fail).rank('owner',StructuredOutfitRequest())
    assert result.status==('Interrupted' if exception is KeyboardInterrupt else 'ProcessingFailure')
    assert result.winner is None and not result.complete


def test_independent_verifier_rejects_forged_flags_and_membership():
    from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
    rows=(g('t','vest'),g('b','trousers'))
    structured=StructuredOutfitRequest(colours=('red',))
    primary=CompactMandatoryFacts(rows,structured,RequestConstraintEvaluator)
    verifier=CompactEligibilityVerifier('owner',rows,structured,RequestConstraintEvaluator)
    actual=primary.evaluate(('upper','lower'),(0,1))
    with pytest.raises(InvalidScoringInput):verifier.verify(('upper','lower'),(0,1),(('colours','red',1,1),))
    for indexes in ((0,0),(0,2),(-1,1),(False,1)):
        with pytest.raises(InvalidScoringInput):verifier.verify(('upper','lower'),indexes,actual)


def test_invalid_totals_are_not_accepted():
    score=CompactScore(Measure(F(1),'Available'),None,Measure(None,'NoPreferences'),F(1),(),())
    with pytest.raises(ValueError):validate_total(score,(F(7,10),F(0),F(3,10)))


@pytest.mark.parametrize('tags',[(None,None),((),()),(('work',),('casual',)),(('rec:v1:occasion:campus:allow','rec:v1:formality:smart_casual:allow'),('rec:v1:occasion:campus:deny',)),(('rec:v1:occasion:campus:allow','rec:v1:occasion:campus:deny'),('rec:v1:formality:smart_casual:allow',)),(('rec:v1:occasion:campus:allow','rec:v1:formality:smart_casual:allow'),)*2])
def test_suitability_conflicts_and_incomplete_annotations(tags):
    rows=[g('t','vest',custom_tags=tags[0]),g('b','trousers',custom_tags=tags[1]),g('d','vest_dress',custom_tags=tags[1])]
    structured=StructuredOutfitRequest(occasion='campus',formality='smart_casual',style='classic',colours=('blue',))
    actual=[]; result=CompactExhaustiveScorer(Query(rows),Preferences(),evaluator_type=SuitabilityRequestEvaluator,audit=actual.append).rank('owner',structured)
    assert signature(result)==signature(reference(rows,structured,(),EXPERIMENTAL,SuitabilityRequestEvaluator))
    assert actual==list(oracle_records(rows,structured,(),EXPERIMENTAL,SuitabilityRequestEvaluator))


@pytest.mark.parametrize('preferences',[(pref('formality',['casual','smart_casual']),),(pref('styles',['classic'],weight='.333333333333333333333'),pref('colours',['red'],weight='.17')),(pref('unknown',['x']),)])
def test_formality_fractional_weights_and_unsupported_preferences(preferences):
    rows=[g('t','vest',custom_tags=('rec:v1:formality:casual:allow',)),g('b','trousers',styles=('classic','bad')),g('d','vest_dress',custom_tags=('rec:v1:formality:casual:deny',))]
    structured=StructuredOutfitRequest();actual=[]
    result=CompactExhaustiveScorer(Query(rows),Preferences(preferences),audit=actual.append).rank('owner',structured)
    assert signature(result)==signature(reference(rows,structured,preferences,EXPERIMENTAL,None))
    assert actual==list(oracle_records(rows,structured,preferences,EXPERIMENTAL,None))


@pytest.mark.parametrize('mode',['truncated','duplicate','reverse'])
def test_incomplete_or_corrupt_stream_cannot_succeed(mode):
    def broken(slots):
        all_items=list(enumerate_indexes(slots))
        yield from (all_items[:1] if mode=='truncated' else all_items+all_items[:1] if mode=='duplicate' else reversed(all_items))
    rows=[g('t','vest'),g('b','trousers'),g('d','vest_dress')]
    result=CompactExhaustiveScorer(Query(rows),Preferences(),stream_factory=broken).rank('owner',StructuredOutfitRequest())
    assert result.status=='InvalidScoringInput' and not result.complete and result.winner is None


def test_stable_role_key_beats_global_index_order():
    rows=[g('aa','vest',None,None),g('bb','trousers',None,None),g('zz','vest_dress',None,None)]
    result=CompactExhaustiveScorer(Query(rows),Preferences()).rank('owner',StructuredOutfitRequest())
    assert result.winner.verified.candidate.key==( ('one_piece','zz'), )
    assert signature(result)==signature(reference(rows,StructuredOutfitRequest(),(),EXPERIMENTAL,None))


@pytest.mark.parametrize('position',range(4))
def test_numeric_comparator_has_every_documented_level(position):
    from app.application.recommendation.compact_exhaustive_scorer import numeric_key
    # Comparator-only vectors. P-only ties cannot arise with fixed positive P
    # weight when S/R/C are identical, but its documented ordering is retained.
    def item(values):
        from types import SimpleNamespace
        return SimpleNamespace(total=values[0],contributions=tuple(values[1:]))
    a=[F(1,2)]*4;b=list(a);a[position]=F(3,4)
    assert numeric_key(item(a))>numeric_key(item(b))


def test_frozen_reference_and_current_sources_remain_intact():
    import hashlib,json,zipfile
    from pathlib import Path
    backend=Path(__file__).resolve().parents[1]
    root=backend/'tests/fixtures/compact_reference'
    manifest=json.loads((root/'manifest.json').read_text())
    with zipfile.ZipFile(root/'app.zip') as archive:
        assert set(archive.namelist())==set(manifest)
        for name,digest in manifest.items():
            assert hashlib.sha256(archive.read(name)).hexdigest()==digest
            from tests.integration_source_guard import integrated_digest
            assert hashlib.sha256((backend/name).read_bytes()).hexdigest()==integrated_digest(name,digest)


def test_immutable_decision_rejects_forged_values_and_coverage():
    from app.application.recommendation.compact_scoring_facts import decision_facts
    valid=decision_facts(((0,1),(1,1)))
    with pytest.raises(FrozenInstanceError):valid.value=F(1)
    for changed in ({'value':F(1)},{'known':0},{'pairs':3},{'basis':'FullyConventional'},{'raw':Measure(None,'Unknown',2,2)}):
        with pytest.raises(ValueError):replace(valid,**changed)
