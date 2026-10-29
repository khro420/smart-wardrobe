from pathlib import Path
from dataclasses import replace
import hashlib,json
import pytest
from app.application.recommendation.context_bundle import ContextBundle,bounded_resource,ARCHIVES,ACTIVE_WAVE
from app.application.recommendation.context_policy_registry import ContextPolicyRegistry
from app.application.recommendation.context_relevance_policy import ContextRelevancePolicy
from app.application.recommendation.context_constraint_compiler import compile_context
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.domain.value_objects.general_context_request import ContextSlot,SourceSpan
from tests.test_context_expansion_equivalence import TEXTS,rank


def test_selected_catalogue_and_specialists():
    old=ContextPolicyRegistry.load();new=ContextPolicyRegistry.load(bundle_id='context_18_v1')
    expected={'A':12,'B':16,'C':18}[ACTIVE_WAVE]
    assert len(new.bindings)==expected
    assert len(new.situations)==expected+5+(ACTIVE_WAVE!='C')
    assert len(ContextRelevancePolicy.load(bundle_id='context_18_v1').entries)==expected-3
    for sid in ('ceremony.wedding','academic.presentation','professional.job_interview'):
        assert new.binding_for(sid)==old.binding_for(sid)

@pytest.mark.parametrize('content',[b'{"x":1,"x":2}',b'{"x":NaN}',b' '*65537],ids=['duplicate','nonfinite','oversized'])
def test_invalid_bounded_resource_rejected(tmp_path,content):
    path=tmp_path/'synthetic.json';path.write_bytes(content)
    with pytest.raises(ValueError):bounded_resource(path,hashlib.sha256(content).hexdigest())

def test_hash_and_unknown_bundle_rejected(tmp_path):
    path=tmp_path/'synthetic.json';path.write_text('{}')
    with pytest.raises(ValueError):bounded_resource(path,'0'*64)
    with pytest.raises(ValueError):ContextBundle.load('foreign_bundle')

@pytest.mark.parametrize('sid',TEXTS)
def test_code_and_explicit_style_rules(sid):
    if sid not in ARCHIVES[ACTIVE_WAVE]['targets']:pytest.skip('Later wave')
    parser=GeneralContextInterpreter('context_18_v1');registry=ContextPolicyRegistry.load(bundle_id='context_18_v1');policy=ContextRelevancePolicy.load(bundle_id='context_18_v1')
    for code in ('casual','smart casual','formal','black tie'):
        result=parser.interpret(TEXTS[sid]+' The dress code is '+code+'.');assert result.status=='Supported',result
        request=result.structured_request;plan=compile_context(registry,request)
        assert plan.available==(code in ('casual','smart casual'))
        if plan.available:assert policy.resolve(request).state=='ObjectiveUnavailable'
    parsed=parser.interpret(TEXTS[sid]+' with casual style').structured_request
    assert policy.resolve(parsed).objective.target=='casual'
    assert policy.resolve(parsed).objective.authority=='explicit_user_style'

@pytest.mark.parametrize('text',["I have a dinner date.","I'm attending a birthday dinner."])
def test_compound_plan_and_both_deny_scopes(text):
    if ACTIVE_WAVE=='A':pytest.skip('Wave B')
    from tests.test_context_relevance_ranking import rows
    parser=GeneralContextInterpreter('context_18_v1');request=parser.interpret(text).structured_request
    plan=compile_context(ContextPolicyRegistry.load(bundle_id='context_18_v1'),request)
    assert plan.available and len(plan.secondary)==1
    scopes=('date','dinner') if request.context.situation.value=='social.date' else ('dinner','party')
    for scope in scopes:
        data=[replace(g,custom_tags=(f'rec:v1:occasion:{scope}:deny',)) for g in rows()]
        assert rank(text,data)[0].status=='NoMatchingCandidates'

def test_facets_cannot_be_forged_into_another_context():
    parser=GeneralContextInterpreter('context_18_v1');request=parser.interpret(TEXTS['academic.library_study']).structured_request
    frame=replace(request.context,facets=ContextSlot('Known',('meal:dinner',),(SourceSpan(0,3,request.context.original_text[:3]),)))
    assert not compile_context(ContextPolicyRegistry.load(bundle_id='context_18_v1'),replace(request,context=frame)).available

def test_expansion_requires_valid_server_selection(monkeypatch):
    from app.application.recommendation.contextual_selection import contextual_selection
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_BUNDLE','context_18_v1')
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE','disabled')
    with pytest.raises(ValueError):contextual_selection()

@pytest.mark.parametrize('text',["I'm attending a wedding as a guest.","I'm attending a university presentation as a presenter.","I'm going to a job interview as a candidate. The dress code is smart casual."])
def test_specialist_explanations_do_not_claim_unreviewed_admission(text):
    from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
    request=GeneralContextInterpreter('context_18_v1').interpret(text).structured_request
    summary=EvaluatorSpecification.current('context_18_v1').construct().summary(request)
    assert summary['version'] in ('general-context-explanation-1.0.0','general-context-explanation-1.2.0')
    assert summary.get('evidence_contract')!='saved_singleton_style_provisional_v1'
