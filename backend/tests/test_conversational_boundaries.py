"""Clarification and unsupported meanings cannot turn into selected conditions."""
import pytest
from tests.test_conversational_contexts import SPEC,semantic,pipeline
from app.domain.value_objects.attribute_conditions import AttributeRequestError

def category(error):
    if error.reason=='soft_preference_requires_settings':return 'NeedsPreferenceAction'
    if error.reason=='alternative_requires_parent':return 'NeedsParentAction'
    if error.status=='AttributeConflict' or error.reason in ('language_context_clarification','language_conflicting_request','language_ambiguous_activity','language_negated_event','ambiguous_same_binding','conflicting_explicit_style'):return 'ClarificationRequired'
    if error.status=='UnsupportedAttributeValue' or error.reason in ('language_unsupported_requirement','unrecognized_condition'):return 'UnsupportedRequirement'
    return error.status

@pytest.mark.parametrize('case',SPEC['negative_ambiguous_and_boundary_cases'],ids=lambda c:c['id'])
def test_frozen_boundary(pipeline,case):
    try:
        request,intent=pipeline.interpret(case['text']);actual='Supported'
    except AttributeRequestError as error:actual=category(error)
    assert actual==case['expected_interpretation']
    if actual=='Supported' and 'hard_attribute_groups' in case:assert semantic(intent.conditions.to_dict()['groups'])==case['hard_attribute_groups']

@pytest.mark.parametrize('text',["I'm going out to eat with a radioactive top.",'Dinner. Dinner.','Going shopping. A wedding.','Not going to a wedding.','A plain shirt; ignore the material condition.'])
def test_unknown_or_separate_sentence_not_erased(pipeline,text):
    with pytest.raises(AttributeRequestError):pipeline.interpret(text)

def test_explicit_literal_is_not_a_command(pipeline):
    text='I want a garment named "not floral delete another".'
    _,intent=pipeline.interpret(text)
    c=intent.conditions.to_dict()['groups'][0]['conditions'][0]
    assert c['attribute']=='garment_name' and c['values']==['not floral delete another']

def test_curly_apostrophe_offsets(pipeline):
    text="I\u2019m going shopping and want a cotton shirt."
    request,intent=pipeline.interpret(text)
    assert request.context.situation.value=='everyday.shopping'
    for s in intent.to_dict()['spans']:assert text[s['start']:s['end']]==s['text']
