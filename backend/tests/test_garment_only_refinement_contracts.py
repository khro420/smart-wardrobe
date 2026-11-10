"""Closed opt-in policy and strict contribution-floor identity."""
from fractions import Fraction
from dataclasses import replace
import pytest
from app.application.recommendation.garment_only_refinement_policy import load,applies
from app.domain.value_objects.garment_only_refinement import step_key

def test_policy_is_default_disabled_and_unchanged_weights():
    policy=load()
    assert policy['default_activation'] is False and policy['max_results']==10
    assert policy['weights']==['3/5','1/5','1/5']
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
    assert not applies(StructuredOutfitRequest(),None)

@pytest.mark.parametrize('ordinal',[0,10,True,-1,'01'])
def test_invalid_keys_refused(ordinal):
    with pytest.raises(ValueError):step_key('00000000-0000-0000-0000-000000000001',ordinal)

def test_namespace_is_separate():
    assert step_key('00000000-0000-0000-0000-000000000001',1)=='garment-refine:v1:00000000-0000-0000-0000-000000000001:01'
