"""Frozen finite-domain expectations, independent of the new P2 policy loader."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
from app.domain.value_objects.attribute_preferences import PreferenceDocument, PreferenceError, DOCUMENT, AXES, encode, weight

LABELS=json.loads((Path(__file__).with_name('fixtures')/'p2_preference_labels.v1.json').read_text(encoding='utf-8'))


def document(family,axis,value,scope='all_selected'):
    return {'contract':DOCUMENT,'last_action':None,'families':{family:{'mode':'override','importance':'1','axes':{axis:{'scope':scope,'importance':'1','liked':[value],'avoided':[]}}}}}


@pytest.mark.parametrize('case',LABELS['catalog']['finite'],ids=lambda c:c['id'])
def test_frozen_finite_values_have_complete_typed_paths_or_explicit_blocker(case):
    raw=document(case['family'],case['axis'],case['value'],case['default_scope'])
    if case['status']=='Blocked':
        with pytest.raises(PreferenceError,match='unavailable|registered'):PreferenceDocument.from_dict(raw)
    else:
        parsed=PreferenceDocument.from_dict(raw)
        assert parsed.to_dict()==raw
        raw['families'].clear()
        assert parsed.to_dict()['families']  # No mutable alias survives capture.


@pytest.mark.parametrize('bad',[True,False,1,0,0.5,None,'-0.1','1.000001','0.1234567','1e-6','NaN',''])
def test_new_weights_are_exact_bounded_strings(bad):
    with pytest.raises(PreferenceError):weight(bad)


@pytest.mark.parametrize('value',['0','0.000001','0.500000','1','1.000000'])
def test_explicit_weights_retain_exact_decimal(value):
    from fractions import Fraction
    assert weight(value)==Fraction(value)


@pytest.mark.parametrize('mutate',[
    lambda d:d.update(owner='foreign'),
    lambda d:d['families'].update(name={'mode':'disabled'}),
    lambda d:d['families']['pattern']['axes']['pattern'].update(origin='owner_selected'),
    lambda d:d['families']['pattern']['axes']['pattern'].update(avoided=['plain']),
    lambda d:d['families']['pattern']['axes']['pattern'].update(liked=['plain','plain']),
    lambda d:d['families']['pattern']['axes']['pattern'].update(scope='men'),
    lambda d:d['families']['pattern']['axes'].update(material={'scope':'base','importance':'1','liked':['cotton'],'avoided':[]}),
])
def test_invalid_shapes_never_become_preferences(mutate):
    raw=document('pattern','pattern','plain');mutate(raw)
    with pytest.raises(PreferenceError):PreferenceDocument.from_dict(raw)


@pytest.mark.parametrize('tag',['rec:v1:occasion:campus:allow','neckline: crew','sleeve length: short','owner_style_forged','appearance_evidence_forged'])
def test_literal_tags_cannot_execute_reserved_declarations(tag):
    with pytest.raises(PreferenceError):PreferenceDocument.from_dict(document('descriptive_tag','descriptive_tag',tag))


def test_exact_hex_dynamic_tag_and_partial_threshold_are_not_approximate():
    for axis in ('primary_colour','secondary_colour','palette_colour'):
        assert PreferenceDocument.from_dict(document('colour',axis,'#123abc'))
    assert PreferenceDocument.from_dict(document('colour','palette_coverage',{'colour':'#123abc','minimum':'0.750000'}))
    assert PreferenceDocument.from_dict(document('descriptive_tag','descriptive_tag','😀'*100))
    with pytest.raises(PreferenceError):PreferenceDocument.from_dict(document('descriptive_tag','descriptive_tag','😀'*101))
    with pytest.raises(PreferenceError):PreferenceDocument.from_dict(document('colour','primary_colour','#ABCDEF'))


def test_document_and_policy_bounds_are_explicit():
    from app.application.recommendation.attribute_preference_policy import AttributePreferencePolicy
    policy=AttributePreferencePolicy.load();caps=policy.capabilities()
    assert len(caps['families'])==10 and len(caps['axes'])==15
    assert caps['limits']['P2_provenance_bytes']==1048576
    with pytest.raises(PreferenceError):PreferenceDocument(b' '*32769)
    with pytest.raises(PreferenceError):AttributePreferencePolicy(policy.payload+b' ')


def test_corrupt_text_and_noncanonical_stored_document_fail_without_repair():
    from app.domain.value_objects.attribute_preferences import decode
    with pytest.raises(PreferenceError):decode('\ud800')
    canonical=PreferenceDocument.from_dict(document('pattern','pattern','plain'))
    with pytest.raises(PreferenceError):PreferenceDocument(canonical.payload+b' ')


def test_snapshot_rejects_unregistered_policy_even_when_other_digests_match():
    from app.domain.value_objects.attribute_preferences import AttributePreferenceSnapshot, SNAPSHOT, POLICY_HASH, digest
    value={'contract':SNAPSHOT,'account_id':'synthetic-account','wearer_id':'00000000-0000-4000-8000-000000000001',
           'document':None,'legacy':[],'legacy_digest':digest([]),'revision':digest({'legacy':[],'document':None}),'policy':POLICY_HASH}
    assert AttributePreferenceSnapshot.from_dict(value)
    value['policy']='0'*64
    with pytest.raises(PreferenceError,match='Unregistered'):AttributePreferenceSnapshot.from_dict(value)
