"""Owner-approved meanings frozen before implementation; no observed-score goldens."""
import json
from pathlib import Path
import pytest
from tests.test_conversational_contexts import pipeline,semantic
from app.domain.value_objects.attribute_conditions import AttributeRequestError

SPEC=json.loads((Path(__file__).parent/'fixtures/manual_binding_acceptance.v1.json').read_text())

@pytest.mark.parametrize('case',SPEC['cases'],ids=lambda c:c['id'])
@pytest.mark.parametrize('capitalized',[False,True])
def test_exact_independent_member_meaning(pipeline,case,capitalized):
    text=case['text'].upper() if capitalized else case['text']
    _,intent=pipeline.interpret(text)
    assert semantic(intent.conditions.to_dict()['groups'])==case['conditions']
    assert intent.to_dict()['original_text']==text
    for s in intent.to_dict()['spans']:
        if s['source']=='nlp':assert text[s['start']:s['end']]==s['text']

@pytest.mark.parametrize('text',[
    'i want a waterproof blue top','i want a blue cotton top with radioactive sleeves',
    'something blue or cotton with long sleeves','i want a blue top except black trousers',
    'i prefer a blue cotton top with long sleeves',
])
def test_unknown_or_soft_scope_never_disappears(pipeline,text):
    with pytest.raises(AttributeRequestError):pipeline.interpret(text)

def test_category_only_literal_and_quote_do_not_infer_fine_evidence(pipeline):
    _,intent=pipeline.interpret('I want long sleeve top garment.')
    assert [c['attribute'] for g in intent.conditions.to_dict()['groups'] for c in g['conditions']]==['category']
    text='I want a garment named "blue trousers without short sleeves".'
    _,intent=pipeline.interpret(text)
    conditions=[c for g in intent.conditions.to_dict()['groups'] for c in g['conditions']]
    assert len(conditions)==1 and conditions[0]['attribute']=='garment_name'
    assert conditions[0]['values']==['blue trousers without short sleeves']

def test_no_blue_trousers_keeps_category_and_polarity(pipeline):
    _,intent=pipeline.interpret('i dont want blue trousers for shopping')
    assert semantic(intent.conditions.to_dict()['groups'])==[{'role':'lower','quantifier':'none','conditions':[
        {'attribute':'primary_colour','operator':'in','values':['blue']},
        {'attribute':'category','operator':'in','values':['trousers']}]}]

def test_four_structures_and_numeric_policies_unchanged():
    from app.domain.value_objects.compatibility_signature import STRUCTURES
    assert len(STRUCTURES)==4

@pytest.mark.parametrize('sleeve,expected',[('wrist-length','Pass'),('short','Fail'),(None,'Unknown')])
def test_compiled_long_sleeve_uses_qualified_same_member(pipeline,sleeve,expected):
    from tests.test_attribute_candidate_selection import make_member,with_field,POLICY,candidate
    from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions
    from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier
    _,intent=pipeline.interpret(SPEC['cases'][0]['text'])
    upper=make_member('long-top','primary_colour','blue',category='short_sleeve_top' if sleeve=='short' else 'long_sleeve_top')
    upper=with_field(upper,'material',['cotton'])
    if sleeve:upper=with_field(upper,'sleeve_length',sleeve)
    lower=make_member('blue-bottom','primary_colour','blue',category='trousers')
    pool=[upper,lower];outfit=candidate(*pool)
    assert PreparedAttributeConditions.prepare(intent.conditions,pool,POLICY).evaluate(outfit)==expected
    assert IndependentAttributeVerifier.prepare(intent.conditions,pool,POLICY).decision(outfit.key)==expected

def test_anonymous_conjunction_cannot_use_three_different_witnesses(pipeline):
    from tests.test_attribute_candidate_selection import make_member,with_field,POLICY,candidate
    from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions
    _,intent=pipeline.interpret(SPEC['cases'][3]['text'])
    upper=with_field(with_field(make_member('grey-long','primary_colour','grey',category='long_sleeve_top'),'material',['wool']),'sleeve_length','wrist-length')
    lower=with_field(make_member('cotton-lower','primary_colour','white',category='skirt'),'material',['cotton'])
    outer=make_member('blue-jacket','primary_colour','blue',category='long_sleeve_outwear')
    assert PreparedAttributeConditions.prepare(intent.conditions,[upper,lower,outer],POLICY).evaluate(candidate(upper,lower,outer))=='Fail'


@pytest.mark.parametrize('text',['I want every blue top.','I want all blue tops.'])
def test_existing_explicit_quantifier_is_preserved(pipeline,text):
    _,intent=pipeline.interpret(text)
    assert semantic(intent.conditions.to_dict()['groups'])==[{'role':'upper','quantifier':'all_present','conditions':[{'attribute':'primary_colour','operator':'in','values':['blue']}]}]

def test_nested_negative_scope_requests_clarification(pipeline):
    with pytest.raises(AttributeRequestError) as result:pipeline.interpret('i dont want a cotton top without short sleeves')
    assert result.value.status=='UnsupportedRequest' and result.value.reason=='language_conflicting_request'

