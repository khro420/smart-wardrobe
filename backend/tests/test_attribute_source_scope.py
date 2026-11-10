"""Approved B1 source transitions, complete frozen matrices and old authorities."""
from tests.retained_evidence import review_path, review_reference
import hashlib,json,os,subprocess,sys
import pytest
from pathlib import Path
from tests import integration_source_guard as guard

ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def test_exact_approved_scope_and_frozen_baseline():
    data=guard.attribute_manifest();approved=review_reference(data['approved_scope_path']).parent
    scope=json.loads((approved/'proposed-source-scope.json').read_text(encoding='utf-8'))
    starts=json.loads((approved/'starting-source-hashes.json').read_text(encoding='utf-8'))
    existing={e['path'] for k in ('existing_production','existing_verification') for e in scope[k]}
    added={e['path'] for k in ('new_production','new_verification') for e in scope[k]}
    assert len(existing)==25 and len(added)==26 and len(starts)==642
    assert set(data['additions'])==added-{'backend/tests/fixtures/attribute_sources.v1.json'}
    for path,value in starts.items():assert sha(ROOT/path)==guard.attribute_digest(path,value),path
    for path,value in data['additions'].items():assert sha(ROOT/path)==guard.p2_digest(path,value),path
    # The historical source manifests and numerical/negative labels are never
    # replaced by hashes generated from the new implementation.
    for path,value in starts.items():
        if path.startswith('backend/tests/fixtures/') and path not in existing:assert sha(ROOT/path)==value,path
    assert data['workspace_applied'] is False and data['runtime_changed'] is False


def test_all_247_rows_and_2814_authored_obligations_retained():
    data=guard.attribute_manifest();approved=review_reference(data['approved_scope_path']).parent
    matrix=json.loads((approved/'B1-attribute-value-coverage.json').read_text(encoding='utf-8'))
    rows=matrix['rows']
    assert len(rows)==247 and len({r['id'] for r in rows})==247
    fixture=json.loads((ROOT/'backend/tests/fixtures/attribute_labels.v1.json').read_text(encoding='utf-8'))
    assert fixture['finite']==json.loads((approved/'independent-finite-acceptance.json').read_text(encoding='utf-8'))
    assert len(fixture['finite']['cases'])==2814
    assert len({c['id'] for c in fixture['finite']['cases']})==2814
    assert fixture['language']==json.loads((approved/'independent-language-expectations.json').read_text(encoding='utf-8'))
    assert fixture['mechanics']==json.loads((approved/'independent-mechanics-expectations.json').read_text(encoding='utf-8'))


def test_default_off_and_unchanged_numerical_sources():
    from app.application.recommendation.attribute_execution_selection import AttributeExecutionSelection
    assert AttributeExecutionSelection().enabled is False
    data=guard.attribute_manifest();baseline=review_reference(data['baseline_source_path'])
    for name in ('request_match_scorer','preference_scorer','compact_scoring_facts','context_relevance_scorer','refinement_selector'):
        path='backend/app/application/recommendation/'+name+'.py'
        assert sha(ROOT/path)==sha(baseline/path),path
    for path in ('backend/app/shared_contracts/confirmed_garment_snapshot.py','backend/app/domain/value_objects/structured_outfit_request.py','backend/app/domain/value_objects/preference_snapshot.py'):
        assert sha(ROOT/path)==sha(baseline/path),path


def original_values(expected,actual):
    """Every original field/value/order is exact; only named old additions exist."""
    if isinstance(expected,dict):
        assert isinstance(actual,dict) and set(expected)<=set(actual)
        assert set(actual)-set(expected)<={'ranking_evidence','refinement_summary','appearance_evidence','contextual_suitability','saved_attribute_evidence'}
        for key,value in expected.items():original_values(value,actual[key])
    elif isinstance(expected,list):
        assert isinstance(actual,list) and len(expected)==len(actual)
        for left,right in zip(expected,actual):original_values(left,right)
    else:assert type(actual) is type(expected) and actual==expected


def worker(tmp_path,label,reference,variant,cases,*,progress=False,digest=False):
    path=tmp_path/(label+'-cases.json');output=tmp_path/(label+'-output.json')
    path.write_text(json.dumps(cases),encoding='utf-8')
    command=[sys.executable,'-B',str(ROOT/'backend/tests/performance_worker.py'),
        '--reference',str(reference),'--variant',variant,'--fixtures',str(path),'--output',str(output),'--digest' if digest else '--trace']
    if progress:command.append('--progress')
    completed=subprocess.run(command,capture_output=True)
    (tmp_path/(label+'-native.log')).write_bytes(completed.stdout+completed.stderr)
    assert completed.returncode==0,completed.stderr.decode(errors='replace')
    return [{k:v for k,v in row.items() if k!='timings'} for row in json.loads(output.read_text())]


@pytest.mark.parametrize('variant',['request','preference','prepared','combined'])
def test_old_2a_original_values_exact_through_named_metadata_descendant(tmp_path,variant):
    from tests.test_scoring_hot_path_equivalence import hot_path_cases
    fixtures=Path(os.environ.get('B1_ORACLE_ARCHIVE_DIR',str(ROOT/'backend/tests/fixtures')))
    reference=fixtures/'performance_reference_2a';cases=hot_path_cases()
    expected=worker(tmp_path,'old',reference,'original',cases)
    current=worker(tmp_path,'current',reference,variant,cases)
    original_values(expected,current)


def test_full_trace_equals_actual_approved_phase_a_b0_before_b1(tmp_path):
    from tests.test_scoring_hot_path_equivalence import hot_path_cases
    reference=Path(os.environ['B1_APPROVED_BASELINE_ORACLE']);manifest=json.loads((reference/'manifest.json').read_text())
    approved=review_reference(guard.attribute_manifest()['approved_scope_path']).parent
    starting=json.loads((approved/'starting-source-hashes.json').read_text())
    assert manifest=={p.removeprefix('backend/'):h for p,h in starting.items() if p.startswith('backend/app/')}
    cases=hot_path_cases()
    expected=worker(tmp_path,'approved-baseline',reference,'original',cases,progress=True)
    current=worker(tmp_path,'current-b1',reference,'combined',cases,progress=True)
    assert current==expected
    assert sum(len(row['progress']) for row in current)>500 and any(row.get('persisted') for row in current)


@pytest.mark.parametrize('folder',['performance_reference_2b','performance_reference_2d1'])
def test_old_progress_and_assistant_values_exact_through_named_descendant(tmp_path,folder):
    from tests.test_scoring_hot_path_equivalence import hot_path_cases
    fixtures=Path(os.environ.get('B1_ORACLE_ARCHIVE_DIR',str(ROOT/'backend/tests/fixtures')));cases=hot_path_cases()
    expected=worker(tmp_path,'old',fixtures/folder,'original',cases,progress=True)
    current=worker(tmp_path,'current',fixtures/folder,'combined',cases,progress=True)
    original_values(expected,current)
    if folder=='performance_reference_2d1':
        trial=worker(tmp_path,'original-trial',fixtures/'performance_trial_2d2','original',cases,progress=True)
        assert trial==expected
    assert sum(len(row['progress']) for row in current)>500 and any(row.get('persisted') for row in current)


@pytest.mark.parametrize('populated',[False,True])
def test_large_stream_exact_approved_baseline_digest_and_original_counts(tmp_path,populated):
    from tests.test_assistant_performance_equivalence import garment,preferences
    rows=[]
    for category,count in (('vest',24),('trousers',24),('vest_dress',6),('long_sleeve_outwear',6)):
        rows.extend(garment(f'{category}-{n:04d}',category,primary_colour='blue',style_tags=['vintage']) for n in range(count))
    cases=[dict(name='large-synthetic',garments=rows,preferences=preferences() if populated else [],service=True)]
    fixtures=Path(os.environ.get('B1_ORACLE_ARCHIVE_DIR',str(ROOT/'backend/tests/fixtures')))
    accepted=Path(os.environ['B1_APPROVED_BASELINE_ORACLE'])
    old=worker(tmp_path,'old-large',fixtures/'performance_reference_2a','original',cases,digest=True)[0]
    baseline=worker(tmp_path,'approved-large',accepted,'original',cases,digest=True)[0]
    current=worker(tmp_path,'current-large',accepted,'combined',cases,digest=True)[0]
    assert current==baseline # exact whole transcript digest, including current metadata
    assert {k:v for k,v in old.items() if k!='transcript'}=={k:v for k,v in current.items() if k!='transcript'}
    assert old['scored_count']==baseline['scored_count']==current['scored_count']==4074
    assert old['transcript']['events']==baseline['transcript']['events']==current['transcript']['events']==12222
