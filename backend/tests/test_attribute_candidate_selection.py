"""Actual structural candidates and literal IDs; score integration follows CP1."""
from dataclasses import replace
import pytest
from tests.test_attribute_qualification import make_member,condition,POLICY,B0_POLICY,LABELS
from app.domain.value_objects.attribute_conditions import AttributeConditions,VERSION
from app.domain.value_objects.outfit_candidate import OutfitCandidate,CandidateMember
from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions,AttributeLedger,conjunction
from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier
from app.application.wardrobe.description_normalizer import normalise_field
from app.application.wardrobe import description_projector as b0
from app.shared_contracts.confirmed_garment_description import ConfirmedGarmentDescription


def with_field(item,field,value):
    document=item.description.to_dict();g=item.snapshot
    record=normalise_field(field,value,B0_POLICY,origin='owner_selected',category=g.category,media_id=g.preferred_media_id,
        event_id='00000000-0000-4000-8000-000000000001',recorded_at='2026-11-04T00:00:00Z',source_revision='0'*64)
    document['fields'][field]=record.to_dict()
    return ConfirmedGarmentDescription(g,b0._document(document['subject'],document['fields']))


def binding_request(q='exists',scope='upper'):
    return AttributeConditions.from_dict({'version':VERSION,'groups':[{'id':'g01','role':scope,'quantifier':q,'conditions':[
      {'id':'c01','attribute':'material','operator':'contains_any','values':['cotton']},
      {'id':'c02','attribute':'neckline','operator':'in','values':['v-neck']}]}]})


def candidate(*members):
    names={'top':'upper','bottom':'lower','dress':'one_piece','outerwear':'outerwear'}
    return OutfitCandidate(tuple(CandidateMember(item.snapshot,names[item.snapshot.structural_role],i+1) for i,item in enumerate(members)))


def test_actual_same_member_filter_uses_fixture_ids():
    cotton=with_field(make_member('U-cotton','material','cotton'),'neckline','crew')
    vneck=with_field(make_member('U-vneck','material','linen'),'neckline','v-neck')
    match=with_field(make_member('U-match','material','cotton'),'neckline','v-neck')
    lower=make_member('L-cotton','material','cotton',category='trousers')
    pool=[cotton,vneck,match,lower];request=binding_request()
    prepared=PreparedAttributeConditions.prepare(request,pool,POLICY)
    independent=IndependentAttributeVerifier.prepare(request,pool,POLICY)
    selected=[]
    for upper in (cotton,vneck,match):
        outfit=candidate(upper,lower);state=prepared.evaluate(outfit)
        assert independent.decision(outfit.key)==state
        if state=='Pass':independent.verify(outfit);selected.append(tuple(m.garment.garment_id for m in outfit.members))
    assert selected==[('U-match','L-cotton')]


@pytest.mark.parametrize('composition',[('vest','trousers'),('vest','trousers','long_sleeve_outwear'),('vest_dress',),('vest_dress','long_sleeve_outwear')])
def test_all_four_structures_hard_filter_all_selected(composition):
    pool=[make_member(str(i),'pattern','plain',category=category) for i,category in enumerate(composition)]
    request=condition('pattern','plain',q='all_present')
    prepared=PreparedAttributeConditions.prepare(request,pool,POLICY)
    independent=IndependentAttributeVerifier.prepare(request,pool,POLICY)
    outfit=candidate(*pool)
    assert prepared.evaluate(outfit)=='Pass';independent.verify(outfit)
    changed=[with_field(pool[0],'pattern','floral'),*pool[1:]]
    assert PreparedAttributeConditions.prepare(request,changed,POLICY).evaluate(candidate(*changed))=='Fail'


@pytest.mark.parametrize('q,expected',[('exists','Fail'),('all_present','Fail'),('none','Pass')])
def test_empty_required_role_and_exclusion(q,expected):
    upper=make_member('U','pattern','plain');lower=make_member('L',category='trousers')
    rq=condition('pattern','plain',q=q,role='outerwear');collection=[upper,lower]
    outfit=candidate(upper,lower)
    assert PreparedAttributeConditions.prepare(rq,collection,POLICY).evaluate(outfit)==expected
    assert IndependentAttributeVerifier.prepare(rq,collection,POLICY).decision(outfit.key)==expected


def test_palette_intervals_keep_unknown_mass_without_renormalizing():
    palette=[{'hex':'#0000ff','coverage':'0.500000'},{'hex':'#ffffff','coverage':'0.250000'}]
    item=with_field(make_member('U'),'colour_palette',palette)
    for minimum,expected in [('0.5','Pass'),('0.6','Unknown'),('0.8','Fail')]:
        rq=condition('palette_coverage',{'colour':'blue','minimum':minimum},op='coverage_ge')
        actual=PreparedAttributeConditions.prepare(rq,[item],POLICY)
        independent=IndependentAttributeVerifier.prepare(rq,[item],POLICY)
        assert actual.evaluate_members((('upper','U'),))==expected
        assert independent.decision((('upper','U'),))==expected


def test_known_failure_precedes_unknown_in_ledger():
    ledger=AttributeLedger()
    assert ledger.observe('Unknown','Fail')=='Fail'
    assert ledger.observe('Fail','Pass')=='Fail'
    assert ledger.observe('Pass','Unknown')=='Unknown'
    assert ledger.observe('Pass','Pass')=='Pass'
    assert ledger.snapshot()=={'structural_examined':4,'legacy_failed':1,'legacy_unknown':0,'attribute_failed':1,'attribute_unknown':1,'joint_passed':1}


def integrated_fixture():
    pool=[with_field(make_member('U-cotton','material','cotton'),'neckline','crew'),
      with_field(make_member('U-vneck','material','linen'),'neckline','v-neck'),
      with_field(make_member('U-match','material','cotton'),'neckline','v-neck'),
      make_member('U-unknown','material','cotton','unqualified_model'),
      make_member('L-cotton','material','cotton',category='trousers')]
    request=binding_request()
    prepared=PreparedAttributeConditions.prepare(request,pool,POLICY)
    independent=IndependentAttributeVerifier.prepare(request,pool,POLICY)
    class Query:
        def get_confirmed_available_garments(self,owner):
            assert owner=='owner-A'
            return tuple(item.snapshot for item in pool)
    return Query(),prepared,independent


def test_actual_reference_stream_rejects_mismatch_and_unknown_before_scoring():
    from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
    query,prepared,independent=integrated_fixture()
    stream=RequestCandidateEngine(query,attribute_context=prepared,attribute_verifier=independent).generate_candidates('owner-A',StructuredOutfitRequest())
    candidates=list(stream)
    assert [tuple(m.garment.garment_id for m in c.candidate.members) for c in candidates]==[('U-match','L-cotton')]
    assert (stream.result.passed,stream.result.failed,stream.result.unknown)==(1,2,1)
    assert stream.attribute_ledger.snapshot()['joint_passed']==1


def test_actual_compact_kernel_selects_only_the_qualified_bound_candidate():
    from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
    query,prepared,independent=integrated_fixture()
    class Preferences:
        def get_active_preferences(self,owner):return ()
    scorer=CompactExhaustiveScorer(query,Preferences(),attribute_context=prepared,attribute_verifier=independent)
    outcome=scorer.rank('owner-A',StructuredOutfitRequest())
    assert outcome.status=='Selected' and outcome.complete
    assert tuple(m.garment.garment_id for m in outcome.winner.verified.candidate.members)==('U-match','L-cotton')
    assert scorer.attribute_ledger.snapshot()=={'structural_examined':4,'legacy_failed':0,'legacy_unknown':0,'attribute_failed':2,'attribute_unknown':1,'joint_passed':1}


FINITE_CASES=LABELS['finite']['cases']
ROLE={'top':'upper','bottom':'lower','dress':'one_piece','outerwear':'outerwear'}


@pytest.mark.parametrize('case',FINITE_CASES,ids=lambda c:c['id'])
def test_complete_frozen_finite_obligation(case):
    """All 14 authored obligations per expression, without changing their labels."""
    from app.domain.value_objects.attribute_conditions import AttributeRequestError,conjoin
    kind=case['case'];field=case['attribute'];value=case['value'];op=case['request_operator']
    if case['expected']=='UnsupportedAttributeValue':
        # palette cream has no named-family anchor; every other domain gets an
        # explicitly unsupported member rather than a fabricated nearest value.
        with pytest.raises(AttributeRequestError):
            condition(field,value if field=='palette_colour' and value=='cream' else '__unsupported_value__',op=op)
        return
    rq=condition(field,value,op=op)
    if kind=='contradiction':
        with pytest.raises(AttributeRequestError) as error:conjoin(rq,condition(field,value,op=op,q='none'))
        assert error.value.status==case['expected'];return
    state=kind if kind in ('missing','stale','conflicting','malformed','unqualified_model') else 'missing' if kind=='negative_unknown' else 'owner'
    actual=case['known_other'] if kind in ('known_mismatch','negative_complete_absence') else value
    item=make_member('eligible-match',field,actual,state)
    role=ROLE[item.snapshot.structural_role]
    if kind=='role_applicability':rq=condition(field,value,op=op,role='upper' if role=='one_piece' else 'one_piece')
    if kind.startswith('negative_'):rq=condition(field,value,op=op,q='none')
    prepared=PreparedAttributeConditions.prepare(rq,[item],POLICY)
    independent=IndependentAttributeVerifier.prepare(rq,[item],POLICY)
    assert prepared.evaluate_members(((role,item.snapshot.garment_id),))==case['expected']
    assert independent.decision(((role,item.snapshot.garment_id),))==case['expected']


@pytest.mark.parametrize('case',[c for c in FINITE_CASES if c['case']=='actual_filter'],ids=lambda c:c['id'])
def test_each_enabled_finite_value_changes_actual_exhaustive_selection(case):
    """Real structural enumeration/ranking, not merely registration or parsing."""
    from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
    from app.domain.value_objects.attribute_conditions import AttributeRequestError
    field,value,op=case['attribute'],case['value'],case['request_operator']
    if case['expected']=='UnsupportedAttributeValue':
        with pytest.raises(AttributeRequestError):condition(field,value,op=op)
        return
    if field=='palette_coverage':
        target=with_field(make_member('eligible-match'),'colour_palette',[{'hex':'#123abc','coverage':'0.500000'},{'hex':'#ffffff','coverage':'0.250000'}])
        other=with_field(make_member('ineligible-mismatch'),'colour_palette',[{'hex':'#ff0000','coverage':'1'}])
        unknown=make_member('ineligible-missing')
    else:
        target=make_member('eligible-match',field,value)
        other=make_member('ineligible-mismatch',field,case['known_other'])
        unknown=make_member('ineligible-missing',field,value,'missing')
    role=ROLE[target.snapshot.structural_role]
    companions=[]
    if role in ('upper','outerwear'):companions.append(make_member('base-lower',category='trousers'))
    if role in ('lower','outerwear'):companions.append(make_member('base-upper',category='vest'))
    pool=[target,other,unknown,*companions]
    rq=condition(field,value,op=op,role=role)
    prepared=PreparedAttributeConditions.prepare(rq,pool,POLICY)
    independent=IndependentAttributeVerifier.prepare(rq,pool,POLICY)
    class Query:
        def get_confirmed_available_garments(self,owner):
            assert owner=='owner-A';return tuple(i.snapshot for i in pool)
    class Preferences:
        def get_active_preferences(self,owner):return ()
    scorer=CompactExhaustiveScorer(Query(),Preferences(),attribute_context=prepared,attribute_verifier=independent)
    outcome=scorer.rank('owner-A',StructuredOutfitRequest())
    assert outcome.status=='Selected' and outcome.complete
    ids=tuple(m.garment.garment_id for m in outcome.winner.verified.candidate.members)
    assert 'eligible-match' in ids
    assert not {'ineligible-mismatch','ineligible-missing'}.intersection(ids)
    # The source request adds a hard gate, never an extra score component.
    assert outcome.winner.score.weights==( __import__('fractions').Fraction(3,5),__import__('fractions').Fraction(1,5),__import__('fractions').Fraction(1,5))


def test_unknown_seen_and_below_floor_counter_never_scores_unknown():
    from fractions import Fraction
    from app.application.recommendation.attribute_condition_evaluator import AttributeRefinementCounterGuard
    class Facts:
        def bounds(self,roles,indexes):
            assert roles==('upper','lower') and indexes==(1,2)
            return Fraction(1,4),Fraction(1,2)
    guard=AttributeRefinementCounterGuard({'U':1,'L':2},Facts(),Fraction(3,4),frozenset())
    members=(('upper','U'),('lower','L'))
    assert guard.ignores(members)
    assert not replace(guard,floor=Fraction(1,2)).ignores(members) # equality stays eligible
    assert replace(guard,seen=frozenset([members])).ignores(members)
    ledger=AttributeLedger()
    for ignored in (True,True,False):assert ledger.observe('Pass','Unknown',seen=ignored)=='Unknown'
    assert ledger.unseen_unknown==1 and ledger.snapshot()['attribute_unknown']==3


@pytest.mark.parametrize('field,value,other,operator',[
    ('garment_name','Named \U0001f455 shirt','Other literal name','exact_text'),
    ('descriptive_tag','handmade, literal note','other literal note','exact_text'),
    ('primary_colour','#123abc','#445566','exact_hex'),
    ('secondary_colour','#123abc','#445566','exact_hex'),
    ('palette_colour','#123abc','#445566','exact_hex'),
    ('palette_coverage',{'colour':'#123abc','minimum':'0.500000'},None,'coverage_ge'),
    ('material',['cotton','linen'],'cotton','contains_all')])
def test_dynamic_domains_change_actual_exhaustive_selection(field,value,other,operator):
    test_each_enabled_finite_value_changes_actual_exhaustive_selection(dict(attribute=field,value=value,
        known_other=other,request_operator=operator,expected='Pass'))
