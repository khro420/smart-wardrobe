"""Default-off dispatch, pinned resources and exact scoped source ancestry."""
import hashlib,json
from pathlib import Path
import pytest
from app.application.nlp.conversational_context_interpreter import load_language,RESOURCE
from app.application.recommendation.conversational_request_pipeline import select_language

def test_disabled_dispatch_does_not_load_a_companion():
    sentinel=object();assert select_language('disabled',None,sentinel)==(sentinel,None)

@pytest.mark.parametrize('name',['unknown','conversational_language_v2','conversational_language_v1'])
def test_unknown_or_missing_dependencies_refused(name):
    with pytest.raises(ValueError):select_language(name,None,object())

def test_tampered_or_oversized_resource_refused(tmp_path):
    for raw in (RESOURCE.read_bytes()+b' ',b' '*65537):
        path=tmp_path/'bad.json';path.write_bytes(raw)
        with pytest.raises(ValueError):load_language(path)

def test_source_ancestry_and_approved_fixture():
    backend=Path(__file__).parents[1];manifest=json.loads((Path(__file__).parent/'fixtures/conversational_language_sources.v1.json').read_text())
    descendants=manifest.get('approved_manual_corrections_descendants',{})
    assert set(descendants)=={'backend/app/infrastructure/persistence/postgresql_repository.py','backend/app/api/account_routes.py','frontend/lib/api.ts','frontend/app/profile/page.tsx'}
    category_descendants=manifest.get('approved_wearer_category_descendants',{})
    assert category_descendants and all(set(v)=={'before','after'} for v in category_descendants.values())
    garment_descendants=manifest.get('approved_garment_continuation_descendants',{})
    assert len(garment_descendants)==40 and set(garment_descendants)==set(manifest['approved_garment_continuation_inputs'])
    for rel,transition in garment_descendants.items():
        assert set(transition)=={'before','after'} and transition['after']==manifest['approved_garment_continuation_inputs'][rel]
        assert _ancestor_digest(backend,rel)==transition['after']
    for rel,digest in manifest['protected_original_inputs'].items():
        transition=descendants.get(rel)
        if transition:assert transition['before']==digest and transition['after']==manifest['production_inputs'][rel]
        prior=transition['after'] if transition else digest
        current=category_descendants.get(rel)
        if current:assert current['before']==prior
        before=current['after'] if current else prior
        next_stage=garment_descendants.get(rel)
        if next_stage:assert next_stage['before']==before
        assert _ancestor_digest(backend,rel)==(next_stage['after'] if next_stage else before)
    for rel,digest in manifest['production_inputs'].items():
        current=category_descendants.get(rel)
        if current:assert current['before']==digest
        before=current['after'] if current else digest
        next_stage=garment_descendants.get(rel)
        if next_stage:assert next_stage['before']==before
        assert _ancestor_digest(backend,rel)==(next_stage['after'] if next_stage else before)
    assert hashlib.sha256((Path(__file__).parent/'fixtures/conversational_language_acceptance.v1.json').read_bytes()).hexdigest()==manifest['acceptance_sha256']


def _ancestor_digest(backend,rel):
    """Validate the current approved descendant, then expose its certified ancestor.

    This is an explicit source-guard bridge, not an unmodified ancestor run.
    Original stage hash assertions above remain against the same ancestor vector.
    """
    manifest=json.loads((backend/'tests/fixtures/conversational_language_sources.v1.json').read_text())
    transition={**manifest['approved_verified_subtype_descendants'],**manifest['approved_verified_subtype_verification_descendants']}.get(rel)
    observed=hashlib.sha256((backend.parent/rel).read_bytes()).hexdigest()
    if transition:
        assert transition['before'] is not None and observed==transition['after']
        return transition['before']
    return observed

def test_exact_verified_subtype_descendants():
    backend=Path(__file__).parents[1]
    manifest=json.loads((backend/'tests/fixtures/conversational_language_sources.v1.json').read_text())
    transitions=manifest['approved_verified_subtype_descendants']
    assert len(transitions)==50
    for rel,transition in transitions.items():
        assert set(transition)=={'before','after'}
        assert hashlib.sha256((backend.parent/rel).read_bytes()).hexdigest()==transition['after']
