"""All candidate decisions/components compared to pre-existing independent fractions."""
from fractions import Fraction as F
from dataclasses import replace
import json
import pytest
from tests.test_context_relevance_ranking import rows,Query,Preferences,LABELS
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
from app.application.recommendation.context_bundle import ARCHIVES,ACTIVE_WAVE
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer

TEXTS={
'academic.library_study':"I'm going to study at the library.",
'academic.group_study':"I have a group project meeting at university.",
'professional.office_day':"I need to go to the office tomorrow.",
'professional.workplace_meeting':"I have a meeting with my colleagues.",
'social.birthday_gathering':"I'm attending a birthday party.",
'social.house_gathering':"I'm visiting my friend's house.",
'leisure.cinema_outing':"I'm going to watch a movie.",
'social.cafe_meetup':"I'm meeting someone at a café.",
'leisure.city_sightseeing':"I'm sightseeing around the city.",
'travel.journey':"I'm taking a train for a trip."}

def rank(text,data=None,prefs=(),compact=True,audit=None):
    parsed=GeneralContextInterpreter('context_18_v1').interpret(text)
    assert parsed.status=='Supported',parsed
    query,preferences=Query(rows() if data is None else data),Preferences(prefs)
    spec=EvaluatorSpecification.current('context_18_v1')
    scorer=CompactExhaustiveScorer(query,preferences,evaluator_type=spec,context_ranking=True,audit=audit) if compact else AggregatedDecisionRecommendationScorer(RequestCandidateEngine(query,evaluator_specification=spec),preferences,context_ranking=True)
    result=scorer.rank('owner',parsed.structured_request)
    return result,query,preferences

@pytest.mark.parametrize('sid',TEXTS)
@pytest.mark.parametrize('compact',[True,False])
def test_new_context_exact_independent_ranking(sid,compact):
    if sid not in ARCHIVES[ACTIVE_WAVE]['targets']:pytest.skip('Later approved wave')
    target=ARCHIVES[ACTIVE_WAVE]['targets'][sid]
    audit=[]
    result,query,prefs=rank(TEXTS[sid],compact=compact,audit=audit.append if compact else None)
    assert result.status=='Selected',result
    assert query.calls==prefs.calls==1
    assert [m.garment.garment_id for m in result.winner.verified.candidate.members]==(['G01','G04'] if target=='casual' else ['G06','G07'])
    score=result.winner.score
    assert (score.request_match.contribution,score.compatibility.contribution,score.preference.contribution,score.total)==(F(1),F(1),F(0),F(4,5))
    proof=json.loads(result.ranking_evidence)
    assert proof['context_plan']['bindings'] and proof['objective']['situation']==sid
    assert proof['coverage']['hard_passed']==20
    if compact:
        assert len(audit)==20
        expected={row[0]:row for row in LABELS['point_rows']}
        for candidate in audit:
            row=expected['+'.join(g for _,g in candidate['key'])]
            actual=candidate['score']
            assert actual['request_match']['summary']['value']==F(row[1 if target=='casual' else 2])
            assert actual['compatibility']['decision']['value']==F(row[3])
            assert actual['total']==F(row[5 if target=='casual' else 6])

@pytest.mark.parametrize('sid',TEXTS)
def test_negative_parent_deny_without_positive_permission(sid):
    record=ARCHIVES[ACTIVE_WAVE]
    if sid not in record['targets']:pytest.skip('Later approved wave')
    parent=record['scopes'][sid]['negative_parent']
    data=[replace(g,custom_tags=(f'rec:v1:occasion:{parent}:deny',)) for g in rows()]
    result,_,_=rank(TEXTS[sid],data)
    assert result.status=='NoMatchingCandidates',result
    data=[replace(g,style_tags=None,custom_tags=(f'rec:v1:occasion:{parent}:allow',)) for g in rows()]
    result,_,_=rank(TEXTS[sid],data)
    assert result.status=='InsufficientEvidence',result

def test_100_garment_preparation_and_enumeration_bound(monkeypatch):
    from app.application.recommendation.context_bundle import ContextBundle
    enumerating=[False];original=ContextBundle.load.__func__;loads=[]
    def load(cls,*args,**kwargs):
        assert not enumerating[0],'Bundle loading during candidate enumeration'
        loads.append(True);return original(cls,*args,**kwargs)
    monkeypatch.setattr(ContextBundle,'load',classmethod(load))
    data=[replace(rows()[i%8],garment_id=f'S{i:03}',preferred_media_id=f'M{i:03}') for i in range(100)]
    query,prefs=Query(data),Preferences();spec=EvaluatorSpecification.current('context_18_v1')
    request=GeneralContextInterpreter('context_18_v1').interpret(TEXTS['academic.library_study']).structured_request
    def checkpoint(stage,*_):
        if stage=='candidate':enumerating[0]=True
        if stage=='closed':enumerating[0]=False
    result=CompactExhaustiveScorer(query,prefs,evaluator_type=spec,context_ranking=True,checkpoint=checkpoint).rank('owner',request)
    assert result.status=='Selected',result
    count={role:sum(g.structural_role==role for g in data) for role in ('top','bottom','dress','outerwear')}
    expected=(count['top']*count['bottom']+count['dress'])*(1+count['outerwear'])
    assert json.loads(result.ranking_evidence)['coverage']['hard_passed']==expected==18928
    assert query.calls==prefs.calls==1


@pytest.mark.parametrize('sid',TEXTS)
@pytest.mark.parametrize('compact',[True,False])
def test_independent_preferences_and_duplicate_mask(sid,compact):
    from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
    target=ARCHIVES[ACTIVE_WAVE]['targets'][sid]
    data=[replace(g,style_tags=(target,)) for g in rows() if g.garment_id in ('G01','G04','G08')]
    green=PreferenceSnapshot('green','owner','colours',json.dumps({'values':['green']}),'1')
    result,_,_=rank(TEXTS[sid],data,[green],compact=compact)
    assert result.status=='Selected'
    score=result.winner.score
    assert [m.garment.garment_id for m in result.winner.verified.candidate.members]==['G08','G04']
    assert (score.request_match.contribution,score.compatibility.contribution,score.preference.contribution,score.total)==(F(1),F(1,2),F(1),F(9,10))
    duplicate=PreferenceSnapshot('same','owner','styles',json.dumps({'values':[target]}),'1')
    result,_,_=rank(TEXTS[sid],data,[duplicate],compact=compact)
    assert result.winner.score.total==F(4,5)
    assert result.winner.score.preference.summary.state=='NotApplicable'
    assert json.loads(result.ranking_evidence)['preferences'][0]['suppressed']


@pytest.mark.parametrize('sid',TEXTS)
@pytest.mark.parametrize('fault',['missing','empty','multiple','uncovered','malformed_source','stale_source'])
def test_missing_or_invalid_evidence_never_supplies_a_positive_match(sid,fault):
    from app.domain.value_objects.saved_attribute_evidence import SavedAttributeEvidence
    data=rows()
    if fault in ('malformed_source','stale_source'):
        data=[replace(g,saved_attribute_evidence=SavedAttributeEvidence('Malformed' if fault=='malformed_source' else 'Stale')) for g in data]
    else:
        style={'missing':None,'empty':(),'multiple':('casual','smart casual'),'uncovered':('sporty',)}[fault]
        data=[replace(g,style_tags=style) for g in data]
    result,_,_=rank(TEXTS[sid],data)
    assert result.status=='InsufficientEvidence',result

@pytest.mark.parametrize('sid',TEXTS)
def test_unknown_optional_outerwear_keeps_complete_base_alternatives(sid):
    data=rows();data[6]=replace(data[6],style_tags=None)
    result,_,_=rank(TEXTS[sid],data)
    assert result.status=='Selected' and all(m.role!='outerwear' for m in result.winner.verified.candidate.members)
    assert json.loads(result.ranking_evidence)['coverage']['hard_passed']==10
    assert result.winner.score.total==F(4,5)


def test_exact_expansion_source_transition_and_independent_starting_declarations():
    from tests import integration_source_guard as guard
    from pathlib import Path
    data=guard.context_expansion_manifest(verify=True)
    assert len(data['replacements'])==24 and len(data['additions'])==8
    for name,change in data['replacements'].items():
        authority=data['starting_authorities'][name]
        value=json.loads((guard.BACKEND/'tests/fixtures'/authority['fixture']).read_text(encoding='utf-8'))
        for key in authority['key_path']:value=value[key]
        assert value==change['before'],name


@pytest.mark.parametrize('sid',TEXTS)
def test_every_candidate_matches_reference_and_public_reconstruction(sid,monkeypatch):
    from dataclasses import asdict
    from app.application.recommendation.context_relevance_scorer import PreparedRelativeFacts
    compact_audit=[]
    compact,_,_=rank(TEXTS[sid],audit=compact_audit.append)
    expected={tuple(tuple(pair) for pair in item['key']):item['score'] for item in compact_audit}
    public={};original=PreparedRelativeFacts.public
    def capture(self,verified,legacy):
        score=original(self,verified,legacy)
        public[verified.candidate.key]=asdict(score)
        return score
    monkeypatch.setattr(PreparedRelativeFacts,'public',capture)
    reference,_,_=rank(TEXTS[sid],compact=False)
    assert compact.status==reference.status=='Selected'
    assert len(expected)==len(public)==20 and expected==public
    assert compact.winner.verified.candidate.key==reference.winner.verified.candidate.key
