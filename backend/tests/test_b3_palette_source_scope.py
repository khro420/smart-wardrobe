"""The new approved source boundary cannot repin historical numerical authority."""
import copy
import pytest
from tests.integration_source_guard import b3_manifest,validate_b3_manifest

def test_exact_scope_approval_and_all_protected_inputs():
    data=b3_manifest()
    assert len(data['files'])==833 and len(data['additions'])==17
    assert len(data['replacements'])<=28 and data['default_activation'] is False

@pytest.mark.parametrize('case',['activation','version','scope','contract','protected_source','new_path','before','label'])
def test_unapproved_source_and_policy_mutations_fail_closed(case):
    data=copy.deepcopy(b3_manifest())
    if case=='activation':data['default_activation']=True
    elif case=='version':data['version']='unapproved'
    elif case=='scope':data['scope_sha256']='0'*64
    elif case=='contract':data['contract_sha256']='0'*64
    elif case=='protected_source':data['files']['backend/app/application/recommendation/preference_scorer.py']='0'*64
    elif case=='new_path':data['additions']['backend/app/unapproved.py']='0'*64
    elif case=='before':data['replacements']['backend/app/api/assistant_models.py']['before']='0'*64
    else:data['files']['backend/tests/fixtures/p2_preference_labels.v1.json']='0'*64
    with pytest.raises(AssertionError):validate_b3_manifest(data)
