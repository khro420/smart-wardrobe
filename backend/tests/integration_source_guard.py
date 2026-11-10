"""Pin explicitly authorized integration changes without weakening scoring oracles."""
from tests.retained_evidence import review_path, review_reference, assert_relocated_authority
import hashlib
import json
import os
from pathlib import Path
from functools import lru_cache

BACKEND = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def p2_manifest():
    """Named approved P2 descendant; old authorities and numerical labels stay fixed."""
    root=review_path('phase_b2_preference_implementation_20261105')
    approval=json.loads((root/'approval.json').read_text(encoding='utf-8'))
    scope_path=root/'approved-contract/proposed-source-scope.json'
    assert hashlib.sha256(scope_path.read_bytes()).hexdigest()==approval['scope_sha256']=='3a05553d5e8e494a1ea2274f19bffed4cb46c32b6ccfb442f410c69e9021499a'
    scope=json.loads(scope_path.read_text(encoding='utf-8'))
    manifest_path=Path(os.environ.get('B2_MANIFEST_PATH',str(root/'checkpoint-manifest.json'))).resolve()
    assert manifest_path.is_relative_to(root.resolve())
    data=json.loads(manifest_path.read_text(encoding='utf-8'))
    baseline=json.loads((root/'approved-contract/baseline-source-hashes.json').read_text(encoding='utf-8'))
    assert data['version']=='p2-preference-sources-1.0.0' and data['default_activation'] is False
    allowed={e['path']:e['before_sha256'] for key in ('existing_production','existing_verification') for e in scope[key]}
    amendment=root/'approved-auth-inventory-amendment.json'
    if amendment.exists():
        record=json.loads(amendment.read_text(encoding='utf-8'))
        assert record['answer']=='Approve the exact one-line verification amendment'
        assert record['path']=='backend/tests/test_durable_logout.py'
        assert record['proposed_after_sha256']=='94004d6f39054c4c9238e20c9041e065e0b196d6071380371ed2f3aa9f69ae42'
        assert hashlib.sha256((BACKEND.parent/record['path']).read_bytes()).hexdigest()==record['proposed_after_sha256']
        allowed[record['path']]=record['before_sha256']
    assert set(data['replacements'])<=set(allowed)
    assert set(data['additions'])<={e['path'] for key in ('new_production','new_verification') for e in scope[key]}
    for path,value in data['replacements'].items():assert value['before']==allowed[path]==baseline[path],path
    for path,value in data['frozen_inputs'].items():assert hashlib.sha256((root/'approved-contract'/path).read_bytes()).hexdigest()==value,path
    assert approval['contract_sha256']=='45df918f40beda26116584ba396cc8f12bf1f71310b198b37f5bfb078480027e'
    return data


def validate_b3_manifest(data):
    root=review_path('phase_b3_c_functional_completion_20261106')
    scope_path=root/'approved-contract/proposed-source-scope.json'
    contract_path=root/'approved-contract/B3_PALETTE_CONTRACT.json'
    scope_hash='57f2354e3c622b56e9732132c97f0eb51df884e2479659e3de6477161d547b4b'
    contract_hash='22ae7ef2a5cfbaae4d2d02782215e693f561412f49480f26aa08d3402ee6ffeb'
    assert hashlib.sha256(scope_path.read_bytes()).hexdigest()==scope_hash==data['scope_sha256']
    assert hashlib.sha256(contract_path.read_bytes()).hexdigest()==contract_hash==data['contract_sha256']
    approval=json.loads((root/'approval.json').read_text(encoding='utf-8'))
    assert approval['answer']=='Approve exact B3 scope, C2 contract and FC-CP0–CP5'
    assert approval['scope_sha256']==scope_hash and approval['contract_sha256']==contract_hash
    assert hashlib.sha256((root/'approval.json').read_bytes()).hexdigest()==data['approval_sha256']
    assert data['version']=='b3-palette-sources-1.0.0' and data['default_activation'] is False
    baseline=json.loads((root/'approved-contract/baseline-source-hashes.json').read_text(encoding='utf-8'))
    predecessor=root.parent/'phase_b2_performance_optimization_20261106'
    assert baseline==json.loads((predecessor/'FINAL_INTEGRITY.json').read_text(encoding='utf-8'))['final_inputs']
    assert hashlib.sha256((predecessor/'checkpoint-manifest.json').read_bytes()).hexdigest()=='d867bffb63b8ff689e674d818ea0be9ae29adea4b8827cf0ad46cac3c278d2c5'
    scope=json.loads(scope_path.read_text(encoding='utf-8'))
    allowed={e['path']:e['before_sha256'] for kind in ('existing_production','existing_verification') for e in scope[kind]}
    additions={e['path'] for kind in ('new_production','new_verification') for e in scope[kind]}
    assert len(allowed)==28 and len(additions)==17
    assert set(data['replacements'])<=set(allowed) and set(data['additions'])==additions
    assert set(data['files'])==set(baseline)|additions
    for path,value in data['files'].items():
        assert type(value) is str and len(value)==64
        if path in data['replacements']:
            entry=data['replacements'][path]
            assert entry['before']==allowed[path]==baseline[path] and entry['after']==value,path
        elif path in additions:assert value==data['additions'][path],path
        else:assert value==baseline[path],('Unapproved B3 edit',path)
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==reconciliation_digest(path,value),path
    fixture=json.loads((BACKEND/'tests/fixtures/b3_palette_sources.v1.json').read_text(encoding='utf-8'))
    assert fixture['contract']=='b3-palette-delivery-1.0.0' and fixture['default_activation'] is False and fixture['historical_labels_unchanged'] is True and fixture['additional_historical_exceptions']==[]
    assert fixture['scope_sha256']==scope_hash and fixture['contract_sha256']==contract_hash
    assert fixture['files']=={p:v for p,v in data['files'].items() if p in set(data['replacements'])|additions and p!='backend/tests/fixtures/b3_palette_sources.v1.json'}
    return data


@lru_cache(maxsize=1)
def b3_manifest():
    root=review_path('phase_b3_c_functional_completion_20261106')
    path=Path(os.environ.get('B3_MANIFEST_PATH',str(root/'checkpoint-manifest.json'))).resolve()
    assert path.is_relative_to(root.resolve())
    return validate_b3_manifest(json.loads(path.read_text(encoding='utf-8')))


def b3_digest(path,previous):
    if not (BACKEND/'tests/fixtures/b3_palette_sources.v1.json').exists():return reconciliation_digest(path,previous)
    data=b3_manifest()
    if path in data['replacements']:
        entry=data['replacements'][path]
        assert entry['before']==previous,('Unrecognised B3 predecessor',path)
        return reconciliation_digest(path,entry['after'])
    if path in data['additions']:
        assert previous is None
        return reconciliation_digest(path,data['additions'][path])
    return reconciliation_digest(path,previous)


def validate_performance_manifest(data):
    """A new exact descendant; original B2 manifest/labels are never repinned."""
    root=review_path('phase_b2_performance_optimization_20261106')
    scope_path=root/'approved-contract/proposed-source-scope.json'
    scope_hash='5ea641229c15d0a9e8e58702def74501f3e8162f2eab8b04a4b15d72b85efb45'
    assert hashlib.sha256(scope_path.read_bytes()).hexdigest()==scope_hash
    approval=json.loads((root/'approval.json').read_text(encoding='utf-8'))
    assert approval['answer']=='Approve exact isolated optimisation scope and PERF-CP0–CP5'
    assert approval['scope_sha256']==scope_hash==data['scope_sha256']
    assert data['version']=='p2-performance-sources-1.0.0' and data['default_activation'] is False
    assert data['approval_sha256']==hashlib.sha256((root/'approval.json').read_bytes()).hexdigest()
    base_path=root/'frozen-baseline-hashes.json'
    assert data['baseline_inputs_sha256']==hashlib.sha256(base_path.read_bytes()).hexdigest()
    baseline=json.loads(base_path.read_text(encoding='utf-8'))
    b2=root.parent/'phase_b2_preference_implementation_20261105'
    assert baseline==json.loads((b2/'FINAL_INTEGRITY.json').read_text(encoding='utf-8'))['final_inputs']
    assert hashlib.sha256((b2/'checkpoint-manifest.json').read_bytes()).hexdigest()=='345be482a09d927fd4586080a8becb0ab3b89591a2a1c2a28dd12e2833ce5b86'
    scope=json.loads(scope_path.read_text(encoding='utf-8'))
    allowed={e['path']:e['before_sha256'] for kind in ('existing_production','existing_verification') for e in scope[kind]}
    additions={e['path'] for e in scope['new_verification']}
    assert len(allowed)==4 and len(additions)==4
    assert set(data['replacements'])==set(allowed) and set(data['additions'])==additions
    assert set(data['files'])==set(baseline)|additions
    for path,value in data['files'].items():
        assert type(value) is str and len(value)==64
        if path in allowed:
            entry=data['replacements'][path]
            assert entry['before']==allowed[path]==baseline[path] and entry['after']==value,path
        elif path in additions:assert data['additions'][path]==value,path
        else:assert value==baseline[path],('Unapproved performance edit',path)
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==b3_digest(path,value),path
    fixture=json.loads((BACKEND/'tests/fixtures/p2_performance_sources.v1.json').read_text(encoding='utf-8'))
    assert fixture['contract']=='p2-performance-delivery-1.0.0' and fixture['default_activation'] is False
    assert fixture['scope_sha256']==scope_hash and fixture['historical_labels_unchanged'] is True and fixture['no_additional_exceptions'] is True
    assert set(fixture['files'])==(set(allowed)|additions)-{'backend/tests/fixtures/p2_performance_sources.v1.json'}
    for path,entry in fixture['files'].items():
        assert entry['before']==baseline.get(path) and entry['after']==data['files'][path],path
    return data


@lru_cache(maxsize=1)
def performance_manifest():
    root=review_path('phase_b2_performance_optimization_20261106')
    path=Path(os.environ.get('P2_PERF_MANIFEST_PATH',str(root/'checkpoint-manifest.json'))).resolve()
    assert path.is_relative_to(root.resolve())
    return validate_performance_manifest(json.loads(path.read_text(encoding='utf-8')))


def performance_digest(path,previous):
    if not (BACKEND/'tests/fixtures/p2_performance_sources.v1.json').exists():return previous
    data=performance_manifest();entry=data['replacements'].get(path)
    if entry is not None:
        assert entry['before']==previous,('Unrecognised performance predecessor',path)
        return b3_digest(path,entry['after'])
    if path in data['additions']:
        assert previous is None
        return b3_digest(path,data['additions'][path])
    return b3_digest(path,previous)


def p2_digest(path,previous):
    data=p2_manifest();entry=data['replacements'].get(path)
    if entry is not None:
        assert entry['before']==previous,('Unrecognised P2 predecessor',path)
        expected=performance_digest(path,entry['after'])
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==expected,path
        return expected
    return performance_digest(path,previous)


@lru_cache(maxsize=1)
def attribute_manifest():
    """Capture immutable approval once; callers still hash every current source.

    The harness freezes and rechecks all source/support inputs around each run.
    Historical authorities and numerical labels retain their original bytes.
    """
    data=json.loads((BACKEND/'tests/fixtures/attribute_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='attribute-sources-1.0.0' and data['default_activation'] is False
    scope_path=review_reference(data['approved_scope_path'])
    assert hashlib.sha256(scope_path.read_bytes()).hexdigest()==data['approved_scope_sha256']=='a1c7d382a14d57590ce9313ea9e414a987e9da4cf9d867a1b792944e881f11c0'
    assert hashlib.sha256((scope_path.parent/'CONTRACT_FREEZE.json').read_bytes()).hexdigest()=='2f485059176133fe6145d70b618f8c2379cc4b19f0175e8600ab8471bc99785d'
    freeze=json.loads((scope_path.parent/'CONTRACT_FREEZE.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(scope_path.read_bytes()).hexdigest()==freeze['artifacts']['proposed-source-scope.json']
    scope=json.loads(scope_path.read_text(encoding='utf-8'))
    starting=json.loads((scope_path.parent/'starting-source-hashes.json').read_text(encoding='utf-8'))
    assert data['baseline_application']=={p.removeprefix('backend/'):h for p,h in starting.items() if p.startswith('backend/app/')}
    for p,h in data['ancestry_authorities'].items():
        assert starting[p]==h,p
        if hashlib.sha256((BACKEND.parent/p).read_bytes()).hexdigest()!=h:
            assert_relocated_authority(p,BACKEND.parent,h)
    allowed={e['path']:e['before_sha256'] for k in ('existing_production','existing_verification') for e in scope[k]}
    assert set(data['replacements'])<=set(allowed)
    assert set(data['additions'])<={e['path'] for k in ('new_production','new_verification') for e in scope[k]}
    for path,change in data['replacements'].items():assert change['before']==allowed[path],path
    for name,value in data['frozen_inputs'].items():
        assert hashlib.sha256((scope_path.parent/name).read_bytes()).hexdigest()==value,name
    assert hashlib.sha256((BACKEND/'tests/fixtures/attribute_labels.v1.json').read_bytes()).hexdigest()==data['frozen_fixture_sha256']
    return data


def attribute_digest(path,previous):
    entry=attribute_manifest()['replacements'].get(path)
    if entry is None:return p2_digest(path,previous)
    assert entry['before']==previous,('Unrecognised B1 predecessor',path)
    expected=p2_digest(path,entry['after'])
    assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==expected,path
    return expected


def description_digest(path, previous):
    """B0 descendant: exact authorized transitions, never replacement historical labels."""
    data=json.loads((BACKEND/'tests/fixtures/description_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='description-sources-1.0.0' and data['default_activation'] is False
    scope_path=review_reference(data['approved_scope_path'])
    assert hashlib.sha256(scope_path.read_bytes()).hexdigest()=='f1f55258481581ea0d5c08addf6ff4070ad82a0acb11e347abd0f584371c1a7c'
    approved=json.loads(scope_path.read_text(encoding='utf-8'))
    allowed={e['path']:e['before_sha256'] for k in ('existing_production','existing_verification') for e in approved[k]}
    assert set(data['replacements'])<=set(allowed)
    assert set(data['additions'])<={e['path'] for k in ('new_production','new_verification') for e in approved[k]}
    assert hashlib.sha256(review_reference(data['frozen_labels_path']).read_bytes()).hexdigest()=='feea8a9b73663af6e4a03f17ce15c7527a3aaebb362b0498b298a47ada784640'
    assert hashlib.sha256((BACKEND/'tests/fixtures/description_labels.v1.json').read_bytes()).hexdigest()=='feea8a9b73663af6e4a03f17ce15c7527a3aaebb362b0498b298a47ada784640'
    change=data['replacements'].get(path)
    if change:
        assert change['before']==previous==allowed[path],path
        expected=attribute_digest(path,change['after'])
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==expected,path
        return expected
    return attribute_digest(path,previous)


def phase_a_manifest():
    data=json.loads((BACKEND/'tests/fixtures/phase_a_wearer_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='phase-a-wearer-sources-1.0.0'
    assert data['workspace_applied'] is False and data['runtime_changed'] is False
    scope_path=review_reference(data['approved_scope_path'])
    assert hashlib.sha256(scope_path.read_bytes()).hexdigest()=='0cb83bb84caf71ca4f4d4f0922a1f3ec5621a6ab10e5022b1a0c542944b23b7e'
    scope=json.loads(scope_path.read_text('utf-8'))
    amendment_path=review_reference(data['fixture_amendment_path'])
    assert hashlib.sha256(amendment_path.read_bytes()).hexdigest()=='8d5729246a131419d99ab4dae4f10e54f0b8cab49fbb55c56b4f0efc9d4131bb'
    amendment=json.loads(amendment_path.read_text('utf-8'))
    assert amendment['version']=='phase-a-fixture-amendment-1.0.0' and amendment['owner_answer']=='Approve this fixture-only addition'
    assert amendment['existing_verification_addition']=='backend/tests/test_garment_workflow.py'
    assert set(data['allowed_existing'])==set(scope['existing_production'])|set(scope['existing_verification_changes'])|{amendment['existing_verification_addition']}
    assert set(data['new_production'])==set(scope['new_production'])
    assert hashlib.sha256(review_reference(data['frozen_labels_path']).read_bytes()).hexdigest()=='4d70ca349fe86a82620a277743c4b248ea9765d9734ef7bed907d7cdd1798ec5'
    return data


def phase_a_digest(path,previous):
    data=phase_a_manifest()
    entry=data['captured_sources'].get(path)
    if entry is None:return previous
    assert previous in entry['ancestry'],('Unrecognised source predecessor',path)
    if entry['start']!=entry['final']:assert path in data['allowed_existing'],path
    expected=description_digest(path,entry['final'])
    assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==expected,path
    return expected


def recommendation_refinement_digest(path, previous):
    data=json.loads((BACKEND/'tests/fixtures/recommendation_refinement_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='recommendation-refinement-sources-1.0.0' and data['default_activation'] is False
    entry=data['source_guard'] if path=='backend/tests/integration_source_guard.py' else data['replacements'].get(path)
    if entry and previous in (entry['before'],entry['after']):
        expected=phase_a_digest(path,entry['after'])
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==expected,path
        return expected
    return phase_a_digest(path,previous)


def context_18_activation_correction_manifest(verify=False):
    data=json.loads((BACKEND/'tests/fixtures/context_18_activation_correction_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='context-18-activation-correction-sources-1.0.0' and data['default_activation'] is False
    assert set(data['replacements'])=={'backend/app/application/nlp/context_expression_matcher.py','backend/tests/test_context_expansion_nlp.py','backend/tests/test_context_expansion_integration.py'}
    assert hashlib.sha256((BACKEND/'tests/fixtures/context_expansion_sources.v1.json').read_bytes()).hexdigest()==data['original_expansion_manifest_sha256']
    for name,digest in data['frozen_labels'].items():
        assert hashlib.sha256((BACKEND/'tests/fixtures'/name).read_bytes()).hexdigest()==digest,name
    if verify:
        for path,entry in data['replacements'].items():
            assert set(entry)=={'before','after'}
            assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==entry['after'],path
        assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==recommendation_refinement_digest('backend/tests/integration_source_guard.py',data['source_guard']['after'])
    return data


def context_18_activation_correction_digest(path,previous):
    data=context_18_activation_correction_manifest()
    entry=data['source_guard'] if path=='backend/tests/integration_source_guard.py' else data['replacements'].get(path)
    if entry and previous in (entry['before'],entry['after']):
        expected=recommendation_refinement_digest(path,entry['after'])
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==expected,path
        return expected
    return recommendation_refinement_digest(path,previous)


def context_expansion_manifest(verify=False):
    data=json.loads((BACKEND/'tests/fixtures/context_expansion_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='context-expansion-sources-1.0.0' and data['default_activation'] is False
    assert set(data['replacements'])=={'backend/app/application/recommendation/context_constraint_compiler.py', 'backend/app/application/recommendation/decision_score_codec.py', 'backend/app/application/recommendation/context_relevance_policy.py', 'backend/app/application/recommendation/context_relevance_verifier.py', 'backend/app/application/recommendation/compact_exhaustive_scorer.py', 'backend/app/application/recommendation/compact_assistant_scorer.py', 'backend/app/application/recommendation/scoring_display.py', 'backend/app/application/recommendation/aggregated_decision_scorer.py', 'backend/app/application/recommendation/context_evidence_resolver.py', 'frontend/lib/recommendation-messages.ts', 'backend/app/infrastructure/workflow_runtime.py', 'frontend/components/RecommendationResult.tsx', 'backend/app/domain/value_objects/assistant_execution_context.py', 'frontend/lib/api.ts', 'backend/app/application/recommendation/context_relevance_scorer.py', 'backend/app/api/recommendation_routes.py', 'backend/app/infrastructure/persistence/recommendation_repository_adapter.py', 'backend/app/domain/value_objects/general_context_request.py', 'backend/app/application/recommendation/context_policy_registry.py', 'backend/app/application/recommendation/outfit_assistant_service.py', 'backend/app/application/recommendation/contextual_selection.py', 'backend/app/application/nlp/general_context_interpreter.py', 'frontend/components/OutfitAssistant.tsx', 'backend/app/application/recommendation/general_context_evaluator.py'}
    assert set(data['additions'])=={'backend/app/application/recommendation/config/context_relevance_policy.v2.json', 'backend/app/application/recommendation/config/context_relevance_objectives.v2.json', 'backend/app/application/recommendation/config/situation_taxonomy.v2.json', 'backend/app/application/recommendation/config/context_policy_registry.v2.json', 'backend/app/application/nlp/context_expression_matcher.py', 'backend/app/application/recommendation/context_bundle.py', 'backend/app/application/nlp/config/context_grammar.v2.json', 'backend/app/application/recommendation/config/context_expansion_bundle.v1.json'}
    if verify:
        for path,entry in data['replacements'].items():
            assert set(entry)=={'before','after'}
            assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==recommendation_refinement_digest(path,entry['after']),path
        for path,digest in data['additions'].items():
            assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==context_18_activation_correction_digest(path,digest),path
        assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==context_expansion_digest('backend/tests/integration_source_guard.py',data['source_guard']['after'])
    return data


def context_expansion_digest(path,previous):
    data=context_expansion_manifest()
    entry=data['source_guard'] if path=='backend/tests/integration_source_guard.py' else data['replacements'].get(path)
    if entry and previous in (entry['before'],entry['after']):
        expected=context_18_activation_correction_digest(path,entry['after'])
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==expected,path
        return expected
    return context_18_activation_correction_digest(path,previous)


def context_relevance_manifest(verify=False):
    data=json.loads((BACKEND/'tests/fixtures/context_relevance_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='context-relevance-sources-1.0.0' and data['default_activation'] is False
    expected={'backend/app/application/recommendation/'+name+'.py' for name in (
        'assistant_scoring_selection','assistant_execution_selection','compact_assistant_scorer','outfit_assistant_service',
        'request_match_scorer','compact_scoring_facts','compact_exhaustive_scorer','aggregated_decision_scorer',
        'preference_scorer','decision_score_codec','scoring_display')}
    expected.update({'backend/app/api/recommendation_routes.py','backend/app/domain/value_objects/ranking_outcome.py',
        'backend/app/domain/value_objects/recommendation_persistence.py','backend/app/infrastructure/persistence/recommendation_repository_adapter.py',
        'backend/app/infrastructure/workflow_runtime.py',*('frontend/'+p for p in ('lib/api.ts','lib/recommendation-messages.ts','components/OutfitAssistant.tsx','components/RecommendationResult.tsx'))})
    assert set(data['replacements'])==expected
    assert set(data['additions'])=={'backend/app/application/recommendation/'+p for p in (
        'context_relevance_policy.py','context_relevance_scorer.py','context_relevance_verifier.py',
        'config/context_relevance_policy.v1.json','config/context_relevance_objectives.v1.json')}|{'backend/app/domain/value_objects/context_relevance.py'}
    if verify:
        for path,change in data['replacements'].items():
            assert set(change)=={'before','after'}
            assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==context_expansion_digest(path,change['after']),path
        for path,value in data['additions'].items():
            assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==context_expansion_digest(path,value),path
        assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==context_expansion_digest('backend/tests/integration_source_guard.py',data['source_guard']['after'])
    return data


def context_relevance_digest(path,previous):
    change=context_relevance_manifest()['replacements'].get(path)
    if change and previous in (change['before'],change['after']):
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==context_expansion_digest(path,change['after']),path
        return context_expansion_digest(path,change['after'])
    return context_expansion_digest(path,previous)


def automatic_admission_manifest(verify=True):
    data = json.loads((BACKEND/'tests/fixtures/automatic_admission_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version'] == 'automatic-admission-1.0.0' and data['default_activation'] is False
    assert set(data['replacements']) == {
        'backend/app/shared_contracts/confirmed_garment_snapshot.py', 'backend/app/infrastructure/persistence/confirmed_garment_query_adapter.py',
        *('backend/app/application/recommendation/'+n for n in ('config/context_policy_registry.v1.json','context_policy_registry.py','context_evidence_resolver.py','general_context_evaluator.py')),
        'backend/app/api/garment_processing_routes.py','backend/app/domain/value_objects/requests.py','backend/app/application/ports/confirmed_garment_writer.py',
        *('backend/app/application/garment_processing/'+n+'.py' for n in ('garment_processing_orchestrator','processing_job_service','review_service')),
        'backend/app/application/wardrobe/wardrobe_service.py',
        *('frontend/'+n for n in ('lib/api.ts','lib/recommendation-messages.ts','components/OutfitAssistant.tsx','components/RecommendationResult.tsx','app/wardrobe/page.tsx','app/extract/page.tsx','app/extract/results/page.tsx'))}
    assert set(data['additions']) == {'backend/app/domain/value_objects/saved_attribute_evidence.py','backend/app/application/garment_processing/automatic_garment_finalization.py'}
    for name, change in data['replacements'].items():
        assert set(change) == {'before','after'}
        if verify:
            assert hashlib.sha256((BACKEND.parent/name).read_bytes()).hexdigest() == context_relevance_digest(name,change['after']), name
    if verify:
        for name, digest in data['additions'].items():
            assert hashlib.sha256((BACKEND.parent/name).read_bytes()).hexdigest() == phase_a_digest(name,digest), name
    return data


def automatic_admission_digest(path, previous):
    # Historical chains already inspect each current path. Verify that exact path
    # here; full-bundle verification remains explicit at manifest/source-set checks.
    # No cached hashes or skipped path assertions are introduced.
    change = automatic_admission_manifest(verify=False)['replacements'].get(path)
    if change and previous in (change['before'],change['after']):
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest() == context_relevance_digest(path,change['after']), path
        return context_relevance_digest(path,change['after'])
    return context_relevance_digest(path,previous)


def owner_style_manifest():
    data = json.loads((BACKEND/'tests/fixtures/owner_style_admission_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version'] == 'owner-style-admission-1.0.0' and data['default_activation'] is False
    assert set(data['replacements']) == {
        'backend/app/domain/value_objects/requests.py',
        *('backend/app/application/garment_processing/'+n+'.py' for n in ('review_service','processing_job_service','garment_processing_orchestrator')),
        'backend/app/application/wardrobe/wardrobe_service.py',
        'frontend/lib/api.ts', 'frontend/app/extract/results/page.tsx', 'frontend/app/wardrobe/page.tsx',
        'frontend/components/OutfitAssistant.tsx', 'frontend/lib/recommendation-messages.ts'}
    assert set(data['additions']) == {'backend/app/application/wardrobe/owner_style_confirmation.py'}
    for name, change in data['replacements'].items():
        assert set(change) == {'before','after'}
        assert hashlib.sha256((BACKEND.parent/name).read_bytes()).hexdigest() == automatic_admission_digest(name,change['after']), name
    for name, digest in data['additions'].items():
        assert hashlib.sha256((BACKEND.parent/name).read_bytes()).hexdigest() == phase_a_digest(name,digest), name
    return data


def owner_style_digest(path, previous):
    change = owner_style_manifest()['replacements'].get(path)
    if change:
        assert previous in (change['before'], change['after']), path
        return automatic_admission_digest(path,change['after'])
    return automatic_admission_digest(path,previous)




def everyday_manifest():
    data = json.loads((BACKEND/'tests/fixtures/everyday_context_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version'] == 'everyday-context-1.0.0' and data['default_activation'] is False
    assert not data['additions']
    assert set(data['replacements']) == {
        'backend/app/application/nlp/general_context_interpreter.py', 'backend/app/application/nlp/config/context_grammar.v1.json',
        'backend/app/application/recommendation/config/situation_taxonomy.v1.json', 'backend/app/application/recommendation/config/context_policy_registry.v1.json',
        'backend/app/application/recommendation/context_policy_registry.py', 'backend/app/application/recommendation/general_context_evaluator.py',
        'frontend/lib/api.ts', 'frontend/lib/recommendation-messages.ts', 'frontend/components/OutfitAssistant.tsx', 'frontend/components/RecommendationResult.tsx'}
    return data


def everyday_digest(path, previous):
    change = everyday_manifest()['replacements'].get(path)
    if change and previous in (change['before'], change['after']):
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest() == owner_style_digest(path, change['after']), path
        return owner_style_digest(path, change['after'])
    return owner_style_digest(path, previous)


def professional_academic_manifest():
    data = json.loads((BACKEND/'tests/fixtures/professional_academic_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version'] == 'professional-academic-context-1.0.0' and data['default_activation'] is False
    assert set(data['replacements']) == {
        'backend/app/application/nlp/general_context_interpreter.py', 'backend/app/application/nlp/config/context_grammar.v1.json',
        *('backend/app/application/recommendation/'+n+'.py' for n in ('context_policy_registry','context_constraint_compiler','context_evidence_resolver','general_context_evaluator')),
        'backend/app/application/recommendation/config/situation_taxonomy.v1.json', 'backend/app/application/recommendation/config/context_policy_registry.v1.json',
        'frontend/lib/api.ts','frontend/lib/recommendation-messages.ts','frontend/components/OutfitAssistant.tsx','frontend/components/RecommendationResult.tsx',
        'backend/app/shared_contracts/confirmed_garment_snapshot.py','backend/app/infrastructure/persistence/confirmed_garment_query_adapter.py',
        'backend/app/domain/value_objects/requests.py','backend/app/api/wardrobe_routes.py','backend/app/application/wardrobe/wardrobe_service.py','frontend/app/wardrobe/page.tsx'}
    assert set(data['additions']) == {'backend/app/domain/value_objects/general_context_evidence.py','backend/app/application/wardrobe/attribute_evidence_review.py'}
    for name,digest in data['additions'].items():
        assert hashlib.sha256((BACKEND.parent/name).read_bytes()).hexdigest() == digest,name
    return data


def professional_academic_digest(path, previous):
    change = professional_academic_manifest()['replacements'].get(path)
    if change and previous in (change['before'],change['after']):
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest() == everyday_digest(path, change['after']),path
        return everyday_digest(path, change['after'])
    return everyday_digest(path, previous)


def date_dinner_manifest():
    data = json.loads((BACKEND/'tests/fixtures/date_dinner_context_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version'] == 'date-dinner-context-1.0.0' and data['default_activation'] is False
    assert not data['additions']
    assert set(data['replacements']) == {
        'backend/app/application/nlp/general_context_interpreter.py',
        'backend/app/application/nlp/config/context_grammar.v1.json',
        *('backend/app/application/recommendation/'+name+'.py' for name in (
            'context_policy_registry', 'context_constraint_compiler', 'context_evidence_resolver', 'general_context_evaluator')),
        'backend/app/application/recommendation/config/situation_taxonomy.v1.json',
        'backend/app/application/recommendation/config/context_policy_registry.v1.json',
        'frontend/lib/api.ts', 'frontend/lib/recommendation-messages.ts',
        'frontend/components/OutfitAssistant.tsx', 'frontend/components/RecommendationResult.tsx'}
    return data


def date_dinner_digest(path, previous):
    change = date_dinner_manifest()['replacements'].get(path)
    if change and previous in (change['before'], change['after']):
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest() == professional_academic_digest(path, change['after']), path
        return professional_academic_digest(path, change['after'])
    return professional_academic_digest(path, previous)


def general_context_manifest():
    data = json.loads((BACKEND/'tests/fixtures/general_context_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version'] == 'general-context-foundations-1.0.0' and data['default_activation'] is False
    assert set(data['replacements']) == {
        *('backend/app/application/recommendation/'+name+'.py' for name in (
            'contextual_selection', 'compact_assistant_scorer', 'request_candidate_engine',
            'compact_mandatory_verifier', 'compact_exhaustive_scorer', 'scoring_eligibility_gate', 'outfit_assistant_service')),
        'backend/app/infrastructure/workflow_runtime.py', 'backend/app/domain/value_objects/assistant_execution_context.py',
        'backend/app/api/recommendation_routes.py', 'frontend/lib/api.ts', 'frontend/lib/recommendation-messages.ts',
        'frontend/components/OutfitAssistant.tsx', 'frontend/components/RecommendationResult.tsx'}
    assert set(data['additions']) == {
        'backend/app/application/nlp/general_context_interpreter.py',
        'backend/app/application/nlp/config/context_grammar.v1.json',
        'backend/app/domain/value_objects/general_context_request.py',
        *('backend/app/application/recommendation/'+name+'.py' for name in (
            'context_policy_registry', 'context_evidence_resolver', 'context_constraint_compiler', 'general_context_evaluator')),
        'backend/app/application/recommendation/config/situation_taxonomy.v1.json',
        'backend/app/application/recommendation/config/context_policy_registry.v1.json'}
    for name, digest in data['additions'].items():
        assert hashlib.sha256((BACKEND.parent/name).read_bytes()).hexdigest() == date_dinner_digest(name, digest), name
    return data


def general_context_digest(path, previous):
    change = general_context_manifest()['replacements'].get(path)
    if change and previous in (change['before'], change['after']):
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest() == date_dinner_digest(path, change['after']), path
        return date_dinner_digest(path, change['after'])
    return date_dinner_digest(path, previous)


def wedding_manifest():
    data = json.loads((BACKEND/'tests/fixtures/contextual_wedding_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version'] == 'contextual-wedding-1.0.0'
    assert data['default_activation'] is False
    assert set(data['replacements']) == {
        'backend/app/api/wardrobe_routes.py',
        'backend/app/application/recommendation/compact_exhaustive_scorer.py',
        'backend/app/application/recommendation/compact_mandatory_verifier.py',
        'backend/app/application/recommendation/outfit_assistant_service.py',
        'backend/app/application/recommendation/scoring_eligibility_gate.py',
        'backend/app/application/wardrobe/wardrobe_service.py',
        'backend/app/domain/value_objects/requests.py',
        'backend/app/infrastructure/persistence/confirmed_garment_query_adapter.py',
        'backend/app/infrastructure/workflow_runtime.py',
        'backend/app/shared_contracts/confirmed_garment_snapshot.py',
        'frontend/app/wardrobe/page.tsx', 'frontend/lib/api.ts',
        'frontend/lib/recommendation-messages.ts', 'frontend/components/OutfitAssistant.tsx',
        'frontend/components/RecommendationResult.tsx'}
    assert set(data['additions']) == {
        'backend/app/application/nlp/contextual_nlp_interpreter.py',
        'backend/app/application/recommendation/config/wedding_guest_suitability.v1.json',
        'backend/app/application/recommendation/contextual_selection.py',
        'backend/app/application/recommendation/contextual_suitability_evaluator.py',
        'backend/app/application/wardrobe/contextual_review.py',
        'backend/app/domain/value_objects/contextual_garment_evidence.py',
        'backend/app/domain/value_objects/contextual_outfit_request.py'}
    for name, digest in data['additions'].items():
        assert hashlib.sha256((BACKEND.parent/name).read_bytes()).hexdigest() == general_context_digest(name, digest), name
    return data


def wedding_digest(path, previous):
    change = wedding_manifest()['replacements'].get(path)
    if change:
        # Nested old guards can reach here before their older transitions have
        # run. Leave those hashes for the old chain; advance only our exact
        # captured before value (or recognise its exact already-advanced value).
        if previous not in (change['before'], change['after']):
            return context_relevance_digest(path,previous)
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest() == general_context_digest(path, change['after']), path
        return general_context_digest(path, change['after'])
    return general_context_digest(path, previous)


def durable_logout_manifest():
    data=json.loads((BACKEND/'tests/fixtures/durable_logout_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='durable-logout-1.0.0'
    assert set(data['replacements'])=={
        'backend/app/infrastructure/security.py','backend/app/api/account_routes.py',
        'backend/app/application/account/account_service.py',
        'backend/app/infrastructure/persistence/postgresql_repository.py',
        'frontend/lib/api.ts','frontend/components/Layout.tsx'}
    assert set(data['additions'])=={
        'backend/app/infrastructure/persistence/session_revocation_store.py',
        'backend/app/infrastructure/persistence/session_revocation_migrations.py'}
    for path,digest in data['additions'].items():
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==digest,path
    return data


def durable_logout_digest(path,previous):
    change=durable_logout_manifest()['replacements'].get(path)
    if change:
        assert change['before']==previous,path
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==wedding_digest(path,change['after']),path
        return wedding_digest(path,change['after'])
    return wedding_digest(path,previous)


def closure_manifest():
    data=json.loads((BACKEND/'tests/fixtures/functional_closure_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='functional-gap-closure-1.0.0'
    assert set(data['replacements'])=={
        'backend/app/api/account_routes.py','backend/app/application/account/account_service.py',
        'backend/app/domain/value_objects/requests.py','backend/app/application/wardrobe/wardrobe_service.py',
        'backend/app/api/wardrobe_routes.py','backend/app/application/nlp/config/vocabulary.v1.json',
        'frontend/app/auth/page.tsx','frontend/app/profile/page.tsx','frontend/app/wardrobe/page.tsx','frontend/lib/api.ts'}
    return data


def closure_digest(path, previous):
    change=closure_manifest()['replacements'].get(path)
    if change:
        assert change['before']==previous,path
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==durable_logout_digest(path,change['after']),path
        return durable_logout_digest(path,change['after'])
    return durable_logout_digest(path,previous)


def failure_logging_manifest():
    data=json.loads((BACKEND/'tests/fixtures/recommendation_failure_logging_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='recommendation-failure-logging-1.0.0'
    assert set(data['replacements'])=={'app/application/recommendation/outfit_assistant_service.py','app/application/recommendation/homepage_recommendation_service.py'}
    assert set(data['additions'])=={'app/application/recommendation/failure_diagnostics.py'}
    for name,digest in data['additions'].items():
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest()==digest,name
    return data


def failure_logging_digest(name, previous):
    change=failure_logging_manifest()['replacements'].get(name)
    if change:
        assert change['before']==previous,name
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest()==wedding_digest('backend/'+name,change['after']),name
        return wedding_digest('backend/'+name,change['after'])
    return wedding_digest('backend/'+name,previous)


def default_digest(name, previous):
    data=json.loads((BACKEND/'tests/fixtures/compact_default_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='compact-default-activation-1.0.0'
    assert data['default_engine']=='compact_exhaustive' and data['default_profile']=='compatibility_deferred'
    assert set(data['replacements'])=={'app/application/recommendation/assistant_execution_selection.py','app/application/recommendation/outfit_assistant_service.py','app/infrastructure/workflow_runtime.py'}
    change=data['replacements'].get(name)
    if change:
        assert change['before']==previous,name
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest()==failure_logging_digest(name,change['after']),name
        return failure_logging_digest(name,change['after'])
    return failure_logging_digest(name,previous)


def compact_integration():
    data=json.loads((BACKEND/'tests/fixtures/compact_integration_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='compact-assistant-integration-1.0.0' and data['default_engine']=='reference'
    assert set(data['replacements'])=={'app/application/recommendation/outfit_assistant_service.py','app/infrastructure/workflow_runtime.py'}
    assert set(data['additions'])=={'app/application/recommendation/assistant_execution_selection.py','app/application/recommendation/compact_assistant_scorer.py','app/domain/value_objects/assistant_execution_context.py'}
    for name,value in {**data['additions'],**{p:v['after'] for p,v in data['replacements'].items()}}.items():
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest()==default_digest(name,value),name
    return data


def integrated_digest(name,previous):
    """Accepted ancestor entry; acyclic exact descendant resolution."""
    source_hash(name,previous)
    data=attribute_manifest();path='backend/'+name
    baseline=data['baseline_application'][name]
    return p2_digest(path,data['replacements'][path]['after'] if path in data['replacements'] else baseline)


def invariant_request_digest(name,previous):
    data=json.loads((BACKEND/'tests/fixtures/invariant_request_sources.v1.json').read_text())
    assert data['version']=='invariant-request-details-1.0.0'
    assert data['default_engine']=='compact_exhaustive' and data['default_profile']=='compatibility_deferred'
    assert data['suitability_default'] is False and data['aggregation_capacity']==256
    assert set(data['replacements'])=={'app/application/recommendation/compact_scoring_facts.py'}
    reference=data['reference']
    assert reference['file']=='tests/fixtures/invariant_request_reference/compact_scoring_facts.py'
    assert hashlib.sha256((BACKEND/reference['file']).read_bytes()).hexdigest()==reference['sha256']
    change=data['replacements'].get(name)
    if change:
        assert previous==change['before']==reference['sha256'],name
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest()==wedding_digest('backend/'+name,change['after']),name
        return wedding_digest('backend/'+name,change['after'])
    return wedding_digest('backend/'+name,previous)


def score_certificate_digest(name,previous):
    data=json.loads((BACKEND/'tests/fixtures/score_certificate_sources.v1.json').read_text())
    assert data['version']=='score-certificate-reuse-1.0.0'
    assert data['default_engine']=='compact_exhaustive' and data['default_profile']=='compatibility_deferred'
    assert set(data['replacements'])=={'app/application/recommendation/compact_scoring_facts.py'}
    reference=data['reference']
    assert reference['file']=='tests/fixtures/score_certificate_reference/compact_scoring_facts.py'
    assert hashlib.sha256((BACKEND/reference['file']).read_bytes()).hexdigest()==reference['sha256']
    change=data['replacements'].get(name)
    if change:
        assert change['before']==previous==reference['sha256'],name
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest()==invariant_request_digest(name,change['after']),name
        return invariant_request_digest(name,change['after'])
    return wedding_digest('backend/'+name,previous)


def compact_additions():
    data=json.loads((BACKEND/'tests/fixtures/compact_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='compact-exhaustive-1.0.0' and data['default_activation'] is False
    expected={'app/domain/value_objects/compact_recommendation.py',*(
        'app/application/recommendation/'+n+'.py' for n in ('compact_candidate_stream','compact_mandatory_verifier','compact_scoring_facts','compact_exhaustive_scorer'))}
    assert set(data['additions'])==expected
    for name,digest in data['additions'].items():
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest()==score_certificate_digest(name,digest),name
    return data['additions']


def critical_path_additions():
    data=json.loads((BACKEND/'tests/fixtures/critical_path_sources.v1.json').read_text(encoding='utf-8'))
    assert set(data['additions'])=={'app/application/recommendation/'+name+'.py' for name in ('prepared_compatibility_aggregation','aggregated_decision_scorer')}
    assert set(data['replacements'])=={'app/application/recommendation/assistant_scoring_selection.py'}
    for name,digest in data['additions'].items():
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest()==digest,name
    for name,entry in data['replacements'].items():
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest()==entry['after'],name
    return data


def assistant_integration():
    data=json.loads((BACKEND/"tests/fixtures/assistant_decision_integration_sources.v1.json").read_text(encoding="utf-8"))
    assert data["version"]=="assistant-decision-integration-1.0.0"
    assert set(data["replacements"])=={"app/application/recommendation/outfit_assistant_service.py","app/infrastructure/workflow_runtime.py","app/application/chat_history/chat_history_service.py"}
    assert set(data["additions"])=={"app/application/recommendation/assistant_scoring_selection.py","app/application/recommendation/scoring_display.py"}
    for name,digest in data["additions"].items():
        replacement=critical_path_additions()['replacements'].get(name)
        if replacement:assert replacement['before']==digest,name
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest()==(replacement['after'] if replacement else digest),name
    for name,entry in data["replacements"].items():
        assert set(entry)=={"before","after"}
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest()==integrated_digest(name,entry["after"]),name
    return data


def suitability_controls_manifest():
    data=json.loads((BACKEND/'tests/fixtures/suitability_controls_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='suitability-controls-1.0.0'
    assert set(data['replacements'])=={'app/application/wardrobe/wardrobe_service.py','app/api/wardrobe_routes.py'}
    assert set(data['additions'])=={'app/application/wardrobe/garment_tag_edit.py'}
    for name,digest in data['additions'].items():
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest()==digest,name
    return data


def fail_closed_digest(path, previous):
    data=json.loads((BACKEND/'tests/fixtures/fail_closed_routing_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='fail-closed-recommendation-routing-1.0.0'
    assert set(data['replacements'])=={'backend/app/api/recommendation_routes.py','frontend/lib/api.ts'}
    change=data['replacements'].get(path)
    if change:
        assert change['before']==previous,path
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==closure_digest(path,change['after']),path
        return closure_digest(path,change['after'])
    return closure_digest(path,previous)


def wardrobe_quota_digest(name, previous):
    data=json.loads((BACKEND/'tests/fixtures/wardrobe_quota_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='wardrobe-active-entries-1.0.0' and data['limit']==100
    assert set(data['replacements'])=={
        'backend/app/application/wardrobe/wardrobe_service.py', 'backend/app/api/wardrobe_routes.py',
        'backend/app/api/garment_processing_routes.py', 'frontend/app/wardrobe/page.tsx',
        'frontend/app/extract/page.tsx', 'frontend/app/extract/results/page.tsx', 'frontend/lib/api.ts'}
    for path, entry in data['replacements'].items():
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==fail_closed_digest(path,entry['after']),path
    change=data['replacements'].get('backend/'+name)
    if change:
        assert change['before']==previous,name
        return fail_closed_digest('backend/'+name,change['after'])
    return fail_closed_digest('backend/'+name,previous)


def suitability_controls_digest(name,previous):
    change=suitability_controls_manifest()['replacements'].get(name)
    if change:
        assert change['before']==previous,name
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest()==wardrobe_quota_digest(name,change['after']),name
        return wardrobe_quota_digest(name,change['after'])
    return wardrobe_quota_digest(name,previous)


def forward_style_digest(name, previous):
    data = json.loads((BACKEND / 'tests/fixtures/forward_style_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version'] == 'forward-style-evidence-1.0.0'
    assert set(data['replacements']) == {'app/application/wardrobe/wardrobe_service.py'}
    change = data['replacements'].get(name)
    if change:
        assert change['before'] == previous, name
        assert hashlib.sha256((BACKEND / name).read_bytes()).hexdigest() == suitability_controls_digest(name, change['after']), name
        return suitability_controls_digest(name, change['after'])
    return suitability_controls_digest(name, previous)


def saved_outfit_digest(name, previous):
    data = json.loads((BACKEND / 'tests/fixtures/saved_outfit_visualisation_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version'] == 'saved-outfit-visualisation-1.0.0'
    assert set(data['replacements']) == {
        'app/application/visualisation/outfit_identifier_validator.py',
        'app/application/visualisation/outfit_visualisation_service.py',
    }
    change = data['replacements'].get(name)
    if change:
        assert change['before'] == previous, name
        assert hashlib.sha256((BACKEND / name).read_bytes()).hexdigest() == change['after'], name
        return change['after']
    return previous


@lru_cache(maxsize=1)
def approved():
    # Capture the expected descendant map once for this frozen certification
    # process. source_hash still compares every actual file on every call.
    hashes = json.loads((BACKEND/"tests/fixtures/integration_actions_sources.v1.json").read_text())
    replacements=assistant_integration()["replacements"]
    for name, digest in hashes.items():
        if name in replacements:
            assert replacements[name]["before"]==digest,name
        previous=replacements.get(name,{}).get("after",digest)
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest() == integrated_digest(name,previous), name
    return {**{n:integrated_digest(n,d) for n,d in hashes.items() if n not in replacements},**{n:integrated_digest(n,d["after"]) for n,d in replacements.items()}}


def experimental_additions():
    # New opt-in modules only. Existing historical archive hashes remain authoritative.
    hashes = json.loads((BACKEND/"tests/fixtures/rule_based_experimental_sources.v1.json").read_text(encoding="utf-8"))
    for name, digest in hashes.items():
        assert "rule_based" in name, name
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest() == wedding_digest('backend/'+name,digest), name
    return hashes


def pair_cache_additions():
    hashes = json.loads((BACKEND/"tests/fixtures/compatibility_pair_cache_sources.v1.json").read_text(encoding="utf-8"))
    expected = {"app/application/recommendation/"+name+".py" for name in
                ("compatibility_pair_cache", "cached_rule_based_compatibility_scorer", "cached_rule_based_recommendation_scorer")}
    assert set(hashes) == expected
    for name, digest in hashes.items():
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest() == wedding_digest('backend/'+name,digest), name
    return hashes


def decision_additions():
    hashes = json.loads((BACKEND/"tests/fixtures/compatibility_decision_sources.v1.json").read_text(encoding="utf-8"))
    expected = {"app/domain/value_objects/compatibility_decision.py", "app/application/recommendation/config/compatibility_decision.v1.json",
                *("app/application/recommendation/"+x+".py" for x in ("compatibility_decision_policy", "decision_recommendation_scorer", "decision_score_codec"))}
    assert set(hashes) == expected
    for name, digest in hashes.items():
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest() == wedding_digest('backend/'+name,digest), name
    return hashes


def prepared_decision_additions():
    hashes = json.loads((BACKEND/"tests/fixtures/prepared_decision_sources.v1.json").read_text(encoding="utf-8"))
    assert set(hashes) == {"app/application/recommendation/"+n+".py" for n in ("prepared_decision_policy", "prepared_decision_scorer")}
    for name, digest in hashes.items():
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest() == wedding_digest('backend/'+name,digest), name
    return hashes


def _legacy_source_set(current, original, extras=()):
    additions = {**failure_logging_manifest()['additions'], **suitability_controls_manifest()['additions'], **experimental_additions(), **pair_cache_additions(), **decision_additions(), **prepared_decision_additions(), **assistant_integration()["additions"], **critical_path_additions()['additions'], **compact_additions(), **compact_integration()['additions']}
    additions.update({name.removeprefix('backend/'):digest for name,digest in durable_logout_manifest()['additions'].items()})
    additions.update({name.removeprefix('backend/'):digest for name,digest in wedding_manifest()['additions'].items() if name.startswith('backend/')})
    additions.update({name.removeprefix('backend/'):digest for name,digest in general_context_manifest()['additions'].items()})
    additions.update({name.removeprefix('backend/'):digest for name,digest in professional_academic_manifest()['additions'].items()})
    additions.update({name.removeprefix('backend/'):digest for name,digest in owner_style_manifest()['additions'].items()})
    additions.update({name.removeprefix('backend/'):digest for name,digest in automatic_admission_manifest()['additions'].items()})
    additions.update({name.removeprefix('backend/'):value for name,value in context_relevance_manifest()['additions'].items() if name.startswith('backend/')})
    for name,value in {**phase_a_manifest()['new_production'],**json.loads((BACKEND/'tests/fixtures/description_sources.v1.json').read_text(encoding='utf-8'))['additions'],**attribute_manifest()['additions']}.items():
        if name.startswith('backend/app/'):
            assert hashlib.sha256((BACKEND.parent/name).read_bytes()).hexdigest()==description_digest(name,value),name
            additions[name.removeprefix('backend/')]=value
    assert not set(additions) & (set(original) | set(approved()) | set(extras))
    assert current == set(original) | set(approved()) | set(extras) | set(additions)


def _legacy_source_hash(name, original_digest):
    replacements=assistant_integration()["replacements"]
    if name in replacements:
        legacy=json.loads((BACKEND/"tests/fixtures/integration_actions_sources.v1.json").read_text(encoding="utf-8"))
        assert replacements[name]["before"]==legacy.get(name,original_digest),name
    expected=approved()
    digest=expected[name] if name in expected else failure_logging_digest(name, forward_style_digest(name, original_digest))
    assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest() == wedding_digest('backend/'+name,digest), name


def source_set(current,original,extras=()):
    """Exact approved A+B0+B1+B2 set; old archive/member manifests stay frozen."""
    data=attribute_manifest();p2=p2_manifest();expected=set(data['baseline_application'])
    expected.update(p.removeprefix('backend/') for p in data['additions'] if p.startswith('backend/app/'))
    expected.update(p.removeprefix('backend/') for p in p2['additions'] if p.startswith('backend/app/'))
    b3=b3_manifest() if (BACKEND/'tests/fixtures/b3_palette_sources.v1.json').exists() else {'additions':{}}
    expected.update(p.removeprefix('backend/') for p in b3['additions'] if p.startswith('backend/app/'))
    assert set(original)<=expected and set(extras)<=expected
    reconciliation=reconciliation_manifest()
    added={p.removeprefix('backend/') for p in reconciliation['additions'] if p.startswith('backend/app/')}
    expected.update(added)
    assert current==expected
    for name in expected:
        path='backend/'+name
        previous=data['baseline_application'].get(name)
        after=(reconciliation_digest(path,None) if name in added else b3_digest(path,None) if path in b3['additions'] else performance_digest(path,p2['additions'][path]) if path in p2['additions'] else
            p2_digest(path,data['replacements'][path]['after'] if path in data['replacements'] else data['additions'].get(path,previous)))
        assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest()==after,name


def source_hash(name,original_digest):
    """Verify a frozen historical ancestor and every current descendant byte."""
    data=attribute_manifest();path='backend/'+name
    assert original_digest in data['historical_source_ancestry'].get(name,()),('Unknown frozen ancestor',name)
    previous=data['baseline_application'][name]
    expected=p2_digest(path,data['replacements'][path]['after'] if path in data['replacements'] else previous)
    assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest()==expected,name


RECONCILIATION_ROOT=review_path('phase_regression_contract_reconciliation_20261107')
RECONCILIATION_SCOPE='6914426ba97ebd99caa5382b0bc0f5bdf1ffa4382a123f4e3991b324ad7831c3'


def validate_reconciliation_manifest(data):
    root=RECONCILIATION_ROOT
    scope_path=root/'approved-contract/proposed-source-scope.json'
    assert hashlib.sha256(scope_path.read_bytes()).hexdigest()==RECONCILIATION_SCOPE==data['scope_sha256']
    scope=json.loads(scope_path.read_text(encoding='utf-8'))
    approval=json.loads((root/'approval.json').read_text(encoding='utf-8'))
    assert approval['answer']=='Approve exact isolated reconciliation scope, version contracts and RR-CP0\u2013CP6'
    assert approval['scope_sha256']==RECONCILIATION_SCOPE
    for name,key in (('SCHEMA_VERSION_RECONCILIATION_CONTRACT.json','schema_contract_sha256'),('INDEPENDENT_ACCEPTANCE_SPECIFICATION.json','acceptance_spec_sha256')):
        assert hashlib.sha256((root/'approved-contract'/name).read_bytes()).hexdigest()==scope[key]==approval[key]
    assert data['approval_sha256']==hashlib.sha256((root/'approval.json').read_bytes()).hexdigest()
    assert data['baseline_sha256']==hashlib.sha256((root/'baseline-source-hashes.json').read_bytes()).hexdigest()
    base=json.loads((root/'baseline-source-hashes.json').read_text(encoding='utf-8'))
    original=root.parent/'phase_final_consolidated_verification_20261106/final-combined-source-manifest.json'
    assert hashlib.sha256(original.read_bytes()).hexdigest()==scope['baseline_manifest_sha256']
    assert base==json.loads(original.read_text(encoding='utf-8'))['files'] and len(base)==833
    allowed={e['path']:e['before_sha256'] for k in ('existing_production','existing_verification') for e in scope[k]}
    additions={e['path'] for k in ('new_production','new_support','new_verification') for e in scope[k]}
    assert data['version']=='regression-reconciliation-sources-1.0.0' and data['default_activation'] is False
    assert data['historical_labels_unchanged'] is True and data['additional_historical_exceptions']==[]
    assert set(data['replacements'])<=set(allowed) and set(data['additions'])<=additions
    assert set(data['files'])==set(base)|set(data['additions'])
    for path,value in data['files'].items():
        assert type(value) is str and len(value)==64
        if path in data['replacements']:
            entry=data['replacements'][path]
            assert entry['before']==base[path]==allowed[path] and entry['after']==value,path
        elif path in data['additions']:assert data['additions'][path]==value,path
        else:assert base[path]==value,('Unapproved reconciliation edit',path)
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==value,path
    fixture=json.loads((BACKEND/'tests/fixtures/reconciliation_sources.v1.json').read_text(encoding='utf-8'))
    assert fixture['contract']=='regression-reconciliation-delivery-1.0.0' and fixture['default_activation'] is False
    assert fixture['scope_sha256']==RECONCILIATION_SCOPE and fixture['historical_labels_unchanged'] is True and fixture['additional_historical_exceptions']==[]
    assert fixture['files']=={p:h for p,h in data['files'].items() if p in set(data['replacements'])|set(data['additions']) and p!='backend/tests/fixtures/reconciliation_sources.v1.json'}
    return data


@lru_cache(maxsize=1)
def reconciliation_manifest():
    path=Path(os.environ.get('RR_MANIFEST_PATH',str(RECONCILIATION_ROOT/'checkpoint-manifest.json'))).resolve()
    assert path.is_relative_to(RECONCILIATION_ROOT.resolve())
    return validate_reconciliation_manifest(json.loads(path.read_text(encoding='utf-8')))


def reconciliation_digest(path,previous):
    if not (BACKEND/'tests/fixtures/reconciliation_sources.v1.json').exists():return previous
    data=reconciliation_manifest()
    if path in data['replacements']:
        entry=data['replacements'][path]
        assert entry['before']==previous,('Unknown reconciliation predecessor',path)
        return entry['after']
    if path in data['additions']:
        assert previous is None,('Unknown new-path predecessor',path)
        return data['additions'][path]
    return previous
