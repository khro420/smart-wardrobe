"""Independent owner matrix and actual disposable source capture."""
import json
from pathlib import Path
import pytest
from tests.test_conversational_history import language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.wardrobe import wearer_category_service as service
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE

SPEC=json.loads((Path(__file__).parent/'fixtures/wearer_category_acceptance.v1.json').read_text())

def set_gender(client,wearer,gender):
    path=f'/api/v1/account/wardrobe-profiles/{wearer}/details';headers={'X-Wardrobe-Profile-Id':wearer}
    current=client.get(path,headers=headers);assert current.status_code==200
    result=client.put(path,headers=headers,json={'version':'wearer-profile-details-1.0.0','expected_revision':current.json()['revision'],'gender_identity':gender});assert result.status_code==200,result.text
    return result.json()

@pytest.fixture
def category_api(language_api,monkeypatch):
    client,wearer=language_api
    set_gender(client,wearer,'male')
    female=client.post('/api/v1/account/wardrobe-profiles',json={'name':'Policy female'}).json()['id'];set_gender(client,female,'female')
    monkeypatch.setenv(service.ENVIRONMENT_KEY,service.PROFILE);configure_local_workflow()
    return client,wearer,female

@pytest.mark.parametrize('gender',['male','female'])
@pytest.mark.parametrize('category',list(GARMENT_STRUCTURE))
def test_complete_independent_matrix(gender,category):
    selected=json.loads(service.configure(service.PROFILE))
    assert (service.decision(category,gender,selected)=='Permit')==SPEC['matrix'][gender][category]

def test_unknown_version_resource_and_category_fail_closed(tmp_path):
    with pytest.raises(ValueError):service.configure('unknown')
    selected=json.loads(service.configure(service.PROFILE));assert service.decision('unknown','female',selected)=='Unknown'
    assert service.effective_category({'category':'trousers','attributes_json':'{"reviewed_category":"skirt"}'}) is None

def test_shared_source_and_unconfigured_profile(category_api):
    client,male,female=category_api
    before=client.get('/api/v1/wardrobe/garments').json()
    male_view=client.get(f'/api/v1/account/wardrobe-profiles/{male}/category-eligibility').json()
    assert male_view['configured'] and len(male_view['allowed_categories'])==8
    female_view=client.get(f'/api/v1/account/wardrobe-profiles/{female}/category-eligibility',headers={'X-Wardrobe-Profile-Id':female}).json();assert len(female_view['allowed_categories'])==13
    set_gender(client,male,None)
    current=client.get(f'/api/v1/account/wardrobe-profiles/{male}/category-eligibility').json();assert not current['configured'] and not current['allowed_categories']
    assert client.get('/api/v1/wardrobe/garments').json()==before


def test_tampered_pinned_matrix_refused(tmp_path,monkeypatch):
    from app.domain.value_objects.wearer_category_eligibility import validate_policy
    raw=json.loads(service.configure(service.PROFILE));raw['allowed']['male'].append('skirt')
    with pytest.raises(ValueError):validate_policy(raw)
    resource=tmp_path/'tampered.json';resource.write_bytes(service.RESOURCE.read_bytes()+b' ')
    monkeypatch.setattr(service,'RESOURCE',resource)
    with pytest.raises(ValueError,match='Unregistered'):service.configure(service.PROFILE)


def test_full_account_capacity_is_checked_before_wearer_filter(category_api,monkeypatch):
    from types import SimpleNamespace
    from fastapi import HTTPException
    client,male,_=category_api
    monkeypatch.setattr(service,'transaction_garment_query',lambda conn:SimpleNamespace(get_confirmed_available_garments=lambda owner:tuple(range(101))))
    with pytest.raises(HTTPException) as error:service.capture('style-owner',male)
    assert error.value.detail['code']=='WardrobeCapacityExceeded'


def test_foreign_header_archived_and_custom_scope_refuse(category_api):
    client,male,female=category_api
    mismatch=client.get(f'/api/v1/account/wardrobe-profiles/{male}/category-eligibility',headers={'X-Wardrobe-Profile-Id':female});assert mismatch.status_code==409
    foreign=client.get('/api/v1/account/wardrobe-profiles/not-owned/category-eligibility',headers={'X-Wardrobe-Profile-Id':'not-owned'});assert foreign.status_code in (404,422)
    set_gender(client,male,'custom');assert client.get(f'/api/v1/account/wardrobe-profiles/{male}/category-eligibility').json()['configured'] is False
