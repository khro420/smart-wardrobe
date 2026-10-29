"""J8 every-candidate frozen/current/public differential; no fashion labels."""
from dataclasses import replace
from pathlib import Path
import json,hashlib,importlib.util
import pytest
from tests.test_compact_exhaustive import oracle_records,signature
from tests.test_rule_based_compatibility import g,Preferences
from tests.test_structural_candidates import Query
from tests.test_preference_modelling import pref
from app.application.recommendation import compact_exhaustive_scorer as kernel
from app.application.recommendation.compact_scoring_facts import CompactScoringFacts
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest,GarmentCategoryConstraint
path=Path(__file__).parent/'fixtures/invariant_request_reference/compact_scoring_facts.py'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='612bf357c8f1c27edb6344297f4c45358f23546f212b29ebdedf1a263b7d3128'
spec=importlib.util.spec_from_file_location('j7_scoring_facts',path);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
VALUES=[('occasion',v) for v in ('campus','work','casual_outing','shopping','dinner','party','date','travel')]+[('formality',v) for v in ('casual','smart_casual')]
STATES=('allow','deny','absent','malformed','conflict','deny_unknown')

def rows_for(field,value,state,combined):
 other=('formality','casual') if field=='occasion' else ('occasion','campus')
 out=[]
 for i,(gid,category,colour,styles) in enumerate([('a','vest','blue',('vintage',)),('b','sling','white',('classic',)),('c','trousers','blue',('vintage','minimal')),('d','skirt',None,None),('e','vest_dress','blue',('vintage',)),('f','long_sleeve_outwear','red',())]):
  s=state if state!='deny_unknown' else 'deny' if i==0 else 'absent' if i==2 else 'allow'
  tag=f'rec:v1:{field}:{value}:';tags=['ordinary tag']
  if combined:tags.append(f'rec:v1:{other[0]}:{other[1]}:allow')
  if s in ('allow','deny'):tags.append(tag+s)
  if s=='malformed':tags.extend([tag+'allow',tag+'maybe'])
  if s=='conflict':tags.extend([tag+'allow',tag+'deny'])
  out.append(g(gid,category,colour,styles,custom_tags=tags))
 return out

@pytest.mark.parametrize('field,value',VALUES)
@pytest.mark.parametrize('state',STATES)
@pytest.mark.parametrize('combined',[False,True])
@pytest.mark.parametrize('profile',[kernel.DEFERRED,kernel.EXPERIMENTAL])
def test_all_values_states_complete_scores_and_winners(monkeypatch,field,value,state,combined,profile):
 rows=rows_for(field,value,state,combined);kwargs={field:value}
 if combined:kwargs.update(style='vintage',colours=('blue',),garment_categories=(GarmentCategoryConstraint('group','outerwear'),),**({'formality':'casual'} if field=='occasion' else {'occasion':'campus'}))
 request=StructuredOutfitRequest(**kwargs);preferences=(pref('colours',['blue'],'1'),pref('styles',['vintage'],'1',identifier='style'))
 logs=[];results=[]
 for implementation,garments in ((old.CompactScoringFacts,rows),(CompactScoringFacts,list(reversed(rows)))):
  monkeypatch.setattr(kernel,'CompactScoringFacts',implementation);audit=[]
  r=kernel.CompactExhaustiveScorer(Query(garments),Preferences(preferences),profile,evaluator_type=SuitabilityRequestEvaluator,audit=audit.append).rank('owner',request)
  assert r.complete;logs.append(audit);results.append(signature(r))
 oracle=list(oracle_records(rows,request,preferences,profile,SuitabilityRequestEvaluator))
 assert logs[0]==logs[1]==oracle and results[0]==results[1]

@pytest.mark.parametrize('field,value',[('occasion','exercise'),('formality','formal')])
def test_unavailable_values_still_unavailable(field,value):
 r=kernel.CompactExhaustiveScorer(Query(rows_for('occasion','campus','allow',False)),Preferences(),evaluator_type=SuitabilityRequestEvaluator).rank('owner',StructuredOutfitRequest(**{field:value}))
 assert r.status=='PolicyUnavailable'

def test_changed_declarations_start_fresh_session(monkeypatch):
 request=StructuredOutfitRequest(occasion='campus');before=rows_for('occasion','campus','allow',False)
 for rows in (before,[replace(g,custom_tags=('rec:v1:occasion:campus:deny',)) for g in before],before):
  records=[]
  for implementation in (old.CompactScoringFacts,CompactScoringFacts):
   monkeypatch.setattr(kernel,'CompactScoringFacts',implementation);audit=[]
   result=kernel.CompactExhaustiveScorer(Query(rows),Preferences(),evaluator_type=SuitabilityRequestEvaluator,audit=audit.append).rank('owner',request)
   records.append((signature(result),audit))
  assert records[0]==records[1]
