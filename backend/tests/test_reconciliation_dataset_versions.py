"""Versioned data compatibility without altering any archived schema or label."""
from dataclasses import replace
from pathlib import Path
import copy,json
import jsonschema
import pytest
from app.shared_contracts.offline_snapshot_codec import decode_snapshot,encode_snapshot,legacy_projection
from app.domain.value_objects.saved_attribute_evidence import SavedAttributeEvidence
from app.domain.value_objects.contextual_garment_evidence import ContextualGarmentEvidence
from app.domain.value_objects.general_context_evidence import AppearanceEvidence
from tests.test_compatibility_evidence_dataset import populated
from tests.test_structural_candidates import garment
from scripts.compatibility_evidence_dataset import validate,import_bundle

ROOT=Path(__file__).resolve().parents[2]


def schema(version):return json.loads((ROOT/f'docs/datasets/compatibility_reviews.schema.v{version}.json').read_text())


def test_original_v1_data_and_schema_remain_valid_and_closed():
    raw=populated();before=copy.deepcopy(raw)
    jsonschema.validate(raw,schema(1));assert validate(raw,True)==before
    member=raw['records'][0]['garments'][0]
    member['snapshot']['saved_attribute_evidence']={'state':'Absent'}
    with pytest.raises(jsonschema.ValidationError):jsonschema.validate(raw,schema(1))
    with pytest.raises(ValueError):validate(raw,True)


@pytest.mark.parametrize('state',['Absent','Known','Malformed','Stale'])
def test_v2_immutable_roundtrip_preserves_explicit_source_state(state):
    snapshot=replace(garment('example','vest_dress'),saved_attribute_evidence=SavedAttributeEvidence(state=state))
    raw=encode_snapshot(snapshot)
    restored=decode_snapshot(raw,'2.0.0')
    assert restored==snapshot and type(restored.saved_attribute_evidence) is SavedAttributeEvidence
    assert raw['saved_attribute_evidence']['state']==state


def test_explicit_current_review_version_keeps_zero_and_source_bytes():
    raw=populated();raw['schema_version']='compatibility-evidence-2.0.0'
    for member in raw['records'][0]['garments']:
        member['snapshot']=encode_snapshot(decode_snapshot(member['snapshot'],'1.0.0'))
    before=copy.deepcopy(raw)
    jsonschema.Draft202012Validator.check_schema(schema(2))
    jsonschema.validate(raw,schema(2))
    result=import_bundle(raw,True)
    assert raw==before and result['dataset']==before
    assert result['schema_version']=='compatibility-evidence-2.0.0'
    assert result['policy']['references'][0]['normalized_value']=={'numerator':0,'denominator':4}
    assert result['activation_approved'] is False


@pytest.mark.parametrize('kind',['saved','appearance','contextual'])
def test_legacy_projection_refuses_any_nondefault_evidence(kind):
    values={'saved':{'saved_attribute_evidence':SavedAttributeEvidence('Malformed')},'appearance':{'appearance_evidence':AppearanceEvidence('Malformed')},'contextual':{'contextual_suitability':ContextualGarmentEvidence('Malformed')}}
    with pytest.raises(ValueError,match='discard'):legacy_projection(replace(garment('example','vest_dress'),**values[kind]))


def test_legacy_projection_retains_both_views_and_hashes_without_mutation():
    snapshot=garment('example','vest_dress');projection=legacy_projection(snapshot)
    assert projection['contract']=='offline-snapshot-legacy-projection-1.0.0'
    assert 'saved_attribute_evidence' in projection['source']
    assert 'saved_attribute_evidence' not in projection['snapshot']
    assert projection['source_sha256']!=projection['projection_sha256']
    assert encode_snapshot(snapshot)==projection['source']
    assert decode_snapshot(projection['snapshot'],'1.0.0')==snapshot


@pytest.mark.parametrize('mutation',['version','unknown_field','unknown_evidence_field','mutable_feature','wrong_state','nonfinite'])
def test_invalid_current_inputs_are_not_repaired(mutation):
    raw=encode_snapshot(garment('example','vest_dress'));version='2.0.0'
    if mutation=='version':version='3.0.0'
    elif mutation=='unknown_field':raw['invented']=True
    elif mutation=='unknown_evidence_field':raw['saved_attribute_evidence']['confidence']=1
    elif mutation=='mutable_feature':raw['appearance_evidence']['features']=[{'collared_neckline':True}]
    elif mutation=='wrong_state':raw['saved_attribute_evidence']['state']='Verified'
    else:raw['colour_palette']=[{'hex_value':'#000000','coverage':float('nan')}]
    with pytest.raises((ValueError,TypeError)):decode_snapshot(raw,version)


def test_new_evaluation_schema_and_both_explicit_reader_versions(tmp_path):
    from tests.test_holistic_ranking import fixture_cases,policy
    from scripts.evaluate_compatibility import load_cases,evaluate
    path,profiles=fixture_cases(tmp_path);raw=json.loads(path.read_text())
    for case in raw['cases']:
        case['wardrobe']=[encode_snapshot(decode_snapshot(g,'1.0.0')) for g in case['wardrobe']]
    raw['schema_version']='2.0.0'
    evaluation_schema=json.loads((ROOT/'docs/datasets/compatibility_evaluation_cases.schema.v2.json').read_text())
    jsonschema.Draft202012Validator.check_schema(evaluation_schema);jsonschema.validate(raw,evaluation_schema)
    path.write_text(json.dumps(raw))
    assert load_cases(path,True,policy())[0]==raw
    result=evaluate(case_path=path,profile_path=profiles,allow_synthetic=True)
    assert result['evaluated_case_count']==1 and result['fashion_accuracy'] is None


def test_original_v1_evaluation_preserves_omitted_structural_defaults(tmp_path):
    from tests.test_holistic_ranking import fixture_cases
    from scripts.evaluate_compatibility import evaluate
    path,profiles=fixture_cases(tmp_path);raw=json.loads(path.read_text())
    for case in raw['cases']:
        for member in case['wardrobe']:
            member.pop('structural_role');member.pop('layering_index')
    path.write_text(json.dumps(raw));before=path.read_bytes()
    result=evaluate(case_path=path,profile_path=profiles,allow_synthetic=True)
    assert path.read_bytes()==before and result['evaluated_case_count']==1
    assert result['cases'][0]['results'][0]['status']=='NoEligibleGarments'
    assert result['cases'][0]['results'][0]['winner_key'] is None
