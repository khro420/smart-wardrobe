"""Literal authored semantic fixtures; never use parser output for expected groups."""
import json
from pathlib import Path
import pytest
from app.application.nlp.attribute_request_interpreter import AttributeRequestInterpreter
from app.domain.value_objects.attribute_conditions import AttributeRequestError

LABELS=json.loads((Path(__file__).parent/'fixtures/attribute_labels.v1.json').read_text(encoding='utf-8'))
EXAMPLES=LABELS['language']['examples']
REGISTRY=json.loads((Path(__file__).parents[1]/'app/application/nlp/config/attribute_grammar.v1.json').read_text(encoding='utf-8'))['entries']


@pytest.fixture(scope='module')
def parser():return AttributeRequestInterpreter()


def semantic(value):
    return [(g['role'],g['quantifier'],[(c['attribute'],c['operator'],c['values']) for c in g['conditions']]) for g in value.to_dict()['groups']]


@pytest.mark.parametrize('case',EXAMPLES,ids=lambda c:c['id'])
def test_owner_examples_bind_all_conditions_with_original_spans(parser,case):
    outcome=parser.parse(case['text'])
    assert outcome.conditions is not None
    from app.domain.value_objects.attribute_conditions import AttributeConditions
    assert semantic(outcome.conditions)==semantic(AttributeConditions.from_dict(case['expected_conditions']))
    assert all(case['text'][start:end]==text for _,_,start,end,text in outcome.spans)
    assert len(outcome.remaining)==len(case['text'])


@pytest.mark.parametrize('entry',REGISTRY,ids=lambda c:c['attribute']+'-'+str(c['value']))
def test_every_registered_finite_expression_is_usable(parser,entry):
    text='I want '+entry['expression']+'.'
    if entry['status']=='Blocked':
        with pytest.raises(AttributeRequestError):parser.parse(text)
        return
    outcome=parser.parse(text)
    observations=[c for g in outcome.conditions.to_dict()['groups'] for c in g['conditions']]
    assert len(observations)==1
    assert observations[0]['attribute']==entry['attribute'] and observations[0]['values']==[entry['value']]


@pytest.mark.parametrize('entry',REGISTRY,ids=lambda c:c['attribute']+'-'+str(c['value']))
def test_every_finite_negative_preserves_its_polarity(parser,entry):
    if entry['status']=='Blocked':return
    outcome=parser.parse(entry['negative_expression'])
    assert all(g['quantifier']=='none' for g in outcome.conditions.to_dict()['groups'])


def test_unknown_meaning_is_left_visible(parser):
    result=parser.parse('I want a waterproof cotton v-neck top.')
    assert 'waterproof' in result.remaining
    assert len(result.conditions.to_dict()['groups'][0]['conditions'])==2


def test_positive_role_with_negative_description_requires_role_and_excludes_within_it(parser,pipeline):
    text='I want a top with no cotton material.'
    parsed=parser.parse(text);groups=parsed.conditions.to_dict()['groups']
    assert [(g['role'],g['quantifier']) for g in groups]==[('upper','exists'),('upper','none')]
    assert groups[0]['conditions'][0]['values']==['long_sleeve_top','short_sleeve_top','sling','vest']
    assert groups[1]['conditions'][0]['values']==['cotton']
    assert pipeline.interpret(text)[1].conditions==parsed.conditions
    assert all(text[start:end]==raw for _,_,start,end,raw in parsed.spans)


def test_original_unicode_and_quoted_literal_are_not_keyword_parsed(parser):
    text='Suggest garment named "\U0001f455 plain silk".'
    outcome=parser.parse(text)
    condition=outcome.conditions.to_dict()['groups'][0]['conditions'][0]
    assert condition['attribute']=='garment_name' and condition['values']==['\U0001f455 plain silk']
    assert len(outcome.conditions.to_dict()['groups'])==1
    assert all(text[a:b]==v for _,_,a,b,v in outcome.spans)


def test_negated_conjunction_is_one_binding(parser):
    parsed=parser.parse('No cotton v-neck top.')
    group=parsed.conditions.to_dict()['groups'][0]
    assert group['quantifier']=='none' and len(group['conditions'])==2


def test_double_negation_refuses(parser):
    with pytest.raises(AttributeRequestError):parser.parse('No not floral pattern.')


@pytest.fixture(scope='module')
def pipeline():
    from app.application.recommendation.attribute_request_pipeline import AttributeRequestPipeline
    from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
    from app.application.wardrobe.description_policy import DescriptionPolicy
    return AttributeRequestPipeline(GeneralContextInterpreter('context_18_v1'),DescriptionPolicy.load())


@pytest.mark.parametrize('case',EXAMPLES,ids=lambda c:c['id'])
def test_examples_compose_with_the_actual_context_interpreter(pipeline,case):
    request,intent=pipeline.interpret(case['text'])
    if case['existing_context']:
        expected=case['existing_context'].split(' + ')[0]
        assert request.context.situation.value==expected
        assert request.context.original_text==case['text']
    if case['id']!='LANG05':assert intent is not None


def test_unknown_meaning_cannot_escape_through_pipeline(pipeline):
    with pytest.raises(AttributeRequestError):pipeline.interpret('I want a waterproof cotton v-neck top.')


def test_typed_only_nonconsecutive_ids_have_no_fabricated_text_span(pipeline):
    from tests.test_attribute_conditions import request
    typed=request();typed['groups'][0]['id']='g07';typed['groups'][0]['conditions'][0]['id']='c09'
    _,intent=pipeline.interpret("I'm going shopping.",typed)
    assert intent.to_dict()['spans']==[{'condition_id':'c09','source':'typed','start':None,'end':None,'text':None}]


def test_ordinary_shopping_projection_is_identical(pipeline):
    text="I'm going shopping."
    actual,intent=pipeline.interpret(text)
    expected=pipeline.interpreter.interpret(text)
    assert intent is None and actual.to_dict()==expected.structured_request.to_dict()


@pytest.mark.parametrize('text,role,q,operator,values',[
 ('I want both cotton and linen material.','all_selected','exists','contains_all',['cotton','linen']),
 ('I want both cotton and linen tops.','upper','exists','contains_all',['cotton','linen']),
 ('Suggest every top must have plain pattern for university.','upper','all_present','in',['plain']),
 ('I want a top with cotton material and v-neck neckline.','upper','exists','contains_any',['cotton']),
 ('No tops with floral pattern.','upper','none','in',['floral'])])
def test_registered_set_quantifier_and_bound_role_frames(pipeline,text,role,q,operator,values):
    request,intent=pipeline.interpret(text)
    group=intent.conditions.to_dict()['groups'][0]
    assert group['role']==role and group['quantifier']==q
    assert group['conditions'][0]['operator']==operator and group['conditions'][0]['values']==values
    if 'v-neck' in text:assert len(group['conditions'])==2
    if 'university' in text:assert request.context.situation.value=='everyday.academic_attendance'


@pytest.mark.parametrize('text',['I want plain pattern and.','I want a cotton top for.','Recommend a waterproof cotton top for university.','Suggest a cotton top and delete history for university.'])
def test_residual_qualifier_and_forbidden_command_never_drop(pipeline,text):
    with pytest.raises(AttributeRequestError):pipeline.interpret(text)
