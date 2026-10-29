"""Independent EC truth tables, exact scoring, semantic equivalence and work bounds."""
from dataclasses import asdict,replace
from fractions import Fraction
from itertools import product
import json
from pathlib import Path
import pytest
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.nlp.nlp_interpreter import NLPInterpreter
from app.application.nlp.contextual_nlp_interpreter import ContextualNLPInterpreter
from app.application.recommendation.general_context_evaluator import GeneralContextEvaluator,EvaluatorSpecification
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.contextual_suitability_evaluator import ContextualSuitabilityEvaluator
from app.application.recommendation.context_policy_registry import ContextPolicyRegistry,CONFIG
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate,InvalidScoringInput
from app.domain.value_objects.request_candidate_evaluation import EvaluatedCandidate
from app.domain.value_objects.contextual_garment_evidence import project_contextual_evidence
from tests.test_contextual_wedding import reviewed
from tests.test_rule_based_compatibility import Preferences
from tests.test_structural_candidates import Query

CONTEXTS=[('campus',"I'm going to class",'Suggest an outfit for campus'),
          ('shopping',"I'm going shopping",'Suggest an outfit for shopping'),
          ('casual_outing',"I'm going out with friends",'Suggest an outfit for a casual outing')]


@pytest.mark.parametrize('target,natural,command',CONTEXTS)
@pytest.mark.parametrize('code,style,review,decisions',list(product(
    [None,'casual','smart_casual'],['casual','smart casual','classic'],[True,False],[(),('allow',),('deny',),('allow','deny')])) )
def test_independent_member_oracle(target,natural,command,code,style,review,decisions):
    text=natural+('' if code is None else '; the dress code is '+code.replace('_',' '))
    request=GeneralContextInterpreter().interpret(text).structured_request
    garment=replace(reviewed(styles=(style,),review=review),custom_tags=tuple('rec:v1:occasion:'+target+':'+d for d in decisions))
    allowed=('casual','smart casual') if code is None else ('casual',) if code=='casual' else ('smart casual',)
    expected='Fail' if 'deny' in decisions else 'Pass' if decisions==('allow',) or style in allowed else 'Unknown'
    actual=GeneralContextEvaluator().member_condition(garment,request,'occasion')
    assert actual[0]==expected
    if actual[0]=='Pass': assert actual[1]==('explicit_declaration' if decisions==('allow',) else 'attribute_inference' if review else 'saved_attribute_provisional')


@pytest.mark.parametrize('target,natural,command',CONTEXTS)
@pytest.mark.parametrize('code',[None,'casual','smart_casual'])
def test_four_structures_exact_reference_public_and_wording(target,natural,command,code):
    style='casual' if code=='casual' else 'smart casual'
    rows=[reviewed('top-A','long_sleeve_top',(style,)),reviewed('bottom-A','trousers',(style,)),reviewed('dress-A',styles=(style,)),reviewed('outer-A','long_sleeve_outwear',(style,))]
    outcomes=[]
    for text in (natural,command):
        request=GeneralContextInterpreter().interpret(text+('' if code is None else '; the dress code is '+code.replace('_',' '))).structured_request
        audit=[];result=CompactExhaustiveScorer(Query(rows),Preferences(),evaluator_type=EvaluatorSpecification.current(),audit=audit.append).rank('owner',request)
        assert result.status=='Selected' and len(audit)==result.scored_count==4
        assert result.winner.verified.candidate.key==(('one_piece','dress-A'),('outerwear','outer-A'))
        for item in audit:
            assert item['verified'] and all(c['state']=='Pass' for c in item['evaluation']['conditions'])
            assert item['score']['weights']==(Fraction(3,5),Fraction(1,5),Fraction(1,5))
            assert item['score']['total']==(Fraction(7,10) if len(item['key'])==1 else Fraction(4,5))
        reference=AggregatedDecisionRecommendationScorer(RequestCandidateEngine(Query(rows),evaluator_specification=EvaluatorSpecification.current()),Preferences()).rank('owner',request)
        assert asdict(reference.winner.score)==asdict(result.winner.score)
        session=RequestCandidateEngine(Query(rows),evaluator_specification=EvaluatorSpecification.current()).generate_candidates('owner',request)
        with pytest.raises(InvalidScoringInput):
            item=result.winner.verified.evaluated
            ScoringEligibilityGate(session,'owner',request).verify(EvaluatedCandidate(item.candidate,replace(item.evaluation,conditions=())))
        session.close();outcomes.append((result.winner.verified.candidate.key,asdict(result.winner.score)))
    assert outcomes[0]==outcomes[1]


@pytest.mark.parametrize('target,natural,command',CONTEXTS)
def test_frozen_profiles_keep_declaration_only_path(target,natural,command):
    garment=reviewed(styles=('casual',))
    for interpreter,evaluator in ((NLPInterpreter(),SuitabilityRequestEvaluator),(ContextualNLPInterpreter(),ContextualSuitabilityEvaluator)):
        request=interpreter.interpret(command).structured_request
        old=CompactExhaustiveScorer(Query([garment]),Preferences(),evaluator_type=evaluator).rank('owner',request)
        assert old.status=='InsufficientEvidence'
        positive=replace(garment,custom_tags=('rec:v1:occasion:'+target+':allow',))
        assert CompactExhaustiveScorer(Query([positive]),Preferences(),evaluator_type=evaluator).rank('owner',request).status=='Selected'
    request=GeneralContextInterpreter().interpret(command).structured_request
    assert CompactExhaustiveScorer(Query([garment]),Preferences(),evaluator_type=EvaluatorSpecification.current()).rank('owner',request).status=='Selected'


@pytest.mark.parametrize('target,natural,command',CONTEXTS)
@pytest.mark.parametrize('deny',[False,True])
def test_malformed_barrier_and_deny_precedence(target,natural,command,deny):
    request=GeneralContextInterpreter().interpret(natural).structured_request
    g=replace(reviewed(styles=('casual',)),custom_tags=('rec:v2:occasion:'+target+':allow',)+(('rec:v1:occasion:'+target+':deny',) if deny else ()))
    assert GeneralContextEvaluator().member_condition(g,request,'occasion')[0]==('Fail' if deny else 'Unknown')
    bad=replace(g,contextual_suitability=project_contextual_evidence({'schema_version':'invalid'},True))
    assert GeneralContextEvaluator().member_condition(bad,request,'occasion')[0]==('Fail' if deny else 'Unknown')


@pytest.mark.parametrize('target,natural,command',CONTEXTS)
def test_preparation_at_100_and_no_metadata_bonus(target,natural,command,monkeypatch):
    from app.application.recommendation.context_evidence_resolver import ContextEvidenceResolver
    from app.application.recommendation import general_context_evaluator as module
    old_resolve,old_compile=ContextEvidenceResolver.resolve,module.compile_context
    calls={'resolve':0,'compile':0,'candidates':0}
    def resolve(*args):
        calls['resolve']+=1;assert calls['candidates'] in (0,100);return old_resolve(*args)
    def compile(*args):
        calls['compile']+=1;assert calls['candidates'] in (0,100);return old_compile(*args)
    def checkpoint(stage,*args):
        if stage=='candidate':calls['candidates']+=1
    monkeypatch.setattr(ContextEvidenceResolver,'resolve',resolve);monkeypatch.setattr(module,'compile_context',compile)
    request=GeneralContextInterpreter().interpret(natural+' tomorrow; the dress code is casual').structured_request
    rows=[reviewed(str(i),styles=('casual',)) for i in range(100)]
    result=CompactExhaustiveScorer(Query(rows),Preferences(),evaluator_type=EvaluatorSpecification.current(),checkpoint=checkpoint).rank('owner',request)
    assert result.status=='Selected' and calls=={'resolve':404,'compile':5,'candidates':100}
    plain=GeneralContextInterpreter().interpret(command+'; the dress code is casual').structured_request
    assert asdict(CompactExhaustiveScorer(Query(rows),Preferences(),evaluator_type=EvaluatorSpecification.current()).rank('owner',plain).winner.score)==asdict(result.winner.score)


@pytest.mark.parametrize('text,target',[
 ('Suggest an outfit for a shopping trip','shopping'),('Suggest an outfit for classes','campus'),
 ("I'm meeting friends",'casual_outing'),("I'm going out casually",'casual_outing'),
 ('I have university tomorrow','campus'),('Suggest an outfit for lecture','campus')])
def test_bounded_aliases_spans_and_declaration_projection(text,target):
    result=GeneralContextInterpreter().interpret(text);assert result.status=='Supported',result
    request=result.structured_request;assert request.occasion==target and request.formality is None
    assert GeneralContextEvaluator().supports(request)
    for value in vars(request.context).values():
        if hasattr(value,'spans'):
            assert all(text[s.start:s.end]==s.text for s in value.spans)


@pytest.mark.parametrize('mutation',['target','assumption','style','venue','companion','source','operator','extra_binding'])
def test_registry_activation_envelope_is_closed(tmp_path,mutation):
    data=json.loads((CONFIG/'context_policy_registry.v1.json').read_text(encoding='utf-8'));b=data['bindings'][5]
    if mutation=='target': b['declaration_target']='shopping'
    if mutation=='assumption': b['assumed_role']='student'
    if mutation=='style': b['predicates'][0]['values'].append('classic')
    if mutation=='venue': b['allowed_venues'].append('laboratory')
    if mutation=='companion': b['allowed_companions'].append('family')
    if mutation=='source': b['evidence_contract']='owner_appearance_observations_v1'
    if mutation=='operator': b['predicates'][0]['operator']='eval'
    if mutation=='extra_binding':data['bindings'].append(b)
    path=tmp_path/'registry.json';path.write_text(json.dumps(data))
    with pytest.raises((ValueError,TypeError)):ContextPolicyRegistry.load(path)


@pytest.mark.parametrize('text',["I'm presenting at class","I'm conducting class","I'm conducting shopping","I'm in the audience shopping"])
def test_nonordinary_actions_are_never_discarded(text):
    result=GeneralContextInterpreter().interpret(text)
    assert result.status=='UnsupportedRequest' and result.structured_request is None


def test_friends_metadata_does_not_change_numeric_score():
    rows=[reviewed(styles=('casual',))];outcomes=[]
    for text in ('Suggest an outfit for a casual outing',"I'm going out with friends tonight"):
        request=GeneralContextInterpreter().interpret(text).structured_request
        result=CompactExhaustiveScorer(Query(rows),Preferences(),evaluator_type=EvaluatorSpecification.current()).rank('owner',request)
        assert result.status=='Selected';outcomes.append(asdict(result.winner.score))
    assert outcomes[0]==outcomes[1]
