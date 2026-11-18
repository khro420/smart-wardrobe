"""Reference replay must retain real B1 admission, not manufacture a ledger."""
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.application.recommendation.context_relevance_scorer import reference_rank
from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
from app.application.recommendation.outfit_assistant_service import CapturedCandidateEngine
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.domain.value_objects.attribute_conditions import AttributeConditions
from tests.test_conversational_phase1_semantics import make_member


@pytest.mark.parametrize('categories',[
    ('vest','trousers'),('vest','trousers','long_sleeve_outwear'),
    ('vest_dress',),('vest_dress','long_sleeve_outwear'),
])
@pytest.mark.parametrize('states',['mixed','fail_only','unknown_only'])
def test_reference_compact_b1_admission_and_scores(categories,states):
    target_role='one_piece' if categories[0]=='vest_dress' else 'upper'
    variants={'mixed':(('match','cotton','owner'),('fail','linen','owner'),('unknown','cotton','missing')),
              'fail_only':(('fail','linen','owner'),),
              'unknown_only':(('unknown','cotton','missing'),)}[states]
    pool=[make_member(name,'material' if state!='missing' else None,value,state,category=categories[0])
          for name,value,state in variants]
    pool.extend(make_member('companion-'+str(i),category=category) for i,category in enumerate(categories[1:]))
    conditions=AttributeConditions.from_dict({'version':'attribute-conditions-1.0.0','groups':[
        {'id':'g01','role':target_role,'quantifier':'exists','conditions':[
            {'id':'c01','attribute':'material','operator':'contains_any','values':['cotton']}]}]})
    policy=AttributeEvidencePolicy.load()
    prepared=PreparedAttributeConditions.prepare(conditions,pool,policy)
    verifier=IndependentAttributeVerifier.prepare(conditions,pool,policy)
    for name,_,state in variants:
        expected_state='Unknown' if state=='missing' else 'Fail' if name=='fail' else 'Pass'
        assert prepared.evaluate_members(((target_role,name),))==expected_state
    class Query:
        def get_confirmed_available_garments(self,owner):
            assert owner=='owner-A'
            return tuple(item.snapshot for item in pool)
    class Preferences:
        def get_active_preferences(self,owner):
            assert owner=='owner-A'
            return ()
    specification=EvaluatorSpecification.current('context_18_v1')
    engine=RequestCandidateEngine(Query(),evaluator_factory=specification.construct,
        attribute_context=prepared,attribute_verifier=verifier)
    captured=CapturedCandidateEngine(engine)
    request=GeneralContextInterpreter('context_18_v1').interpret("I'm going shopping.").structured_request
    reference=reference_rank(captured,Preferences(),'owner-A',request)
    compact_scorer=CompactExhaustiveScorer(Query(),Preferences(),evaluator_type=specification,
        context_ranking=True,attribute_context=prepared,attribute_verifier=verifier)
    compact=compact_scorer.rank('owner-A',request)
    expected={'mixed':'Selected','fail_only':'NoMatchingCandidates','unknown_only':'InsufficientEvidence'}[states]
    assert reference.status==compact.status==expected
    assert reference.complete and compact.complete
    assert captured.session.result.complete
    assert captured.session.attribute_context is prepared
    assert captured.session.attribute_verifier is verifier
    assert captured.session.attribute_ledger.snapshot()==compact_scorer.attribute_ledger.snapshot()
    coverage=captured.session.attribute_ledger.snapshot()
    assert coverage['attribute_failed']>0 if states!='unknown_only' else coverage['attribute_failed']==0
    assert coverage['attribute_unknown']>0 if states!='fail_only' else coverage['attribute_unknown']==0
    if states=='mixed':
        assert reference.winner.verified.candidate.key==compact.winner.verified.candidate.key
        assert asdict(reference.winner.score)==asdict(compact.winner.score)
        assert 'match' in [member.garment.garment_id for member in reference.winner.verified.candidate.members]
        assert verifier.decision(reference.winner.verified.candidate.key)=='Pass'
    else:
        assert reference.winner is None and compact.winner is None


def test_reference_retains_unknown_counter_guard_without_admitting_unknown(monkeypatch):
    # Observe the actual replay session; do not replace its admission evaluator.
    from app.application.recommendation import request_candidate_engine as module
    sessions=[]
    original=module.RequestCandidateEngine.generate_candidates
    def observe(self,*args):
        result=original(self,*args);sessions.append(result);return result
    monkeypatch.setattr(module.RequestCandidateEngine,'generate_candidates',observe)
    specification=EvaluatorSpecification.current('context_18_v1')
    upper=make_member('unknown',state='missing')
    lower=make_member('lower',category='trousers')
    conditions=AttributeConditions.from_dict({'version':'attribute-conditions-1.0.0','groups':[
        {'id':'g01','role':'upper','quantifier':'exists','conditions':[
            {'id':'c01','attribute':'material','operator':'contains_any','values':['cotton']}]}]})
    policy=AttributeEvidencePolicy.load();pool=(upper,lower)
    prepared=PreparedAttributeConditions.prepare(conditions,pool,policy)
    verifier=IndependentAttributeVerifier.prepare(conditions,pool,policy)
    query=SimpleNamespace(get_confirmed_available_garments=lambda owner:tuple(item.snapshot for item in pool))
    engine=RequestCandidateEngine(query,evaluator_factory=specification.construct,
        attribute_context=prepared,attribute_verifier=verifier)
    engine.attribute_seen=((('upper','unknown'),('lower','lower')),)
    engine.attribute_counter_guard=SimpleNamespace(ignores=lambda members:True)
    result=reference_rank(CapturedCandidateEngine(engine),SimpleNamespace(get_active_preferences=lambda owner:()),
        'owner-A',GeneralContextInterpreter('context_18_v1').interpret("I'm going shopping.").structured_request)
    session=sessions[0]
    assert session.attribute_seen==frozenset(engine.attribute_seen)
    assert session.attribute_counter_guard is engine.attribute_counter_guard
    assert result.status=='InsufficientEvidence' and result.winner is None
    assert session.attribute_ledger.snapshot()['attribute_unknown']==1
    assert session.attribute_ledger.unseen_unknown==0
