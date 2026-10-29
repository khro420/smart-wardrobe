"""Source/score forgery, exact encoding, independent modes and preparation bounds."""
from dataclasses import asdict,replace
from fractions import Fraction as F
import copy,json
import pytest
from app.application.recommendation.context_relevance_verifier import validate_evidence
from app.application.recommendation.decision_score_codec import score_from_json,score_to_json
from app.application.recommendation.context_relevance_policy import ContextRelevancePolicy
from app.domain.value_objects.context_relevance import ratio,read_ratio,RelativeEncodingLimit,read_proof
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
from app.domain.value_objects.saved_attribute_evidence import SavedAttributeEvidence
from tests.test_context_relevance_ranking import rank,rows,TEXTS


@pytest.fixture(scope='module')
def selected():
    result=rank(rows(),TEXTS[0])
    assert result.status=='Selected'
    return result


@pytest.mark.parametrize('mutation',[
    lambda p:p.update(policy_sha256='0'*64),lambda p:p.update(catalogue_sha256='0'*64),
    lambda p:p.update(actual_profile='compatibility_deferred'),lambda p:p.update(version='future'),
    lambda p:p['objective'].update(authority='external_dress_code'),lambda p:p['objective'].update(target='smart casual'),
    lambda p:p['selected_members'][0].update(match=0),lambda p:p['selected_members'][0].update(origin='model_reported'),
    lambda p:p['selected_members'][0].update(snapshot_sha256='0'*64),lambda p:p['selected_members'][0].update(styles=['smart casual']),
    lambda p:p['coverage'].update(hard_passed=21),lambda p:p['coverage'].update(global_optimum_certified=False),
    lambda p:p.update(fallback_reason='objective_unavailable'),lambda p:p.update(relative_R={'numerator':'0','denominator':'1'}),
    lambda p:p.update(total={'numerator':'1','denominator':'1'}),lambda p:p.update(numeric_ties=0),
])
def test_forged_or_inconsistent_immutable_proof_rejected(selected,mutation):
    data=json.loads(selected.ranking_evidence);mutation(data)
    with pytest.raises(ValueError):validate_evidence(data,selected.winner.score,selected.winner.verified.candidate)


def test_relative_string_ratios_roundtrip_without_number_conversion(selected):
    encoded=score_to_json(selected.winner.score)
    assert score_from_json(encoded)==selected.winner.score
    raw=json.loads(encoded)
    assert raw['total']=={'numerator':'4','denominator':'5'}
    raw['total']['numerator']=4
    with pytest.raises(ValueError):score_from_json(json.dumps(raw))
    huge=F(9007199254740993,9007199254740994)
    assert read_ratio(ratio(huge))==huge
    with pytest.raises(RelativeEncodingLimit):ratio(F(1,10**5000))


def test_archived_proof_reader_does_not_reinterpret_with_active_catalogue_constants(selected,monkeypatch):
    import importlib
    from app.application.recommendation import context_relevance_policy as active
    from app.application.recommendation import context_relevance_verifier as archived
    try:
        with monkeypatch.context() as local:
            local.setattr(active,'CATALOGUE_SHA256','f'*64)
            local.setattr(active,'SCOPES',())
            importlib.reload(archived)
            assert archived.validate_evidence(json.loads(selected.ranking_evidence),selected.winner.score,selected.winner.verified.candidate)
    finally:importlib.reload(archived)


@pytest.mark.parametrize('kind,values',[('styles',['smart casual']),('colours',['green']),('garment_categories',[{'kind':'category','value':'trousers'}])])
def test_conflicting_or_independent_preferences_not_suppressed(kind,values):
    prefs=[PreferenceSnapshot('preference','owner',kind,json.dumps({'values':values}),'1')]
    result=rank(rows(),TEXTS[0],prefs)
    proof=json.loads(result.ranking_evidence)
    assert result.status=='Selected' and not proof['preferences'][0]['suppressed']
    reference=rank(rows(),TEXTS[0],prefs,False)
    assert asdict(result.winner.score)==asdict(reference.winner.score)
    assert result.winner.verified.candidate.key==reference.winner.verified.candidate.key


@pytest.mark.parametrize('state',['Malformed','Stale'])
def test_present_invalid_source_with_clean_allow_is_unknown_relative_not_positive(state):
    data=rows()
    data[5]=replace(data[5],saved_attribute_evidence=SavedAttributeEvidence(state),custom_tags=('rec:v1:occasion:dinner:allow',))
    result=rank(data,TEXTS[4])
    assert result.status=='Selected'
    proof=json.loads(result.ranking_evidence)
    assert proof['coverage']['unresolved_candidates']==2
    assert not proof['coverage']['global_optimum_certified']
    assert [m.garment.garment_id for m in result.winner.verified.candidate.members]==['G02','G03']


def test_preparation_only_config_loading_and_100_garment_search_bound(monkeypatch):
    from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
    from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
    from tests.test_context_relevance_ranking import Query,Preferences,parsed
    data=[]
    for index in range(100):
        prototype=rows()[index%8]
        data.append(replace(prototype,garment_id=f'S{index:03}',preferred_media_id=f'M{index:03}'))
    loads=[];original=ContextRelevancePolicy.load.__func__
    monkeypatch.setattr(ContextRelevancePolicy,'load',classmethod(lambda cls,*a,**kw:(loads.append(True),original(cls,*a,**kw))[1]))
    enumerating=[False]
    def checkpoint(stage,*args):
        if stage=='candidate':enumerating[0]=True
        if stage=='closed':enumerating[0]=False
    # No relevance-loader work is allowed once candidate streaming begins.
    def load(cls,*a,**kw):
        assert not enumerating[0]
        loads.append(True);return original(cls,*a,**kw)
    monkeypatch.setattr(ContextRelevancePolicy,'load',classmethod(load))
    query=Query(data);preferences=Preferences()
    scorer=CompactExhaustiveScorer(query,preferences,evaluator_type=EvaluatorSpecification.current(),context_ranking=True,checkpoint=checkpoint)
    result=scorer.rank('owner',parsed(TEXTS[0]))
    assert result.status=='Selected' and loads==[True]
    count={role:sum(g.structural_role==role for g in data) for role in ('top','bottom','dress','outerwear')}
    expected=(count['top']*count['bottom']+count['dress'])*(1+count['outerwear'])
    assert json.loads(result.ranking_evidence)['coverage']['hard_passed']==expected
    assert query.calls==preferences.calls==1


def test_exact_source_transitions_keep_old_chain_and_phase_a_checkpoint():
    from tests import integration_source_guard as guard
    data=guard.context_relevance_manifest(verify=True)
    guard.automatic_admission_manifest(verify=True)
    for name,change in data['replacements'].items():
        # Verify every starting digest directly against a retained independent
        # accepted declaration. Do not recursively recertify unrelated archives
        # twenty times; historical guard entry points keep their old assertions.
        authority=data['starting_authorities'][name]
        value=json.loads((guard.BACKEND/'tests/fixtures'/authority['fixture']).read_text(encoding='utf-8'))
        for key in authority['key_path']:value=value[key]
        assert value==change['before'],name
    assert len(data['checkpoint_a'])==4
