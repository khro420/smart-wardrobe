"""Mutation checks prove the independent evaluation checker rejects invalid evidence."""
import ast
import copy
import json
from pathlib import Path
import pytest
from tests.final_evaluation_auditor import audit

ROOT=Path(__file__).resolve().parents[2]
CASES=ROOT/'storage/verification/phase5f2e3j15/initial-cases'

def load(name='D01'):
    return json.loads((CASES/(name+'.json')).read_text())

@pytest.mark.parametrize('case',['D01','P01','S19','S23','S24','S26','S27','S28','S29','S30'])
def test_valid_retained_results_pass(case):
    result=audit(load(case))
    assert result['generated'] and result['pass'],result['errors']

@pytest.mark.parametrize('change',['foreign','archived','unconfirmed','wrong_job_owner','missing_member','query_origin','score','weight','provenance','snapshot','receipt','extra_write','mandatory_deny'])
def test_corrupt_evidence_cannot_pass(change):
    row=load();first=row['result']['items'][0]['garment_id']
    garment=next(g for g in row['wardrobe_before'] if g['id']==first)
    if change=='foreign':garment['user_id']='foreign'
    elif change=='archived':garment['status']='archived'
    elif change=='unconfirmed':garment['evidence_review_status']='accepted'
    elif change=='wrong_job_owner':garment['evidence_job_owner']='foreign'
    elif change=='missing_member':row['result']['items'][0]['garment_id']='absent'
    elif change=='query_origin':row['query_observations']=[]
    elif change=='score':row['result']['score_metadata']['total']={'numerator':0,'denominator':1}
    elif change=='weight':row['result']['score_metadata']['weights'][0]={'numerator':1,'denominator':1}
    elif change=='provenance':row['result']['provenance']['scoring_profile']='compatibility_deferred'
    elif change=='snapshot':row['persisted']['snapshots'][0]['display_json']='{}'
    elif change=='receipt':row['persisted']['receipt']['recommendation_id']='foreign'
    elif change=='extra_write':row['counts_after']['recommendations']+=1
    else:garment['custom_tags']='["rec:v1:occasion:campus:deny"]'
    assert not audit(row)['pass']

def test_equal_score_wrong_stable_id_rejected():
    row=load('S30')
    replacement=copy.deepcopy(row['result']['items'][0]);replacement['garment_id']='j15-S30-b'
    row['result']['items']=[replacement]
    assert 'winner_or_tie_break' in audit(row)['errors']

def test_checker_imports_no_application_calculator():
    tree=ast.parse((ROOT/'backend/tests/final_evaluation_auditor.py').read_text())
    assert not any(isinstance(n,ast.ImportFrom) and (n.module or '').startswith('app') for n in ast.walk(tree))

def test_frozen_mismatches_are_retained_as_failures():
    for name in ['S07','S15']:
        row=load(name)
        assert row['case']['intent']=='Supported' and row['actual_intent']=='UnsupportedRequest'
        assert not audit(row)['pass']
