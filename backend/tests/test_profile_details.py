"""Disposable authenticated profile details; no demo-data writes from pytest."""
import pytest
from tests.test_conversational_history import language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle
from app.infrastructure.persistence import postgresql_repository as db

def body(revision,gender):return {'version':'wearer-profile-details-1.0.0','expected_revision':revision,'gender_identity':gender}

def test_details_read_no_create_cas_validation_and_ownership(language_api):
    client,wearer=language_api;path=f'/api/v1/account/wardrobe-profiles/{wearer}/details'
    with db.connection() as c:
        before=c.execute('SELECT count(*) FROM wardrobe_profile_details_v1').fetchone()[0]
        old_columns=tuple(r[1] for r in c.execute('PRAGMA table_info(wardrobe_profiles)'))
    first=client.get(path);assert first.status_code==200;first=first.json()
    assert first['gender_identity'] is None and first['updated_at'] is None
    with db.connection() as c:assert c.execute('SELECT count(*) FROM wardrobe_profile_details_v1').fetchone()[0]==before
    changed=client.put(path,json=body(first['revision'],'male'));assert changed.status_code==200
    assert client.put(path,json=body(first['revision'],'female')).status_code==409
    for value in ['', ' male', 'x'*61,12,'a\nname','e\u0301']:
        assert client.put(path,json=body(changed.json()['revision'],value)).status_code==422
    for mutation in [{'version':'unknown'},{'extra':'forbidden'}]:
        assert client.put(path,json={**body(changed.json()['revision'],'female'),**mutation}).status_code==422
    foreign=client.get('/api/v1/account/wardrobe-profiles/not-owned/details');assert foreign.status_code==404
    assert client.get(path,headers={'X-Wardrobe-Profile-Id':'wrong'}).status_code==409
    assert client.put(path,json=body(changed.json()['revision'],None),headers={'X-Wardrobe-Profile-Id':'wrong'}).status_code==409
    cleared=client.put(path,json=body(changed.json()['revision'],None));assert cleared.status_code==200 and cleared.json()['gender_identity'] is None
    with db.connection() as c:assert tuple(r[1] for r in c.execute('PRAGMA table_info(wardrobe_profiles)'))==old_columns and len(old_columns)==7

def test_gender_metadata_does_not_change_ranking_or_old_history(language_api):
    from tests.test_b3_palette_integration import submit
    client,wearer=language_api;path=f'/api/v1/account/wardrobe-profiles/{wearer}/details'
    _,before=submit(client,wearer,'Going shopping.');history=client.get('/api/v1/chats/'+before['chat_id']).json()
    ids={g['id'] for g in client.get('/api/v1/wardrobe/garments').json()}
    for gender in ['male','female','Nonbinary',None]:
        current=client.get(path).json();assert client.put(path,json=body(current['revision'],gender)).status_code==200
        response,after=submit(client,wearer,'Going shopping.');assert response.status_code==201
        assert [i['garment_id'] for i in before['items']]==[i['garment_id'] for i in after['items']]
        for k in ['request_match_score','compatibility_score','preference_score','total_score']:assert before[k]==after[k]
        assert {g['id'] for g in client.get('/api/v1/wardrobe/garments').json()}==ids
        assert client.get('/api/v1/chats/'+before['chat_id']).json()==history

def test_archived_profile_details_read_only(language_api):
    client,wearer=language_api
    other=client.post('/api/v1/account/wardrobe-profiles',json={'name':'Archive details case'}).json()['id']
    path=f'/api/v1/account/wardrobe-profiles/{other}/details';headers={'X-Wardrobe-Profile-Id':other}
    current=client.get(path,headers=headers).json();assert client.put(path,json=body(current['revision'],'female'),headers=headers).status_code==200
    assert client.post(f'/api/v1/account/wardrobe-profiles/{other}/archive').status_code==200
    assert client.get(path,headers=headers).json()['gender_identity']=='female'
    assert client.put(path,json=body(client.get(path,headers=headers).json()['revision'],'male'),headers=headers).status_code==409
