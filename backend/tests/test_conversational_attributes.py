"""B1 group bindings, canonical vocabulary and original coordinates."""
import json
from pathlib import Path
import pytest
from tests.test_conversational_contexts import SPEC,semantic,pipeline
from app.application.nlp.attribute_request_interpreter import AttributeRequestInterpreter
from app.application.nlp.conversational_attribute_interpreter import ConversationalAttributeInterpreter

@pytest.mark.parametrize('case',SPEC['attribute_cases'],ids=lambda c:c['id'])
def test_frozen_attribute_bindings(pipeline,case):
    request,intent=pipeline.interpret(case['text']);assert intent is not None
    assert semantic(intent.conditions.to_dict()['groups'])==case['hard_attribute_groups']
    for s in intent.to_dict()['spans']:assert case['text'][s['start']:s['end']]==s['text']

REGISTRY=json.loads((Path(__file__).parents[1]/'app/application/nlp/config/attribute_grammar.v1.json').read_text())
@pytest.mark.parametrize('entry',[e for e in REGISTRY['entries'] if e['status']=='Planned'],ids=lambda e:e['expression'])
def test_existing_registered_field_expression_is_not_lost(entry):
    text='I want '+entry['expression']+'.'
    old=AttributeRequestInterpreter().parse(text);new=ConversationalAttributeInterpreter().parse(text)
    assert old.conditions is not None and new.conditions is not None
    assert semantic(new.conditions.to_dict()['groups'])==semantic(old.conditions.to_dict()['groups'])

def test_alias_and_material_stay_on_same_garment(pipeline):
    _,intent=pipeline.interpret('I want a long-sleeved cotton shirt.')
    groups=intent.conditions.to_dict()['groups'];assert len(groups)==1 and groups[0]['role']=='upper'
    assert {c['attribute'] for c in groups[0]['conditions']}=={'sleeve_length','material'}
    assert len({s['condition_id'] for s in intent.to_dict()['spans']})==2

def test_typed_and_spoken_conditions_remain_distinct(pipeline):
    typed={'version':'attribute-conditions-1.0.0','groups':[{'id':'g01','role':'lower','quantifier':'exists','conditions':[{'id':'c01','attribute':'material','operator':'contains_any','values':['denim']}]}]}
    _,intent=pipeline.interpret('I want a cotton shirt.',typed)
    assert len(intent.conditions.to_dict()['groups'])==2
    assert any(s['source']=='typed' and s['start'] is None for s in intent.to_dict()['spans'])
