"""Pin explicitly authorized integration changes without weakening scoring oracles."""
import hashlib
import json
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def recommendation_refinement_digest(path, previous):
    data=json.loads((BACKEND/'tests/fixtures/recommendation_refinement_sources.v1.json').read_text(encoding='utf-8'))
    assert data['version']=='recommendation-refinement-sources-1.0.0' and data['default_activation'] is False
    entry=data['source_guard'] if path=='backend/tests/integration_source_guard.py' else data['replacements'].get(path)
    if entry and previous in (entry['before'],entry['after']):
        assert hashlib.sha256((BACKEND.parent/path).read_bytes()).hexdigest()==entry['after'],path
        return entry['after']
    return previous


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
            assert hashlib.sha256((BACKEND.parent/name).read_bytes()).hexdigest() == digest, name
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
        assert hashlib.sha256((BACKEND.parent/name).read_bytes()).hexdigest() == digest, name
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
    change=compact_integration()['replacements'].get(name)
    if change:
        assert change['before']==previous,name
        return score_certificate_digest(name, forward_style_digest(name, saved_outfit_digest(name, default_digest(name,change['after']))))
    return score_certificate_digest(name, forward_style_digest(name, saved_outfit_digest(name, default_digest(name,previous))))


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


def approved():
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


def source_set(current, original, extras=()):
    additions = {**failure_logging_manifest()['additions'], **suitability_controls_manifest()['additions'], **experimental_additions(), **pair_cache_additions(), **decision_additions(), **prepared_decision_additions(), **assistant_integration()["additions"], **critical_path_additions()['additions'], **compact_additions(), **compact_integration()['additions']}
    additions.update({name.removeprefix('backend/'):digest for name,digest in durable_logout_manifest()['additions'].items()})
    additions.update({name.removeprefix('backend/'):digest for name,digest in wedding_manifest()['additions'].items() if name.startswith('backend/')})
    additions.update({name.removeprefix('backend/'):digest for name,digest in general_context_manifest()['additions'].items()})
    additions.update({name.removeprefix('backend/'):digest for name,digest in professional_academic_manifest()['additions'].items()})
    additions.update({name.removeprefix('backend/'):digest for name,digest in owner_style_manifest()['additions'].items()})
    additions.update({name.removeprefix('backend/'):digest for name,digest in automatic_admission_manifest()['additions'].items()})
    additions.update({name.removeprefix('backend/'):value for name,value in context_relevance_manifest()['additions'].items() if name.startswith('backend/')})
    assert not set(additions) & (set(original) | set(approved()) | set(extras))
    assert current == set(original) | set(approved()) | set(extras) | set(additions)


def source_hash(name, original_digest):
    replacements=assistant_integration()["replacements"]
    if name in replacements:
        legacy=json.loads((BACKEND/"tests/fixtures/integration_actions_sources.v1.json").read_text(encoding="utf-8"))
        assert replacements[name]["before"]==legacy.get(name,original_digest),name
    expected=approved()
    digest=expected[name] if name in expected else failure_logging_digest(name, forward_style_digest(name, original_digest))
    assert hashlib.sha256((BACKEND/name).read_bytes()).hexdigest() == wedding_digest('backend/'+name,digest), name
