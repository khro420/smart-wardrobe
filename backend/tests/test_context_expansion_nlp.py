"""Approved author-labelled NLP mechanics; no independently validated NLP claim."""
from pathlib import Path
import json
import pytest
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.recommendation.context_policy_registry import ContextPolicyRegistry
from app.application.recommendation.context_constraint_compiler import compile_context
from app.application.recommendation.context_bundle import ACTIVE_WAVE,ARCHIVES

LABELS=json.loads((Path(__file__).with_name('fixtures')/'context_expansion_nlp_labels.v1.json').read_text(encoding='utf-8'))['cases']


@pytest.fixture(scope='module')
def parser():return GeneralContextInterpreter('context_18_v1')


@pytest.mark.parametrize('case',LABELS,ids=lambda c:c['id'])
def test_approved_language_case(case,parser):
    if ACTIVE_WAVE=='A' and not case['id'].startswith(('LS-','GS-','OW-','WM-')):pytest.skip('Later approved wave')
    if ACTIVE_WAVE=='B' and case['id'].startswith(('SS-','TD-')):pytest.skip('Wave C')
    result=parser.interpret(case['text'])
    if case.get('classification') in ('C','D'):
        if case['classification']=='C':assert result.reason=='context_clarification_required',result
        elif result.status=='Supported':
            assert not compile_context(ContextPolicyRegistry.load(bundle_id='context_18_v1'),result.structured_request).available,result
        else:assert result.status=='UnsupportedRequest',result
        return
    assert result.status=='Supported',result
    request=result.structured_request
    sid=case.get('expected_situation',case.get('expected_slots',{}).get('situation'))
    if sid is None:
        assert getattr(request,'context',None) is None
        return
    frame=request.context
    assert frame.situation.value==sid
    plan=compile_context(ContextPolicyRegistry.load(bundle_id='context_18_v1'),request)
    assert plan.available,(case,plan)
    if 'binding' in case:assert plan.binding.identifier==case['binding']
    for name,value in case.get('expected_slots',{}).items():
        slot=getattr(frame,name)
        if value=='Unspecified':assert slot.state=='Unspecified',(name,slot)
        elif isinstance(value,list):assert list(slot.values)==value,(name,slot)
        else:assert slot.value==value,(name,slot)
    for name in frame.__dataclass_fields__:
        slot=getattr(frame,name)
        if hasattr(slot,'spans'):
            assert all(case['text'][span.start:span.end]==span.text for span in slot.spans)


def test_legacy_default_remains_eight_contexts():
    parser=GeneralContextInterpreter()
    assert parser.bundle_id=='legacy_8_v1'
    assert len(ContextPolicyRegistry.load().bindings)==8
    assert parser.interpret("I'm going to study at the library.").status=='UnsupportedRequest'


@pytest.mark.parametrize('text',["I'm meeting someone at a café.","I'm visiting my friend’s house."])
def test_unicode_spans_are_original(text,parser):
    if ACTIVE_WAVE=='A':pytest.skip('Wave B')
    result=parser.interpret(text);assert result.status=='Supported'
    for name in ('situation','venue','companions'):
        slot=getattr(result.structured_request.context,name)
        assert all(text[s.start:s.end]==s.text for s in slot.spans)


@pytest.mark.parametrize('text,sid,target',[
    ("I'm going shopping.",'everyday.shopping','casual'),
    ("I'm going to class.",'everyday.academic_attendance','casual'),
    ("I'm going out with friends.",'everyday.casual_outing','casual'),
    ("I'm going on a date tonight.",'social.date','smart casual'),
    ("I'm meeting friends for dinner.",'social.meal','smart casual'),
    ("I'm meeting friends.",'everyday.casual_outing','casual'),
    ("I'm meeting friends for a dinner.",'social.meal','smart casual'),
])
def test_activation_correction_preserves_original_requests(text,sid,target,parser):
    from app.application.recommendation.context_relevance_policy import ContextRelevancePolicy
    result=parser.interpret(text)
    assert result.status=='Supported',result
    request=result.structured_request
    assert request.context.situation.value==sid
    assert request.context.companions.values==(('friends',) if 'friends' in text else ())
    assert compile_context(ContextPolicyRegistry.load(bundle_id='context_18_v1'),request).available
    assert ContextRelevancePolicy.load(bundle_id='context_18_v1').resolve(request).objective.target==target


@pytest.mark.parametrize('text',[
    "I'm meeting friends for dinner and hiking.",
    "I'm not meeting friends for dinner.",
    "I have a meeting.",
    "I'm meeting friends for dinner at the office.",
    "I'm meeting colleagues for dinner.",
    "I'm meeting friends for dinner. The dress code is formal.",
])
def test_activation_correction_does_not_erase_other_conditions(text,parser):
    result=parser.interpret(text)
    if result.status=='Supported':
        assert not compile_context(ContextPolicyRegistry.load(bundle_id='context_18_v1'),result.structured_request).available
    else:assert result.status=='UnsupportedRequest'


def test_activation_correction_keeps_workplace_meeting(parser):
    result=parser.interpret('I have a meeting with my colleagues.')
    assert result.status=='Supported'
    assert result.structured_request.context.situation.value=='professional.workplace_meeting'


def test_activation_correction_source_transition():
    from tests import integration_source_guard as guard
    data=guard.context_18_activation_correction_manifest(verify=True)
    assert data['replacements']['backend/app/application/nlp/context_expression_matcher.py']['before']==guard.context_expansion_manifest()['additions']['backend/app/application/nlp/context_expression_matcher.py']
