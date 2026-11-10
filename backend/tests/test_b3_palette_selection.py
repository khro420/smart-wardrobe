"""Small actual pools prove C2 affects selection without changing R/P or gates."""
from dataclasses import replace
from fractions import Fraction as F
import json
import pytest
from tests.test_b3_palette_compatibility import member,BLUE,RED
from tests.test_p2_preference_selection import snapshot,family
from tests.test_context_relevance_ranking import Query,Preferences
from app.application.recommendation.palette_compatibility_preparation import PreparedPaletteCompatibility
from app.application.recommendation.attribute_preference_preparation import PreparedAttributePreferences
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter

def rank(pool,request,compact,p2=False,relative=False,enabled=True,audit=None):
    garments=tuple(v.snapshot for v in pool);query=Query(garments);prefs=Preferences()
    options={}
    if enabled:options['compatibility_context']=PreparedPaletteCompatibility('owner-A',pool)
    if p2:options['preference_context']=PreparedAttributePreferences(snapshot({'colour':family('primary_colour',['blue'])}),pool,request=request,original_text=getattr(getattr(request,'context',None),'original_text','Synthetic request'))
    if compact:scorer=CompactExhaustiveScorer(query,prefs,evaluator_type=EvaluatorSpecification.current('context_18_v1'),context_ranking=relative,audit=audit,**options)
    else:
        scorer=AggregatedDecisionRecommendationScorer(RequestCandidateEngine(query,evaluator_specification=EvaluatorSpecification.current('context_18_v1')),prefs,context_ranking=relative,**options)
        scorer.p2_audit=audit
    return scorer.rank('owner-A',request)

@pytest.mark.parametrize('compact',[True,False])
@pytest.mark.parametrize('p2',[False,True])
def test_palette_actually_changes_winner_before_comparison_preserving_R_P(compact,p2):
    pool=[member('A',BLUE),member('B',RED),member('L',RED,'trousers')]
    old=rank(pool,StructuredOutfitRequest(),compact,p2,enabled=False)
    new=rank(pool,StructuredOutfitRequest(),compact,p2)
    assert old.status==new.status=='Selected',(old,new)
    assert old.winner.verified.candidate.key[0][1]=='A'
    assert new.winner.verified.candidate.key[0][1]=='B'
    assert old.winner.score.request_match==new.winner.score.request_match
    assert old.winner.score.preference==new.winner.score.preference
    assert new.winner.score.compatibility.contribution==1

@pytest.mark.parametrize('relative',[False,True])
@pytest.mark.parametrize('p2',[False,True])
@pytest.mark.parametrize('categories',[('vest','trousers'),('vest','trousers','long_sleeve_outwear'),('vest_dress',),('vest_dress','long_sleeve_outwear')])
def test_both_engines_four_structures_exact_score_proof_and_winner(categories,p2,relative):
    pool=tuple(member(str(i),BLUE,c) for i,c in enumerate(categories))
    request=GeneralContextInterpreter('context_18_v1').interpret("I'm going shopping.").structured_request if relative else StructuredOutfitRequest()
    a=rank(pool,request,True,p2,relative);b=rank(pool,request,False,p2,relative)
    assert a.status==b.status=='Selected',(a,b)
    assert a.winner.score==b.winner.score
    assert a.winner.verified.candidate.key==b.winner.verified.candidate.key
    assert json.loads(a.ranking_evidence or 'null')==json.loads(b.ranking_evidence or 'null')

def test_hard_colour_mismatch_cannot_be_rescued_by_palette_bonus():
    pool=[member('A',RED),member('L',RED,'trousers')]
    # All legacy primary identities are blue. A complete RED palette cannot
    # witness this distinct existing red-primary requirement.
    for compact in (False,True):
        result=rank(pool,StructuredOutfitRequest(colours=('red',)),compact)
        assert result.winner is None and result.status=='NoMatchingCandidates'

def test_disabled_path_keeps_exact_old_score_and_policy_identity():
    pool=[member('A',BLUE),member('L',RED,'trousers')]
    for compact in (False,True):
        old=rank(pool,StructuredOutfitRequest(),compact,enabled=False)
        assert old.status=='Selected' and old.winner.score.profile_name=='experimental_compatibility_decision_v1'
        assert old.winner.score.compatibility.decision.policy_version=='compatibility-decision-1.0.0'

from tests.test_p2_preference_values import CONTEXT_TEXTS

@pytest.mark.parametrize('sid',CONTEXT_TEXTS)
@pytest.mark.parametrize('p2',[False,True])
def test_all18_contexts_keep_every_mandatory_verdict_and_R_P_with_both_C2_engines(sid,p2):
    from tests.test_p2_preference_selection import engine_fixture
    from tests.test_b3_palette_compatibility import B0_POLICY
    from app.application.wardrobe.description_normalizer import normalise_field
    from app.application.wardrobe.description_projector import _document
    _,prepared,_,_,_,_,_=engine_fixture([]);pool=[]
    for item in prepared.collection:
        doc=item.description.to_dict();g=item.snapshot
        doc['fields']['colour_palette']=normalise_field('colour_palette',BLUE,B0_POLICY,origin='owner_selected',category=g.category,media_id=g.preferred_media_id,
            event_id='00000000-0000-4000-8000-000000000001',recorded_at='2026-11-06T00:00:00Z',source_revision='0'*64).to_dict()
        pool.append(replace(item,description=_document(doc['subject'],doc['fields'])))
    parsed=GeneralContextInterpreter('context_18_v1').interpret(CONTEXT_TEXTS[sid]);assert parsed.status=='Supported'
    before={};after={}
    def capture(target):
        def audit(row):
            score=row['score']
            target[tuple(row['key'])]=(row['evaluation'],None if score is None else (score['request_match'],score['preference']))
        return audit
    old=rank(pool,parsed.structured_request,True,p2,True,False,capture(before))
    compact=rank(pool,parsed.structured_request,True,p2,True,True,capture(after))
    reference=rank(pool,parsed.structured_request,False,p2,True,True)
    assert before==after
    assert old.status==compact.status==reference.status,(old,compact,reference)
    assert compact.complete==reference.complete
    if compact.winner:
        assert compact.winner.score==reference.winner.score
        assert compact.winner.verified.candidate.key==reference.winner.verified.candidate.key
