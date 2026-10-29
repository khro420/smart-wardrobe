"""Frozen mechanics checked through compact, reference and public reconstruction."""
from fractions import Fraction as F
import json
import pytest
from tests.test_context_relevance_ranking import rows,Query,Preferences,LABELS
from app.domain.value_objects.recommendation_refinement import RefinementPlan
from app.application.recommendation.refinement_selector import base_signature
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine


def rank(text,plan,compact=True,data=None,prefs=(),audit=None):
    request=GeneralContextInterpreter('context_18_v1').interpret(text).structured_request
    query,preferences=Query(rows() if data is None else data),Preferences(prefs)
    spec=EvaluatorSpecification.current('context_18_v1')
    scorer=(CompactExhaustiveScorer(query,preferences,evaluator_type=spec,context_ranking=True,audit=audit)
        if compact else AggregatedDecisionRecommendationScorer(RequestCandidateEngine(query,evaluator_specification=spec),preferences,context_ranking=True))
    result=scorer.rank('owner',request,refinement_plan=plan)
    assert query.calls==1
    return result


@pytest.mark.parametrize('compact',[True,False])
@pytest.mark.parametrize('text,expected',[
    ("I'm going shopping.",[(('G01','G04'),'4/5'),(('G01','G05'),'7/10'),(('G08','G04'),'7/10'),(('G08','G05'),'7/10')]),
    ("I'm going on a date tonight.",[(('G06','G07'),'4/5'),(('G02','G03'),'4/5')]),
])
def test_independent_complete_sequences(compact,text,expected):
    seen=[];plan=RefinementPlan();root_total=None
    for ordinal,(ids,total) in enumerate(expected):
        ledger=[]
        result=rank(text,plan,compact,audit=ledger.append if compact else None)
        assert result.status=='Selected',result
        assert tuple(m.garment.garment_id for m in result.winner.verified.candidate.members)==ids
        score=result.winner.score
        assert score.total==F(total) and score.request_match.contribution==1
        root_total=root_total or score.total
        proof=json.loads(result.ranking_evidence)
        assert proof['version']=='context-relevance-evidence-1.2.0'
        coverage=proof['coverage']
        assert coverage['hard_passed']==20
        assert sum(coverage[k] for k in ('point_candidates','unresolved_candidates','already_seen','below_floor_points','unresolved_below_floor'))==20
        if compact:
            assert len(ledger)==20
            table={row[0]:row for row in LABELS['point_rows']}
            for row in ledger:
                expected_row=table['+'.join(g for _,g in row['key'])]
                assert row['score']['total']==F(expected_row[5 if 'shopping' in text else 6])
        seen.append(base_signature(result.winner.verified.candidate))
        plan=RefinementPlan(root_id='00000000-0000-4000-8000-000000000001',
            parent_id=f'00000000-0000-4000-8000-{ordinal+1:012d}',ordinal=ordinal+1,
            root_R=F(1),root_total=root_total,seen=tuple(seen))
    assert rank(text,plan,compact).status=='RefinementExhausted'


@pytest.mark.parametrize('compact',[True,False])
def test_excluded_dresses_and_conflict(compact):
    from app.domain.value_objects.recommendation_refinement import SHORTCUTS
    result=rank("I'm going on a date tonight.",RefinementPlan(exclusions=dict(SHORTCUTS)['Dresses']),compact)
    assert result.status=='Selected',result
    assert [m.garment.garment_id for m in result.winner.verified.candidate.members]==['G02','G03']
    assert json.loads(result.ranking_evidence)['coverage']['hard_passed']==18


def test_scoped_coverage_forgery_rejected():
    from app.application.recommendation.context_relevance_verifier import validate_evidence
    result=rank("I'm going shopping.",RefinementPlan())
    proof=json.loads(result.ranking_evidence);proof['coverage']['already_seen']=1
    with pytest.raises(ValueError):validate_evidence(proof,result.winner.score)


@pytest.mark.parametrize('compact',[True,False])
def test_unknown_qualifier_is_not_exhaustion(compact):
    from dataclasses import replace
    data=[replace(g,style_tags=None,custom_tags=('rec:v1:occasion:dinner:allow',)) if g.garment_id=='G06' else g for g in rows()]
    root=rank("I'm meeting friends for dinner.",RefinementPlan(),compact,data=data)
    assert root.status=='Selected',root
    assert base_signature(root.winner.verified.candidate)==(('upper','G02'),('lower','G03'))
    plan=RefinementPlan(root_id='00000000-0000-4000-8000-000000000001',parent_id='00000000-0000-4000-8000-000000000001',
        ordinal=1,root_R=F(1),root_total=F(4,5),seen=(base_signature(root.winner.verified.candidate),))
    assert rank("I'm meeting friends for dinner.",plan,compact,data=data).status=='RefinementInsufficientEvidence'


@pytest.mark.parametrize('compact',[True,False])
def test_all_base_exclusions_and_positive_conflict(compact):
    from app.domain.value_objects.recommendation_refinement import CATEGORIES
    plan=RefinementPlan(exclusions=tuple(c for c in CATEGORIES if not c.endswith('_outwear')))
    result=rank("I'm going shopping.",plan,compact)
    assert result.status=='InsufficientStructure',result
    result=rank('Suggest an outfit for shopping with trousers',RefinementPlan(exclusions=('trousers',)),compact)
    assert result.status=='RefinementConflict',result


@pytest.mark.parametrize('compact',[True,False])
def test_known_zero_root_keeps_zero_floor(compact):
    data=[g for g in rows() if g.garment_id in ('G02','G03','G06','G07')]
    root=rank("I'm going shopping.",RefinementPlan(),compact,data=data)
    assert root.status=='Selected' and root.winner.score.request_match.contribution==0
    plan=RefinementPlan(root_id='00000000-0000-4000-8000-000000000001',parent_id='00000000-0000-4000-8000-000000000001',
        ordinal=1,root_R=F(0),root_total=root.winner.score.total,seen=(base_signature(root.winner.verified.candidate),))
    result=rank("I'm going shopping.",plan,compact,data=data)
    assert result.status=='Selected' and result.winner.score.request_match.contribution==0


@pytest.mark.parametrize('text',["I'm going shopping.","I'm meeting friends for dinner."])
def test_every_remaining_candidate_public_parity_and_independent_partitions(text,monkeypatch):
    from dataclasses import asdict
    from app.application.recommendation.context_relevance_scorer import PreparedRelativeFacts
    seen=[];plan=RefinementPlan();original=PreparedRelativeFacts.public
    expected_table={row[0]:row for row in LABELS['point_rows']}
    for ordinal in range(2):
        ledger=[];compact=rank(text,plan,audit=ledger.append)
        public={}
        def capture(self,verified,legacy):
            score=original(self,verified,legacy);public[verified.candidate.key]=asdict(score);return score
        with monkeypatch.context() as local:
            local.setattr(PreparedRelativeFacts,'public',capture)
            reference=rank(text,plan,compact=False)
        assert compact.winner.score==reference.winner.score
        assert compact.winner.verified.candidate==reference.winner.verified.candidate
        assert {tuple(row['key']):row['score'] for row in ledger}==public
        counts=dict(already_seen=0,below_floor_points=0,point_candidates=0)
        for row in ledger:
            base=tuple((role,gid) for role,gid in row['key'] if role!='outerwear')
            written=expected_table['+'.join(gid for _,gid in row['key'])]
            r=F(written[1 if 'shopping' in text else 2])
            assert row['score']['request_match']['summary']['value']==r
            assert row['score']['compatibility']['decision']['value']==F(written[3])
            assert row['score']['total']==F(written[5 if 'shopping' in text else 6])
            counts['already_seen' if base in seen else 'below_floor_points' if ordinal and r<1 else 'point_candidates']+=1
        coverage=json.loads(compact.ranking_evidence)['coverage']
        assert all(coverage[k]==v for k,v in counts.items())
        assert coverage['global_optimum_certified'] and coverage['unresolved_candidates']==0
        seen.append(base_signature(compact.winner.verified.candidate))
        plan=RefinementPlan(root_id='00000000-0000-4000-8000-000000000001',parent_id=f'00000000-0000-4000-8000-{ordinal+1:012d}',ordinal=ordinal+1,root_R=F(1),root_total=F(4,5),seen=tuple(seen))


@pytest.mark.parametrize('excluded,expected,count',[
    (('trousers',),('G01','G05'),8),
    (('long_sleeve_outwear','short_sleeve_outwear'),('G02','G03'),10),
    (('shorts','skirt','trousers'),('G06','G07'),2),
])
@pytest.mark.parametrize('compact',[True,False])
def test_frozen_exclusion_winners(excluded,expected,count,compact):
    text="I'm going shopping." if excluded==('trousers',) else "I'm going on a date tonight."
    result=rank(text,RefinementPlan(exclusions=excluded),compact)
    assert tuple(m.garment.garment_id for m in result.winner.verified.candidate.members)==expected
    assert json.loads(result.ranking_evidence)['coverage']['hard_passed']==count


def test_valid_extreme_exact_score_and_new_only_encoding_limits():
    from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
    from app.domain.value_objects.context_relevance import ratio,read_ratio,bounded_json,read_proof,RelativeEncodingLimit
    from app.application.recommendation.decision_score_codec import score_to_json,score_from_json
    from app.application.recommendation.refinement_verifier import bounded_provenance,EVIDENCE_VERSION
    huge=F(10**4095-1,10**4095)
    assert read_ratio(ratio(huge))==huge
    with pytest.raises(RelativeEncodingLimit):ratio(F(1,10**4096))
    prefs=[PreferenceSnapshot('tiny','owner','styles','{"values":["smart casual"]}','1e-4090'),PreferenceSnapshot('unit','owner','colours','{"values":["blue"]}','1')]
    result=rank("I'm going shopping.",RefinementPlan(),prefs=prefs)
    assert result.status=='Selected',result
    encoded=score_to_json(result.winner.score)
    assert score_from_json(encoded)==result.winner.score
    assert len(json.loads(encoded)['total']['denominator'])>4000
    # Encoder envelopes are tested separately from semantic proof validation.
    for version,limit in [('context-relevance-evidence-1.1.0',262144),('context-relevance-evidence-1.2.0',294912)]:
        value={'version':version,'padding':''};size=len(bounded_json(value).encode());value['padding']='x'*(limit-size)
        assert len(bounded_json(value).encode())==limit and read_proof(bounded_json(value))==value
        value['padding']+='x'
        with pytest.raises(RelativeEncodingLimit):bounded_json(value)
        with pytest.raises(RelativeEncodingLimit):read_proof(json.dumps(value,separators=(',',':')))
    for ref,limit in [(None,262144),({'version':EVIDENCE_VERSION},327680)]:
        value={'padding':''}
        if ref:value['refinement']=ref
        size=len(bounded_provenance(value).encode());value['padding']='x'*(limit-size)
        assert len(bounded_provenance(value).encode())==limit
        value['padding']+='x'
        with pytest.raises(RelativeEncodingLimit):bounded_provenance(value)


def test_100_garment_stream_has_no_candidate_loop_configuration(monkeypatch):
    from dataclasses import replace
    from app.application.recommendation.context_bundle import ContextBundle
    from app.application.recommendation.context_relevance_policy import ContextRelevancePolicy
    from app.application.recommendation.refinement_policy import RefinementPolicy
    state={'enumerating':False};counts={}
    for cls in (ContextBundle,ContextRelevancePolicy,RefinementPolicy):
        original=cls.load.__func__;name=cls.__name__;counts[name]=0
        def load(klass,*args,_original=original,_name=name,**kwargs):
            assert not state['enumerating'],'Configuration I/O inside candidate loop'
            counts[_name]+=1;return _original(klass,*args,**kwargs)
        monkeypatch.setattr(cls,'load',classmethod(load))
    data=[replace(rows()[i%8],garment_id=f'S{i:03}',preferred_media_id=f'M{i:03}') for i in range(100)]
    query,prefs=Query(data),Preferences();spec=EvaluatorSpecification.current('context_18_v1')
    request=GeneralContextInterpreter('context_18_v1').interpret("I'm going shopping.").structured_request
    def checkpoint(stage,*args):
        if stage=='candidate':state['enumerating']=True
        if stage=='closed':state['enumerating']=False
    result=CompactExhaustiveScorer(query,prefs,evaluator_type=spec,context_ranking=True,checkpoint=checkpoint).rank('owner',request,refinement_plan=RefinementPlan())
    assert result.status=='Selected' and query.calls==prefs.calls==1
    assert json.loads(result.ranking_evidence)['coverage']['hard_passed']==18928
    assert counts['ContextRelevancePolicy']==1


@pytest.mark.parametrize('compact',[True,False])
def test_lower_alternative_recomputes_uncertainty_certificate(compact):
    from dataclasses import replace
    data=[replace(g,garment_id='G00',style_tags=None,custom_tags=('rec:v1:occasion:shopping:allow',)) if g.garment_id=='G08' else g for g in rows()]
    root=rank("I'm going shopping.",RefinementPlan(),compact,data=data)
    assert root.status=='Selected' and json.loads(root.ranking_evidence)['coverage']['global_optimum_certified']
    plan=RefinementPlan(root_id='00000000-0000-4000-8000-000000000001',parent_id='00000000-0000-4000-8000-000000000001',ordinal=1,root_R=F(1),root_total=F(4,5),seen=(base_signature(root.winner.verified.candidate),))
    alternative=rank("I'm going shopping.",plan,compact,data=data)
    assert alternative.status=='Selected' and alternative.winner.score.total==F(7,10)
    assert not json.loads(alternative.ranking_evidence)['coverage']['global_optimum_certified']


def test_bounded_rank_and_extreme_encoding_observation(tmp_path):
    import time,tracemalloc
    from dataclasses import replace
    from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
    from app.application.recommendation.decision_score_codec import score_to_json
    from app.application.recommendation.refinement_verifier import finalize_supplement,validate_refinement,request_digest,snapshot_digest,preference_digest,bounded_provenance
    observations={}
    for label,data,prefs in [('ordinary_100',[replace(rows()[i%8],garment_id=f'S{i:03}',preferred_media_id=f'M{i:03}') for i in range(100)],()),
        ('extreme_exact_8',rows(),(PreferenceSnapshot('tiny','owner','styles','{"values":["smart casual"]}','1e-4090'),PreferenceSnapshot('unit','owner','colours','{"values":["blue"]}','1')))]:
        plan=RefinementPlan();tracemalloc.start();started=time.perf_counter()
        result=rank("I'm going shopping.",plan,data=data,prefs=prefs)
        elapsed=time.perf_counter()-started;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        assert result.status=='Selected',result
        relative=json.loads(result.ranking_evidence);payload=relative['context_plan']['request'];identifier='00000000-0000-4000-8000-000000000001'
        started=time.perf_counter()
        supplement=finalize_supplement(plan,identifier,None,result.winner.score,relative,snapshot_digest(data),preference_digest('owner',prefs),request_digest("I'm going shopping.",payload,()))
        validate_refinement(supplement,relative,result.winner.score,identifier,"I'm going shopping.",payload,result.winner.verified.candidate)
        provenance=bounded_provenance({'context_relevance':relative,'refinement':supplement})
        observations[label]=dict(rank_seconds=elapsed,rank_tracemalloc_peak_bytes=peak,proof_preparation_seconds=time.perf_counter()-started,
            candidates=relative['coverage']['hard_passed'],provenance_bytes=len(provenance.encode()),supplement_bytes=len(json.dumps(supplement).encode()),score_bytes=len(score_to_json(result.winner.score).encode()))
    (tmp_path/'performance-observation.json').write_text(json.dumps(observations,indent=2))


@pytest.mark.parametrize('compact',[True,False])
@pytest.mark.parametrize('case',['deny','broad_deny','broad_allow_missing','compound_dinner_deny','compound_birthday_deny','override','green','duplicate'])
def test_refinement_preserves_mandatory_compound_and_preference_meanings(compact,case):
    from dataclasses import replace
    from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
    text="I'm going shopping.";data=rows();prefs=();expected='Selected'
    if case in ('deny','broad_deny','compound_dinner_deny','compound_birthday_deny'):
        text,occasion={
            'deny':(text,'shopping'),'broad_deny':("I'm going to study at the library.",'campus'),
            'compound_dinner_deny':("I'm going on a dinner date.",'dinner'),
            'compound_birthday_deny':("I'm attending a birthday dinner.",'party')}[case]
        data=[replace(g,custom_tags=(f'rec:v1:occasion:{occasion}:deny',)) for g in data];expected='NoMatchingCandidates'
    elif case=='broad_allow_missing':
        text="I'm going to study at the library.";data=[replace(g,style_tags=None,custom_tags=('rec:v1:occasion:campus:allow',)) for g in data];expected='InsufficientEvidence'
    elif case=='override':text='Suggest an outfit for dinner with casual style'
    else:
        green=PreferenceSnapshot('green','owner','colours','{"values":["green"]}','1')
        prefs=(green,) if case=='green' else (PreferenceSnapshot('same','owner','styles','{"values":["casual"]}','1'),green)
    result=rank(text,RefinementPlan(),compact,data=data,prefs=prefs)
    assert result.status==expected,result
    if result.winner:
        assert base_signature(result.winner.verified.candidate)==(('upper','G08' if case=='green' else 'G01'),('lower','G04'))
        assert result.winner.score.total==F(9,10) if case=='green' else result.winner.score.total==F(4,5)
        if case=='duplicate':assert json.loads(result.ranking_evidence)['preference_denominator']=={'numerator':'2','denominator':'1'}
