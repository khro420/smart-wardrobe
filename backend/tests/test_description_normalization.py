"""Frozen literal values and independent state expectations, not normalizer output."""
import dataclasses
import json
from pathlib import Path
import pytest

from app.application.wardrobe.description_policy import DescriptionPolicy, select_policy
from app.application.wardrobe.description_normalizer import normalise_field, qualified
from app.domain.value_objects.garment_description_evidence import DescriptionField, encode

LABELS = json.loads((Path(__file__).with_name('fixtures')/'description_labels.v1.json').read_text(encoding='utf-8'))
FINITE = [c for c in LABELS['cases'] if c['id'].startswith('F')]
ALIASES = [c for c in LABELS['cases'] if c['id'].startswith('L')]


@pytest.fixture(scope='module')
def policy():
    return DescriptionPolicy.load()


@pytest.mark.parametrize('case', FINITE, ids=lambda c:c['id'])
def test_every_frozen_finite_value(policy, case):
    category = 'vest'
    if case['field']=='sleeve_length':
        category = 'long_sleeve_top' if case['input']=='wrist-length' else 'short_sleeve_top' if case['input']=='short' else 'vest'
    result=normalise_field(case['field'],case['input'],policy,origin='owner_selected',category=category).to_dict()
    assert result['state']==case['expected_state']
    if 'expected_canonical_values' in case:
        assert result['canonical_values']==case['expected_canonical_values']
    if 'expected_exact_hex' in case:
        assert result['canonical_values']==[case['expected_exact_hex']]
        assert policy.colour_family(case['expected_exact_hex'])==case['expected_family']


@pytest.mark.parametrize('case', ALIASES, ids=lambda c:c['id'])
def test_exact_legacy_alias_does_not_attest_model(policy,case):
    result=normalise_field(case['field'],case['input'],policy,category='vest')
    assert result.to_dict()['canonical_values']==[case['expected_legacy_canonical']]
    assert not qualified(result)
    model=normalise_field(case['field'],case['input'],policy,category='vest',origin='model_suggestion').to_dict()
    assert model['state']=='Unrecognized' and not model['canonical_values'] and model['selected'] is None


@pytest.mark.parametrize('raw,state,values',[
    (None,'Absent',[]),([], 'KnownEmpty',[]),(['casual'],'Known',['casual']),
    (['casual','formal'],'Known',['casual','formal']),(['glam'],'Unrecognized',[]),
    ([7],'Malformed',[]),(['casual','casual'],'Malformed',[]),('', 'Unspecified',[])])
def test_style_states_do_not_invent_singleton_pass(policy,raw,state,values):
    record=normalise_field('style',raw,policy).to_dict()
    assert record['state']==state and record['canonical_values']==values
    assert not qualified(record)


@pytest.mark.parametrize('raw,state,values',[
    (None,'Absent',[]),('', 'Unspecified',[]),([], 'KnownEmpty',[]),
    (['cotton','linen'],'Known',['cotton','linen']),(['not sure'],'Unsure',[]),
    (['cotton','not sure'],'Unsure',['cotton']),('rayon','Unrecognized',[]),
    (['cotton','cotton'],'Malformed',[])])
def test_material_uncertainty(policy,raw,state,values):
    record=normalise_field('material',raw,policy).to_dict()
    assert record['state']==state and record['canonical_values']==values


@pytest.mark.parametrize('field,value',[('colour_temperature',None),('colour_dominance',None)])
def test_missing_observation_is_not_a_default(policy,field,value):
    assert normalise_field(field,value,policy).to_dict()['state']=='Absent'


def test_literal_colour_and_palette_conventions(policy):
    assert policy.colour_family('#123abc') is None
    assert normalise_field('primary_colour','#123abc',policy).to_dict()['canonical_values']==['#123abc']
    raw=[{'hex':'#0000ff','coverage':'0.500000'},{'hex':'#ffffff','coverage':'0.250000'}]
    result=normalise_field('colour_palette',raw,policy).to_dict()
    assert result['canonical_values']==raw and result['completeness']=='partial'
    assert normalise_field('colour_palette',[{'hex':'#000000','coverage':'1.000001'}],policy).to_dict()['state']=='Malformed'
    assert normalise_field('colour_dominance',0,policy).to_dict()['state']=='Malformed'


def test_field_binding_immutability_and_corruption(policy):
    record=normalise_field('neckline','crew',policy)
    view=record.to_dict();view['canonical_values']=['v-neck']
    assert record.to_dict()['canonical_values']==['crew']
    with pytest.raises(ValueError):DescriptionField.from_dict(view)
    with pytest.raises(dataclasses.FrozenInstanceError):record.payload=b'changed'
    with pytest.raises(ValueError):DescriptionField(b' '*32769)
    with pytest.raises(ValueError):encode(float('nan'))


def test_source_qualification_needs_real_event(policy):
    assert not qualified(normalise_field('pattern','plain',policy,origin='owner_selected'))
    event=normalise_field('pattern','plain',policy,origin='owner_selected',event_id='00000000-0000-4000-8000-000000000001',recorded_at='2026-10-31T00:00:00Z',source_revision='0'*64)
    assert qualified(event)
    assert not qualified(normalise_field('pattern','plain',policy,origin='model_suggestion'))


def test_unknown_role_is_not_assumed_applicable(policy):
    field=normalise_field('neckline','crew',policy,origin='owner_selected',category='Unclassified garment',event_id='00000000-0000-4000-8000-000000000001',recorded_at='2026-10-31T00:00:00Z',source_revision='0'*64)
    assert field.to_dict()['applicability']=='unknown' and not qualified(field)


def test_missing_model_value_is_not_an_unrecognized_label(policy):
    record=normalise_field('silhouette',None,policy,origin='model_suggestion',category='vest').to_dict()
    assert record['state']=='Absent' and record['suggestion'] is None
    assert normalise_field('silhouette','',policy,origin='model_suggestion',category='vest').to_dict()['state']=='Unspecified'


def test_resources_pinned_and_disabled_does_not_load(tmp_path,monkeypatch):
    with pytest.raises(ValueError):DescriptionPolicy.load(tmp_path)
    monkeypatch.setattr(DescriptionPolicy,'load',classmethod(lambda cls: (_ for _ in ()).throw(AssertionError('loader called'))))
    assert select_policy('disabled') is None
    with pytest.raises(ValueError):select_policy('other')
