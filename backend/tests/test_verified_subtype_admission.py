import pytest
from tests.test_verified_subtype_registry import declared,row,types,OWNER
@pytest.mark.parametrize('parent',types.PARENTS)
@pytest.mark.parametrize('kind',types.VALUES)
def test_frozen_male_female_identity_decisions(parent,kind):
    _,_,source=declared(kind,parent)
    assert types.decision(parent,'male',source)==('Deny' if kind=='blouse' else 'Permit')
    assert types.decision(parent,'female',source)=='Permit'
@pytest.mark.parametrize('parent',types.PARENTS)
def test_unknown_cannot_admit_a_male_top(parent):
    source=types.project(row(parent),OWNER,[])
    assert types.decision(parent,'male',source)=='Unknown'
    assert types.decision(parent,'female',source)=='Permit'
def test_trousers_do_not_require_review():
    source=types.project(row('trousers'),OWNER,[])
    assert types.decision('trousers','male',source)=='Permit'
