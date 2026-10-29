"""Independent approved predicate reductions, exact arithmetic and bounded preparation."""
from dataclasses import asdict, replace
from fractions import Fraction
from itertools import product
import json
from pathlib import Path
import pytest
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.recommendation.general_context_evaluator import GeneralContextEvaluator, EvaluatorSpecification
from app.application.recommendation.context_policy_registry import ContextPolicyRegistry, CONFIG, freeze_expression
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.domain.value_objects.general_context_evidence import project_appearance_evidence
from tests.test_contextual_wedding import reviewed
from tests.test_rule_based_compatibility import Preferences
from tests.test_structural_candidates import Query


def observed(g,feature=True,condition='clean_intact'):
    raw={'schema_version':'1.0.0','source':'owner_review','category':g.category,'media_id':g.preferred_media_id,
         'construction_features':{'collared_neckline':feature,'tailored_cut':feature,'structured_shape':feature},
         'condition_observation':condition,'reviewed_at':'2026-10-25T00:00:00+08:00'}
    return replace(g,appearance_evidence=project_appearance_evidence(raw,True))


@pytest.mark.parametrize('style,style_review,feature,condition,parent',list(product(
    ['smart casual','casual','classic'],[True,False],[True,False,None],['clean_intact','needs_attention','unknown'],[(),('allow',),('deny',),('allow','deny')])) )
def test_independent_interview_truth_table(style,style_review,feature,condition,parent):
    request=GeneralContextInterpreter().interpret('Suggest an outfit for a job interview as a candidate; the dress code is smart casual').structured_request
    g=observed(reviewed(styles=(style,),review=style_review),feature,condition)
    g=replace(g,custom_tags=tuple('rec:v1:occasion:work:'+v for v in parent))
    expected='Fail' if 'deny' in parent or condition=='needs_attention' else 'Pass' if style_review and style=='smart casual' and feature is True and condition=='clean_intact' else 'Unknown'
    assert GeneralContextEvaluator().member_condition(g,request,'occasion')[0]==expected


@pytest.mark.parametrize('role,code,style,style_review,parent',list(product(
    ['presenter','attendee'],[None,'casual','smart_casual'],['smart casual','casual','classic'],[True,False],[(),('allow',),('deny',),('allow','deny')])) )
def test_independent_academic_truth_table(role,code,style,style_review,parent):
    text='Suggest an outfit for a university presentation as a '+role+('' if code is None else '; the dress code is '+code.replace('_',' '))
    request=GeneralContextInterpreter().interpret(text).structured_request
    g=replace(reviewed(styles=(style,),review=style_review),custom_tags=tuple('rec:v1:occasion:campus:'+v for v in parent))
    allowed=['smart casual'] if code=='smart_casual' or code is None and role=='presenter' else ['casual'] if code=='casual' else ['casual','smart casual']
    expected='Fail' if 'deny' in parent else 'Pass' if style_review and style in allowed else 'Unknown'
    assert GeneralContextEvaluator().member_condition(g,request,'occasion')[0]==expected


@pytest.mark.parametrize('text',[
    'Suggest an outfit for a job interview as a candidate; the dress code is smart casual',
    'Suggest an outfit for a job interview as an interviewer; the dress code is smart casual',
    'Suggest an outfit for a university presentation as a presenter',
    'Suggest an outfit for a university presentation as an attendee'])
def test_every_structure_exact_score_reference_and_public_agree(text):
    rows=[observed(reviewed('top-A','long_sleeve_top')),observed(reviewed('bottom-A','trousers')),
          observed(reviewed('dress-A')),observed(reviewed('outer-A','long_sleeve_outwear'))]
    request=GeneralContextInterpreter().interpret(text).structured_request
    audit=[]
    result=CompactExhaustiveScorer(Query(rows),Preferences(),evaluator_type=EvaluatorSpecification.current(),audit=audit.append).rank('owner',request)
    assert result.status=='Selected' and len(audit)==result.scored_count==4
    assert result.winner.verified.candidate.key==(('one_piece','dress-A'),('outerwear','outer-A'))
    for c in audit:
        assert c['verified'] and all(v['state']=='Pass' for v in c['evaluation']['conditions'])
        assert c['score']['total']==(Fraction(7,10) if len(c['key'])==1 else Fraction(4,5))
        assert c['score']['weights']==(Fraction(3,5),Fraction(1,5),Fraction(1,5))
    reference=AggregatedDecisionRecommendationScorer(RequestCandidateEngine(Query(rows),evaluator_specification=EvaluatorSpecification.current()),Preferences()).rank('owner',request)
    assert asdict(reference.winner.score)==asdict(result.winner.score)
    assert reference.winner.verified.candidate.key==result.winner.verified.candidate.key


def preparation_observation(kind,monkeypatch):
    from app.application.recommendation.context_evidence_resolver import ContextEvidenceResolver
    from app.application.recommendation import general_context_evaluator as module
    text='Suggest an outfit for a '+('job interview as a candidate; the dress code is smart casual' if kind=='interview' else 'university presentation as a presenter; the dress code is smart casual')
    request=GeneralContextInterpreter().interpret(text).structured_request
    rows=[observed(reviewed(str(i))) for i in range(100)]
    calls={'resolve':0,'compile':0,'candidates':0}
    old_resolve,old_compile=ContextEvidenceResolver.resolve,module.compile_context
    def resolve(*args):
        calls['resolve']+=1;assert calls['candidates'] in (0,100);return old_resolve(*args)
    def compile(*args):
        calls['compile']+=1;assert calls['candidates'] in (0,100);return old_compile(*args)
    def checkpoint(stage,*args):
        if stage=='candidate': calls['candidates']+=1
    monkeypatch.setattr(ContextEvidenceResolver,'resolve',resolve);monkeypatch.setattr(module,'compile_context',compile)
    result=CompactExhaustiveScorer(Query(rows),Preferences(),evaluator_type=EvaluatorSpecification.current(),checkpoint=checkpoint).rank('owner',request)
    assert result.status=='Selected' and calls=={'resolve':404,'compile':5,'candidates':100}
    return calls


@pytest.mark.parametrize('kind',['interview','academic'])
def test_preparation_at_100_avoids_candidate_loop_work(kind,monkeypatch):
    assert preparation_observation(kind,monkeypatch)=={'resolve':404,'compile':5,'candidates':100}


@pytest.mark.parametrize('mutation',['scope','role','style','feature','condition','operator','arity','depth','positive_parent','missing_role_case'])
def test_unapproved_registry_mutations_fail_closed(tmp_path,mutation):
    data=json.loads((CONFIG/'context_policy_registry.v1.json').read_text());b=data['bindings'][3];rule=b['predicates'][0]
    if mutation=='scope': b['parent_negative']='campus'
    if mutation=='role': b['roles'].append('guest')
    if mutation=='style': rule['expressions_by_member_role']['one_piece']['children'][0]['values']=['casual']
    if mutation=='feature': rule['expressions_by_member_role']['one_piece']['children'][1]['field']='material'
    if mutation=='condition': rule['expressions_by_member_role']['one_piece']['children'][2]['value']='unknown'
    if mutation=='operator': rule['expressions_by_member_role']['one_piece']['operator']='eval'
    if mutation=='arity': rule['expressions_by_member_role']['one_piece']['children']*=5
    if mutation=='depth': rule['expressions_by_member_role']['one_piece']={'operator':'all','children':[{'operator':'all','children':[{'operator':'all','children':[{'operator':'reviewed_style_in','values':['smart casual']}]}]}]}
    if mutation=='positive_parent': b['parent_allow_is_child_permission']=True
    if mutation=='missing_role_case': rule['expressions_by_member_role'].pop('outerwear')
    target=tmp_path/'registry.json';target.write_text(json.dumps(data))
    with pytest.raises((ValueError,TypeError)): ContextPolicyRegistry.load(target)


def test_unknown_model_source_and_stale_observations_cannot_supply_inference():
    request=GeneralContextInterpreter().interpret('Suggest an outfit for a job interview as a candidate; the dress code is smart casual').structured_request
    good=observed(reviewed())
    stale=replace(good,preferred_media_id='changed-source')
    assert GeneralContextEvaluator().member_condition(stale,request,'occasion')[0]=='Unknown'
    missing=reviewed()
    assert GeneralContextEvaluator().member_condition(missing,request,'occasion')[0]=='Unknown'
    with pytest.raises(ValueError): freeze_expression({'operator':'reviewed_observation_equals','field':'structured_shape','value':1})
