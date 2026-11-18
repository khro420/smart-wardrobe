"""Author-specified Phase 1 meanings; no application startup or live storage."""
from dataclasses import replace
import pytest
from app.application.nlp.conversational_context_interpreter import ConversationalContextInterpreter
from app.application.recommendation.conversational_request_pipeline import ConversationalRequestPipeline
from app.application.wardrobe.description_policy import DescriptionPolicy
from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.domain.value_objects.attribute_conditions import AttributeRequestError

AUDIT = [
    "I'm heading to the mall to buy a few things.",
    "I've got classes tomorrow. What should I wear?",
    "I'm meeting someone for dinner tonight.",
    "I want a black top.",
    "I'd like a striped shirt.",
    "Something made of cotton would be nice.",
    "I prefer loose-fitting clothes.",
    "I don't want to wear shorts.",
    "A black shirt with blue jeans.",
    "Something black on top and blue at the bottom.",
    "I have a presentation at university and I'm the presenter.",
    "I need something smart casual for my job interview as a candidate.",
]


def make_member(identifier,field=None,value=None,state='owner',category='vest'):
    """Synthetic unit evidence built through the unchanged B0 projector."""
    from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
    from app.shared_contracts.confirmed_garment_description import ConfirmedGarmentDescription
    from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
    from app.application.wardrobe import description_projector as b0
    from app.application.wardrobe.description_normalizer import normalise_field
    policy=DescriptionPolicy.load();role,layer=GARMENT_STRUCTURE[category]
    primary=value if field=='primary_colour' else 'blue'
    if state=='missing':primary=None
    snapshot=ConfirmedGarmentSnapshot(identifier,'owner-A','available',category,'Unit fixture','media-A',False,
        '2026-11-14T00:00:00Z',role,layer,primary_colour=primary,style_tags=('casual',))
    row={'id':identifier,'user_id':'owner-A','processing_item_id':'item-'+identifier,'name':'Unit fixture',
         'category':category,'preferred_media_id':'media-A','primary_colour':primary,'attributes_json':'{}'}
    document=b0.project(row,'owner-A',policy).to_dict()
    if field=='material':
        document['fields']['material']=normalise_field('material',[value],policy,origin='owner_selected',
            category=category,media_id='media-A',event_id='00000000-0000-4000-8000-000000000001',
            recorded_at='2026-11-14T00:00:00Z',source_revision='0'*64).to_dict()
    return ConfirmedGarmentDescription(snapshot,b0._document(document['subject'],document['fields']))

@pytest.fixture(scope='module')
def pipeline():
    return ConversationalRequestPipeline(ConversationalContextInterpreter(),DescriptionPolicy.load())

def groups(intent):return intent.conditions.to_dict()['groups'] if intent else []
def clauses(intent):
    return [(g['role'],g['quantifier'],c['attribute'],c['operator'],tuple(c['values'])) for g in groups(intent) for c in g['conditions']]

@pytest.mark.parametrize('index',range(12),ids=lambda i:f'audit-{i+1:02d}')
def test_twelve_author_requests(pipeline,index):
    text=AUDIT[index]
    if index in (5,6):
        with pytest.raises(AttributeRequestError) as error:pipeline.interpret(text)
        assert error.value.reason=='soft_preference_requires_settings'
        return
    request,intent=pipeline.interpret(text)
    expected_context={0:'everyday.shopping',1:'everyday.academic_attendance',2:'social.meal',10:'academic.presentation',11:'professional.job_interview'}
    if index in expected_context:
        assert request.context.situation.value==expected_context[index]
        evaluator=EvaluatorSpecification.current('context_18_v1').construct()
        assert evaluator.summary(request)['available'] is True
        assert request.context.original_text==text
        for name in request.context.__dataclass_fields__:
            slot=getattr(request.context,name)
            for span in getattr(slot,'spans',()):assert text[span.start:span.end]==span.text
    if intent:
        for span in intent.to_dict()['spans']:
            assert span['source']=='nlp' and text[span['start']:span['end']]==span['text']
    if index==3:assert ('upper','exists','primary_colour','in',('black',)) in clauses(intent)
    if index==4:assert ('upper','exists','pattern','in',('stripe',)) in clauses(intent)
    if index==7:assert ('lower','none','category','in',('shorts',)) in clauses(intent)
    if index==8:
        lower=next(g for g in groups(intent) if g['role']=='lower')
        assert {(c['attribute'],tuple(c['values'])) for c in lower['conditions']}=={('primary_colour',('blue',)),('category',('trousers',)),('material',('denim',))}
    if index==9:
        assert clauses(intent)==[('upper','exists','primary_colour','in',('black',)),('lower','exists','primary_colour','in',('blue',))]
        assert request.colours is None
    if index==10:assert request.context.role.value=='presenter'
    if index==11:
        assert request.context.role.value=='candidate' and request.formality=='smart_casual'
        assert request.context.dress_code.value is None and intent is None

def test_swapped_colours_fail_and_missing_colour_stays_unknown(pipeline):
    _,intent=pipeline.interpret(AUDIT[9])
    def evaluate(upper,lower,missing=False):
        u=make_member('u','primary_colour',upper,'missing' if missing else 'owner',category='long_sleeve_top')
        l=make_member('l','primary_colour',lower,category='trousers')
        prepared=PreparedAttributeConditions.prepare(intent.conditions,[u,l],AttributeEvidencePolicy.load())
        return prepared.evaluate_members((('upper','u'),('lower','l')))
    assert evaluate('black','blue')=='Pass'
    assert evaluate('blue','black')=='Fail'
    assert evaluate('black','blue',True)=='Unknown'

def test_category_exclusion_uses_existing_mandatory_evaluator(pipeline):
    _,intent=pipeline.interpret(AUDIT[7]);policy=AttributeEvidencePolicy.load()
    for category,expected in [('shorts','Fail'),('trousers','Pass')]:
        member=make_member('l',category=category)
        prepared=PreparedAttributeConditions.prepare(intent.conditions,[member],policy)
        assert prepared.evaluate_members((('lower','l'),))==expected

@pytest.mark.parametrize('text,expected',[
    ('Black shirt with blue jeans.',{'upper':{'primary_colour'},'lower':{'primary_colour','category','material'}}),
    ('Striped top with plain trousers.',{'upper':{'pattern'},'lower':{'pattern','category'}}),
    ('Cotton shirt and denim pants.',{'upper':{'material'},'lower':{'material','category'}}),
    ('Long-sleeve black top with blue trousers.',{'upper':{'sleeve_length','primary_colour'},'lower':{'primary_colour','category'}}),
])
def test_same_member_conjunctions(pipeline,text,expected):
    _,intent=pipeline.interpret(text)
    assert len(groups(intent))==2
    assert {g['role']:{c['attribute'] for c in g['conditions']} for g in groups(intent)}==expected

def test_material_cannot_be_borrowed_from_another_member(pipeline):
    _,intent=pipeline.interpret('A black cotton shirt with blue jeans.')
    def evaluate(upper_material,lower_material):
        upper=make_member('u','material',upper_material,category='long_sleeve_top')
        upper=replace(upper,snapshot=replace(upper.snapshot,primary_colour='black'))
        lower=make_member('l','material',lower_material,category='trousers')
        prepared=PreparedAttributeConditions.prepare(intent.conditions,[upper,lower],AttributeEvidencePolicy.load())
        return prepared.evaluate_members((('upper','u'),('lower','l')))
    assert evaluate('cotton','denim')=='Pass'
    assert evaluate('denim','cotton')=='Fail'

@pytest.mark.parametrize('text,attribute,value',[
    ('I want a striped top.','pattern','stripe'),
    ('I want a plain top.','pattern','plain'),
    ('I want a loose-fitting top.','silhouette','loose'),
    ('I want a long-sleeved shirt.','sleeve_length','wrist-length'),
])
def test_existing_canonical_attribute_domains(pipeline,text,attribute,value):
    _,intent=pipeline.interpret(text)
    assert any(c[2]==attribute and c[4]==(value,) for c in clauses(intent))

@pytest.mark.parametrize('text',[
    "I'd prefer a cotton shirt.",'Cotton would be nice.','Something made of cotton would be nice.',
    'I prefer loose-fitting clothes.','I want a black top; cotton would be nice.',
])
def test_soft_wording_returns_existing_explicit_limitation(pipeline,text):
    with pytest.raises(AttributeRequestError) as error:pipeline.interpret(text)
    assert error.value.reason=='soft_preference_requires_settings'

@pytest.mark.parametrize('text',[
    'Buy me a black shirt.','Purchase an outfit for shopping.',
    "I'm heading to the mall to buy a few things; buy me a shirt.",
    "I'm heading to the mall to buy waterproof clothes.",
    'I want cotton and polyester.','Something black on top and blue on top.',
    'I want a waterproof cotton shirt.','I want a black or blue top.',
    "I'm going shopping. A wedding.","I'm not going shopping.",
    "I need something smart casual for my job interview as a candidate; the dress code is formal.",
    'Something black on top and blue at the bottom for radioactive work.',
])
def test_unsupported_or_conflicting_meaning_is_not_discarded(pipeline,text):
    with pytest.raises(AttributeRequestError):pipeline.interpret(text)

@pytest.mark.parametrize('text',[
    "I'm going shopping later.","I've got classes tomorrow.","I'm presenting at university tomorrow.",
])
def test_bounded_context_paraphrases(pipeline,text):
    request,intent=pipeline.interpret(text)
    assert request.context.situation.value in ('everyday.shopping','everyday.academic_attendance','academic.presentation')
    assert EvaluatorSpecification.current('context_18_v1').construct().supports(request)

def test_formal_is_not_changed_to_smart_casual(pipeline):
    request,_=pipeline.interpret('I need something formal for my job interview as a candidate.')
    assert request.formality=='formal'
    summary=EvaluatorSpecification.current('context_18_v1').construct().summary(request)
    assert not summary['available'] and summary['reason']=='unsupported_dress_code'

def test_garment_style_does_not_become_dress_code(pipeline):
    request,intent=pipeline.interpret('I want a smart casual shirt for my job interview as a candidate.')
    assert request.formality is None and request.context.dress_code.value is None
    assert any(c[2]=='style' and c[4]==('smart casual',) for c in clauses(intent))
    assert not EvaluatorSpecification.current('context_18_v1').construct().supports(request)

def test_interview_role_is_not_inferred(pipeline):
    request,_=pipeline.interpret('I need something smart casual for my job interview.')
    summary=EvaluatorSpecification.current('context_18_v1').construct().summary(request)
    assert not summary['available'] and 'role' in summary['missing_context']

def test_explicit_dress_code_and_literal_fields_are_preserved(pipeline):
    request,intent=pipeline.interpret("I'm going shopping; the dress code is smart casual.")
    assert request.context.dress_code.value=='smart_casual' and request.formality=='smart_casual'
    _,intent=pipeline.interpret('I want a garment named "buy cotton would be nice".')
    assert clauses(intent)==[('all_selected','exists','garment_name','exact_text',('buy cotton would be nice',))]
