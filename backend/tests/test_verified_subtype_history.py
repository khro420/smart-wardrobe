import copy
import pytest
from tests.test_verified_subtype_registry import declared,types
def test_captured_source_validates_without_active_resource(monkeypatch):
    _,_,source=declared('blouse');saved=types.encode(source)
    monkeypatch.setattr(types.RESOURCE.__class__,'read_bytes',lambda *a:pytest.fail('Current resource accessed'))
    assert types.validate_source(types.decode(saved,262144))['value']=='blouse'
def test_old_selected_source_cannot_be_relabelled():
    _,_,source=declared('blouse');before=types.encode(source);changed=copy.deepcopy(source);changed['value']='t_shirt'
    with pytest.raises(ValueError):types.validate_source(changed)
    assert types.encode(source)==before
