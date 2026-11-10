"""Bare upper is required; black applies only to canonical trousers."""
import pytest,json
from pathlib import Path
from tests.test_conversational_contexts import pipeline,semantic
from app.domain.value_objects.attribute_conditions import AttributeRequestError
SPEC=json.loads((Path(__file__).parent/'fixtures/wearer_category_acceptance.v1.json').read_text())['nlp']

@pytest.mark.parametrize('text',['i want a shirt with black trousers','i want a top with black trousers','i want a shirt and black trousers','I WANT A SHIRT WITH BLACK TROUSERS'])
def test_frozen_bare_upper_and_lower_colour(pipeline,text):
    _,intent=pipeline.interpret(text)
    expected=json.loads(json.dumps(SPEC['conditions']))
    for group in expected:
        for condition in group['conditions']:condition['values']=sorted(condition['values'])
    assert semantic(intent.conditions.to_dict()['groups'])==expected
    for s in intent.to_dict()['spans']:assert text[s['start']:s['end']]==s['text']

@pytest.mark.parametrize('text',['i want a shirt with waterproof black trousers','i dont want a shirt with black trousers'])
def test_unknown_and_negative_scope_are_not_erased(pipeline,text):
    with pytest.raises(AttributeRequestError):pipeline.interpret(text)

def test_quoted_name_is_literal(pipeline):
    _,intent=pipeline.interpret('i want a garment named "shirt with black trousers"')
    conditions=[c for g in intent.conditions.to_dict()['groups'] for c in g['conditions']]
    assert len(conditions)==1 and conditions[0]['attribute']=='garment_name'
