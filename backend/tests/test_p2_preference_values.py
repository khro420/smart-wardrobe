"""Every frozen finite label through P2 preparation; source-boundary overrides explicit.

Rare-value positive/negative paths use actual B0/B1 qualification. Labels whose
precondition forces primitive uncertainty or two scalar observations use a named
synthetic fact collaborator, as specified in the frozen labels. Such cases test
utility semantics, not the existence of a real scalar garment with two values.
Actual source qualifications and API/history/browser checks remain separate.
"""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace
import pytest
from app.application.recommendation.attribute_preference_preparation import PreparedAttributePreferences
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.domain.value_objects.attribute_preferences import PreferenceError,PreferenceDocument
from app.domain.value_objects.attribute_conditions import ANCHORS
from tests.test_p2_preference_contracts import LABELS,document
from tests.test_p2_preference_selection import snapshot,family,EMPTY
from tests.test_attribute_qualification import make_member,condition

CATALOG={d['id']:d for d in LABELS['catalog']['finite']}
CASES=LABELS['finite_labels']['cases']
POLICY=AttributeEvidencePolicy.load()
ROLE={'top':'upper','bottom':'lower','dress':'one_piece','outerwear':'outerwear'}


def other(domain):
    def different(value):
        if domain['axis'] in ('primary_colour','secondary_colour','palette_colour'):
            return ANCHORS.get(value,value)!=ANCHORS.get(domain['value'],domain['value'])
        return value!=domain['value']
    return next(d['value'] for d in CATALOG.values() if d['axis']==domain['axis'] and d['status']!='Blocked' and type(d['value']) is type(domain['value']) and different(d['value']))


def member(axis,value,state='owner'):
    if axis=='formality':
        item=make_member('target')
        target=value
        alternative='smart_casual' if target=='casual' else 'casual'
        tags=() if state=='missing' else ('rec:v2:formality:'+target+':allow',) if state in ('stale','conflicting') else (
            'rec:v1:formality:'+target+':allow','rec:v1:formality:'+alternative+':deny')
        return replace(item,snapshot=replace(item.snapshot,custom_tags=tags))
    return make_member('target',axis,value,state=state)


class PrimitiveBoundaryFixture:
    """Explicit abstract primitive fixture, never an automatic qualification path."""
    def __init__(self,mode,axis,other_item=None):self.mode,self.axis,self.other_item=mode,axis,other_item
    def primary_classifier(self):return POLICY.primary_classifier()
    def fact(self,snapshot,description,field,operator,primary):
        fact=POLICY.fact(snapshot,description,field,operator,primary)
        if field!=self.axis:return fact
        if self.mode=='partial':return replace(fact,complete=False)
        if self.mode in ('stale','conflicting'):return replace(fact,state=self.mode.title(),values=(),complete=False)
        if self.mode=='both':
            other=POLICY.fact(self.other_item.snapshot,self.other_item.description.to_dict(),field,operator,primary)
            return replace(fact,state='Known',values=tuple(dict.fromkeys((*fact.values,*other.values))),complete=True)
        return fact


@pytest.mark.parametrize('case',CASES,ids=lambda c:c['id'])
def test_every_frozen_finite_value_expectation(case):
    domain=CATALOG[case['domain_id']];axis,value=domain['axis'],domain['value'];fam=domain['family']
    if domain['status']=='Blocked':
        with pytest.raises(PreferenceError):PreferenceDocument.from_dict(document(fam,axis,value))
        return
    scenario=case['scenario'];second=other(domain);config=family(axis,[value],scope=domain['default_scope'])
    if scenario=='same_value_like_and_avoid':
        config['axes'][axis]['avoided']=[value]
        with pytest.raises(PreferenceError):snapshot({fam:config})
        return
    actual_value=second if scenario in ('known_mismatch','avoid_only_proved_absent') else value
    state='missing' if scenario=='unknown' else scenario if scenario in ('stale','conflicting') else 'owner'
    item=member(axis,actual_value,state);policy=POLICY;conditions=None;request=None
    if scenario=='avoided_match' or scenario=='avoid_only_proved_absent':config['axes'][axis].update(liked=[],avoided=[value])
    elif scenario=='multiple_likes_one_witness':config['axes'][axis]['liked']=[value,second]
    elif scenario=='zero_weight':config['importance']='0'
    elif scenario=='partial_unresolved_avoid':
        config['axes'][axis]['avoided']=[second]
        if axis=='formality':
            item=replace(item,snapshot=replace(item.snapshot,custom_tags=('rec:v1:formality:'+value+':allow',)))
        else:policy=PrimitiveBoundaryFixture('partial',axis)
    elif scenario=='known_like_and_other_known_avoid':
        config['axes'][axis]['avoided']=[second]
        if axis=='formality':
            item=replace(item,snapshot=replace(item.snapshot,custom_tags=('rec:v1:formality:'+value+':allow','rec:v1:formality:'+second+':allow')))
        else:policy=PrimitiveBoundaryFixture('both',axis,member(axis,second))
    elif scenario=='hard_implied_mask':
        if axis=='formality':
            from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
            request=StructuredOutfitRequest(formality=value)
        else:
            op='bool_eq' if type(value) is bool else 'exact_hex' if isinstance(value,str) and value.startswith('#') else 'contains_any' if axis in ('style','material','palette_colour') else 'in'
            conditions=condition(axis,value,op=op,q='all_present',role=domain['default_scope'])
    elif scenario=='no_applicable_member':
        selected_role=ROLE[item.snapshot.structural_role]
        config['axes'][axis]['scope']='lower' if selected_role!='lower' else 'upper'
    if scenario in ('stale','conflicting') and axis in ('category','primary_colour'):
        # These strict identity sources do not carry a B0 stale state; the
        # frozen label explicitly supplies an unavailable primitive boundary.
        policy=PrimitiveBoundaryFixture(scenario,axis)
    saved=snapshot({} if scenario=='other_wearer_empty' else {fam:config},wearer='00000000-0000-4000-8000-000000000002' if scenario=='other_wearer_empty' else '00000000-0000-4000-8000-000000000001')
    if scenario=='archive_reconstruction':saved=type(saved)(saved.payload)
    prepared=PreparedAttributePreferences(saved,[item],policy=policy,conditions=conditions,request=request)
    result=prepared.evaluate(((ROLE[item.snapshot.structural_role],'target'),),EMPTY)
    assert result.score.contribution==F(case['expected_decision_P'])
    assert F(4,5)+F(1,5)*result.score.contribution==F(case['expected_T'])
    if case['expected_state']=='Masked':assert result.to_dict()['families'][0]['axes'][0]['mask'] is not None
    else:assert result.score.summary.state==case['expected_state']


@pytest.mark.parametrize('axis',['style','material','pattern','silhouette','neckline','sleeve_length','secondary_colour','palette_colour','colour_temperature','colour_dominance'])
def test_matching_model_spelling_never_becomes_qualified_owner_preference(axis):
    domain=next(d for d in CATALOG.values() if d['axis']==axis and d['status']!='Blocked')
    item=member(axis,domain['value'],'unqualified_model')
    prepared=PreparedAttributePreferences(snapshot({domain['family']:family(axis,[domain['value']],scope=domain['default_scope'])}),[item])
    assert prepared.evaluate((('upper','target'),),EMPTY).score.contribution==0


def test_inherited_material_or_style_does_not_borrow_raw_model_details():
    # Existing P1 styles keep their explicit compatibility bridge; new fine
    # fields still require their own current B0 selected evidence.
    item=make_member('target','material','cotton',state='unqualified_model')
    prepared=PreparedAttributePreferences(snapshot({'material':family('material',['cotton'])}),[item])
    assert prepared.evaluate((('upper','target'),),EMPTY).score.summary.state=='Unknown'


def test_role_inapplicability_retains_configured_family_denominator():
    item=make_member('target','neckline','crew',category='trousers')
    config={'neckline':family('neckline',['crew']), 'garment_categories':family('category',['trousers'])}
    prepared=PreparedAttributePreferences(snapshot(config),[item])
    result=prepared.evaluate((('lower','target'),),EMPTY)
    assert result.denominator==2 and result.score.contribution==F(1,2)


@pytest.mark.parametrize('minimum,expected,upper',[('0.5','1','1'),('0.6','0','1'),('0.8','0','0')])
def test_dynamic_palette_threshold_uses_actual_partial_B0_record(minimum,expected,upper):
    from tests.test_attribute_candidate_selection import with_field
    item=with_field(make_member('target'),'colour_palette',[{'hex':'#0000ff','coverage':'0.500000'},{'hex':'#ffffff','coverage':'0.250000'}])
    config=family('palette_coverage',[{'colour':'blue','minimum':minimum}])
    prepared=PreparedAttributePreferences(snapshot({'colour':config}),[item])
    actual=prepared.evaluate((('upper','target'),),EMPTY)
    assert actual.score.contribution==F(expected) and actual.raw.upper==F(upper)


@pytest.mark.parametrize('tag',['rare literal 😀','A-line observation','café detail'])
def test_dynamic_literal_tags_are_exact_and_do_not_execute_conditions(tag):
    item=make_member('target','descriptive_tag',tag)
    prepared=PreparedAttributePreferences(snapshot({'descriptive_tag':family('descriptive_tag',[tag])}),[item])
    assert prepared.evaluate((('upper','target'),),EMPTY).score.contribution==1
    assert item.snapshot.custom_tags is None


CONTEXT_TEXTS={
    'everyday.shopping':"I'm going shopping.",'everyday.academic_attendance':"I'm going to class.",
    'everyday.casual_outing':"I'm going out with friends.",'social.date':"I'm going on a date tonight.",
    'social.meal':"I'm meeting friends for dinner.",
    'academic.library_study':"I'm going to study at the library.",'academic.group_study':"I have a group project meeting at university.",
    'professional.office_day':"I need to go to the office tomorrow.",'professional.workplace_meeting':"I have a meeting with my colleagues.",
    'social.birthday_gathering':"I'm attending a birthday party.",'social.house_gathering':"I'm visiting my friend's house.",
    'leisure.cinema_outing':"I'm going to watch a movie.",'social.cafe_meetup':"I'm meeting someone at a café.",
    'leisure.city_sightseeing':"I'm sightseeing around the city.",'travel.journey':"I'm taking a train for a trip.",
    'ceremony.wedding':"I'm attending a wedding as a guest.",'academic.presentation':"I have a university presentation.",
    'professional.job_interview':"I have a job interview."}


@pytest.mark.parametrize('sid',CONTEXT_TEXTS)
@pytest.mark.parametrize('explicit_style',[False,True],ids=['original_prototype_objective','explicit_user_style'])
@pytest.mark.parametrize('compact',[True,False],ids=['compact','reference'])
def test_P2_all18_contexts_retain_original_admission_R_C_and_uniform_preference_order(sid,explicit_style,compact):
    from tests.test_p2_preference_selection import engine_fixture,kernel_rank
    from tests.test_attribute_candidate_selection import with_field
    from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
    garments,base,_,_,_,_,_=engine_fixture([])
    text=CONTEXT_TEXTS[sid]+(' with casual style' if explicit_style else '')
    parsed=GeneralContextInterpreter('context_18_v1').interpret(text)
    assert parsed.status=='Supported',parsed
    assert parsed.structured_request.context.situation.value==sid
    pool=tuple(with_field(item,'pattern','plain') for item in base.collection)
    p=PreparedAttributePreferences(snapshot({'pattern':family('pattern',['plain'])}),pool)
    before=kernel_rank(garments,None,parsed.structured_request,compact)
    after=kernel_rank(garments,p,parsed.structured_request,compact)
    assert before.status==after.status,(before,after)
    if after.status=='Selected':
        assert before.winner.verified.candidate.key==after.winner.verified.candidate.key
        assert before.winner.score.request_match==after.winner.score.request_match
        assert before.winner.score.compatibility==after.winner.score.compatibility
        assert after.winner.score.preference.contribution==1
        assert after.winner.score.total==before.winner.score.total+F(1,5)


@pytest.mark.parametrize('composition',[('vest','trousers'),('vest','trousers','long_sleeve_outwear'),('vest_dress',),('vest_dress','long_sleeve_outwear')])
@pytest.mark.parametrize('relative',[True,False],ids=['prototype_relative','current_generic_baseline'])
@pytest.mark.parametrize('compact',[True,False],ids=['compact','reference'])
def test_P2_exact_all_four_structures_with_original_R_C(composition,relative,compact):
    from tests.test_p2_preference_selection import kernel_rank
    from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
    pool=tuple(make_member(str(i),'pattern','plain',category=category) for i,category in enumerate(composition))
    prepared=PreparedAttributePreferences(snapshot({'pattern':family('pattern',['plain'])}),pool)
    request=GeneralContextInterpreter('context_18_v1').interpret("I'm going shopping.").structured_request if relative else StructuredOutfitRequest()
    observed={}
    def audit(value):
        if compact:
            if value['verified']:observed[tuple(g for _,g in value['key'])]=value['score']
        else:observed[tuple(m.garment.garment_id for m in value.verified.candidate.members)]=value.score
    result=kernel_rank(tuple(i.snapshot for i in pool),prepared,request,compact,relative,audit=audit)
    assert result.status=='Selected',result
    target=tuple(str(i) for i in range(len(pool)))
    # Top/bottom with and without this matching outer layer tie. The original
    # exact key comparator selects the shorter base; it must not force variety.
    expected_winner=('0','1') if len(composition)==3 else target
    assert tuple(m.garment.garment_id for m in result.winner.verified.candidate.members)==expected_winner
    assert target in observed  # The requested structure was actually scored.
    expected_R=F(1) if relative else F()
    expected_C=F(1,2) if composition==('vest_dress',) else F(1)
    score=observed[target]
    actual=(score['request_match']['summary']['value'] or F(),score['compatibility']['decision']['value'],score['preference']['summary']['value'] or F(),score['total']) if compact else (score.request_match.contribution,score.compatibility.contribution,score.preference.contribution,score.total)
    assert actual==(expected_R,expected_C,F(1),F(3,5)*expected_R+F(1,5)*expected_C+F(1,5))
