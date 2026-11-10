"""Author-written typed algebra negatives; independent of a parser/evaluator."""
import copy
import json
import pytest
from app.domain.value_objects.attribute_conditions import AttributeConditions,AttributeRequestError,VERSION,conjoin


def request(field='material',op='contains_any',values=None,role='upper',q='exists'):
    return {'version':VERSION,'groups':[{'id':'g01','role':role,'quantifier':q,
      'conditions':[{'id':'c01','attribute':field,'operator':op,'values':['cotton'] if values is None else values}]}]}


def test_value_sets_canonicalize_without_changing_binding_or_input():
    raw=request(values=['linen','cotton']);original=copy.deepcopy(raw)
    value=AttributeConditions.from_dict(raw)
    assert raw==original and value.to_dict()['groups'][0]['conditions'][0]['values']==['cotton','linen']
    assert AttributeConditions(value.payload)==value
    altered=value.to_dict();altered['groups'][0]['conditions'][0]['values'].clear()
    assert value.to_dict()['groups'][0]['conditions'][0]['values']==['cotton','linen']


def test_false_is_distinct_from_missing_and_integer():
    assert AttributeConditions.from_dict(request('colour_dominance','bool_eq',[False]))
    for value in (None,0,1,'false'):
        with pytest.raises(AttributeRequestError):AttributeConditions.from_dict(request('colour_dominance','bool_eq',[value]))


@pytest.mark.parametrize('field,op,values',[
 ('pattern','in',['paisley']),('neckline','in',['boat']),('silhouette','in',['mermaid']),
 ('primary_colour','exact_hex',['#123abc']),('secondary_colour','in',['cream']),
 ('palette_coverage','coverage_ge',[{'colour':'blue','minimum':'0.500000'}]),
 ('garment_name','exact_text',['My \U0001f455 shirt']),('descriptive_tag','exact_text',['handmade']),
 ('construction_collared','bool_eq',[False]),('condition','in',['needs_attention'])])
def test_supported_fields(field,op,values):
    value=AttributeConditions.from_dict(request(field,op,values))
    assert value.to_dict()['groups'][0]['conditions'][0]['values']==values


@pytest.mark.parametrize('field,op,values',[
 ('material','contains_any',['rayon']),('material','contains_any',['not sure']),
 ('sleeve_length','in',['three quarter']),('neckline','in',['round-crew']),
 ('palette_colour','contains_any',['cream']),('condition','in',['unknown']),
 ('primary_colour','exact_hex',['#123ABC']),('style','regex',['.*']),
 ('descriptive_tag','contains_any',['rec:v1:occasion:work:allow']),
 ('descriptive_tag','exact_text',['neckline: crew']),
 ('palette_coverage','coverage_ge',[{'colour':'blue','minimum':0.5}]),
 ('palette_coverage','coverage_ge',[{'colour':'blue','minimum':'1.000001'}]),
 ('palette_coverage','coverage_ge',[{'colour':'blue','minimum':'0.5000000'}])])
def test_refuse_unsupported_values_and_domains(field,op,values):
    with pytest.raises(AttributeRequestError):AttributeConditions.from_dict(request(field,op,values))


def test_same_member_conflict_is_not_separate_existential_conflict():
    raw=request('pattern','in',['plain'])
    raw['groups'][0]['conditions'].append({'id':'c02','attribute':'pattern','operator':'in','values':['floral']})
    with pytest.raises(AttributeRequestError) as exc:AttributeConditions.from_dict(raw)
    assert exc.value.status=='AttributeConflict'
    first=AttributeConditions.from_dict(request('pattern','in',['plain'],role='all_selected'))
    second=AttributeConditions.from_dict(request('pattern','in',['floral'],role='all_selected'))
    assert len(conjoin(first,second).to_dict()['groups'])==2


def test_required_and_forbidden_contradiction():
    first=AttributeConditions.from_dict(request('pattern','in',['plain']))
    second=AttributeConditions.from_dict(request('pattern','in',['plain'],role='all_selected',q='none'))
    with pytest.raises(AttributeRequestError) as exc:conjoin(first,second)
    assert exc.value.status=='AttributeConflict'


def test_named_and_exact_anchor_are_not_falsely_conflicting():
    raw=request('primary_colour','in',['blue'])
    raw['groups'][0]['conditions'].append({'id':'c02','attribute':'primary_colour','operator':'exact_hex','values':['#0000ff']})
    assert AttributeConditions.from_dict(raw)


@pytest.mark.parametrize('mutation',[
 {'version':'future'},{'origin':'owner_selected'},{'groups':None},
 {'groups':[{'id':'g01','role':{},'quantifier':'exists','conditions':[]}]},
 {'groups':[{'id':'g01','role':'upper','quantifier':'exists','conditions':[]}]}])
def test_strict_shape_refusals(mutation):
    raw=request();raw.update(mutation)
    with pytest.raises(AttributeRequestError):AttributeConditions.from_dict(raw)


def test_duplicate_json_keys_and_values_refused():
    with pytest.raises(AttributeRequestError):AttributeConditions(b'{"version":"x","version":"y","groups":[]}')
    with pytest.raises(AttributeRequestError):AttributeConditions.from_dict(request(values=['cotton','cotton']))


def test_all_frozen_language_examples_have_their_authored_bindings():
    from pathlib import Path
    labels=json.loads((Path(__file__).parent/'fixtures/attribute_labels.v1.json').read_text(encoding='utf-8'))
    for case in labels['language']['examples']:
        value=AttributeConditions.from_dict(case['expected_conditions'])
        assert value.to_dict()==case['expected_conditions']
