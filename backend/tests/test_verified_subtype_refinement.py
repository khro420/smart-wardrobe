import pytest
from app.domain.value_objects.attribute_conditions import AttributeConditions,conjoin
def requirement(kind,version='attribute-conditions-2.0.0'):
    return {'version':version,'groups':[{'id':'g01','role':'upper','quantifier':'exists','conditions':[{'id':'c01','attribute':'verified_subtype','operator':'in','values':[kind]}]}]}
def test_v1_cannot_smuggle_new_type():
    with pytest.raises(ValueError):AttributeConditions.from_dict(requirement('blouse','attribute-conditions-1.0.0'))
def test_conjoin_keeps_v2_type_and_original_requirement():
    original=AttributeConditions.from_dict({'version':'attribute-conditions-1.0.0','groups':[{'id':'g01','role':'upper','quantifier':'exists','conditions':[{'id':'c01','attribute':'primary_colour','operator':'in','values':['red']}]}]})
    combined=conjoin(original,AttributeConditions.from_dict(requirement('blouse'))).to_dict()
    assert combined['version']=='attribute-conditions-2.0.0'
    assert [c['attribute'] for g in combined['groups'] for c in g['conditions']]==['primary_colour','verified_subtype']
