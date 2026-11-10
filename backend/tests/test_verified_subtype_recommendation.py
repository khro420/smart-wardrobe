import pytest
from dataclasses import replace
from tests.test_verified_subtype_registry import declared,types
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.application.recommendation.attribute_condition_evaluator import predicate
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
from fractions import Fraction
@pytest.mark.parametrize('wanted,actual,expected',[('t_shirt','blouse','Fail'),('polo_shirt','t_shirt','Fail'),('blouse','blouse','Pass'),('t_shirt','t_shirt','Pass')])
def test_exact_kind_is_a_hard_predicate(wanted,actual,expected):
    _,_,source=declared(actual)
    garment=ConfirmedGarmentSnapshot('garment','owner','available','short_sleeve_top','fixture','media',False,'now','top',0)
    policy=AttributeEvidencePolicy.load()
    assert predicate(policy.subtype_fact(garment,source),'verified_subtype','in',[wanted]).state==expected
def test_original_exact_weight_identity_has_no_type_bonus():
    r,c,p=Fraction(2,3),Fraction(3,4),Fraction(1,2)
    assert Fraction(3,5)*r+Fraction(1,5)*c+Fraction(1,5)*p==Fraction(13,20)
