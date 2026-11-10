"""Adversarial immutable-key and lifecycle boundaries; original B2 is the oracle."""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
from types import SimpleNamespace
import sqlite3
import pytest
from tests.test_p2_performance_equivalence import paired_prepared,frozen_modules
from tests.test_p2_preference_selection import snapshot,family,EMPTY
from tests.test_attribute_qualification import make_member
from app.application.recommendation.attribute_preference_preparation import PreparedAttributePreferences
from app.domain.value_objects.compact_recommendation import CompactScore,Measure
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest

WEIGHTS=(F(3,5),F(1,5),F(1,5))

def setup_numeric():
    from app.application.recommendation.compact_scoring_facts import CompactScoringFacts
    from app.application.recommendation.rule_based_compatibility_policy import RuleBasedCompatibilityPolicy
    pool=tuple(make_member(g,'pattern','plain',category=c) for g,c in (('A','vest'),('B','vest'),('L','trousers')))
    saved=snapshot({'pattern':family('pattern',['plain'])})
    prepared=PreparedAttributePreferences(saved,pool)
    garments=tuple(i.snapshot for i in pool)
    facts=CompactScoringFacts(garments,StructuredOutfitRequest(),prepared.composed.legacy,RuleBasedCompatibilityPolicy.load(),WEIGHTS,True,19900,256)
    base=facts.score(('upper','lower'),(0,2))
    return pool,saved,garments,base

class NumericProducer:
    """Already-validated original numeric collaborator; not an eligibility gate."""
    def __init__(self,value):self.value=value;self.calls=0
    def score(self,*args):self.calls+=1;return self.value
    @property
    def cache_info(self):return {'calls':self.calls}

def change(base,**kwargs):
    value=base._replace(**kwargs)
    return value._replace(total=sum((w*v for w,v in zip(WEIGHTS,value.contributions)),F()))

def test_complete_original_input_perturbations_never_alias_equal_totals():
    from app.application.recommendation.attribute_preference_relative_facts import P2CompactFacts
    pool,saved,garments,base=setup_numeric();oldprep,newprep=paired_prepared(saved,pool)
    _,oldfacts=frozen_modules();a=NumericProducer(base);b=NumericProducer(base)
    old=oldfacts.P2CompactFacts(a,oldprep,garments);new=P2CompactFacts(b,newprep,garments)
    variants=[base,
        change(base,request=Measure(F(1),'Available',1,1),request_details=(Measure(F(1),'Available',1,1),)),
        change(base,request=Measure(F(1),'Partial',0,1),request_details=(Measure(F(1),'Partial',0,1),)),
        change(base,request=Measure(F(1),'Available',2,2),request_details=(Measure(F(1),'Available',2,2),)),
        change(base,request=Measure(F(1,3),'Available',1,1),request_details=(Measure(F(1,3),'Available',1,1),)),
        change(base,request=Measure(F(123456789012345678901,10**45+7),'Available',1,1)),
        change(base,preference=Measure(None,'Unknown',0,2)),
        change(base,preference=Measure(None,'NoSupportedPreferences'))]
    for i,value in enumerate((*variants,*reversed(variants))):
        a.value=b.value=value;indexes=(i%2,2)
        assert new.score(('upper','lower'),indexes)==old.score(('upper','lower'),indexes)
    assert a.calls==b.calls==len(variants)*2

def test_bounded_eviction_and_return_to_an_evicted_exact_input():
    from app.application.recommendation.attribute_preference_relative_facts import P2CompactFacts
    pool,saved,garments,base=setup_numeric();oldprep,newprep=paired_prepared(saved,pool)
    _,oldfacts=frozen_modules();a=NumericProducer(base);b=NumericProducer(base)
    old=oldfacts.P2CompactFacts(a,oldprep,garments);new=P2CompactFacts(b,newprep,garments)
    for i,n in enumerate((*range(350),*range(349,-1,-1),0,349)):
        a.value=b.value=change(base,request=Measure(F(n,349),'Available',1,1),request_details=(Measure(F(n,349),'Available',1,1),))
        assert new.score(('upper','lower'),(i%2,2))==old.score(('upper','lower'),(i%2,2))
        if hasattr(newprep,'reuse_cache_info'):assert newprep.reuse_cache_info['entries']<=256
        assert len(newprep._cache)<=256
    if hasattr(newprep,'reuse_cache_info'):assert newprep.reuse_cache_info['evictions']>0

@pytest.mark.parametrize('legacy',[Measure(F(1),'Available',1,1),Measure(F(1),'Partial',0,1),Measure(None,'Unknown',0,1),Measure(None,'NoPreferences')])
def test_legacy_summary_metadata_preserved_before_and_after_warm_hits(legacy):
    pool,saved,garments,base=setup_numeric();old,new=paired_prepared(saved,pool)
    value=SimpleNamespace(preference=legacy,preference_details=())
    expected=old.compact(garments,('upper','lower'),(0,2),value).to_dict()
    for _ in range(3):assert new.compact(garments,('upper','lower'),(0,2),value).to_dict()==expected

@pytest.mark.parametrize('invalid',[Measure(1,'Available',1,1),Measure(F(1),'Available',True,1),Measure(F(1),'Available',1,True)])
def test_type_equal_but_invalid_legacy_summary_cannot_hit_a_valid_cache_entry(invalid):
    pool,saved,garments,base=setup_numeric();old,new=paired_prepared(saved,pool)
    good=SimpleNamespace(preference=Measure(F(1),'Available',1,1),preference_details=())
    new.compact(garments,('upper','lower'),(0,2),good)
    bad=SimpleNamespace(preference=invalid,preference_details=())
    for prepared in (old,new):
        with pytest.raises(ValueError):prepared.compact(garments,('upper','lower'),(0,2),bad)

def test_request_objective_binding_and_wearer_isolation_do_not_reuse_old_projection():
    from app.application.recommendation.context_relevance_policy import ContextRelevancePolicy
    from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
    pool=(make_member('A','style','casual'),)
    saved=snapshot({'styles':family('style',['casual'],scope='base')})
    old,new=paired_prepared(saved,pool)
    legacy=SimpleNamespace(preference=Measure(None,'NoPreferences'),preference_details=())
    request=GeneralContextInterpreter('context_18_v1').interpret("I'm going shopping.").structured_request
    objective=ContextRelevancePolicy.load(bundle_id='context_18_v1').resolve(request).objective
    for p in (old,new):
        assert p.compact((pool[0].snapshot,),('upper',),(0,),legacy,relative=True).score.contribution==1
        p.bind_request(request);p.bind_objective(objective)
        assert p.compact((pool[0].snapshot,),('upper',),(0,),legacy,relative=True).score.contribution==0
        p.bind_request(request);p.bind_objective(objective)
        with pytest.raises(ValueError):p.bind_request(StructuredOutfitRequest())
    a=PreparedAttributePreferences(snapshot({'colour':family('primary_colour',['blue'])}),pool)
    b=PreparedAttributePreferences(snapshot({'colour':family('primary_colour',['green'])},wearer='00000000-0000-4000-8000-000000000002'),pool)
    assert a.compact((pool[0].snapshot,),('upper',),(0,),legacy).score.contribution==1
    assert b.compact((pool[0].snapshot,),('upper',),(0,),legacy).score.contribution==0
    assert a._member_classes['A']==b._member_classes['A']==0

@pytest.mark.parametrize('members',[(),(('upper','missing'),),(('upper','A'),('lower','A')),(('shoe','A'),)])
def test_member_permission_checks_still_run_after_a_hit(members):
    pool,saved,garments,base=setup_numeric();old,new=paired_prepared(saved,pool)
    for p in (old,new):
        p.evaluate((('upper','A'),),EMPTY)
        with pytest.raises(ValueError):p.evaluate(members,EMPTY)

def test_warm_certificate_path_does_not_perform_source_or_normalization_IO(monkeypatch):
    from app.application.recommendation.attribute_preference_relative_facts import P2CompactFacts
    from app.application.recommendation.preference_normalizer import PreferenceNormalizer
    from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
    pool,saved,garments,base=setup_numeric();p=PreparedAttributePreferences(saved,pool);source=NumericProducer(base);facts=P2CompactFacts(source,p,garments)
    expected=facts.score(('upper','lower'),(0,2))
    def forbidden(*args,**kwargs):raise AssertionError('IO/normalization in numeric enumeration')
    monkeypatch.setattr(Path,'open',forbidden);monkeypatch.setattr(sqlite3,'connect',forbidden)
    monkeypatch.setattr(PreferenceNormalizer,'normalize',forbidden);monkeypatch.setattr(AttributeEvidencePolicy,'fact',forbidden)
    for i in range(100):assert facts.score(('upper','lower'),(i%2,2))==expected
    assert source.calls==100

def test_repeated_equal_numeric_inputs_reuse_validated_certificates(monkeypatch):
    # This test is deliberately red on certified B2 before optimisation. It
    # requires reuse, not a changed numerical answer or skipped source fetch.
    import app.application.recommendation.attribute_preference_relative_facts as module
    pool,saved,garments,base=setup_numeric();p=PreparedAttributePreferences(saved,pool);source=NumericProducer(base)
    calls=[];original=module.validate_total
    def validate(*args):calls.append(1);return original(*args)
    monkeypatch.setattr(module,'validate_total',validate)
    facts=module.P2CompactFacts(source,p,garments)
    first=facts.score(('upper','lower'),(0,2))
    for i in range(1,100):assert facts.score(('upper','lower'),(i%2,2))==first
    assert source.calls==100
    assert len(calls)<=4,'Immutable numeric certificate was rebuilt for every candidate'
