"""Owner-frozen meanings, literal spans and qualified descriptor boundaries."""
import json
from pathlib import Path
import pytest
from app.application.nlp.conversational_context_interpreter import ConversationalContextInterpreter
from app.application.recommendation.conversational_request_pipeline import ConversationalRequestPipeline
from app.application.wardrobe.description_policy import DescriptionPolicy
from app.domain.value_objects.attribute_conditions import AttributeRequestError

CASES=json.loads((Path(__file__).parent/'fixtures/garment_only_refinement_cases.v1.json').read_text())['wording_cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['id'])
def test_frozen_meanings(case):
    pipeline=ConversationalRequestPipeline(ConversationalContextInterpreter(),DescriptionPolicy.load())
    if 'outcome' in case:
        with pytest.raises(AttributeRequestError) as caught:pipeline.interpret(case['text'])
        assert caught.value.status==case['outcome']
        if 'reason' in case:assert caught.value.reason==case['reason']
        return
    request,intent=pipeline.interpret(case['text'])
    groups=intent.conditions.to_dict()['groups']
    actual=[{k:g[k] for k in ('role','quantifier')}|{'conditions':[{k:c[k] for k in ('attribute','operator','values')} for c in g['conditions']]} for g in groups]
    assert actual==case['expected']
    assert intent.to_dict()['original_text']==case['text']
    for span in intent.to_dict()['spans']:
        if span['source']=='nlp':assert case['text'][span['start']:span['end']]==span['text']
    from app.application.nlp.garment_wording_guidance import capture,validate
    note=capture(case['text'],intent)
    if 'mandatory_wording_disclosure' in case:assert note is not None and 'subtype is not verified' in note['message']
    assert validate(note,case['text'],intent)==note

@pytest.mark.parametrize('text',['I want a garment named "dark blouse T-shirt".','I want a garment tagged "tailored".'])
def test_literals_never_become_descriptor_aliases(text):
    pipeline=ConversationalRequestPipeline(ConversationalContextInterpreter(),DescriptionPolicy.load())
    _,intent=pipeline.interpret(text)
    assert all(c['attribute'] in ('garment_name','descriptive_tag') for g in intent.conditions.to_dict()['groups'] for c in g['conditions'])

@pytest.mark.parametrize('field,text,category,value',[('construction_collared','I want a collared shirt.','short_sleeve_top',True),('construction_tailored','I want tailored trousers.','trousers',True),('sleeve_length','I want a long-sleeved shirt.','long_sleeve_top','wrist-length')])
@pytest.mark.parametrize('state,expected',[('owner','Pass'),('missing','Unknown'),('stale','Unknown'),('malformed','Unknown')])
def test_fine_descriptors_require_qualified_current_member_evidence(field,text,category,value,state,expected):
    from tests.test_attribute_qualification import make_member,POLICY
    from tests.test_attribute_candidate_selection import candidate
    from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions
    from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier
    pipeline=ConversationalRequestPipeline(ConversationalContextInterpreter(),DescriptionPolicy.load())
    _,intent=pipeline.interpret(text)
    subject=make_member('subject',field,value,state=state,category=category)
    companion=make_member('companion',category='short_sleeve_top' if category=='trousers' else 'trousers')
    pool=[companion,subject] if category=='trousers' else [subject,companion]
    outfit=candidate(*pool)
    assert PreparedAttributeConditions.prepare(intent.conditions,pool,POLICY).evaluate(outfit)==expected
    assert IndependentAttributeVerifier.prepare(intent.conditions,pool,POLICY).decision(outfit.key)==expected

@pytest.mark.parametrize('field,text,category',[('construction_collared','I want a collared shirt.','short_sleeve_top'),('construction_tailored','I want tailored trousers.','trousers')])
def test_false_is_not_missing_or_positive(field,text,category):
    from tests.test_attribute_qualification import make_member,POLICY
    from tests.test_attribute_candidate_selection import candidate
    from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions
    _,intent=ConversationalRequestPipeline(ConversationalContextInterpreter(),DescriptionPolicy.load()).interpret(text)
    subject=make_member('subject',field,False,category=category)
    other=make_member('other',field,True,category='short_sleeve_top' if category=='trousers' else 'trousers')
    pool=[other,subject] if category=='trousers' else [subject,other]
    assert PreparedAttributeConditions.prepare(intent.conditions,pool,POLICY).evaluate(candidate(*pool))=='Fail'

def test_positive_coarse_T_shirt_can_retain_a_separate_negative_pattern_condition():
    # Owner contract excludes negative subtype guesses, not unrelated hard negation.
    pipeline=ConversationalRequestPipeline(ConversationalContextInterpreter(),DescriptionPolicy.load())
    _,intent=pipeline.interpret('I want a T-shirt without floral patterns.')
    groups=intent.conditions.to_dict()['groups']
    assert any(g['quantifier']=='exists' and any(c['attribute']=='category' and c['values']==['short_sleeve_top'] for c in g['conditions']) for g in groups)
    assert any(g['role']=='upper' and g['quantifier']=='none' and any(c['attribute']=='pattern' and c['values']==['floral'] for c in g['conditions']) for g in groups)
