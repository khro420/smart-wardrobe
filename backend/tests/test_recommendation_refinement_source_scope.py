"""Exact approved increment and preservation of the captured starting workspace."""
from pathlib import Path
import hashlib,json
from tests import integration_source_guard as guard

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=Path(__file__).with_name('fixtures')/'recommendation_refinement_sources.v1.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def test_exact_scope_frozen_labels_and_prior_source_authority():
    manifest=json.loads(MANIFEST.read_text('utf-8'))
    start=Path(manifest['retained_starting_hashes']);evidence=start.parent
    assert sha(start)==manifest['starting_hashes_sha256']
    scope=json.loads((evidence/'retained-design/proposed-scope.json').read_text('utf-8'))
    assert set(manifest['replacements'])==set(scope['existing_production']) and len(manifest['replacements'])==22
    assert set(manifest['additions'])==set(scope['new_production']) and len(manifest['additions'])==7
    starts={name.replace(chr(92),'/'):value for name,value in json.loads(start.read_text('utf-8')).items()}
    # The independently retained design snapshot covers the session module too;
    # it has no earlier per-file fixture declaration. Never invent such authority.
    prior=json.loads((evidence/'prior-source-authorities.json').read_text('utf-8'))
    for name,change in manifest['replacements'].items():
        assert sha(evidence/'before'/name)==change['before']==starts[name]
        assert sha(ROOT/name)==change['after']
        if name in prior:
            assert change['before']==prior[name]['before']
            assert change['before'] in (ROOT/prior[name]['fixture']).read_text('utf-8')
    assert len(prior)==21
    for name,digest in manifest['additions'].items():assert sha(ROOT/name)==digest
    labels=Path(__file__).with_name('fixtures')/'recommendation_refinement_labels.v1.json'
    assert sha(labels)==sha(evidence/'frozen-labels.json')==manifest['frozen_labels_sha256']
    allowed=set(manifest['replacements'])|{'backend/tests/integration_source_guard.py'}
    for name,digest in starts.items():
        if name not in allowed:assert sha(ROOT/name)==digest,name
    assert sha(ROOT/'backend/tests/integration_source_guard.py')==manifest['source_guard']['after']
    for name,change in manifest['replacements'].items():
        assert guard.recommendation_refinement_digest(name,change['before'])==change['after']
