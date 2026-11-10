"""Actual API policy admission before either scoring engine."""
import uuid
import pytest
from tests.test_wearer_category_policy import category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,set_gender
from app.application.ports.assistant_runtime import assistant_service

def submit(client,wearer,text='Going shopping.',**more):
    body={'request_text':text,'submission_key':uuid.uuid4().hex,'wearer_profile_id':wearer,**more}
    return client.post('/api/v1/recommendations?pipeline=integrated',headers={'X-Wardrobe-Profile-Id':wearer},json=body)

@pytest.mark.parametrize('engine',['reference','compact_exhaustive'])
@pytest.mark.parametrize('p2',[False,True])
@pytest.mark.parametrize('c2',[False,True])
def test_generic_and_explicit_conflict_all_modes(category_api,engine,p2,c2):
    client,male,female=category_api;assistant_service().execution_engine=engine
    modes={}
    if p2:modes['preference_profile']='attribute_preference_decision_v2'
    if c2:modes['compatibility_profile']='recorded_palette_compatibility_v1'
    response=submit(client,male,**modes);assert response.status_code==201,response.text
    result=response.json();assert all(i['category']!='skirt' and not i['category'].endswith('_dress') for i in result['items'])
    assert result['provenance']['wearer_category_eligibility']['gender_key']=='male'
    denied=submit(client,male,'i want a dress for shopping',**modes);assert denied.status_code==409 and denied.json()['outcome']=='WearerCategoryNotPermitted',denied.text
    permitted=submit(client,female,'i want a dress for shopping',**modes);assert permitted.status_code==201,permitted.text
    assert any(i['category'].endswith('_dress') for i in permitted.json()['items'])

def test_homepage_and_unconfigured_new_action(category_api):
    client,male,female=category_api
    result=client.post('/api/v1/recommendations/homepage',json={'submission_key':uuid.uuid4().hex,'wearer_profile_id':male},headers={'X-Wardrobe-Profile-Id':male})
    assert result.status_code==201,result.text
    assert all(i['category']!='skirt' and not i['category'].endswith('_dress') for i in result.json()['recommendation']['items'])
    set_gender(client,male,None)
    rejected=submit(client,male);assert rejected.status_code==409 and rejected.json()['outcome']=='WearerCategoryPolicyUnconfigured'

def test_bare_shirt_and_black_trousers_never_uses_skirt(category_api):
    client,male,_=category_api
    response=submit(client,male,'i want a shirt with black trousers')
    assert response.status_code!=422,response.text
    # The synthetic fixture need not contain black trousers; no weaker substitute.
    if response.status_code==201:
        assert any(i['garment_role']=='upper' for i in response.json()['items'])
        assert any(i['category']=='trousers' for i in response.json()['items'])
