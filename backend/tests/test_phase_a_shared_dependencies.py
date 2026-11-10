"""Approved A01-A04: shared graph protection and origin preservation."""
import pytest
from tests.test_recommendation_refinement_integration import (
    refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,
    wardrobe,submit as legacy_submit,
)
from app.infrastructure.persistence import postgresql_repository as db

def submit(client):
    import uuid
    response=client.post('/api/v1/recommendations?pipeline=integrated',json={
        'request_text':"I'm going shopping.",'submission_key':uuid.uuid4().hex,
        'wearer_profile_id':client.headers['X-Wardrobe-Profile-Id']})
    return response,response.json()



@pytest.mark.parametrize('legacy',[False,True],ids=['shared-null','legacy-origin'])
def test_shared_dependencies_and_archive_policy(refinement_api,legacy):
    client,_=refinement_api
    a=client.get('/api/v1/account/wardrobe-profiles').json()[0]['id']
    b=client.post('/api/v1/account/wardrobe-profiles',json={'name':'Other wearer'}).json()['id']
    client.headers['X-Wardrobe-Profile-Id']=a;ids=wardrobe(client)
    response,root=submit(client);assert response.status_code==201,root
    response=client.post('/api/v1/recommendations/'+root['id']+'/save-as-outfit',json={'name':'Shared complete outfit'})
    assert response.status_code==201;oid=response.json()['id']
    if legacy:
        with db.connection() as conn:
            conn.execute('UPDATE garments SET profile_id=? WHERE id=?',(a,ids['Blue T-shirt']))
            conn.execute('UPDATE outfits SET profile_id=? WHERE id=?',(a,oid))
    client.headers['X-Wardrobe-Profile-Id']=b
    deps=client.get('/api/v1/wardrobe/garments/'+ids['Blue T-shirt']+'/dependencies')
    assert deps.status_code==200 and [o['id'] for o in deps.json()['active_outfits']]==[oid]
    assert not deps.json()['can_archive']
    assert client.delete('/api/v1/wardrobe/garments/'+ids['Blue T-shirt']).status_code==409
    assert client.get('/api/v1/wardrobe/outfits/'+oid+'/dependencies').status_code==200
    assert client.delete('/api/v1/wardrobe/outfits/'+oid).status_code==204
    assert client.delete('/api/v1/wardrobe/garments/'+ids['Blue T-shirt']).status_code==204


def test_initializer_does_not_erase_existing_origin(refinement_api):
    client,_=refinement_api
    profile=client.get('/api/v1/account/wardrobe-profiles').json()[0]['id']
    ids=wardrobe(client)
    response=client.post('/api/v1/wardrobe/outfits',json={'name':'Origin outfit','garment_ids':[ids['Blue T-shirt'],ids['Blue Jeans']]})
    assert response.status_code==201;oid=response.json()['id']
    with db.connection() as conn:
        conn.execute('UPDATE garments SET profile_id=? WHERE id=?',(profile,ids['Blue T-shirt']))
        conn.execute('UPDATE outfits SET profile_id=? WHERE id=?',(profile,oid))
    db.initialise_database()  # This fixture owns a disposable database only.
    with db.connection() as conn:
        assert conn.execute('SELECT profile_id FROM garments WHERE id=?',(ids['Blue T-shirt'],)).fetchone()[0]==profile
        assert conn.execute('SELECT profile_id FROM outfits WHERE id=?',(oid,)).fetchone()[0]==profile
        assert conn.execute('SELECT profile_id FROM garments WHERE id=?',(ids['Blue Jeans'],)).fetchone()[0] is None
