from tests.integration_source_guard import source_set, source_hash
"""Completed-2B independent progress oracle; synthetic validation faults only."""
from dataclasses import dataclass, field, InitVar, FrozenInstanceError, fields, replace
import hashlib, json, subprocess, sys, zipfile
from types import SimpleNamespace
import pytest
from tests.test_scoring_hot_path_equivalence import hot_path_cases
from tests.test_assistant_performance_equivalence import BACKEND
from app.application.recommendation.recommendation_engine import CandidateGenerationSession
from app.application.recommendation.request_candidate_session import RequestCandidateSession, RequestProcessingError
from app.domain.value_objects.candidate_generation_result import CandidateGenerationResult, GarmentExclusion
from app.domain.value_objects.request_candidate_evaluation import RequestGenerationResult, RequestEvaluation, MandatoryCondition

REFERENCE = BACKEND / 'tests/fixtures/performance_reference_2b'

def execute(path, variant):
    source=path/'cases.json'; source.write_text(json.dumps(hot_path_cases()))
    output=path/(variant+'.json')
    subprocess.run([sys.executable,'-B',str(BACKEND/'tests/performance_worker.py'),'--reference',str(REFERENCE),'--variant',variant,'--fixtures',str(source),'--output',str(output),'--trace','--progress'],check=True,capture_output=True)
    return [{k:v for k,v in row.items() if k!='timings'} for row in json.loads(output.read_text())]

def test_completed_2b_full_trace_and_every_validated_progress(tmp_path):
    original=execute(tmp_path,'original'); current=execute(tmp_path,'combined')
    assert original==current
    assert sum(len(row['progress']) for row in current)>500
    assert any(row.get('persisted') for row in current)

def test_completed_2b_integrity():
    manifest=json.loads((REFERENCE/'manifest.json').read_text())
    allowed={'app/application/recommendation/'+name+'.py' for name in ('recommendation_engine','request_candidate_session')}
    current={p.relative_to(BACKEND).as_posix() for p in (BACKEND/'app').rglob('*') if p.suffix in ('.py','.json')}
    source_set(current,manifest)
    with zipfile.ZipFile(REFERENCE/'app.zip') as z:
        assert set(z.namelist())==set(manifest)
        for name,digest in manifest.items():
            assert hashlib.sha256(z.read(name)).hexdigest()==digest
            if name not in allowed: source_hash(name,digest)

@pytest.mark.parametrize('kind',['structural','request'])
def test_subclass_generic_replace_initvar_and_init_false(kind):
    base=CandidateGenerationResult if kind=='structural' else RequestGenerationResult
    @dataclass(frozen=True)
    class Extended(base):
        marker: str='kept'
        init_token: InitVar[str]='default'
        derived: str=field(init=False)
        def __post_init__(self,init_token):
            super().__post_init__()
            object.__setattr__(self,'derived',init_token+':'+self.status)
    before=Extended('Pending',False,marker='custom',init_token='original')
    if kind=='structural':
        session=CandidateGenerationSession([object()],before)
        next(session); expected=replace(before,status='Running',candidate_count=1)
    else:
        structural=CandidateGenerationSession([object()],CandidateGenerationResult('Pending',False))
        evaluator=SimpleNamespace(evaluate=lambda *_:RequestEvaluation((MandatoryCondition('style','vintage','Fail'),)))
        session=RequestCandidateSession(structural,None,evaluator,before)
        list(session); expected=replace(before,status='NoMatchingCandidates',complete=True,examined=1,failed=1)
    assert type(session.result) is Extended and session.result==expected
    assert before.derived=='original:Pending' and before.marker=='custom'
    with pytest.raises(FrozenInstanceError): session.result.status='Pending'

@pytest.mark.parametrize('state',['Pass','Fail','Unknown'])
def test_every_rejected_or_accepted_progress_is_fresh_and_validated(monkeypatch,state):
    from tests.test_structural_candidates import garment,Query
    from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
    snapshots=[]; original=RequestGenerationResult.__post_init__
    def validated(self):
        original(self); snapshots.append(self)
    monkeypatch.setattr(RequestGenerationResult,'__post_init__',validated)
    styles={'Pass':('vintage',),'Fail':('classic',),'Unknown':None}[state]
    rows=[replace(garment('d'+str(i),'vest_dress'),style_tags=styles) for i in range(3)]
    session=RequestCandidateEngine(Query(rows)).generate_candidates('owner',StructuredOutfitRequest(style='vintage'))
    list(session)
    running=[s for s in snapshots if s.status=='Running']
    assert [s.examined for s in running]==[1,2,3]
    assert [getattr(s,{'Pass':'passed','Fail':'failed','Unknown':'unknown'}[state]) for s in running]==[1,2,3]
    assert len({id(s) for s in running})==3 and session.result.complete

def test_structural_all_fields_and_validation_exception_boundary(monkeypatch):
    before=CandidateGenerationResult('Pending',False,7,'retain',(GarmentExclusion('bad','unknown'),))
    session=CandidateGenerationSession([object()],before); next(session)
    assert session.result==replace(before,status='Running',candidate_count=8)
    assert session.result is not before and before.candidate_count==7
    original=CandidateGenerationResult.__post_init__
    def fail(self):
        original(self)
        if self.status=='Running': raise ValueError('synthetic validation')
    monkeypatch.setattr(CandidateGenerationResult,'__post_init__',fail)
    session=CandidateGenerationSession([object()],before)
    with pytest.raises(ValueError,match='synthetic validation'): next(session)
    assert session.result is before and not session._terminal

def test_request_validation_failure_still_closes_and_reports_processing_failure(monkeypatch):
    structural=CandidateGenerationSession([object()],CandidateGenerationResult('Pending',False))
    evaluator=SimpleNamespace(evaluate=lambda *_:RequestEvaluation((MandatoryCondition('style','vintage','Fail'),)))
    before=RequestGenerationResult(reason='retain')
    session=RequestCandidateSession(structural,None,evaluator,before)
    original=RequestGenerationResult.__post_init__
    def fail(self):
        original(self)
        if self.status=='Running': raise ValueError('synthetic validation')
    monkeypatch.setattr(RequestGenerationResult,'__post_init__',fail)
    with pytest.raises(RequestProcessingError): next(session)
    assert session.result.status=='ProcessingFailure' and session.result.examined==0
    assert structural.result.status=='Interrupted'

def test_result_field_schema_guard():
    assert tuple(f.name for f in fields(CandidateGenerationResult))==('status','complete','candidate_count','reason','exclusions','validity')
    assert tuple(f.name for f in fields(RequestGenerationResult))==('status','complete','examined','passed','failed','unknown','reason')
    assert all(f.init for cls in (CandidateGenerationResult,RequestGenerationResult) for f in fields(cls))

def test_request_preserves_nonzero_counters_and_reason():
    before=RequestGenerationResult('Running',False,7,4,1,2,'retained diagnostic')
    structural=CandidateGenerationSession([object()],CandidateGenerationResult('Pending',False))
    evaluator=SimpleNamespace(evaluate=lambda *_:RequestEvaluation((MandatoryCondition('style','vintage','Fail'),)))
    seen=[];original=evaluator.evaluate
    def evaluate(*args):
        seen.append(session.result)
        return original(*args)
    evaluator.evaluate=evaluate
    session=RequestCandidateSession(structural,None,evaluator,before)
    list(session)
    assert seen==[before] and before.examined==7
    assert session.result==replace(before,status='MatchingCandidates',complete=True,examined=8,failed=2)

def test_interleaved_sessions_never_share_progress():
    a=CandidateGenerationSession([object(),object()],CandidateGenerationResult('Pending',False,reason='A'))
    b=CandidateGenerationSession([object()],CandidateGenerationResult('Pending',False,reason='B'))
    next(a);saved=a.result;next(b);next(a)
    assert saved.candidate_count==1 and a.result.candidate_count==2 and b.result.candidate_count==1
    assert (a.result.reason,b.result.reason)==('A','B')
    a.close();assert not b._terminal
    assert b.result.status=='Running' and saved.status=='Running'

def test_unknown_dataclass_result_uses_original_generic_operation():
    @dataclass(frozen=True)
    class Foreign:
        status: str='Pending'
        complete: bool=False
        candidate_count: int=0
        marker: str='foreign default'
    before=Foreign(marker='retained foreign data')
    session=CandidateGenerationSession([object()],before)
    next(session)
    assert type(session.result) is Foreign
    assert session.result==replace(before,status='Running',candidate_count=1)

def test_required_subclass_initvar_keeps_generic_exception_semantics():
    @dataclass(frozen=True,kw_only=True)
    class RequiresToken(CandidateGenerationResult):
        token: InitVar[str]
        def __post_init__(self,token):
            super().__post_init__()
    before=RequiresToken('Pending',False,token='supplied only at construction')
    session=CandidateGenerationSession([object()],before)
    with pytest.raises(ValueError,match='InitVar') as expected:
        replace(before,status='Running',candidate_count=1)
    with pytest.raises(type(expected.value),match='InitVar') as actual:
        next(session)
    assert str(actual.value)==str(expected.value)
    assert session.result is before and not session._terminal
