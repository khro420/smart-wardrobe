"""Exact differentials against separately frozen, byte-certified B2 modules."""
from tests.retained_evidence import review_path, review_reference
from pathlib import Path
from dataclasses import asdict
from fractions import Fraction as F
from types import SimpleNamespace
import hashlib,importlib.util,json,os,sys
import pytest
from tests.test_p2_preference_selection import snapshot,family,EMPTY,engine_fixture,kernel_rank
from tests.test_attribute_qualification import make_member,condition
from app.application.recommendation.attribute_preference_preparation import PreparedAttributePreferences
from app.domain.value_objects.compact_recommendation import Measure

ROOT=Path(os.environ.get('P2_PERF_ROOT',str(review_path('phase_b2_performance_optimization_20261106'))))

def frozen_modules():
    scope=json.loads((ROOT/'approved-contract/proposed-source-scope.json').read_text())
    loaded=[]
    for entry in scope['existing_production']:
        path=ROOT/'frozen-b2-oracle'/entry['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['before_sha256']
        name='tests._frozen_b2_'+path.stem
        if name not in sys.modules:
            spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
            sys.modules[name]=module;spec.loader.exec_module(module)
        loaded.append(sys.modules[name])
    return tuple(loaded)

def paired_prepared(saved,pool,**kwargs):
    old,_=frozen_modules()
    return old.PreparedAttributePreferences(saved,pool,**kwargs),PreparedAttributePreferences(saved,pool,**kwargs)

def compare_rank(pool,saved,request,compact,relative,monkeypatch):
    from app.application.recommendation.attribute_preference_codec import archived_legacy_component
    import app.application.recommendation.attribute_preference_selection as selection
    oldprep,oldfacts=frozen_modules();garments=tuple(v.snapshot for v in pool)
    outputs=[]
    for original in (True,False):
        prepared=(oldprep.PreparedAttributePreferences if original else PreparedAttributePreferences)(saved,pool)
        observed={};ledgers={}
        def audit(value):
            if compact:
                key=tuple(value['key']);observed[key]=value
                if not value['verified']:return
                rel=value['score']['request_match']['summary']['name']=='relative_style_alignment'
            else:
                key=value.verified.candidate.key
                observed[key]={'key':key,'score':asdict(value.score),'evaluation':asdict(value.verified.evaluated.evaluation)}
                rel=value.score.request_match.summary.name=='relative_style_alignment'
            legacy=archived_legacy_component(prepared,key)
            ledgers[key]=prepared.evaluate(key,legacy,relative=rel).to_dict()
        with monkeypatch.context() as patch:
            if original:
                patch.setitem(sys.modules,'app.application.recommendation.attribute_preference_relative_facts',oldfacts)
                for name in ('P2RelativeFacts','P2RelativeTracker','public_score','measure'):patch.setattr(selection,name,getattr(oldfacts,name))
            result=kernel_rank(garments,prepared,request,compact,relative,audit=audit)
        outputs.append((result,observed,ledgers))
    before,after=outputs
    assert before[1:]==after[1:]
    a,b=before[0],after[0]
    assert (a.status,a.complete,a.scored_count,a.diagnostics,a.ranking_evidence,a.refinement_summary)==(b.status,b.complete,b.scored_count,b.diagnostics,b.ranking_evidence,b.refinement_summary)
    if a.winner:
        assert a.winner.verified.candidate.key==b.winner.verified.candidate.key
        assert a.winner.score==b.winner.score
    else:assert b.winner is None

from tests.test_p2_preference_values import CONTEXT_TEXTS,CATALOG,member

@pytest.mark.parametrize('sid',CONTEXT_TEXTS)
@pytest.mark.parametrize('explicit_style',[False,True])
@pytest.mark.parametrize('compact',[True,False])
def test_all18_contexts_every_candidate_score_ledger_coverage_and_winner(sid,explicit_style,compact,monkeypatch):
    from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
    from tests.test_attribute_candidate_selection import with_field
    _,base,_,_,_,_,_=engine_fixture([])
    pool=tuple(with_field(g,'pattern','plain' if i%2 else 'floral') for i,g in enumerate(base.collection))
    saved=snapshot({'pattern':family('pattern',['plain'],['floral']),'colour':family('primary_colour',['blue'])})
    text=CONTEXT_TEXTS[sid]+(' with casual style' if explicit_style else '')
    parsed=GeneralContextInterpreter('context_18_v1').interpret(text);assert parsed.status=='Supported'
    compare_rank(pool,saved,parsed.structured_request,compact,True,monkeypatch)

@pytest.mark.parametrize('composition',[('vest','trousers'),('vest','trousers','long_sleeve_outwear'),('vest_dress',),('vest_dress','long_sleeve_outwear')])
@pytest.mark.parametrize('relative',[False,True])
@pytest.mark.parametrize('compact',[False,True])
def test_four_structures_generic_and_relative_complete_differential(composition,relative,compact,monkeypatch):
    from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
    pool=tuple(make_member(str(i),'pattern','plain',category=c) for i,c in enumerate(composition))
    request=GeneralContextInterpreter('context_18_v1').interpret("I'm going shopping.").structured_request if relative else StructuredOutfitRequest()
    compare_rank(pool,snapshot({'pattern':family('pattern',['plain'])}),request,compact,relative,monkeypatch)

SUPPORTED=[v for v in CATALOG.values() if v['status']!='Blocked']

@pytest.mark.parametrize('domain',SUPPORTED,ids=lambda d:d['id'])
@pytest.mark.parametrize('relative',[False,True])
def test_every_supported_value_through_compact_conversion_and_warm_hits(domain,relative):
    axis,value=domain['axis'],domain['value'];item=member(axis,value)
    saved=snapshot({domain['family']:family(axis,[value],scope=domain['default_scope'])})
    old,new=paired_prepared(saved,[item]);role={'top':'upper','bottom':'lower','dress':'one_piece','outerwear':'outerwear'}[item.snapshot.structural_role]
    legacy=SimpleNamespace(preference=Measure(None,'NoPreferences'),preference_details=())
    expected=old.compact((item.snapshot,),(role,),(0,),legacy,relative=relative)
    for _ in range(3):
        actual=new.compact((item.snapshot,),(role,),(0,),legacy,relative=relative)
        assert actual.to_dict()==expected.to_dict() and actual.score==expected.score

@pytest.mark.parametrize('state',['owner','missing','stale','conflicting','malformed','unqualified_model'])
@pytest.mark.parametrize('masked',[False,True])
def test_source_states_and_hard_masks_preserve_raw_and_effective_records(state,masked):
    item=make_member('A','pattern','plain',state=state)
    kwargs={'conditions':condition('pattern','plain',q='all_present')} if masked else {}
    saved=snapshot({'pattern':family('pattern',['plain'])})
    old,new=paired_prepared(saved,[item],**kwargs)
    legacy=SimpleNamespace(preference=Measure(None,'NoPreferences'),preference_details=())
    for relative in (False,True,False):
        a=old.compact((item.snapshot,),('upper',),(0,),legacy,relative=relative)
        b=new.compact((item.snapshot,),('upper',),(0,),legacy,relative=relative)
        assert a.to_dict()==b.to_dict() and a.score==b.score
