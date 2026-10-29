"""J9 frozen populations, actual structural enumeration and small public oracle."""
import json
from collections import Counter
from pathlib import Path
import pytest
from tests.test_compact_exhaustive import oracle_records, signature, reference
from tests.test_rule_based_compatibility import g, Preferences
from tests.test_structural_candidates import Query
from tests.test_preference_modelling import pref
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.application.recommendation.recommendation_engine import RecommendationEngine
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.nlp.nlp_interpreter import NLPInterpreter

PLAN=json.loads((Path(__file__).parent/'fixtures/capacity_150.v1.json').read_text())


def population(name, small=False):
    seen=Counter(); rows=[]
    for r in PLAN['mixes'][name]:
        seen[r['category']]+=1
        if small and seen[r['category']]>1: continue
        rows.append(g(r['id'],r['category'],r['primary_colour'],r['style'],custom_tags=r['custom_tags']))
    return rows


@pytest.mark.parametrize('name',PLAN['mixes'])
def test_actual_complete_structural_population(name):
    rows=population(name)
    assert len(rows)==len({r.garment_id for r in rows})==150
    assert any(r.primary_colour is None for r in rows)
    assert any(r.style_tags is None for r in rows)
    assert any(r.style_tags==() for r in rows)
    session=RecommendationEngine(Query(rows)).generate_homepage_candidates('owner')
    counts=Counter(tuple(m.role for m in candidate.members) for candidate in session)
    expected={('upper','lower'):3600,('upper','lower','outerwear'):54000,('one_piece',):15,('one_piece','outerwear'):225} if name=='balanced-150' else {('upper','lower'):2500,('upper','lower','outerwear'):125000}
    assert dict(counts)==expected
    assert sum(counts.values())==PLAN['expected_structural'][name]


@pytest.mark.parametrize('cell',PLAN['schedule'])
def test_small_population_every_candidate_public_oracle(cell):
    rows=population(cell['workload'],small=True)
    preferences=tuple(pref(p['type'],p['values'],'1',identifier=str(i)) for i,p in enumerate(PLAN['preferences']))
    interpreted=NLPInterpreter().interpret(PLAN['requests'][cell['request']])
    assert interpreted.status=='Supported'
    if cell['suitability']:
        assert interpreted.structured_request.occasion=='campus'
        assert interpreted.structured_request.formality=='casual'
    evaluator=SuitabilityRequestEvaluator if cell['suitability'] else RequestConstraintEvaluator
    audit=[]
    actual=CompactExhaustiveScorer(Query(rows),Preferences(preferences),cell['profile'],evaluator_type=evaluator,audit=audit.append).rank('owner',interpreted.structured_request)
    assert actual.complete and actual.status=='Selected'
    assert audit==list(oracle_records(rows,interpreted.structured_request,preferences,cell['profile'],evaluator))
    assert signature(actual)==signature(reference(rows,interpreted.structured_request,preferences,cell['profile'],evaluator))
