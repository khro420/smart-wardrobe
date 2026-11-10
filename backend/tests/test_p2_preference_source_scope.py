"""A separately named P2 descendant, retaining every historical source/label authority."""
from tests.retained_evidence import review_path, review_reference
from pathlib import Path
import hashlib,json
from tests.integration_source_guard import p2_manifest,performance_digest,performance_manifest,validate_performance_manifest
ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def test_final_P2_exact_scope_and_all_protected_sources():
    manifest=p2_manifest();data=json.loads((ROOT/'backend/tests/fixtures/p2_preference_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='p2-preference-delivery-1.0.0' and data['default_activation'] is False
    assert data['approved_scope_sha256']=='3a05553d5e8e494a1ea2274f19bffed4cb46c32b6ccfb442f410c69e9021499a'
    assert len(manifest['replacements'])==29 and len(manifest['additions'])==34
    assert len(data['files'])==62
    for path,value in data['files'].items():assert sha(ROOT/path)==performance_digest(path,value),path
    authority=review_reference(data['approved_contract_path'])
    baseline=json.loads((authority/'baseline-source-hashes.json').read_text(encoding='utf-8'))
    support=json.loads((authority/'baseline-support-hashes.json').read_text(encoding='utf-8'))
    assert len(baseline)==668 and len(support)==110
    for path,value in baseline.items():assert sha(ROOT/path)==performance_digest(path,manifest['replacements'].get(path,{}).get('after',value)),path
    for path,value in support.items():assert sha(ROOT/path)==value,path
    assert sha(ROOT/'backend/tests/fixtures/p2_preference_sources.v1.json')==manifest['additions']['backend/tests/fixtures/p2_preference_sources.v1.json']


def test_frozen_P2_labels_and_original_247_ids_are_unchanged():
    data=json.loads((ROOT/'backend/tests/fixtures/p2_preference_sources.v1.json').read_text(encoding='utf-8'))
    approved=review_reference(data['approved_contract_path'])
    for path,value in data['frozen_inputs'].items():assert sha(approved/path)==value,path
    labels=json.loads((ROOT/'backend/tests/fixtures/p2_preference_labels.v1.json').read_text(encoding='utf-8'))
    for key,path in (('catalog','preference-value-catalog.json'),('finite_labels','finite-value-labels.json'),('acceptance','independent-acceptance.json'),('mechanics','independent-mechanics-expectations.json')):
        assert labels[key]==json.loads((approved/path).read_text(encoding='utf-8'))
    assert len(labels['finite_labels']['cases'])==3106
    rows=json.loads((approved/'B2-attribute-value-coverage.json').read_text(encoding='utf-8'))['rows']
    assert len(rows)==247 and len({row['id'] for row in rows})==247
    assert data['historical_direct_test_exceptions']==json.loads((approved/'legacy-test-exceptions.json').read_text(encoding='utf-8'))


def test_exact_performance_descendant_and_protected_source_negative_cases():
    import copy
    import pytest
    data=performance_manifest()
    assert len(data['files'])==816 and len(data['replacements'])==len(data['additions'])==4
    mutations=[]
    v=copy.deepcopy(data);v['default_activation']=True;mutations.append(v)
    v=copy.deepcopy(data);v['version']='unapproved';mutations.append(v)
    v=copy.deepcopy(data);v['scope_sha256']='0'*64;mutations.append(v)
    v=copy.deepcopy(data);v['files']['backend/app/application/recommendation/preference_scorer.py']='0'*64;mutations.append(v)
    v=copy.deepcopy(data);v['replacements']['backend/app/application/recommendation/attribute_preference_preparation.py']['before']='0'*64;mutations.append(v)
    v=copy.deepcopy(data);v['additions']['backend/tests/not_approved.py']='0'*64;mutations.append(v)
    v=copy.deepcopy(data);v['files']['backend/tests/fixtures/p2_preference_labels.v1.json']='0'*64;mutations.append(v)
    for value in mutations:
        with pytest.raises(AssertionError):validate_performance_manifest(value)


def test_B3_is_a_separate_approved_descendant_without_new_historical_exceptions():
    from tests.integration_source_guard import b3_manifest
    data=b3_manifest()
    assert len(data['files'])==833 and len(data['additions'])==17
    assert data['default_activation'] is False
    original=json.loads((ROOT/'backend/tests/fixtures/p2_preference_sources.v1.json').read_text(encoding='utf-8'))
    fixture=json.loads((ROOT/'backend/tests/fixtures/b3_palette_sources.v1.json').read_text(encoding='utf-8'))
    assert fixture['historical_labels_unchanged'] is True and fixture['additional_historical_exceptions']==[]
    assert original['historical_direct_test_exceptions']
