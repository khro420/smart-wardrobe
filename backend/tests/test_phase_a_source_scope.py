"""Approved descendant transition, frozen expectations and complete source bounds."""
from tests.retained_evidence import review_path, review_reference
import hashlib,json
from pathlib import Path
from tests import integration_source_guard as guard


def test_phase_a_exact_approved_scope_and_unchanged_oracles():
    data=guard.phase_a_manifest();root=Path(__file__).resolve().parents[2]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    changed=set()
    for name,entry in data['captured_sources'].items():
        assert sha(review_reference(data['frozen_source'])/name)==entry['start']
        assert sha(root/name)==guard.description_digest(name,entry['final']),name
        if entry['start']!=entry['final']:changed.add(name)
    assert changed<=set(data['allowed_existing'])
    assert len(data['captured_sources'])==612
    for name,value in data['new_production'].items():assert sha(root/name)==guard.description_digest(name,value),name
    for name,value in data['new_verification'].items():assert sha(root/name)==guard.description_digest(name,value),name
    for name,value in data['historical_manifests'].items():assert sha(root/name)==guard.description_digest(name,value),name
    assert sha(review_reference(data['frozen_labels_path']))==data['frozen_labels_sha256']
    assert data['decisions']=='PA01-PA09; CP1-CP6'
