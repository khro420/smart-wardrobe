"""Approved hard exclusions, independent structural counts and strict wire input."""
from dataclasses import replace
from pathlib import Path
import json
import pytest
from app.domain.value_objects.recommendation_refinement import (
    CATEGORIES, SHORTCUTS, REQUEST_VERSION, RefinementAction, RefinementError, step_key,
)
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest, GarmentCategoryConstraint
from app.application.nlp.vocabulary import Vocabulary
from app.application.recommendation.refinement_policy import RefinementPolicy
from app.application.recommendation.refinement_selector import filter_snapshot, check_category_conflicts
from tests.test_context_relevance_ranking import rows


@pytest.mark.parametrize('excluded,count,bound', [([],8,20),
    (list(dict(SHORTCUTS)['Dresses']),7,18), (['trousers'],6,8),
    (list(dict(SHORTCUTS)['Outerwear']),7,10), (['shorts','trousers','skirt'],5,2),
    ([c for c in CATEGORIES if not c.endswith('_outwear')],1,0)])
def test_approved_filter_counts(excluded,count,bound):
    original=rows(); before=tuple(original)
    result=filter_snapshot(original, excluded)
    assert len(result.garments)==count
    assert result.structural_bound_before==20 and result.structural_bound_after==bound
    assert result.excluded_garments==8-count and tuple(original)==before
    assert all(g.category not in excluded for g in result.garments)


@pytest.mark.parametrize('bad', [None, 'dress', ['dress'], ['Trousers'], [' trousers'],
    ['trousers','trousers'], [True], [1], [None], {}, ('trousers',), ['shorts']*14])
def test_wire_categories_reject(bad):
    with pytest.raises(ValueError):
        RefinementAction.parse(dict(version=REQUEST_VERSION, kind='initial', excluded_categories=bad))


def test_canonical_intent_and_exact_fields():
    a=RefinementAction.parse(dict(version=REQUEST_VERSION,kind='initial',excluded_categories=['trousers','shorts']))
    b=RefinementAction.parse(dict(version=REQUEST_VERSION,kind='initial',excluded_categories=['shorts','trousers']))
    assert a==b and a.to_dict()['excluded_categories']==['shorts','trousers']
    for extra in ('owner','Seen','root_R','parent_recommendation_id'):
        with pytest.raises(ValueError): RefinementAction.parse({**a.to_dict(),extra:'forged'})


def test_positive_category_conflict_and_partial_group():
    vocab=Vocabulary.load()
    request=StructuredOutfitRequest(garment_categories=(GarmentCategoryConstraint('category','trousers'),))
    with pytest.raises(RefinementError, match='required_category_excluded'):
        check_category_conflicts(request, ('trousers',), vocab)
    group=next(key for key,values in vocab.groups.items() if set(values)=={'shorts','trousers','skirt'})
    request=replace(request, garment_categories=(GarmentCategoryConstraint('group',group),))
    check_category_conflicts(request, ('trousers',), vocab)
    with pytest.raises(RefinementError): check_category_conflicts(request, ('shorts','trousers','skirt'), vocab)


def test_pinned_policy_and_malformed_resources(tmp_path):
    from app.application.recommendation.refinement_policy import CONFIG
    assert len(RefinementPolicy.load().ordinary_situations)==15
    target=tmp_path/'policy.json'
    target.write_bytes(CONFIG.read_bytes()+b' ')
    with pytest.raises(ValueError): RefinementPolicy.load(target)
    target.write_bytes(b' '*65537)
    with pytest.raises(ValueError): RefinementPolicy.load(target)


def test_canonical_action_keys_and_uuid():
    root='00000000-0000-4000-8000-000000000001'
    assert step_key(root,1)==f'refine:v1:{root}:01'
    assert len(step_key(root,9))==49
    for ordinal in (0,10,True,'1'):
        with pytest.raises(ValueError): step_key(root,ordinal)
    for bad in (root.replace('-',''), root.upper().replace('0001','000A'), None):
        with pytest.raises(ValueError):
            RefinementAction.parse(dict(version=REQUEST_VERSION,kind='alternative',parent_recommendation_id=bad))
