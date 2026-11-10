"""Actual disposable authenticated preference API; no model/private account."""
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4
import json
import pytest
from tests.test_attribute_persistence import attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.infrastructure.persistence import postgresql_repository as db
from app.domain.value_objects.attribute_preferences import TYPE, SOURCE, SNAPSHOT, PreferenceError
from app.application.recommendation.attribute_preference_policy import configure
from app.infrastructure.persistence.attribute_preference_query_adapter import capture_rows


@pytest.fixture
def p2_api(attribute_api,monkeypatch):
    client,create=attribute_api
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_PREFERENCE_PROFILE','attribute_preference_decision_v2')
    configure_local_workflow()
    wearer=client.get('/api/v1/account/wardrobe-profiles').json()[0]['id']
    yield client,wearer
    configure('disabled')


def url(wearer):return '/api/v1/account/wardrobe-profiles/'+wearer+'/attribute-preferences'
def action(view,families):return {'contract':'attribute-preferences-update-1.0.0','wearer_id':view['wearer_id'],'expected_revision':view['revision'],'action_id':str(uuid4()),'families':families}
def pattern(value='plain'):
    return {'pattern':{'mode':'override','importance':'1','axes':{'pattern':{'scope':'all_selected','importance':'1','liked':[value],'avoided':[]}}}}


def test_active_legacy_api_is_unchanged_and_wearers_do_not_leak(p2_api):
    client,a=p2_api;b=client.post('/api/v1/account/wardrobe-profiles',json={'name':'B'}).json()['id']
    client.headers['X-Wardrobe-Profile-Id']=a
    assert client.put('/api/v1/account/preferences/colours',json={'preference_value':{'values':['blue']},'weight':0.5}).status_code==200
    av=client.get(url(a)).json();assert av['effective']['colour']['importance']=='1/2'
    payload=action(av,pattern());saved=client.put(url(a),json=payload);assert saved.status_code==200,saved.text
    rows=client.get('/api/v1/account/preferences').json();assert len(rows)==1 and rows[0]['preference_type']=='colours'
    client.headers['X-Wardrobe-Profile-Id']=b
    bv=client.get(url(b)).json();assert not bv['effective'] and bv['document'] is None
    assert 'blue' not in json.dumps(bv)
    with db.connection() as conn:
        row=conn.execute('SELECT * FROM user_preferences WHERE preference_type=?',(TYPE,)).fetchone()
        assert row['profile_id']==a and row['is_active']==0 and row['weight']==0 and row['source']==SOURCE


def test_latest_exact_retry_and_changed_key_intent_conflict(p2_api):
    client,a=p2_api;v=client.get(url(a)).json();payload=action(v,pattern())
    first=client.put(url(a),json=payload);assert first.status_code==200,first.text
    with db.connection() as conn:before=dict(conn.execute('SELECT * FROM user_preferences WHERE preference_type=?',(TYPE,)).fetchone())
    retry=client.put(url(a),json=payload);assert retry.status_code==200 and retry.json()==first.json()
    payload['families']=pattern('stripe');assert client.put(url(a),json=payload).status_code==409
    with db.connection() as conn:assert dict(conn.execute('SELECT * FROM user_preferences WHERE preference_type=?',(TYPE,)).fetchone())==before


def test_revision_race_one_write_and_no_partial_config(p2_api):
    client,a=p2_api;v=client.get(url(a)).json();one=action(v,pattern());two=action(v,pattern('stripe'))
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda body:client.put(url(a),json=body),(one,two)))
    assert sorted(r.status_code for r in responses)==[200,409]
    with db.connection() as conn:assert conn.execute('SELECT count(*) FROM user_preferences WHERE preference_type=?',(TYPE,)).fetchone()[0]==1


def test_legacy_edit_invalidates_settings_revision_and_clear_does_not_resurrect(p2_api):
    client,a=p2_api;v=client.get(url(a)).json()
    client.headers['X-Wardrobe-Profile-Id']=a
    assert client.put('/api/v1/account/preferences/colours',json={'preference_value':{'values':['blue']},'weight':1}).status_code==200
    assert client.put(url(a),json=action(v,pattern())).status_code==409
    v=client.get(url(a)).json();saved=client.put(url(a),json=action(v,{'colour':{'mode':'disabled'}}))
    assert saved.status_code==200 and 'colour' not in saved.json()['effective']
    assert len(client.get('/api/v1/account/preferences').json())==1


def test_foreign_header_archive_and_corrupt_sentinel_fail_closed(p2_api):
    client,a=p2_api
    assert client.get(url(str(uuid4()))).status_code==404
    client.headers['X-Wardrobe-Profile-Id']=str(uuid4());assert client.get(url(a)).status_code==422
    client.headers.pop('X-Wardrobe-Profile-Id')
    v=client.get(url(a)).json();assert client.put(url(a),json=action(v,pattern())).status_code==200
    with db.connection() as conn:conn.execute('UPDATE user_preferences SET is_active=1 WHERE preference_type=?',(TYPE,))
    assert client.get(url(a)).status_code==409
    with db.connection() as conn:conn.execute('UPDATE user_preferences SET is_active=0 WHERE preference_type=?',(TYPE,))
    assert client.post('/api/v1/account/wardrobe-profiles',json={'name':'Second'}).status_code==201
    assert client.post('/api/v1/account/wardrobe-profiles/'+a+'/archive').status_code==200
    assert client.get(url(a)).status_code==409
    with db.connection() as conn:assert conn.execute('SELECT count(*) FROM user_preferences WHERE profile_id=? AND preference_type=?',(a,TYPE)).fetchone()[0]==1


def test_missing_scope_and_duplicate_doc_never_choose_a_row(p2_api):
    client,a=p2_api;v=client.get(url(a)).json();assert client.put(url(a),json=action(v,pattern())).status_code==200
    with db.connection() as conn:
        with pytest.raises(PreferenceError):capture_rows(conn,'style-owner',None)
        conn.execute('INSERT INTO user_preferences SELECT ?,user_id,profile_id,preference_type,preference_value_json,weight,source,is_active,created_at,updated_at FROM user_preferences WHERE preference_type=?',(str(uuid4()),TYPE))
    assert client.get(url(a)).status_code==409


def test_disabled_default_does_not_advertise_or_write(p2_api):
    client,a=p2_api;configure('disabled')
    assert client.get('/api/v1/account/attribute-preference-capabilities').json()['enabled'] is False
    assert client.get(url(a)).status_code==422


@pytest.mark.parametrize('raw',['{"contract":"future"}',b'not text','{broken'])
def test_corrupt_documents_are_visible_without_repair(p2_api,raw):
    client,a=p2_api;v=client.get(url(a)).json();assert client.put(url(a),json=action(v,pattern())).status_code==200
    with db.connection() as conn:conn.execute('UPDATE user_preferences SET preference_value_json=? WHERE preference_type=?',(raw,TYPE))
    assert client.get(url(a)).status_code==409
    with db.connection() as conn:assert conn.execute('SELECT preference_value_json FROM user_preferences WHERE preference_type=?',(TYPE,)).fetchone()[0]==raw


def test_duplicate_supported_legacy_rows_fail_visibly(p2_api):
    client,a=p2_api;client.headers['X-Wardrobe-Profile-Id']=a
    assert client.put('/api/v1/account/preferences/colours',json={'preference_value':{'values':['blue']},'weight':1}).status_code==200
    with db.connection() as conn:conn.execute('INSERT INTO user_preferences SELECT ?,user_id,profile_id,preference_type,preference_value_json,weight,source,is_active,created_at,updated_at FROM user_preferences WHERE preference_type=?',(str(uuid4()),'colours'))
    reply=client.get(url(a));assert reply.status_code==409 and reply.json()['detail']['code']=='PreferenceInvalid'


def test_noop_does_not_create_a_document_and_fault_rolls_back(p2_api,monkeypatch):
    client,a=p2_api;v=client.get(url(a)).json();assert client.put(url(a),json=action(v,{})).json()==v
    with db.connection() as conn:assert conn.execute('SELECT count(*) FROM user_preferences WHERE preference_type=?',(TYPE,)).fetchone()[0]==0
    from app.application.account import attribute_preference_service as service
    original=service._view
    def fail(snapshot):
        if snapshot.to_dict()['document'] is not None:raise PreferenceError('SyntheticFault','After-write failure.',507)
        return original(snapshot)
    monkeypatch.setattr(service,'_view',fail)
    assert client.put(url(a),json=action(v,pattern())).status_code==507
    with db.connection() as conn:assert conn.execute('SELECT count(*) FROM user_preferences WHERE preference_type=?',(TYPE,)).fetchone()[0]==0


def test_all_three_new_endpoints_require_authentication_and_durable_logout(p2_api,monkeypatch):
    client,a=p2_api;token=client.headers.pop('Authorization')
    from app.infrastructure import security
    monkeypatch.setattr(security,'ALLOW_DEVELOPMENT_IDENTITY',False)
    client.headers.pop('X-User-Id',None)
    assert client.get('/api/v1/account/attribute-preference-capabilities').status_code==401
    assert client.get(url(a)).status_code==401
    assert client.put(url(a),json={}).status_code==401
    client.headers['Authorization']=token
    assert client.post('/api/v1/account/logout').status_code==204
    assert client.get(url(a)).status_code==401
