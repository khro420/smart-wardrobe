import copy
import pytest
from tests.test_verified_subtype_registry import declared,row,types,OWNER
@pytest.mark.parametrize('kind',['t_shirt','polo_shirt','button_up_shirt','knit_top','blouse'])
def test_owner_confirmation_survives_canonical_encoding(kind):
    garment,event,source=declared(kind)
    assert types.validate_source(types.decode(types.encode(source),262144))['value']==kind
@pytest.mark.parametrize('field,value',[('media_id','different'),('subtype','blouse'),('owner_id','foreign'),('category','trousers')])
def test_tampering_is_refused(field,value):
    garment,event,source=declared();bad=copy.deepcopy(source);bad['events'][0][field]=value
    with pytest.raises(ValueError):types.validate_source(bad)
def test_replacement_media_stales_identity():
    garment,event,source=declared();garment['preferred_media_id']='replacement'
    assert types.project(garment,OWNER,[event])['state']=='Stale'
