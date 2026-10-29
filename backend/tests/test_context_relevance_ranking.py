"""Independent frozen examples through the real compact and public paths."""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import json
import pytest
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine

FACTS=[('G01','Blue T-shirt','short_sleeve_top','blue','casual'),('G02','White Shirt','long_sleeve_top','white','smart casual'),
    ('G03','Black Trousers','trousers','black','smart casual'),('G04','Blue Jeans','trousers','blue','casual'),
    ('G05','Beige Shorts','shorts','beige','casual'),('G06','Navy Dress','vest_dress','navy','smart casual'),
    ('G07','Grey Jacket','long_sleeve_outwear','grey','smart casual'),('G08','Green Sweatshirt','long_sleeve_top','green','casual')]
TEXTS=["I'm going shopping.","I'm going to class.","I'm going out with friends.","I'm going on a date tonight.","I'm meeting friends for dinner."]
LABELS=json.loads((Path(__file__).with_name('fixtures')/'context_relevance_labels.v1.json').read_text())


class Query:
    def __init__(self,rows):self.rows=rows;self.calls=0
    def get_confirmed_available_garments(self,user):self.calls+=1;return tuple(self.rows)


class Preferences:
    def __init__(self,rows=()):self.rows=rows;self.calls=0
    def get_active_preferences(self,user):self.calls+=1;return self.rows


def rows():
    return [ConfirmedGarmentSnapshot(g,'owner','available',category,name,'media-'+g,False,'synthetic-time',
        structural_role=GARMENT_STRUCTURE[category][0],layering_index=GARMENT_STRUCTURE[category][1],
        primary_colour=colour,style_tags=(style,)) for g,name,category,colour,style in FACTS]


def parsed(text):
    result=GeneralContextInterpreter().interpret(text)
    assert result.status=='Supported'
    return result.structured_request


def rank(data,text,prefs=(),compact=True,audit=None):
    query,preferences=Query(data),Preferences(prefs)
    if compact:
        scorer=CompactExhaustiveScorer(query,preferences,evaluator_type=EvaluatorSpecification.current(),context_ranking=True,audit=audit)
    else:
        engine=RequestCandidateEngine(query,evaluator_specification=EvaluatorSpecification.current())
        scorer=AggregatedDecisionRecommendationScorer(engine,preferences,context_ranking=True)
    result=scorer.rank('owner',parsed(text))
    assert query.calls==1 and preferences.calls==1
    return result


@pytest.mark.parametrize('index',range(5))
@pytest.mark.parametrize('compact',[True,False])
def test_five_automatic_frozen_winners_and_exact_scores(index,compact):
    result=rank(rows(),TEXTS[index],compact=compact)
    assert result.status=='Selected',result
    assert [m.garment.garment_id for m in result.winner.verified.candidate.members]==LABELS['cases'][index]['winner']
    score=result.winner.score
    assert (score.request_match.contribution,score.compatibility.contribution,score.preference.contribution,score.total)==(F(1),F(1),F(0),F(4,5))
    proof=json.loads(result.ranking_evidence)
    assert proof['coverage']==dict(hard_passed=20,point_candidates=20,unresolved_candidates=0,objective_unavailable_candidates=0,global_optimum_certified=True)


@pytest.mark.parametrize('index',[0,3])
def test_all_twenty_candidates_against_independent_hand_authored_rows(index):
    audit=[]
    result=rank(rows(),TEXTS[index],audit=audit.append)
    assert result.status=='Selected'
    expected={r[0]:r for r in LABELS['point_rows']}
    assert len(audit)==20
    for candidate in audit:
        key='+'.join(g for role,g in candidate['key'])
        expected_row=expected[key]
        r=F(expected_row[1 if index==0 else 2]);c=F(expected_row[3]);p=F(expected_row[4]);t=F(expected_row[5 if index==0 else 6])
        score=candidate['score']
        assert score['request_match']['summary']['value']==r
        assert score['compatibility']['decision']['value']==c
        assert (score['preference']['summary']['value'] or 0)==p
        assert score['total']==t


@pytest.mark.parametrize('case',LABELS['cases'][5:],ids=lambda c:c['id'])
@pytest.mark.parametrize('compact',[True,False])
def test_frozen_override_deny_unknown_preference_and_fallback_cases(case,compact):
    data=rows();target=case['context'];text="I'm meeting friends for dinner." if target=='dinner' else TEXTS[0]
    if case.get('explicit_style'):text='Suggest an outfit for dinner with casual style'
    for index,g in enumerate(data):
        if case.get('deny')==g.garment_id:data[index]=replace(g,custom_tags=('rec:v1:occasion:dinner:deny',))
        if case.get('missing_style')==g.garment_id or case.get('all_base_styles_missing') and g.structural_role!='outerwear':
            data[index]=replace(g,style_tags=None,custom_tags=(f'rec:v1:occasion:{target}:allow',) if case.get('allow_missing') else ())
    prefs=[]
    pref=case.get('preference')
    if pref:
        kind,values=('garment_categories',[{'kind':'category','value':'vest_dress'}]) if pref=='dress' else ('colours',['green']) if pref=='green' else ('styles',['casual'])
        prefs=[PreferenceSnapshot('synthetic-pref','owner',kind,json.dumps({'values':values}),'1')]
    if case.get('objective_absent'):
        # Supported explicit code has no unspecified-code A1 objective. Clean
        # formality declarations preserve this case's same twenty-member pool.
        text="I'm going shopping; the dress code is casual."
        data=[replace(g,custom_tags=('rec:v1:occasion:shopping:allow','rec:v1:formality:casual:allow')) for g in data]
    result=rank(data,text,prefs,compact)
    if case['profile_kind']=='no_result':
        assert result.status=='InsufficientEvidence' and result.winner is None
        return
    assert result.status=='Selected',result
    assert [m.garment.garment_id for m in result.winner.verified.candidate.members]==case['winner']
    score=result.winner.score
    assert (score.request_match.contribution,score.compatibility.contribution,score.preference.contribution,score.total)==tuple(F(case[k]) for k in ('R','C','P','T'))
    proof=json.loads(result.ranking_evidence)
    assert proof['coverage']['hard_passed']==case['eligible']
    if 'global_optimum_certified' in case:assert proof['coverage']['global_optimum_certified']==case['global_optimum_certified']
    assert proof['selection_mode']==('best_evidenced_with_coverage_v1' if case['profile_kind']=='relative' else 'baseline_disclosed_v1')


@pytest.mark.parametrize('reverse',[True,False])
def test_stable_ties_and_independent_mixed_preference_denominator(reverse):
    data=rows()[::-1] if reverse else rows()
    prefs=[PreferenceSnapshot('style','owner','styles','{"values":["casual"]}','1'),PreferenceSnapshot('green','owner','colours','{"values":["green"]}','1')]
    result=rank(data,TEXTS[0],prefs)
    assert result.status=='Selected'
    assert [m.garment.garment_id for m in result.winner.verified.candidate.members]==['G01','G04']
    assert result.winner.score.total==F(4,5)
    proof=json.loads(result.ranking_evidence)
    assert proof['preference_denominator']=={'numerator':'2','denominator':'1'}


def test_extreme_accepted_weight_fails_new_encoding_without_fallback_or_old_weight_change():
    prefs=[PreferenceSnapshot('tiny','owner','colours','{"values":["green"]}','1e-5000')]
    result=rank(rows(),TEXTS[0],prefs)
    assert result.status=='ProfileUnavailable' and result.winner is None
    assert ('ranking_reason','exact_encoding_budget_exceeded') in result.diagnostics
