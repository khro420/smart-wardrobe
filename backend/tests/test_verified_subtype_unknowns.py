import pytest
from tests.test_verified_subtype_registry import declared,row,types,OWNER
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy,AttributeFact
from app.application.recommendation.attribute_condition_evaluator import predicate
@pytest.mark.parametrize('kind',types.VALUES)
def test_unknown_never_proves_presence_or_absence(kind):
    assert predicate(AttributeFact('Unspecified'),'verified_subtype','in',[kind]).state=='Unknown'
def test_unknown_is_not_a_hidden_deny_or_permit():
    _,_,source=declared(None,state='Unspecified')
    assert types.decision(source['category'],'male',source)=='Unknown'
    assert types.decision(source['category'],'female',source)=='Permit'
