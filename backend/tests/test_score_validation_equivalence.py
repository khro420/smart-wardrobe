from tests.integration_source_guard import source_set, source_hash
"""Independent final-score arithmetic, malformed input and full Assistant oracle."""
import hashlib,json,subprocess,sys,zipfile
from tests.test_assistant_performance_equivalence import BACKEND
from tests.test_scoring_hot_path_equivalence import hot_path_cases
REFERENCE=BACKEND/'tests/fixtures/performance_reference_2d1'
TRIAL=BACKEND/'tests/fixtures/performance_trial_2d2'

def test_independent_validator_types_values_precedence_and_diagnostics(tmp_path):
    outputs=[]
    for label,frozen in (('reference',REFERENCE),('trial',TRIAL),('live',None)):
        out=tmp_path/(label+'.json')
        command=[sys.executable,'-B',str(BACKEND/'tests/score_validation_worker.py'),'--output',str(out)]
        if frozen:command+=['--reference',str(frozen)]
        subprocess.run(command,check=True,capture_output=True)
        outputs.append(json.loads(out.read_text()))
    assert outputs[0]==outputs[1]==outputs[2]
    assert len(outputs[0])>850
    assert any(x.get('error')==['ValueError','Total does not match component calculation.'] for x in outputs[0])
    assert any(x['calls'] for x in outputs[0])

def test_independent_completed_2d1_full_assistant_trace(tmp_path):
    source=tmp_path/'cases.json';source.write_text(json.dumps(hot_path_cases()))
    outputs=[]
    for label,reference,variant in (('reference',REFERENCE,'original'),('trial',TRIAL,'original'),('live',REFERENCE,'combined')):
        out=tmp_path/(label+'.json')
        subprocess.run([sys.executable,'-B',str(BACKEND/'tests/performance_worker.py'),'--reference',str(reference),'--variant',variant,'--fixtures',str(source),'--output',str(out),'--trace','--progress'],check=True,capture_output=True)
        outputs.append([{k:v for k,v in row.items() if k!='timings'} for row in json.loads(out.read_text())])
    assert outputs[0]==outputs[1]==outputs[2]

def test_frozen_completed_2d1_only_approved_application_file_changed():
    manifest=json.loads((REFERENCE/'manifest.json').read_text())
    current={p.relative_to(BACKEND).as_posix() for p in (BACKEND/'app').rglob('*') if p.suffix in ('.py','.json')}
    source_set(current,manifest)
    with zipfile.ZipFile(REFERENCE/'app.zip') as z:
        assert set(z.namelist())==set(manifest)
        for name,digest in manifest.items():
            assert hashlib.sha256(z.read(name)).hexdigest()==digest
            source_hash(name,digest)
    trial_manifest=json.loads((TRIAL/'manifest.json').read_text())
    assert [name for name in manifest if manifest[name]!=trial_manifest[name]]==['app/domain/value_objects/recommendation_score.py']
    with zipfile.ZipFile(TRIAL/'app.zip') as z:
        assert set(z.namelist())==set(trial_manifest)
        for name,digest in trial_manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
