"""Owner-approved correction expectations, frozen before implementation."""
from tests.retained_evidence import review_path, review_reference
from pathlib import Path
import dataclasses,hashlib,json,re
import pytest
from app.application.nlp.conversational_context_interpreter import ConversationalContextInterpreter
from app.application.recommendation.conversational_request_pipeline import ConversationalRequestPipeline
from app.application.wardrobe.description_policy import DescriptionPolicy
from app.domain.value_objects.attribute_conditions import AttributeRequestError
ROOT=Path(__file__).parents[2]
SPEC=json.loads((Path(__file__).parent/'fixtures/regression_corrections_acceptance.v1.json').read_text(encoding='utf-8'))
@pytest.fixture
def pipeline(monkeypatch):
    monkeypatch.setenv('SMART_WARDROBE_VERIFIED_SUBTYPE_PROFILE','verified_subtype_v1')
    return ConversationalRequestPipeline(ConversationalContextInterpreter(),DescriptionPolicy.load())
def semantic(groups):
    return sorted((g['role'],g['quantifier'],sorted((c['attribute'],c['operator'],json.dumps(c['values'],sort_keys=True)) for c in g['conditions'])) for g in groups)
def expected(groups):return sorted((role,q,sorted((a,op,json.dumps(v,sort_keys=True)) for a,op,v in fields)) for role,q,fields in groups)
def spans(text,request,intent):
    if intent:
        assert intent.to_dict()['original_text']==text
        for s in intent.to_dict()['spans']:
            if s['source']=='nlp':assert text[s['start']:s['end']]==s['text']
    context=getattr(request,'context',None)
    if context:
        assert context.original_text==text
        for f in dataclasses.fields(context):
            for s in getattr(getattr(context,f.name),'spans',()):assert text[s.start:s.end]==s.text
@pytest.mark.parametrize('case',SPEC['binding'],ids=lambda c:c['id'])
def test_frozen_same_member_and_conjunction_bindings(pipeline,case):
    request,intent=pipeline.interpret(case['text'])
    assert semantic(intent.conditions.to_dict()['groups'])==expected(case['expected_groups'])
    spans(case['text'],request,intent)
@pytest.mark.parametrize('text',SPEC['ambiguous'])
def test_ambiguous_binding_never_guessed(pipeline,text):
    with pytest.raises(AttributeRequestError):pipeline.interpret(text)
@pytest.mark.parametrize('case',SPEC['language'],ids=lambda c:c['id'])
def test_all18_original_and_equivalent_frames(pipeline,case):
    if case['expected']=='refused':
        with pytest.raises(AttributeRequestError):pipeline.interpret(case['text'])
        return
    request,intent=pipeline.interpret(case['text'])
    assert request.context.situation.value==case['situation']
    if 'groups' in case:assert semantic(intent.conditions.to_dict()['groups'] if intent else [])==semantic(case['groups'])
    spans(case['text'],request,intent)
def test_N38_keeps_frozen_unsupported_requirement(pipeline):
    case=SPEC['literal_refusal']
    with pytest.raises(AttributeRequestError) as caught:pipeline.interpret(case['text'])
    assert (caught.value.status,caught.value.reason)==(case['expected_status'],case['expected_reason'])
@pytest.mark.parametrize('text',SPEC['literal_controls'])
def test_supported_literals_keep_original_words(pipeline,text):
    request,intent=pipeline.interpret(text)
    values=[c['values'] for g in intent.conditions.to_dict()['groups'] for c in g['conditions'] if c['attribute'] in ('garment_name','descriptive_tag')]
    assert values==[[json.loads(re.search(r'"(?:[^"\\]|\\.)*"',text).group())]]
    spans(text,request,intent)
def test_typed_and_natural_equivalence(pipeline):
    case=SPEC['binding'][0];groups=[];index=0
    for n,(role,q,fields) in enumerate(case['expected_groups'],1):
        conditions=[]
        for a,op,values in fields:
            index+=1;conditions.append({'id':f'c{index:02}','attribute':a,'operator':op,'values':values})
        groups.append({'id':f'g{n:02}','role':role,'quantifier':q,'conditions':conditions})
    _,natural=pipeline.interpret(case['text'])
    _,typed=pipeline.interpret('I want an outfit.',{'version':'attribute-conditions-1.0.0','groups':groups})
    assert semantic(natural.conditions.to_dict()['groups'])==semantic(typed.conditions.to_dict()['groups'])
def test_exact_correction_authority_and_protected_source():
    authority=json.loads((Path(__file__).parent/'fixtures/regression_corrections_sources.v1.json').read_text(encoding='utf-8'))
    assert set(authority['production_changes'])==set(authority['approved_production_before'])
    for p,h in authority['baseline'].items():
        target=authority['production_changes'].get(p,{}).get('after',h)
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==target,p
    for p,t in authority['production_changes'].items():assert t['before']==authority['approved_production_before'][p]==authority['baseline'][p]
    before=json.loads((review_reference(authority['before_directory'])/'backend/app/application/nlp/config/conversational_language.v1.json').read_text(encoding='utf-8'))
    after=json.loads((ROOT/'backend/app/application/nlp/config/conversational_language.v1.json').read_text(encoding='utf-8'))
    assert before['contexts']==after['contexts']
    assert before['attribute_aliases']==after['attribute_aliases'] and before['noun_descriptors']==after['noun_descriptors']
    a=(review_reference(authority['before_directory'])/'backend/app/application/recommendation/attribute_selection_verifier.py').read_text(encoding='utf-8')
    b=(ROOT/'backend/app/application/recommendation/attribute_selection_verifier.py').read_text(encoding='utf-8')
    old=a.split('registered_grammars=(',1)[1].split(')\n',1)[0];new=b.split('registered_grammars=(',1)[1].split(')\n',1)[0]
    assert set(re.findall(r"'([0-9a-f]{64})'",old))<set(re.findall(r"'([0-9a-f]{64})'",new))
