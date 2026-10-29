"""J-18 real authenticated HTTP, write validation, listing and correction evidence."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from fractions import Fraction
import json
import os
from pathlib import Path
import sqlite3
from threading import Barrier

import pytest
from app.application.nlp.nlp_interpreter import NLPInterpreter
from app.application.account import account_service
from app.application.ports.assistant_runtime import assistant_service
from app.application.ports.homepage_runtime import homepage_service
from app.infrastructure import security
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.persistence.active_preference_query_adapter import SqliteActivePreferenceQuery
from app.application.recommendation.preference_normalizer import PreferenceNormalizer
from tests.test_release_configuration import release
from tests.test_forward_style_semantics import lifecycle
from tests.test_suitability_assistant_e2e import make
from tests.test_recommendation_failure_logging import events, failure

PASSWORD='J18-disposable-password-123'
BASE={'email':'j18-owner@example.test','password':PASSWORD,'password_confirmation':PASSWORD,'display_name':'J18 Owner'}


def audit(case, **values):
    folder=os.getenv('SMART_WARDROBE_CLOSURE_EVIDENCE')
    if folder:
        with (Path(folder)/'api-trials.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps({'case':case,**values},sort_keys=True)+'\n')


@pytest.fixture
def accounts(release, monkeypatch):
    client,_=release
    monkeypatch.setattr(security,'ALLOW_DEVELOPMENT_IDENTITY',False)
    client.headers.clear()
    return client


def register_login(client, email=BASE['email']):
    registered=client.post('/api/v1/account/register',json={**BASE,'email':email})
    assert registered.status_code==201,registered.text
    assert 'access_token' not in registered.json()
    logged=client.post('/api/v1/account/login',json={'email':email,'password':PASSWORD})
    assert logged.status_code==200
    return registered.json()['profile'],{'Authorization':'Bearer '+logged.json()['access_token']}


def users():
    with db.connection() as c:return [tuple(row) for row in c.execute('SELECT * FROM users ORDER BY id')]


@pytest.mark.parametrize('changes',[
    {'password_confirmation':None},{'password_confirmation':'different-password'},
    {'password':'short','password_confirmation':'short'},{'email':'not-an-email'},
    {'email':'a..b@example.test'},{'email':'a@-example.test'},{'email':'a@exam ple.test'},
    {'display_name':'  '},{'display_name':'Hidden\nname'}, {'display_name':'x'*101},
])
def test_invalid_registration_never_inserts(accounts,changes):
    before=users()
    response=accounts.post('/api/v1/account/register',json={**BASE,**changes})
    assert response.status_code==422 and users()==before
    audit('invalid_registration',fields=list(changes),http=response.status_code,users_unchanged=True)


def test_missing_confirmation_and_duplicate_registration(accounts):
    before=users();body={k:v for k,v in BASE.items() if k!='password_confirmation'}
    assert accounts.post('/api/v1/account/register',json=body).status_code==422 and users()==before
    profile,headers=register_login(accounts,'J18-Owner@Example.Test')
    assert profile['email']=='j18-owner@example.test'
    assert accounts.get('/api/v1/account/profile').status_code==401
    assert accounts.get('/api/v1/account/profile',headers=headers).json()==profile
    before=users()
    duplicate=accounts.post('/api/v1/account/register',json={**BASE,'email':' J18-OWNER@example.test '})
    assert duplicate.status_code==409 and users()==before
    audit('registration_login_duplicate',registered=profile,http=duplicate.status_code,no_automatic_session=True)


def test_concurrent_duplicate_registration_is_one_account(accounts):
    before=len(users());barrier=Barrier(2)
    def attempt(_):
        barrier.wait()
        return accounts.post('/api/v1/account/register',json=BASE).status_code
    with ThreadPoolExecutor(2) as pool:codes=list(pool.map(attempt,range(2)))
    assert sorted(codes)==[201,409] and len(users())==before+1
    audit('concurrent_duplicate_registration',http=codes,added_users=1)


@pytest.mark.parametrize('body',[{}, {'email':BASE['email']},{'email':'','password':''},{'email':BASE['email'],'password':''}])
def test_missing_login_fields(accounts,body):
    before=users()
    assert accounts.post('/api/v1/account/login',json=body).status_code==422 and users()==before


def test_invalid_credentials_are_general(accounts):
    register_login(accounts)
    wrong=accounts.post('/api/v1/account/login',json={'email':BASE['email'],'password':'wrong-password'})
    unknown=accounts.post('/api/v1/account/login',json={'email':'unknown@example.test','password':PASSWORD})
    assert wrong.status_code==unknown.status_code==401
    assert wrong.json()==unknown.json()=={'detail':'Invalid email or password.'}
    audit('invalid_credentials',http=401,same_message=wrong.json())


@pytest.mark.parametrize('kind,value,weight',[
    ('unsupported',{'values':['blue']},1),('colours',{'values':['ultraviolet']},1),
    ('styles',{'values':['arbitrary personal prose']},1),('styles',{'values':['unsupported']},0),
    ('colours',{'values':['blue'],'extra':'bad'},1),('styles',{},1),
    ('styles',{'values':'vintage'},1),('colours',{'values':[5]},1),
    ('formality',{'values':['formal']},1),('garment_categories',{'values':[{'kind':'category','value':'shoes'}]},1),
    ('garment_categories',{'values':['top']},1),('style_note',{'value':'arbitrary prose'},1),
    ('colours',{'values':['blue']},True),('colours',{'values':['blue']},-0.1),('colours',{'values':['blue']},1.1),
])
def test_invalid_preference_preserves_previous_values(accounts,kind,value,weight):
    _,headers=register_login(accounts)
    assert accounts.put('/api/v1/account/preferences/colours',headers=headers,json={'preference_value':{'values':['red']},'weight':.5}).status_code==200
    before=accounts.get('/api/v1/account/preferences',headers=headers).json()
    response=accounts.put('/api/v1/account/preferences/'+kind,headers=headers,json={'preference_value':value,'weight':weight})
    assert response.status_code==422 and accounts.get('/api/v1/account/preferences',headers=headers).json()==before
    audit('invalid_preference',kind=kind,value=value,weight=weight,http=422,previous_unchanged=True)


def test_supported_preference_options_save_clear_and_owner_isolation(accounts):
    owner,headers=register_login(accounts);_,other=register_login(accounts,'other@example.test')
    options=accounts.get('/api/v1/account/preference-options',headers=headers).json()
    assert options['formality']==['casual','smart_casual']
    assert 'blue' in options['colours'] and 'classic' in options['styles']
    values={'colours':['blue'],'styles':['vintage'],'garment_categories':[{'kind':'group','value':'dress'}],'formality':['casual']}
    for kind,choices in values.items():
        response=accounts.put('/api/v1/account/preferences/'+kind,headers=headers,json={'preference_value':{'values':choices},'weight':.5})
        assert response.status_code==200
    rows=SqliteActivePreferenceQuery().get_active_preferences(owner['id'])
    normalized=PreferenceNormalizer().normalize(owner['id'],rows)
    assert len(normalized.preferences)==4 and not normalized.diagnostics
    assert all(item.importance==Fraction(1,2) for item in normalized.preferences)
    assert accounts.get('/api/v1/account/preferences',headers=other).json()==[]
    own_before=accounts.get('/api/v1/account/preferences',headers=headers).json()
    accounts.put('/api/v1/account/preferences/colours',headers=other,json={'preference_value':{'values':['red']},'weight':1})
    assert accounts.get('/api/v1/account/preferences',headers=headers).json()==own_before
    cleared=accounts.put('/api/v1/account/preferences/colours',headers=headers,json={'preference_value':{'values':[]},'weight':1})
    assert cleared.status_code==200 and not cleared.json()['is_active']
    assert {p['preference_type'] for p in accounts.get('/api/v1/account/preferences',headers=headers).json()}==set(values)-{'colours'}
    with db.connection() as c:
        retained=c.execute("SELECT * FROM user_preferences WHERE user_id=? AND preference_type='colours'",(owner['id'],)).fetchone()
        assert retained['is_active']==0 and json.loads(retained['preference_value_json'])=={'values':['blue']}
    audit('preferences_supported_clear_owner',owner=owner['id'],types=list(values),normalized_importance='1/2',clear_keeps_record=True)


def test_failed_profile_and_preference_transactions_preserve_storage(accounts):
    profile,headers=register_login(accounts)
    for value in ['  ','bad\nname']:
        assert accounts.patch('/api/v1/account/profile',headers=headers,json={'display_name':value}).status_code==422
    assert accounts.get('/api/v1/account/profile',headers=headers).json()==profile
    url='/api/v1/account/preferences/styles'
    assert accounts.put(url,headers=headers,json={'preference_value':{'values':['vintage']}}).status_code==200
    before=accounts.get('/api/v1/account/preferences',headers=headers).json()
    with db.connection() as c:
        c.execute("CREATE TRIGGER fail_profile BEFORE UPDATE ON users BEGIN SELECT RAISE(ABORT,'injected profile failure'); END")
        c.execute("CREATE TRIGGER fail_preference BEFORE UPDATE ON user_preferences BEGIN SELECT RAISE(ABORT,'injected preference failure'); END")
    with pytest.raises(sqlite3.IntegrityError):accounts.patch('/api/v1/account/profile',headers=headers,json={'display_name':'Not saved'})
    with pytest.raises(sqlite3.IntegrityError):accounts.put(url,headers=headers,json={'preference_value':{'values':['classic']}})
    assert accounts.get('/api/v1/account/profile',headers=headers).json()==profile
    assert accounts.get('/api/v1/account/preferences',headers=headers).json()==before
    audit('injected_profile_preference_failure',profile_unchanged=True,preferences_unchanged=True)


def test_preference_acknowledges_committed_write_if_another_connection_clears(accounts,monkeypatch):
    owner,headers=register_login(accounts)
    url='/api/v1/account/preferences/styles'
    assert accounts.put(url,headers=headers,json={'preference_value':{'values':['vintage']}}).status_code==200
    underlying=account_service.connection;clears=[]
    @contextmanager
    def competing_connection():
        wrote=False
        with underlying() as c:
            yield c
            wrote=c.in_transaction
        if wrote and not clears:
            clears.append(True)
            # A second real SQLite connection clears after commit, before response projection.
            def clear():
                with underlying() as other:
                    other.execute("UPDATE user_preferences SET is_active=0 WHERE user_id=? AND preference_type='styles'",(owner['id'],))
            with ThreadPoolExecutor(1) as pool:pool.submit(clear).result()
    monkeypatch.setattr(account_service,'connection',competing_connection)
    response=accounts.put(url,headers=headers,json={'preference_value':{'values':['classic']},'weight':.5})
    assert response.status_code==200 and response.json()['preference_value']=={'values':['classic']}
    assert clears==[True] and accounts.get('/api/v1/account/preferences',headers=headers).json()==[]
    audit('preference_acknowledgement_competing_clear',http=200,committed_values=['classic'],later_clear_retained=True)


def test_saved_preference_consumed_by_actual_scorer_and_history_replay(release):
    client,create=release;gid=make(client,create)
    body={'request_text':'Suggest a vintage style outfit','submission_key':'preference-before'}
    before=client.post('/api/v1/recommendations?pipeline=integrated',json=body).json()
    assert before['preference_score'] is None
    for kind,values in [('colours',['blue']),('styles',['vintage']),('garment_categories',[{'kind':'group','value':'dress'}])]:
        assert client.put('/api/v1/account/preferences/'+kind,json={'preference_value':{'values':values},'weight':.5}).status_code==200
    result=client.post('/api/v1/recommendations?pipeline=integrated',json={**body,'submission_key':'preference-after'})
    assert result.status_code==201,result.text
    saved=result.json();assert saved['preference_score']==1 and saved['items'][0]['garment_id']==gid
    assert saved['provenance']['scoring_profile']=='experimental_compatibility_decision_v1'
    assert saved['score_metadata']['weights']==before['score_metadata']['weights']
    replay=client.post('/api/v1/recommendations?pipeline=integrated',json=body).json()
    assert replay['id']==before['id'] and replay['score_metadata']==before['score_metadata'] and replay['provenance']==before['provenance']
    audit('saved_preference_actual_scorer',before=before['score_metadata'],after=saved['score_metadata'],historical_replay_unchanged=True)


def test_listing_filters_owner_status_styles_and_quota_are_read_only(release):
    client,create=release;gid=make(client,create);empty=create([])
    db.ensure_user("another-owner")
    with db.connection() as c:
        c.execute("UPDATE garments SET primary_colour='red',attributes_json=? WHERE id=?",(json.dumps({'style':['vintage']}),empty))
        for identifier,owner,status in [('archive','style-owner','archived'),('other-state','style-owner','unavailable'),('foreign','another-owner','available')]:
            c.execute("INSERT INTO garments(id,user_id,preferred_media_id,name,category,primary_colour,attributes_json,style_tags,status,created_at,updated_at) VALUES(?,?,'unused',?,'vest','blue','{}','[\"vintage\"]',?,'now','now')",(identifier,owner,identifier,status))
    def snapshot():
        with db.connection() as c:return [tuple(r) for r in c.execute('SELECT * FROM garments ORDER BY id')]
    before=snapshot();quota=client.get('/api/v1/wardrobe/quota').json()
    def ids(**params):
        response=client.get('/api/v1/wardrobe/garments',params=params);assert response.status_code==200,response.text
        return {g['id'] for g in response.json()}
    assert ids()=={gid,empty}
    assert ids(colour=' BLUE ',style='VINTAGE')=={gid}
    assert ids(style='vintage',colour='red')==set()  # Authoritative [] is not promoted from legacy attributes.
    assert ids(availability='archived')=={'archive'}
    assert ids(availability='unavailable')=={'other-state'}
    assert ids(availability='all')=={gid,empty,'archive','other-state'}
    assert ids(colour="blue' OR 1=1 --",availability='all')==set()
    assert client.get('/api/v1/wardrobe/garments',params={'availability':'invalid'}).status_code==422
    assert snapshot()==before and client.get('/api/v1/wardrobe/quota').json()==quota and quota['used']==3
    audit('listing_filters',all_owner_ids=sorted(ids(availability='all')),quota=quota,garment_rows_unchanged=True)


@pytest.mark.parametrize('text',['Suggest a classic outfit','Please suggest a classic outfit'])
def test_classic_outfit_correction_actual_http(release,text):
    client,create=release;gid=make(client,create)
    client.patch('/api/v1/wardrobe/garments/'+gid,json={'attributes':{'style':['classic']}})
    interpreted=NLPInterpreter().interpret(text)
    assert interpreted.status=='Supported' and interpreted.structured_request.style=='classic'
    result=client.post('/api/v1/recommendations?pipeline=integrated',json={'request_text':text,'submission_key':'classic-correction'})
    assert result.status_code==201,result.text
    assert result.json()['items'][0]['garment_id']==gid
    audit('classic_outfit_correction',text=text,http=201,structured=interpreted.structured_request.to_dict(),result=result.json())


@pytest.mark.parametrize('text',['Suggest a classic outfit for rainy weather','Suggest an outfit without classic style','Tell me about classic novels'])
def test_classic_mapping_keeps_unsupported_boundaries(text):
    assert NLPInterpreter().interpret(text).status=='UnsupportedRequest'


@pytest.mark.parametrize('operation',['assistant','homepage'])
def test_authenticated_api_failure_retains_safe_response_and_actual_logs(release,monkeypatch,caplog,operation):
    client,_=release
    service=assistant_service() if operation=='assistant' else homepage_service()
    method='find_assistant_submission' if operation=='assistant' else 'find_homepage_submission'
    monkeypatch.setattr(service.repository,method,lambda *args:failure())
    with db.connection() as c:before=[tuple(r) for r in c.execute('SELECT * FROM recommendations')]
    response=client.post('/api/v1/recommendations'+('?pipeline=integrated' if operation=='assistant' else '/homepage'),json={'submission_key':'api-fault',**({'request_text':'PRIVATE_REQUEST medical personal note'} if operation=='assistant' else {})})
    assert response.status_code==503 and response.json()['status']=='PersistenceFailure'
    assert 'SECRET' not in response.text and 'PRIVATE' not in response.text
    logged=events(caplog);assert len(logged)==1 and logged[0]['operation']==operation and logged[0]['stage']=='lookup'
    with db.connection() as c:assert [tuple(r) for r in c.execute('SELECT * FROM recommendations')]==before
    audit('actual_api_failure_logging',operation=operation,http=503,response=response.json(),safe_event=logged[0])
