"""Frozen author-specified utterances, assessed through the combined pipeline."""
from pathlib import Path
import json
import pytest
from app.application.nlp.conversational_context_interpreter import ConversationalContextInterpreter
from app.application.recommendation.conversational_request_pipeline import ConversationalRequestPipeline
from app.application.wardrobe.description_policy import DescriptionPolicy

SPEC=json.loads((Path(__file__).parent/'fixtures/conversational_language_acceptance.v1.json').read_text(encoding='utf-8'))
def semantic(groups):
    return [{k:v for k,v in g.items() if k!='id'}|{'conditions':[{k:v for k,v in c.items() if k!='id'} for c in g['conditions']]} for g in groups]
@pytest.fixture(scope='module')
def pipeline():return ConversationalRequestPipeline(ConversationalContextInterpreter(),DescriptionPolicy.load())

@pytest.mark.parametrize('case',SPEC['context_cases'],ids=lambda c:c['id'])
def test_frozen_context_and_attribute_meaning(pipeline,case):
    request,intent=pipeline.interpret(case['text'])
    assert request.context.situation.value==case['expected_situation']
    groups=semantic(intent.conditions.to_dict()['groups']) if intent else []
    assert groups==case['hard_attribute_groups']
    assert request.context.original_text==case['text']
    for name in request.context.__dataclass_fields__:
        slot=getattr(request.context,name)
        for span in getattr(slot,'spans',()):assert case['text'][span.start:span.end]==span.text
    if intent:
        for s in intent.to_dict()['spans']:assert case['text'][s['start']:s['end']]==s['text']
    if 'expected_facets' in case:assert list(request.context.facets.values)==case['expected_facets']

@pytest.mark.parametrize('text',["I'm going to eat","I am going to eat.",'Going to eat tonight.',"I'm going to eat with friends.","I'm going to eat with no floral patterns.","I'm going out to eat"])
def test_dining_patch_variants_keep_original_spans(pipeline,text):
    request,intent=pipeline.interpret(text)
    assert request.context.situation.value=='social.meal'
    assert request.context.original_text==text
    for span in request.context.situation.spans:assert text[span.start:span.end]==span.text
    if 'no floral' in text:
        assert semantic(intent.conditions.to_dict()['groups'])==[{'role':'all_selected','quantifier':'none','conditions':[{'attribute':'pattern','operator':'in','values':['floral']}]}]

@pytest.mark.parametrize('text',["I'm not going to eat.","I'm not going out to eat.","I'm going to eat or go shopping.","I'm going to eat. Not dinner.","I'm going to eat with a radioactive top."])
def test_dining_patch_does_not_erase_conditions(pipeline,text):
    from app.domain.value_objects.attribute_conditions import AttributeRequestError
    with pytest.raises(AttributeRequestError):pipeline.interpret(text)
