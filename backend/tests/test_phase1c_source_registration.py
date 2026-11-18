"""New current scope registration; never a substitute for old source guards."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

ROOT=Path(__file__).parents[2]
REGISTRY=Path(__file__).with_name('fixtures')/'nlp_phase1c_production_descendant.v1.json'
EXPECTED_PATHS={
    'backend/app/application/nlp/config/conversational_language.v1.json',
    'backend/app/application/nlp/conversational_attribute_interpreter.py',
    'backend/app/application/nlp/conversational_context_interpreter.py',
    'backend/app/application/nlp/general_context_interpreter.py',
    'backend/app/application/recommendation/attribute_selection_verifier.py',
    'backend/app/application/recommendation/context_relevance_policy.py',
    'backend/app/application/recommendation/context_relevance_scorer.py',
    'backend/app/application/recommendation/conversational_request_pipeline.py',
    'backend/app/application/recommendation/general_context_evaluator.py',
    'backend/app/shared_contracts/grammar_identity.py',
}


def verify(data):
    assert set(data)=={'version','base_commit','scope','hash_contract','entries'}
    assert data['version']=='nlp-production-descendant-1.0.0'
    assert data['base_commit']=='8f3e0cb6607a588fb2300c8f55bebba256f4afae'
    assert data['hash_contract']=='raw-byte-sha256'
    assert data['scope']=='Phase 1 through Phase 1C modified production paths only; not a full historical source certificate'
    assert set(data['entries'])==EXPECTED_PATHS
    for path,entry in data['entries'].items():
        assert set(entry)=={'before_git_blob_sha256','after_file_sha256'}
        if path=='backend/app/shared_contracts/grammar_identity.py':
            assert entry['before_git_blob_sha256'] is None
            assert subprocess.run(['git','cat-file','-e',data['base_commit']+':'+path],cwd=ROOT,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
        else:
            before=subprocess.check_output(['git','show',data['base_commit']+':'+path],cwd=ROOT)
            assert hashlib.sha256(before).hexdigest()==entry['before_git_blob_sha256']
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==entry['after_file_sha256']


def registration():
    raw=REGISTRY.read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='a6af60f9293c2a616b2411fa70ca23a8bc31351bfddb29130d0238808b8931fc'
    return json.loads(raw)


def test_exact_current_scope_and_real_predecessor_blobs():
    verify(registration())


@pytest.mark.parametrize('kind',['before','after','unknown_path','commit'])
def test_scope_registration_refuses_unregistered_identities(kind):
    data=copy.deepcopy(registration())
    path='backend/app/application/nlp/general_context_interpreter.py'
    if kind=='before':data['entries'][path]['before_git_blob_sha256']='0'*64
    elif kind=='after':data['entries'][path]['after_file_sha256']='0'*64
    elif kind=='unknown_path':data['entries']['backend/unknown.py']=data['entries'][path]
    else:data['base_commit']='0'*40
    with pytest.raises(AssertionError):verify(data)
