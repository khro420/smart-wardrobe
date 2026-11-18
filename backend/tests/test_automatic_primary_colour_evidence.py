"""Qualified extractor colour families remain hard evidence, never a fallback."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.application.wardrobe.description_policy import DescriptionPolicy
from app.application.wardrobe.description_projector import project
from app.domain.value_objects.attribute_conditions import AttributeConditions
from app.domain.value_objects.attribute_conditions import digest
from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
from app.domain.value_objects.outfit_candidate import CandidateMember, OutfitCandidate
from app.application.recommendation.attribute_selection_verifier import build_selection, validate_selection
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.shared_contracts.confirmed_garment_description import ConfirmedGarmentDescription
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot, GarmentPaletteEntry


POLICY = AttributeEvidencePolicy.load()
DESCRIPTION_POLICY = DescriptionPolicy.load()


def item(hex_value, *, coverage=.60, palette=None, media='media-A', category='vest', identifier='top'):
    role, layer = GARMENT_STRUCTURE[category]
    snapshot = ConfirmedGarmentSnapshot(identifier, 'owner', 'available', category, 'Top', media, False,
        '2026-11-13T00:00:00Z', role, layer, primary_colour=hex_value,
        colour_palette=tuple(GarmentPaletteEntry(value, mass) for value, mass in (palette or [(hex_value, coverage), ('#ffffff', 1-coverage)])))
    row = {'id':identifier,'user_id':'owner','processing_item_id':'item','name':'Top','category':category,
           'preferred_media_id':media,'primary_colour':hex_value,'attributes_json':'{}'}
    return ConfirmedGarmentDescription(snapshot, project(row, 'owner', DESCRIPTION_POLICY))


def request(colour, op='in'):
    return AttributeConditions.from_dict({'version':'attribute-conditions-1.0.0','groups':[{
        'id':'g01','role':'upper','quantifier':'exists','conditions':[{
            'id':'c01','attribute':'primary_colour','operator':op,'values':[colour]}]}]})


@pytest.mark.parametrize(('hex_value','family'), [
    ('#050507','black'), ('#fafafa','white'), ('#808184','grey'), ('#0055dd','blue'),
    ('#dd2015','red'), ('#179b43','green'), ('#ff9d08','orange'), ('#ffe600','yellow'),
    ('#7020a0','purple'), ('#ef4f9e','pink'), ('#071a5c','navy'),
])
def test_qualified_extracted_primary_maps_to_closed_family(hex_value, family):
    prepared=PreparedAttributeConditions.prepare(request(family), [item(hex_value)], POLICY)
    assert prepared.evaluate_members((('upper','top'),)) == 'Pass'
    fact=prepared.facts['top','c01']
    assert fact.source == 'automatic_primary_colour_family_v1'
    assert len(fact.revision) == 64


@pytest.mark.parametrize('hex_value', ['#090d14', '#111216', '#25252c'])
def test_ambiguous_near_black_is_not_promoted(hex_value):
    prepared=PreparedAttributeConditions.prepare(request('black'), [item(hex_value)], POLICY)
    assert prepared.evaluate_members((('upper','top'),)) == 'Unknown'


def test_partial_or_non_primary_palette_evidence_is_unknown():
    partial=item('#050507', palette=[('#050507', .40), ('#303030', .20)])
    mismatch=item('#050507', palette=[('#303030', .60), ('#050507', .40)])
    for candidate in (partial, mismatch):
        prepared=PreparedAttributeConditions.prepare(request('black'), [candidate], POLICY)
        assert prepared.evaluate_members((('upper','top'),)) == 'Unknown'


def test_current_media_binding_invalidates_derived_colour():
    candidate=item('#050507')
    stale=ConfirmedGarmentDescription(replace(candidate.snapshot, preferred_media_id='media-B'), candidate.description)
    prepared=PreparedAttributeConditions.prepare(request('black'), [stale], POLICY)
    assert prepared.evaluate_members((('upper','top'),)) == 'Unknown'


def test_qualified_extracted_hex_keeps_exact_matching_semantics():
    prepared=PreparedAttributeConditions.prepare(request('#050507', 'exact_hex'), [item('#050507')], POLICY)
    assert prepared.evaluate_members((('upper','top'),)) == 'Pass'
    mismatch=PreparedAttributeConditions.prepare(request('#000000', 'exact_hex'), [item('#050507')], POLICY)
    assert mismatch.evaluate_members((('upper','top'),)) == 'Fail'


def test_archived_automatic_colour_replays_the_same_palette_evidence():
    selected=item('#050507')
    lower=item('#fafafa',category='trousers',identifier='lower')
    conditions=request('black')
    from app.application.nlp.attribute_request_interpreter import GRAMMAR_SHA256
    intent=AttributeIntent.capture('black top',None,conditions,[{
        'condition_id':'c01','source':'nlp','start':0,'end':5,'text':'black'}], GRAMMAR_SHA256, POLICY.sha256)
    prepared=PreparedAttributeConditions.prepare(conditions,[selected,lower],POLICY)
    from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier
    independent=IndependentAttributeVerifier.prepare(conditions,[selected,lower],POLICY)
    candidate=OutfitCandidate((CandidateMember(selected.snapshot,'upper',1),CandidateMember(lower.snapshot,'lower',2)))
    wearer=SimpleNamespace(account_id='owner',profile_id='00000000-0000-4000-8000-000000000002')
    evidence=build_selection(intent,[selected,lower],prepared,independent,candidate,
        {'structural_examined':2,'legacy_failed':0,'legacy_unknown':0,'attribute_failed':0,'attribute_unknown':0,'joint_passed':2},
        '1'*64,wearer)
    restored=validate_selection(evidence.to_dict(),'owner',wearer.profile_id,'1'*64)
    assert restored.payload==evidence.payload
    assert evidence.to_dict()['decisions']['member_results'][0]['source_kind']=='automatic_primary_colour_family_v1'
    corrupt=evidence.to_dict();corrupt['selected_evidence'][0].pop('colour_palette');corrupt['revision']=digest({**corrupt,'revision':''})
    with pytest.raises(ValueError,match='palette evidence missing'):
        validate_selection(corrupt,'owner',wearer.profile_id,'1'*64)
