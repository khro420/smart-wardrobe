"""Prepared current-source P2 facts; expected utilities come from frozen examples."""
from dataclasses import asdict,replace
from fractions import Fraction as F
from types import SimpleNamespace
from app.domain.value_objects.attribute_preferences import AttributePreferenceSnapshot,DOCUMENT,SNAPSHOT,POLICY_HASH,digest
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
from app.domain.value_objects.recommendation_score import ComponentScore,ScoreEvidence
from app.application.recommendation.attribute_preference_preparation import PreparedAttributePreferences
import pytest
from tests.test_attribute_qualification import make_member,condition


EMPTY=ComponentScore(ScoreEvidence('preference',None,'NoPreferences'))


def snapshot(families,legacy=(),wearer='00000000-0000-4000-8000-000000000001'):
    document={'contract':DOCUMENT,'families':families,'last_action':None};rows=[asdict(row) for row in legacy]
    return AttributePreferenceSnapshot.from_dict({'contract':SNAPSHOT,'account_id':'owner-A','wearer_id':wearer,'document':document,'legacy':rows,
        'legacy_digest':digest(rows),'revision':digest({'legacy':rows,'document':document}),'policy':POLICY_HASH})


def family(axis,liked,avoided=(),scope='all_selected',importance='1'):
    return {'mode':'override','importance':importance,'axes':{axis:{'scope':scope,'importance':'1','liked':list(liked),'avoided':list(avoided)}}}


def test_prepared_shared_pool_different_wearer_colour_preferences_change_winner():
    pool=[make_member('blue','primary_colour','blue'),make_member('green','primary_colour','green')]
    a=PreparedAttributePreferences(snapshot({'colour':family('primary_colour',['blue'])}),pool)
    b=PreparedAttributePreferences(snapshot({'colour':family('primary_colour',['green'])},wearer='00000000-0000-4000-8000-000000000002'),pool)
    assert [a.evaluate((('upper',g.snapshot.garment_id),),EMPTY).score.contribution for g in pool]==[F(1),F(0)]
    assert [b.evaluate((('upper',g.snapshot.garment_id),),EMPTY).score.contribution for g in pool]==[F(0),F(1)]
    assert a.snapshot.to_dict()['wearer_id']!=b.snapshot.to_dict()['wearer_id']


def test_numeric_cache_reuses_equal_facts_without_adopting_unknown_or_uncaptured_members():
    pool=[make_member('A','pattern','plain'),make_member('B','pattern','plain'),make_member('C','pattern','plain',state='missing')]
    prepared=PreparedAttributePreferences(snapshot({'pattern':family('pattern',['plain'])}),pool)
    first=prepared.evaluate((('upper','A'),),EMPTY)
    assert prepared.evaluate((('upper','B'),),EMPTY) is first
    assert prepared.cache_hits==1 and first.score.contribution==1
    assert prepared.evaluate((('upper','C'),),EMPTY).score.contribution==0
    with pytest.raises(ValueError):prepared.evaluate((('upper','uncaptured'),),EMPTY)


def test_known_and_unknown_pattern_member_mean_retains_denominator():
    pool=[make_member('A','pattern','plain'),make_member('B','pattern','plain',state='missing')]
    p=PreparedAttributePreferences(snapshot({'pattern':family('pattern',['plain'])}),pool)
    value=p.evaluate((('upper','A'),('lower','B')),EMPTY)
    assert value.score.contribution==F(1,2) and value.raw.upper==1
    assert value.score.summary.state=='Partial'
    before=p.predicate_calls
    for _ in range(10):assert p.evaluate((('upper','A'),('lower','B')),EMPTY)==value
    assert p.predicate_calls==before and p.cache_hits==10


def test_partial_material_membership_with_unknown_avoid_earns_no_reward():
    item=make_member('A','material',['cotton'])
    # A genuinely partial recorded label set cannot establish no wool.
    from app.application.wardrobe.description_projector import _document
    from app.domain.value_objects.garment_description_evidence import seal_field
    doc=item.description.to_dict();record=doc['fields']['material'];record['completeness']='partial';seal_field(record)
    item=replace(item,description=_document(doc['subject'],doc['fields']))
    p=PreparedAttributePreferences(snapshot({'material':family('material',['cotton'],['wool'])}),[item])
    value=p.evaluate((('upper','A'),),EMPTY)
    assert value.score.contribution==0 and value.raw.upper==1


def test_hard_implied_plain_is_masked_without_changing_configured_denominator():
    pool=[make_member('A','pattern','plain')]
    p=PreparedAttributePreferences(snapshot({'pattern':family('pattern',['plain'])}),pool,conditions=condition('pattern','plain',q='all_present'))
    value=p.evaluate((('upper','A'),),EMPTY)
    assert value.denominator==1 and value.raw.lower==1 and value.score.contribution==0
    assert value.to_dict()['families'][0]['axes'][0]['mask']['rule']=='hard_implied_utility_one_v1'


def test_empty_and_disabled_never_borrow_legacy_or_another_wearer():
    pool=[make_member('A','primary_colour','blue')]
    p=PreparedAttributePreferences(snapshot({}),pool)
    assert p.evaluate((('upper','A'),),EMPTY).score.summary.state=='NoPreferences'
    legacy=(PreferenceSnapshot('old','owner-A','colours','{"values":["blue"]}','1','owner',True),)
    p=PreparedAttributePreferences(snapshot({'colour':{'mode':'disabled'}},legacy),pool)
    assert p.evaluate((('upper','A'),),EMPTY).score.contribution==0


def test_secondary_missing_is_not_a_primary_fallback_and_colour_is_bounded():
    pool=[make_member('A','primary_colour','blue')]
    config=family('primary_colour',['blue']);config['axes']['secondary_colour']={'scope':'all_selected','importance':'1','liked':['blue'],'avoided':[]}
    p=PreparedAttributePreferences(snapshot({'colour':config}),pool)
    result=p.evaluate((('upper','A'),),EMPTY)
    assert result.score.contribution==F(1,2)
    assert result.denominator==1


def engine_fixture(liked):
    from tests.test_context_relevance_ranking import rows,Query,Preferences,LABELS
    from app.shared_contracts.confirmed_garment_description import ConfirmedGarmentDescription
    from app.application.wardrobe.description_policy import DescriptionPolicy
    from app.application.wardrobe.description_projector import project
    from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
    policy=DescriptionPolicy.load();garments=tuple(replace(g,user_id='owner-A') for g in rows())
    collection=[]
    for g in garments:
        row={'id':g.garment_id,'user_id':g.user_id,'processing_item_id':None,'name':g.name,'category':g.category,
             'preferred_media_id':g.preferred_media_id,'primary_colour':g.primary_colour,'attributes_json':'{}'}
        collection.append(ConfirmedGarmentDescription(g,project(row,'owner-A',policy)))
    saved=snapshot({'colour':family('primary_colour',liked)} if liked else {})
    prepared=PreparedAttributePreferences(saved,collection)
    request=GeneralContextInterpreter('context_18_v1').interpret("I'm going shopping.").structured_request
    # Accepted original hand-authored R/C rows, with independent boolean P2.
    colours={g.garment_id:g.primary_colour for g in garments}
    expected={}
    for row in LABELS['point_rows']:
        ids=tuple(row[0].split('+'));r,c=F(row[1]),F(row[3]);p=F(int(any(colours[g] in liked for g in ids))) if liked else F()
        expected[ids]=(r,c,p,F(3,5)*r+F(1,5)*c+F(1,5)*p)
    winner=min(expected,key=lambda ids:(-expected[ids][3],-expected[ids][0],-expected[ids][1],-expected[ids][2],
        tuple((('upper' if g.startswith(('G01','G02','G08')) else 'lower' if g.startswith(('G03','G04','G05')) else 'one_piece' if g=='G06' else 'outerwear'),g) for g in ids)))
    return garments,prepared,request,expected,winner,Query(garments),Preferences()


@pytest.mark.parametrize('liked',[['blue'],['green'],[]],ids=['blue','green','empty'])
@pytest.mark.parametrize('compact',[True,False],ids=['compact','reference'])
def test_both_engines_every_candidate_against_original_frozen_R_C_and_independent_P2(liked,compact):
    from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
    from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
    from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
    from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
    from app.domain.value_objects.attribute_preferences import PROFILE
    garments,prepared,request,expected,winner,query,prefs=engine_fixture(liked);observed={}
    def audit(value):
        if compact:
            if not value['verified']:return
            ids=tuple(g for _,g in value['key']);s=value['score']
            observed[ids]=(s['request_match']['summary']['value'] or F(),s['compatibility']['decision']['value'],s['preference']['summary']['value'] or F(),s['total'])
        else:
            s=value.score;observed[tuple(m.garment.garment_id for m in value.verified.candidate.members)]=(s.request_match.contribution,s.compatibility.contribution,s.preference.contribution,s.total)
    if compact:
        scorer=CompactExhaustiveScorer(query,prefs,evaluator_type=EvaluatorSpecification.current('context_18_v1'),context_ranking=True,preference_context=prepared,audit=audit)
    else:
        scorer=AggregatedDecisionRecommendationScorer(RequestCandidateEngine(query,evaluator_specification=EvaluatorSpecification.current('context_18_v1')),
            prefs,context_ranking=True,preference_context=prepared);scorer.p2_audit=audit
    result=scorer.rank('owner-A',request)
    assert result.status=='Selected',result
    assert observed==expected
    assert tuple(m.garment.garment_id for m in result.winner.verified.candidate.members)==winner
    assert result.winner.score.profile_name==PROFILE
    assert query.calls==prefs.calls==1


def kernel_rank(garments,prepared,request,compact=True,relative=True,audit=None):
    from tests.test_context_relevance_ranking import Query,Preferences
    from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
    from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
    from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
    from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
    query=Query(garments);prefs=Preferences(prepared.snapshot.legacy_rows() if prepared else ())
    options={'preference_context':prepared} if prepared else {}
    if compact:scorer=CompactExhaustiveScorer(query,prefs,evaluator_type=EvaluatorSpecification.current('context_18_v1'),context_ranking=relative,audit=audit,**options)
    else:
        scorer=AggregatedDecisionRecommendationScorer(RequestCandidateEngine(query,evaluator_specification=EvaluatorSpecification.current('context_18_v1')),prefs,context_ranking=relative,**options)
        scorer.p2_audit=audit
    return scorer.rank('owner-A',request)


@pytest.mark.parametrize('compact',[True,False])
def test_inherited_four_families_reproduce_original_P1_exact_decisions_and_style_mask(compact):
    import json
    from tests.test_context_relevance_ranking import Query,Preferences
    from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
    from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
    from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
    from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
    garments,p,request,_,_,_,_=engine_fixture([])
    legacy=tuple(PreferenceSnapshot(kind,'owner-A',kind,json.dumps({'values':values}),weight,'owner',True) for kind,values,weight in (
        ('colours',['blue'],'0.123456789012'),('styles',['casual'],'1'),('garment_categories',[{'kind':'category','value':'trousers'}],'0.5'),('formality',['casual'],'1')))
    prepared=PreparedAttributePreferences(snapshot({},legacy),p.collection)
    prefs=Preferences(legacy);query=Query(garments)
    if compact:old=CompactExhaustiveScorer(query,prefs,evaluator_type=EvaluatorSpecification.current('context_18_v1'),context_ranking=True).rank('owner-A',request)
    else:old=AggregatedDecisionRecommendationScorer(RequestCandidateEngine(query,evaluator_specification=EvaluatorSpecification.current('context_18_v1')),prefs,context_ranking=True).rank('owner-A',request)
    new=kernel_rank(garments,prepared,request,compact)
    assert old.status==new.status=='Selected',(old,new)
    assert old.winner.verified.candidate.key==new.winner.verified.candidate.key
    assert old.winner.score.total==new.winner.score.total
    assert old.winner.score.preference.contribution==new.winner.score.preference.contribution
    ledger=prepared.public(new.winner.verified,relative=True).to_dict()
    style=next(f for f in ledger['families'] if f['family']=='styles')
    assert style['axes'][0]['mask']['rule']=='duplicate_R_semantic_test_suppressed'


@pytest.mark.parametrize('compact',[True,False])
def test_unresolved_R_competitor_uses_decision_P2_zero_not_raw_upper_one(compact):
    import json
    garments,base,request,_,_,_,_=engine_fixture([])
    # Explicit original occasion admission keeps the missing-style dress eligible;
    # otherwise the mandatory gate excludes it before unresolved R is examined.
    changed=tuple(replace(g,style_tags=None,custom_tags=('rec:v1:occasion:shopping:allow',)) if g.garment_id=='G06' else g for g in garments)
    collection=tuple(replace(item,snapshot=next(g for g in changed if g.garment_id==item.snapshot.garment_id)) for item in base.collection)
    prepared=PreparedAttributePreferences(snapshot({'pattern':family('pattern',['plain'])}),collection)
    result=kernel_rank(changed,prepared,request,compact)
    assert result.status=='Selected',result
    proof=json.loads(result.ranking_evidence)
    assert proof['coverage']['unresolved_candidates']>0 and proof['coverage']['global_optimum_certified']
    assert proof['strongest_unresolved']['optimistic'][-1]=={'numerator':'0','denominator':'1'}
    assert prepared.public(result.winner.verified,relative=True).raw.upper==1


@pytest.mark.parametrize('compact',[True,False])
def test_generic_baseline_uses_P2_without_a_relative_objective(compact):
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
    garments,prepared,_,_,_,_,_=engine_fixture(['blue'])
    request=StructuredOutfitRequest()
    result=kernel_rank(garments,prepared,request,compact,relative=False)
    assert result.status=='Selected',result
    assert result.winner.score.preference.contribution==1
    assert result.ranking_evidence is None
