"""Authored Phase 2B meanings and safety boundaries; no model or live storage."""
import pytest
from app.application.nlp.conversational_context_interpreter import ConversationalContextInterpreter
from app.application.recommendation.conversational_request_pipeline import ConversationalRequestPipeline
from app.application.wardrobe.description_policy import DescriptionPolicy
from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions
from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier
from app.domain.value_objects.attribute_conditions import AttributeConditions,AttributeRequestError
from tests.test_attribute_qualification import make_member,POLICY,condition

@pytest.fixture(scope='module')
def pipeline():return ConversationalRequestPipeline(ConversationalContextInterpreter(),DescriptionPolicy.load())

def parse(pipeline,text):
    request,intent=pipeline.interpret(text)
    assert intent is not None
    for span in intent.to_dict()['spans']:
        assert span['source']=='nlp' and text[span['start']:span['end']]==span['text']
    return request,intent.conditions.to_dict()['groups']

@pytest.mark.parametrize('text',[
    "I don't want shorts.","Don't give me any shorts.",'No shorts, please.',
    'Anything except shorts.','Please avoid shorts.',
])
def test_equivalent_lower_category_exclusions(pipeline,text):
    _,groups=parse(pipeline,text)
    assert [(g['role'],g['quantifier']) for g in groups]==[('lower','none')]
    assert groups[0]['conditions'][0]['attribute']=='category' and groups[0]['conditions'][0]['values']==['shorts']

@pytest.mark.parametrize('text',['Anything except denim.',"I don't want denim.",'No denim clothes.'])
def test_universal_material_exclusion(pipeline,text):
    _,groups=parse(pipeline,text);group=groups[0]
    assert len(groups)==1 and (group['role'],group['quantifier'])==('all_selected','none')
    assert group['conditions'][0]['attribute']=='material' and group['conditions'][0]['values']==['denim']

@pytest.mark.parametrize('text,field,value,role',[
    ('Striped shirt.','pattern','stripe','upper'),('Stripe-patterned top.','pattern','stripe','upper'),
    ('A shirt with stripes.','pattern','stripe','upper'),('Plain trousers.','pattern','plain','lower'),
    ('Regular-fit top.','silhouette','regular','upper'),('Regular fitting shirt.','silhouette','regular','upper'),
    ('Loose-fitting top.','silhouette','loose','upper'),('Long-sleeved shirt.','sleeve_length','wrist-length','upper'),
    ('Short-sleeved top.','sleeve_length','short','upper'),('Sleeveless top.','sleeve_length','sleeveless','upper'),
])
def test_morphological_forms_keep_role_and_canonical_value(pipeline,text,field,value,role):
    _,groups=parse(pipeline,text)
    assert any(g['role']==role and g['quantifier']=='exists' and any(c['attribute']==field and c['values']==[value] for c in g['conditions']) for g in groups)

def test_postnominal_exclusion_is_bound_to_existing_top(pipeline):
    _,groups=parse(pipeline,'A top without stripes.')
    assert [(g['role'],g['quantifier']) for g in groups]==[('upper','exists'),('upper','none')]
    assert groups[1]['conditions'][0]['values']==['stripe']

@pytest.mark.parametrize('text,positive,negative,field,role',[
    ('I want black trousers, not blue ones.','black','blue','primary_colour','lower'),
    ('Black trousers instead of blue trousers.','black','blue','primary_colour','lower'),
    ('Give me a striped shirt, not a plain one.','stripe','plain','pattern','upper'),
    ('I want jeans, but no shorts.','trousers','shorts','category','lower'),
])
def test_unambiguous_contrasts_preserve_both_sides(pipeline,text,positive,negative,field,role):
    _,groups=parse(pipeline,text)
    assert [(g['role'],g['quantifier']) for g in groups]==[(role,'exists'),(role,'none')]
    assert any(c['attribute']==field and positive in c['values'] for c in groups[0]['conditions'])
    assert any(c['attribute']==field and negative in c['values'] for c in groups[1]['conditions'])

@pytest.mark.parametrize('text',[
    "I want shorts, but don't include shorts.",'I want shorts, but no shorts.',
    'I want black trousers, not black ones.','I want jeans, but no denim.',
])
def test_real_contradictions_remain_conflicts(pipeline,text):
    with pytest.raises(AttributeRequestError) as error:pipeline.interpret(text)
    assert error.value.status=='AttributeConflict'

@pytest.mark.parametrize('text',[
    'Give me a blue one.','Not blue ones.',
    'I want a shirt and trousers, not blue ones.',
    'I want black trousers, not blue ones, not red ones.',
    'I want black trousers instead of blue shirts.',
    'Anything except denim and cotton.',
])
def test_unresolved_or_over_complex_scope_never_guesses(pipeline,text):
    with pytest.raises(AttributeRequestError):pipeline.interpret(text)

@pytest.mark.parametrize('text',['Slim-fit shirt.','Relaxed-fit clothes.','I want relaxed-fitting trousers.'])
def test_no_invented_fit_equivalence(pipeline,text):
    with pytest.raises(AttributeRequestError) as error:pipeline.interpret(text)
    assert (error.value.status,error.value.reason)==('UnsupportedAttributeValue','unsupported_fit_mapping')

@pytest.mark.parametrize('text',["I don't want polyester.",'Anything except polyester.','No rayon clothes.'])
def test_exclusion_does_not_add_a_material_vocabulary(pipeline,text):
    with pytest.raises(AttributeRequestError):pipeline.interpret(text)

@pytest.mark.parametrize('text',["I'd prefer cotton.",'Cotton would be nice.','I prefer relaxed-fitting clothes.'])
def test_soft_wishes_never_become_mandatory(pipeline,text):
    with pytest.raises(AttributeRequestError) as error:pipeline.interpret(text)
    assert error.value.reason=='soft_preference_requires_settings'

@pytest.mark.parametrize('text',['Give me something smart casual.','I need something formal.'])
def test_unscoped_formality_requests_need_a_scope(pipeline,text):
    with pytest.raises(AttributeRequestError) as error:pipeline.interpret(text)
    assert error.value.reason=='outfit_style_scope_required'

@pytest.mark.parametrize('style',['casual','smart casual','formal'])
def test_explicit_outfit_style_uses_existing_all_selected_policy(pipeline,style):
    request,groups=parse(pipeline,'Give me a '+style+' outfit.')
    assert request.formality is None
    assert [(g['role'],g['quantifier']) for g in groups]==[('all_selected','all_present')]
    assert groups[0]['conditions'][0]['values']==[style]

@pytest.mark.parametrize('state',['missing','unqualified_model','stale','conflicting'])
def test_unresolved_material_cannot_satisfy_exclusion(pipeline,state):
    request,intent=pipeline.interpret('Anything except denim.')
    upper=make_member('U','material','cotton',state);lower=make_member('L','material','cotton',category='trousers')
    pool=[upper,lower];members=(('upper','U'),('lower','L'))
    assert PreparedAttributeConditions.prepare(intent.conditions,pool,POLICY).evaluate_members(members)=='Unknown'
    assert IndependentAttributeVerifier.prepare(intent.conditions,pool,POLICY).decision(members)=='Unknown'

def test_sleeve_category_is_not_a_substitute_for_fine_evidence(pipeline):
    _,intent=pipeline.interpret('Short-sleeved top.')
    item=make_member('U',category='short_sleeve_top')
    assert PreparedAttributeConditions.prepare(intent.conditions,[item],POLICY).evaluate_members((('upper','U'),))=='Unknown'
    _,groups=parse(pipeline,'I want short sleeve top garment.')
    assert {c['attribute'] for g in groups for c in g['conditions']}=={'category'}

def test_contrast_uses_full_forbidden_conjunction_not_shared_category(pipeline):
    _,intent=pipeline.interpret('I want black trousers, not blue ones.')
    black=make_member('L','primary_colour','black',category='trousers')
    blue=make_member('U','primary_colour','blue')
    assert PreparedAttributeConditions.prepare(intent.conditions,[black,blue],POLICY).evaluate_members((('upper','U'),('lower','L')))=='Pass'

def test_literal_words_do_not_enter_fit_or_pronoun_rules(pipeline):
    _,groups=parse(pipeline,'Suggest garment named "slim-fit one instead of blue ones".')
    assert groups[0]['conditions'][0]['attribute']=='garment_name'

def test_context_guard_does_not_license_nonattribute_exceptions(pipeline):
    for text in ('Anything except dinner.','Shopping instead of dinner.','I do not want to go shopping.'):
        with pytest.raises(AttributeRequestError):pipeline.interpret(text)
