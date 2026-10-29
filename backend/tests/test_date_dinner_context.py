"""Approved independently labelled API cases; no private data or model inference."""
from dataclasses import replace
from itertools import product
import json
import os
from pathlib import Path
import re
import uuid
import pytest
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.recommendation.general_context_evaluator import GeneralContextEvaluator
from app.application.recommendation.context_policy_registry import ContextPolicyRegistry, CONFIG
from app.domain.value_objects.contextual_garment_evidence import KEY
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.security import issue_access_token
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.ports.assistant_runtime import assistant_service
from tests.test_contextual_wedding import reviewed, patch, review
from tests.test_suitability_controls import patch_tags
from tests.test_release_configuration import release, submit
from tests.test_forward_style_semantics import lifecycle

LABELS = json.loads((Path(__file__).with_name('fixtures')/'date_dinner_context_labels.v1.json').read_text())


@pytest.fixture
def date_api(release, monkeypatch):
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE', 'general_context_v1')
    configure_local_workflow()
    return release


def write_observation(case, response, result):
    folder = os.environ.get('SMART_WARDROBE_DATE_DINNER_EVIDENCE')
    if folder:
        target = Path(folder)/('case-'+case['id']+'.json')
        assert not target.exists()
        target.write_text(json.dumps({'label': case, 'http_status': response.status_code, 'response': result}, indent=2)+'\n')


@pytest.mark.parametrize('case', LABELS['cases'], ids=[c['id'] for c in LABELS['cases']])
def test_approved_actual_api_matrix(date_api, monkeypatch, case):
    client, create = date_api
    identifier, fixture, text = case['id'], case['fixture'], case['request']
    style = 'smart casual' if fixture.startswith('F1') else 'classic' if fixture.startswith('F2') else 'casual'
    ids = []
    def add(category='vest_dress', do_review=True):
        gid = create([style])
        patch(client, gid, {'category': category, 'primary_colour': 'blue'})
        if do_review:
            assert review(client, gid, review_style=True).status_code == 200
        ids.append(gid)
        return gid
    base = add('long_sleeve_top' if identifier in ('G05', 'G06') else 'vest_dress',
               not fixture.startswith('F2') and identifier != 'E16')
    if identifier == 'E18':
        assert review(client, base, review_style=True).status_code == 200
    if identifier == 'E12':
        assert review(client, base, wedding_choice='allow').status_code == 200
    tags = re.findall(r'rec:v1:[a-z_]+:[a-z_]+:(?:allow|deny)', fixture)
    extra = {
        'U01': ['rec:v1:occasion:date:allow'], 'U02': ['rec:v1:occasion:dinner:allow'],
        'E07': ['rec:v1:occasion:date:allow', 'rec:v1:occasion:date:deny'],
        'E08': ['rec:v1:occasion:dinner:allow', 'rec:v2:occasion:dinner:allow'],
        'E09': ['rec:v1:occasion:date:deny', 'rec:v2:occasion:date:allow'],
        'E13': ['rec:v1:occasion:dinner:allow', 'rec:v1:formality:casual:deny'],
        'E14': ['rec:v1:occasion:date:deny', 'rec:v1:formality:casual:allow'],
        'E20': ['rec:v1:occasion:dinner:allow'], 'H02': ['rec:v1:occasion:date:deny'],
    }
    tags = extra.get(identifier, tags)
    assert patch_tags(client, base, tags).status_code == 200
    if identifier == 'E17':
        patch(client, base, {'category': 'sling_dress'})
    if identifier == 'E20':
        # Deliberately corrupt only this synthetic fixture's namespace. Both
        # canonical attribute mirrors retain the same fault for the real reader.
        with db.connection() as conn:
            for column in ('attributes_json', 'additional_attributes'):
                row = conn.execute('SELECT '+column+' FROM garments WHERE id=?', (base,)).fetchone()
                attributes = json.loads(row[0]); attributes[KEY] = {'schema_version': 'invalid'}
                conn.execute('UPDATE garments SET '+column+'=? WHERE id=?', (json.dumps(attributes), base))
    if identifier in ('G01', 'G02'):
        with db.connection() as conn:
            conn.execute('UPDATE garments SET status=? WHERE id=?', ('archived' if identifier == 'G01' else 'unavailable', base))
    if identifier == 'G03':
        db.ensure_user('other-owner')
        client.headers['Authorization'] = 'Bearer '+issue_access_token('other-owner')
    if identifier == 'G04':
        with db.connection() as conn:
            conn.execute("UPDATE processing_items SET review_status='accepted' WHERE id=(SELECT processing_item_id FROM garments WHERE id=?)", (base,))
    if identifier == 'G06':
        add('trousers'); outer = add('long_sleeve_outwear')
        assert patch_tags(client, outer, ['rec:v1:occasion:dinner:deny']).status_code == 200
    if identifier == 'G07':
        add('long_sleeve_outwear', False)
    if identifier == 'G08':
        add('long_sleeve_top'); add('trousers'); add('long_sleeve_outwear')
    key = uuid.uuid4().hex
    if identifier in ('P01', 'P03'):
        if identifier == 'P01':
            assert patch_tags(client, base, ['rec:v1:occasion:date:allow']).status_code == 200
            monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE', 'disabled')
            configure_local_workflow()
        text = 'Suggest an outfit for a date'
        _, previous = submit(client, text, key)
        assert previous['outcome'] == 'Selected', previous
        monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE', 'general_context_v1')
        configure_local_workflow()
        if identifier == 'P03': text = "I'm going on a date"
    if identifier == 'P02':
        repository = assistant_service().repository
        original = repository.persist_assistant
        def change_review(command):
            patch(client, base, {'style': ['classic']})
            return original(command)
        monkeypatch.setattr(repository, 'persist_assistant', change_review)
    response, result = submit(client, text, key)
    write_observation(case, response, result)
    # Explicit approved 1.4 overlay; retained labels still describe the old policy.
    expected_outcome = 'Selected' if identifier in ('E16','E17') else case['expected_outcome']
    assert result['outcome'] == expected_outcome, result
    if identifier == 'P01':
        assert result['replayed'] and result['recommendation'] == previous['recommendation']
        assert result['score_metadata'] == previous['score_metadata']
    if identifier == 'P02':
        with db.connection() as conn:
            assert conn.execute('SELECT count(*) FROM nlp_chats').fetchone()[0] == 0
    if result['outcome'] == 'Selected' and identifier != 'P01':
        proof = result['recommendation']['provenance']['general_context']
        assert proof['declaration_target'] == case['occasion_target']
        assert not any('Guest role' in assumption for assumption in proof['assumptions'])
        assert bool(proof['policy_note']) == (proof['dress_code'] is None and proof['formality'] is None)
        expected_total = {'numerator': 4, 'denominator': 5} if identifier in ('G06', 'G07', 'G08') else {'numerator': 7, 'denominator': 10}
        assert result['score_metadata']['total'] == expected_total
        assert all(c['basis'] == ('explicit_declaration' if identifier in ('E05', 'E06') else 'saved_attribute_provisional' if identifier in ('E16','E17') or identifier=='G07' and m['garment_id']!=base else 'attribute_inference')
                   for m in proof['members'] for c in m['conditions'] if c['field'] == 'occasion')
        if identifier == 'G06':
            assert {item['garment_id'] for item in result['recommendation']['items']} == set(ids[:2])
        if identifier == 'G07':
            assert [item['garment_id'] for item in result['recommendation']['items']] == ids  # 1.4 admits its valid saved-style outerwear.


@pytest.mark.parametrize('occasion,code,style,reviewed_flag,decisions', list(product(
    ['date', 'dinner'], [None, 'casual', 'smart_casual'], ['casual', 'smart casual', 'classic', None],
    [True, False], [(), ('allow',), ('deny',), ('allow', 'deny')])) )
def test_independent_social_member_truth_table(occasion, code, style, reviewed_flag, decisions):
    request = GeneralContextInterpreter().interpret('Suggest an outfit for '+occasion+
        ('' if code is None else '; the dress code is '+code.replace('_', ' '))).structured_request
    garment = reviewed(styles=() if style is None else (style,), review=reviewed_flag)
    garment = replace(garment, custom_tags=tuple('rec:v1:occasion:'+occasion+':'+d for d in decisions))
    # Separate labelled reduction; no production rule/config/resolver called.
    allowed = ('casual', 'smart casual') if code is None else (('casual',) if code == 'casual' else ('smart casual',))
    expected = ('Fail' if 'deny' in decisions else 'Pass' if decisions == ('allow',)
                else 'Pass' if style in allowed else 'Unknown')
    actual = GeneralContextEvaluator().member_condition(garment, request, 'occasion')
    assert actual[0] == expected
    if expected == 'Pass':
        assert actual[1] == ('explicit_declaration' if decisions else 'attribute_inference' if reviewed_flag else 'saved_attribute_provisional')


@pytest.mark.parametrize('mutation', ['values', 'operator', 'venue', 'companion', 'target', 'assumption', 'missing', 'extra', 'source', 'version'])
def test_social_registry_rejects_unapproved_mutations(tmp_path, mutation):
    data = json.loads((CONFIG/'context_policy_registry.v1.json').read_text())
    binding = data['bindings'][1]
    if mutation == 'values': binding['predicates'][0]['values'].append('classic')
    if mutation == 'operator': binding['predicates'][0]['operator'] = 'reviewed_style_equals'
    if mutation == 'venue': binding['allowed_venues'].append('hotel')
    if mutation == 'companion': binding['allowed_companions'].append('friends')
    if mutation == 'target': binding['declaration_target'] = 'dinner'
    if mutation == 'assumption': binding['assumed_role'] = 'guest'
    if mutation == 'missing': data['bindings'].pop()
    if mutation == 'extra': binding['python'] = 'anything'
    if mutation == 'source': binding['declaration_source'] = 'wedding_overrides_v1'
    if mutation == 'version': data['version'] = 'context-registry-1.0.0'
    target = tmp_path/'invalid.json'; target.write_text(json.dumps(data))
    with pytest.raises((ValueError, TypeError)):
        ContextPolicyRegistry.load(target)
