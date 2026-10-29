"""Synthetic stratified examples, never independently reviewed fashion labels."""
import json
from pathlib import Path
from collections import Counter
import pytest
from tests.test_score_certificate_reuse import old
from tests.test_compact_exhaustive import oracle_records,signature
from tests.test_rule_based_compatibility import g,Preferences
from tests.test_structural_candidates import Query
from tests.test_preference_modelling import pref
from app.application.recommendation import compact_exhaustive_scorer as kernel
from app.application.recommendation.compact_scoring_facts import CompactScoringFacts
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.nlp.nlp_interpreter import NLPInterpreter
PLAN=json.loads((Path(__file__).parent/'fixtures/evidence_diversity.v1.json').read_text())
def small(name):
 seen=Counter();out=[]
 for r in PLAN['mixes'][name]:
  seen[r['category']]+=1
  if seen[r['category']]<=2:out.append(g(r['id'],r['category'],r['primary_colour'],r['style'],custom_tags=r['custom_tags']))
 return out
@pytest.mark.parametrize('name',list(PLAN['mixes']))
def test_frozen_categories_and_exact_structural_counts(name):
 rows=PLAN['mixes'][name];n=len(rows);counts=Counter(r['category'] for r in rows)
 assert len(counts)==13 and n in (100,200)
 assert (int(n*.4)**2+int(n*.1))*(1+int(n*.1))==(17710 if n==100 else 134820)
 assert any(r['style'] is None for r in rows) and any(r['style']==[] for r in rows)
 assert any(r['primary_colour'] is None for r in rows)
@pytest.mark.parametrize('name',['varied-200','missing-200'])
@pytest.mark.parametrize('case_name',['generic','style','colour','combined','suitability'])
@pytest.mark.parametrize('profile',[kernel.DEFERRED,kernel.EXPERIMENTAL])
def test_stratified_every_candidate_frozen_current_public_oracle(monkeypatch,name,case_name,profile):
 rows=small(name);preferences=tuple(pref(p['type'],p['values'],'1',identifier=str(i)) for i,p in enumerate(PLAN['preferences']))
 interpreted=NLPInterpreter().interpret(PLAN['requests'][case_name]);assert interpreted.status=='Supported'
 evaluator=SuitabilityRequestEvaluator if case_name=='suitability' else kernel.RequestConstraintEvaluator
 logs=[];signatures=[]
 for facts in (old.CompactScoringFacts,CompactScoringFacts):
  monkeypatch.setattr(kernel,'CompactScoringFacts',facts);audit=[]
  result=kernel.CompactExhaustiveScorer(Query(rows),Preferences(preferences),profile,evaluator_type=evaluator,audit=audit.append).rank('owner',interpreted.structured_request)
  assert result.complete
  logs.append(audit);signatures.append(signature(result))
 assert logs[0]==logs[1]==list(oracle_records(rows,interpreted.structured_request,preferences,profile,evaluator))
 assert signatures[0]==signatures[1]

