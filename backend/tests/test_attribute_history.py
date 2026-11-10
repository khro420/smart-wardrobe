"""New immutable proof reader, with active policy/NLP/model access prohibited."""
from pathlib import Path
from types import SimpleNamespace
import copy
import pytest
from tests.test_attribute_candidate_selection import integrated_fixture,candidate
from tests.test_attribute_nlp import pipeline
from app.domain.value_objects.attribute_conditions import digest
from app.application.recommendation.attribute_selection_verifier import build_selection,validate_selection

WEARER=SimpleNamespace(account_id='owner-A',profile_id='00000000-0000-4000-8000-000000000002')
BASE='1'*64


@pytest.fixture
def captured(pipeline):
    query,prepared,independent=integrated_fixture()
    _,intent=pipeline.interpret('I want a cotton v-neck top.')
    collection=tuple(prepared.rows.values())
    # Explicit author fixture selection; never ask the selector for expected IDs.
    outfit=candidate(prepared.rows['U-match'],prepared.rows['L-cotton'])
    coverage={'structural_examined':4,'legacy_failed':0,'legacy_unknown':0,'attribute_failed':2,'attribute_unknown':1,'joint_passed':1}
    return build_selection(intent,collection,prepared,independent,outfit,coverage,BASE,WEARER)


def test_archived_description_read_uses_no_active_loader_or_nlp(captured,monkeypatch):
    from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
    from app.application.nlp.attribute_request_interpreter import AttributeRequestInterpreter
    from app.application.wardrobe.description_policy import DescriptionPolicy
    def forbidden(*args,**kwargs):raise AssertionError('Active loader/model/NLP forbidden for archived proof')
    monkeypatch.setattr(Path,'open',forbidden)
    monkeypatch.setattr(AttributeEvidencePolicy,'load',forbidden)
    monkeypatch.setattr(DescriptionPolicy,'load',forbidden)
    monkeypatch.setattr(AttributeRequestInterpreter,'parse',forbidden)
    restored=validate_selection(captured.to_dict(),'owner-A',WEARER.profile_id,BASE)
    assert restored.payload==captured.payload


@pytest.mark.parametrize('case',['source','policy','scope','wearer','condition','decision','unknown_field','version','counter'])
def test_corruption_is_visible_without_repair(captured,case):
    value=captured.to_dict();original=copy.deepcopy(value)
    if case=='source':value['selected_evidence'][0]['description']['fields']['material']['selected']['source_digest']='0'*64
    elif case=='policy':value['policy_snapshot']['model_sources']=[{'field':'material'}]
    elif case=='scope':value['attribute_scope_sha256']='0'*64
    elif case=='wearer':value['wearer_profile_id']='00000000-0000-4000-8000-000000000003'
    elif case=='condition':value['intent']['conditions']['groups'][0]['conditions'][0]['values']=['linen']
    elif case=='decision':value['decisions']['member_results'][0]['state']='Unknown'
    elif case=='unknown_field':value['extra']=True
    elif case=='version':value['version']='attribute-selection-evidence-99.0.0'
    else:value['coverage']['attribute_unknown']+=1
    # Recompute the outer integrity aid to exercise inner schema/scope/source
    # verification as well. This is not a claimed adversarial signature scheme.
    value['revision']=digest({**value,'revision':''})
    with pytest.raises((ValueError,TypeError,KeyError)):
        validate_selection(value,'owner-A',WEARER.profile_id,BASE)
    assert captured.to_dict()==original


def test_foreign_account_cannot_restore_owned_proof(captured):
    with pytest.raises(ValueError):validate_selection(captured.to_dict(),'foreign',WEARER.profile_id,BASE)
