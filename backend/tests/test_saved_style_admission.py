"""Independent approved saved-style condition oracle and provenance boundaries."""
from dataclasses import asdict, replace
from fractions import Fraction
from itertools import product
import json
from pathlib import Path
import pytest
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.recommendation.general_context_evaluator import GeneralContextEvaluator, EvaluatorSpecification
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.domain.value_objects.saved_attribute_evidence import source_record, project_saved_attribute_evidence, SavedAttributeEvidence
from tests.test_contextual_wedding import reviewed
from tests.test_rule_based_compatibility import Preferences
from tests.test_structural_candidates import Query

CONTEXTS=[('campus',"I'm going to class"),('shopping',"I'm going shopping"),('casual_outing',"I'm going out with friends"),('date',"I'm going on a date"),('dinner',"I'm meeting friends for dinner")]


@pytest.mark.parametrize('target,text',CONTEXTS)
def test_saved_unreviewed_preparation_is_outside_candidate_loop(target,text,monkeypatch):
    from app.application.recommendation.context_evidence_resolver import ContextEvidenceResolver
    from app.application.recommendation import general_context_evaluator as module
    old_resolve,old_compile=ContextEvidenceResolver.resolve,module.compile_context
    calls={'resolve':0,'compile':0,'candidates':0}
    def resolve(*args):
        calls['resolve']+=1
        assert calls['candidates'] in (0,100)
        return old_resolve(*args)
    def compile_context(*args):
        calls['compile']+=1
        assert calls['candidates'] in (0,100)
        return old_compile(*args)
    def checkpoint(stage,*args):
        if stage=='candidate':calls['candidates']+=1
    monkeypatch.setattr(ContextEvidenceResolver,'resolve',resolve)
    monkeypatch.setattr(module,'compile_context',compile_context)
    rows=[reviewed(str(i),styles=('casual',),review=False) for i in range(100)]
    request=GeneralContextInterpreter().interpret(text+'; the dress code is casual').structured_request
    result=CompactExhaustiveScorer(Query(rows),Preferences(),evaluator_type=EvaluatorSpecification.current(),checkpoint=checkpoint).rank('owner',request)
    assert result.status=='Selected'
    assert calls=={'resolve':404,'compile':5,'candidates':100}


@pytest.mark.parametrize('target,text',CONTEXTS)
@pytest.mark.parametrize('code,style,has_review,decisions',list(product([None,'casual','smart_casual'],['casual','smart casual','classic',None],[False,True],[(),('allow',),('deny',),('allow','deny')])))
def test_independent_saved_style_oracle(target,text,code,style,has_review,decisions):
    request=GeneralContextInterpreter().interpret(text+('' if code is None else '; the dress code is '+code.replace('_',' '))).structured_request
    g=replace(reviewed(styles=() if style is None else (style,),review=has_review),custom_tags=tuple('rec:v1:occasion:'+target+':'+d for d in decisions))
    allowed=('casual','smart casual') if code is None else ('casual',) if code=='casual' else ('smart casual',)
    expected='Fail' if 'deny' in decisions else 'Pass' if decisions==('allow',) or style in allowed else 'Unknown'
    result=GeneralContextEvaluator().member_condition(g,request,'occasion')
    assert result[0]==expected
    if expected=='Pass':assert result[1]==('explicit_declaration' if decisions else 'attribute_inference' if has_review else 'saved_attribute_provisional')


@pytest.mark.parametrize('origin',['unknown','owner_supplied','adapter_output','model_reported','synthetic'])
@pytest.mark.parametrize('fault',[None,'style','category','media','owner','timestamp','extra'])
def test_bound_immutable_origin_never_becomes_review(origin,fault):
    g=reviewed(styles=('casual',),review=False)
    raw=source_record({'style':['casual']},g.user_id,g.category,g.preferred_media_id,'2026-10-27T00:00:00+00:00',origin,'synthetic_contract_probe')
    entry=raw['style']
    if fault=='style':entry['value_sha256']='0'*64
    if fault=='category':entry['category']='trousers'
    if fault=='media':entry['media_id']='other'
    if fault=='owner':entry['owner_id']='other'
    if fault=='timestamp':entry['recorded_at']='not-a-date'
    if fault=='extra':entry['reviewed_at']='fabricated'
    source=project_saved_attribute_evidence(raw,True,g.style_tags,g.category,g.preferred_media_id,g.user_id)
    g=replace(g,saved_attribute_evidence=source)
    request=GeneralContextInterpreter().interpret("I'm going shopping").structured_request
    result=GeneralContextEvaluator().member_condition(g,request,'occasion')
    assert result[0]==('Pass' if fault is None else 'Unknown')
    if fault is None:
        proof=GeneralContextEvaluator().explain(type('Candidate',(),{'members':(type('Member',(),{'garment':g})(),)})(),request)
        assert proof['version']=='general-context-explanation-1.4.0'
        assert proof['members'][0]['style_verification']=='saved_unreviewed'
        assert proof['members'][0]['saved_attribute_evidence']['origin']==origin
        assert proof['members'][0]['review']['reviewed_at'] is None
    with pytest.raises((AttributeError,TypeError)):source.origin='owner_supplied'


@pytest.mark.parametrize('text',["I'm going to a wedding","I'm presenting my project at university","I'm being interviewed for a job; the dress code is smart casual"])
def test_strict_specialist_inference_does_not_use_unreviewed_style(text):
    request=GeneralContextInterpreter().interpret(text).structured_request
    g=reviewed(styles=('smart casual',),review=False)
    assert GeneralContextEvaluator().member_condition(g,request,'occasion')[0]=='Unknown'


@pytest.mark.parametrize('target,text',CONTEXTS)
def test_four_structures_and_exact_reference_unchanged(target,text):
    rows=[reviewed('top-A','long_sleeve_top',('casual',),review=False),reviewed('bottom-A','trousers',('casual',),review=False),reviewed('dress-A',styles=('casual',),review=False),reviewed('outer-A','long_sleeve_outwear',('casual',),review=False)]
    request=GeneralContextInterpreter().interpret(text).structured_request;audit=[]
    result=CompactExhaustiveScorer(Query(rows),Preferences(),evaluator_type=EvaluatorSpecification.current(),audit=audit.append).rank('owner',request)
    assert result.status=='Selected' and len(audit)==result.scored_count==4
    for item in audit:
        assert item['verified']
        assert item['score']['weights']==(Fraction(3,5),Fraction(1,5),Fraction(1,5))
        assert item['score']['total']==(Fraction(7,10) if len(item['key'])==1 else Fraction(4,5))
    assert result.winner.verified.candidate.key==(('one_piece','dress-A'),('outerwear','outer-A'))
    reference=AggregatedDecisionRecommendationScorer(RequestCandidateEngine(Query(rows),evaluator_specification=EvaluatorSpecification.current()),Preferences()).rank('owner',request)
    assert asdict(reference.winner.score)==asdict(result.winner.score)


def test_stale_or_withdrawn_review_is_not_rehabilitated():
    request=GeneralContextInterpreter().interpret("I'm going shopping").structured_request
    stale=replace(reviewed(styles=('casual',)),category='sling_dress')
    assert GeneralContextEvaluator().member_condition(stale,request,'occasion')[1]=='saved_attribute_provisional'
    bad=replace(stale,contextual_suitability=replace(stale.contextual_suitability,review_state='Malformed'))
    assert GeneralContextEvaluator().member_condition(bad,request,'occasion')[0]=='Unknown'
