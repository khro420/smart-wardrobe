import pytest
from tests.test_verified_subtype_registry import DATA
from app.application.nlp.conversational_context_interpreter import ConversationalContextInterpreter
from app.application.recommendation.conversational_request_pipeline import ConversationalRequestPipeline
from app.application.wardrobe.description_policy import DescriptionPolicy
@pytest.fixture
def parser(monkeypatch):
    monkeypatch.setenv('SMART_WARDROBE_VERIFIED_SUBTYPE_PROFILE','verified_subtype_v1')
    return ConversationalRequestPipeline(ConversationalContextInterpreter(),DescriptionPolicy.load())
@pytest.mark.parametrize('case',DATA['specification']['nlp_cases'],ids=lambda c:c['text'])
def test_frozen_nouns_descriptors_and_spans(parser,case):
    request,intent=parser.interpret(case['text']);assert intent is not None
    data=intent.to_dict();groups=data['conditions']['groups']
    expected=case['same_member_predicates']
    def matches(group):
        return all(any(c['attribute']==e['attribute'] and c['values']==e.get('values',[e.get('value')]) for c in group['conditions']) for e in expected)
    assert any(matches(g) for g in groups)
    if 'quantifier' in case:assert next(g for g in groups if matches(g))['quantifier']==case['quantifier']
    for span in data['spans']:
        assert case['text'][span['start']:span['end']]==span['text']
    assert data['original_text']==case['text'] and data['version']=='assistant-attribute-intent-2.0.0'
@pytest.mark.parametrize('case',DATA['specification']['context_subtype_cases'],ids=lambda c:c['situation']+':'+c['required_subtype'])
def test_all18_contexts_preserve_subtype_and_situation(parser,case):
    request,intent=parser.interpret(case['text'])
    assert request.context.situation.value==case['situation']
    assert any(c['attribute']=='verified_subtype' and c['values']==[case['required_subtype']] for g in intent.conditions.to_dict()['groups'] for c in g['conditions'])

@pytest.mark.parametrize('text',["I play polo.","I want a button-down shirt.","I want an Oxford shirt.","I prefer a blouse.","I want a blouse without a blouse.","I want a dark polo shirt.","I want a T-shirt blouse."])
def test_unsupported_or_ambiguous_distinctions_are_not_dropped(parser,text):
    from app.domain.value_objects.attribute_conditions import AttributeRequestError
    with pytest.raises(AttributeRequestError):parser.interpret(text)
def test_quoted_name_does_not_become_a_second_type(parser):
    text='I want a T-shirt named "blouse".'
    request,intent=parser.interpret(text)
    fields=[c for g in intent.conditions.to_dict()['groups'] for c in g['conditions']]
    assert [c['values'] for c in fields if c['attribute']=='verified_subtype']==[['t_shirt']]
    assert [c['values'] for c in fields if c['attribute']=='garment_name']==[['blouse']]
def test_literal_only_name_does_not_verify_type(parser):
    _,intent=parser.interpret('I want a garment named "polo shirt".')
    assert all(c['attribute']!='verified_subtype' for g in intent.conditions.to_dict()['groups'] for c in g['conditions'])
