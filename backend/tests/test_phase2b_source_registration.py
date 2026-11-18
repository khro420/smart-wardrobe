"""Additive current-stage registration; predecessor assertions stay unchanged."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

ROOT=Path(__file__).parents[2]
FIXTURES=Path(__file__).with_name('fixtures')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def registration():
    raw=(FIXTURES/'nlp_phase2b_production_descendant.v1.json').read_bytes()
    assert sha(raw)=='e8b87d7ab540ec2367f6991bd9722fee969732959e8d4acac8268a9d6432eda9'
    return json.loads(raw)


def verify(data):
    previous=(FIXTURES/'nlp_phase1c_production_descendant.v1.json').read_bytes()
    assert sha(previous)=='a6af60f9293c2a616b2411fa70ca23a8bc31351bfddb29130d0238808b8931fc'
    assert set(data)=={'version','base_commit','predecessor_registration_sha256','scope','hash_contract','entries'}
    assert data['version']=='nlp-phase2b-production-scope-1.0.0'
    assert data['base_commit']=='8f3e0cb6607a588fb2300c8f55bebba256f4afae'
    assert data['predecessor_registration_sha256']==sha(previous)
    assert data['hash_contract']=='raw-byte-sha256'
    assert data['scope']=='Phase 1 through Phase 2B modified production paths only; not a full historical source certificate'
    old=json.loads(previous)
    assert set(data['entries'])==set(old['entries'])|{
        'backend/app/application/nlp/conversational_attribute_forms.py','frontend/lib/recommendation-messages.ts'}
    for path,entry in data['entries'].items():
        assert set(entry)=={'before_git_blob_sha256','before_phase2b_file_sha256','after_file_sha256'}
        prior=subprocess.run(['git','show',data['base_commit']+':'+path],cwd=ROOT,capture_output=True)
        assert entry['before_git_blob_sha256']==(sha(prior.stdout) if prior.returncode==0 else None)
        if path in old['entries']:
            assert entry['before_phase2b_file_sha256']==old['entries'][path]['after_file_sha256']
        elif 'conversational_attribute_forms.py' in path:
            assert entry['before_phase2b_file_sha256'] is None
        else:
            assert len(entry['before_phase2b_file_sha256'])==64
        assert sha((ROOT/path).read_bytes())==entry['after_file_sha256']


def test_phase2b_current_scope_with_retained_predecessor():verify(registration())


@pytest.mark.parametrize('kind',['before','after','predecessor','unknown_path','missing_path','commit'])
def test_phase2b_scope_refuses_unregistered_identity(kind):
    data=copy.deepcopy(registration())
    path='backend/app/application/nlp/conversational_attribute_forms.py'
    if kind=='before':data['entries'][path]['before_git_blob_sha256']='0'*64
    elif kind=='after':data['entries'][path]['after_file_sha256']='0'*64
    elif kind=='predecessor':data['predecessor_registration_sha256']='0'*64
    elif kind=='unknown_path':data['entries']['unknown.py']=data['entries'][path]
    elif kind=='missing_path':del data['entries'][path]
    else:data['base_commit']='0'*40
    with pytest.raises(AssertionError):verify(data)
