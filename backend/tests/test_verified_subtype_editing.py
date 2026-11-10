import copy
import pytest
from tests.test_verified_subtype_registry import declared,types,OWNER
def test_category_change_does_not_erase_retained_blouse():
    garment,event,source=declared('blouse');garment['category']='vest'
    changed=types.project(garment,OWNER,[event])
    assert changed['state']=='Stale' and types.decision('vest','male',changed)=='Unknown'
def test_clear_without_a_real_event_cannot_create_permission():
    _,_,source=declared('blouse');source['events']=[];source['state']='Absent';source['value']=None
    with pytest.raises(ValueError):types.validate_source(source)
def test_name_change_does_not_reclassify():
    garment,event,source=declared('blouse');garment['name']='T-shirt'
    assert types.project(garment,OWNER,[event])['value']=='blouse'
