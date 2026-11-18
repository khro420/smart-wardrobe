"""Genuine login/normal routes on disposable data; no live account credentials."""
from pathlib import Path
import json,uuid,hashlib,os
import pytest
from tests.test_wearer_category_policy import category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,set_gender
from tests.test_processing_subtype_identity_integration import _preserve_composition

SOURCE=Path(__file__).resolve().parents[2]/'assets/development/fixture-catalog.json'
CASES=['I need jeans.','I want a cotton shirt.','Suggest a striped top.','I need a long-sleeved shirt.','I want black trousers.',
 'I need a white top and black pants.',"I don't want shorts, give me trousers instead.","I'd prefer blue trousers.",
 "I need a shirt that's either black or white.",'I need grey trousers, not a grey shirt.','I want trousers but not blue ones.','I need trousers, preferably black.']

@pytest.fixture(autouse=True)
def composition_boundary():
    with _preserve_composition():yield

@pytest.fixture
def bank(category_api,monkeypatch):
    client,_,_=category_api
    from app.infrastructure.persistence import postgresql_repository as db
    from app.infrastructure.media import protected_media_store as media
    from app.infrastructure import security
    from app.development.main_fixture.manage import seed
    from app.development.main_fixture.gateway import open_store,ENV
    from app.development.main_fixture.store import PROFILE
    root=db.DATABASE_PATH.resolve().parent;target=root/'media';target.mkdir(exist_ok=True)
    monkeypatch.setattr(media,'MEDIA_DIR',target)
    monkeypatch.setattr(security,'ALLOW_DEVELOPMENT_IDENTITY',False)
    monkeypatch.setenv(ENV,PROFILE)
    monkeypatch.setenv('SMART_WARDROBE_MAIN_FIXTURE_CONFIG',str(root/'phase2nd/runtime.private.json'))
    email='fixture-'+uuid.uuid4().hex+'@example.test';password='Disposable-Only-'+uuid.uuid4().hex
    r=client.post('/api/v1/account/register',json={'email':email,'password':password,'password_confirmation':password,'display_name':'Synthetic verification account'});assert r.status_code==201,r.text
    r=client.post('/api/v1/account/login',json={'email':email,'password':password});assert r.status_code==200
    client.headers['Authorization']='Bearer '+r.json()['access_token'];client.headers.pop('X-User-Id',None)
    profiles=client.get('/api/v1/account/wardrobe-profiles').json();pid=profiles[0]['id'];set_gender(client,pid,'female')
    seeded=seed(SOURCE,owner_email=email);assert seeded['added']==30
    s=open_store();assert seed(SOURCE,owner_email=email)['reconciled']==30
    return client,s,pid,email,password

def post(client,pid,text,key=None):return client.post('/api/v1/recommendations?pipeline=synthetic_development_v1',headers={'X-Wardrobe-Profile-Id':pid},json={'wearer_profile_id':pid,'request_text':text,'submission_key':key or uuid.uuid4().hex})

def test_all_twelve_reference_compact_scores_persistence_history_and_real_media(bank):
    client,s,pid,_,_=bank
    from app.development.main_fixture.core import select
    from app.application.recommendation.decision_score_codec import score_from_json
    from fractions import Fraction as F
    caps=client.get('/api/v1/recommendations/capabilities').json();assert caps['synthetic_fixture']['enabled']
    assert caps['synthetic_fixture']['normal_garments_included'] is False
    for raw in CASES:
        expected=select(s.catalog,raw,pid,'reference');compact=select(s.catalog,raw,pid,'compact_exhaustive')
        assert expected==compact==select(s.catalog,raw,pid,independent=True)
        key=uuid.uuid4().hex;r=post(client,pid,raw,key);assert r.status_code==201,r.json()
        data=r.json();assert data['synthetic_fixture_display']['decision']==expected
        sc=score_from_json(json.dumps(data['score_metadata']));assert sc.total==F(3,5)*sc.request_match.contribution+F(1,5)*sc.compatibility.contribution+F(1,5)*sc.preference.contribution
        again=post(client,pid,raw,key);assert again.status_code==200 and again.json()['id']==data['id'] and again.json()['replayed']
        history=client.get('/api/v1/chats/'+data['chat_id'],headers={'X-Wardrobe-Profile-Id':pid});assert history.status_code==200,history.text
        assert history.json()['request_text']==raw and history.json()['recommendation']['synthetic_fixture_display']==data['synthetic_fixture_display']
    for e in s.catalog['garments']:
        image=client.get('/api/v1/media/'+e['media']['id']);assert image.status_code==200 and hashlib.sha256(image.content).hexdigest()==e['image_sha256']
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    with s.connection() as c:
        assert not SqliteConfirmedGarmentQuery(c).get_confirmed_available_garments(s.catalog['owner_id'])
        assert c.execute('select count(*) from phase2nd_proofs').fetchone()[0]==12

def test_refusals_profile_off_atomic_rollback_and_scope_conflicts(bank,monkeypatch):
    client,s,pid,_,_=bank
    from app.development.main_fixture import gateway
    before=lambda:tuple(c for c in ())
    def counts():
        with s.connection() as c:return tuple(c.execute('select count(*) from '+t).fetchone()[0] for t in ['phase2nd_proofs','recommendations','nlp_chats','recommendation_submissions'])
    start=counts()
    for raw,status in [('I need a purple top.','NoMatchingCandidates'),('I need an orange checked cotton shirt.','InsufficientEvidence')]:
        r=post(client,pid,raw);assert r.status_code==200 and r.json()['status']==status;assert counts()==start
    original=gateway.mirror
    def failing(*args):original(*args);raise RuntimeError('injected after mirror')
    with monkeypatch.context() as m:
        m.setattr(gateway,'mirror',failing);r=post(client,pid,'I need jeans.');assert r.status_code==503
    assert counts()==start
    key=uuid.uuid4().hex;r=post(client,pid,'I need jeans.',key);assert r.status_code==201
    assert post(client,pid,'I want black trousers.',key).status_code==409
    normal=client.post('/api/v1/recommendations?pipeline=integrated',headers={'X-Wardrobe-Profile-Id':pid},json={'request_text':'I need jeans.','submission_key':key,'wearer_profile_id':pid});assert normal.status_code==409
    with monkeypatch.context() as m:
        m.setenv(gateway.ENV,'disabled');assert post(client,pid,'I need jeans.').status_code==503
        assert client.get('/api/v1/chats/'+r.json()['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200
    assert client.get('/api/v1/media/'+s.catalog['garments'][0]['media']['id'],headers={'Authorization':'Bearer invalid'}).status_code==401
    with s.connection() as c:c.execute("update garments set attributes_json='{}' where id=?",(s.catalog['garments'][0]['row']['id'],))
    assert post(client,pid,'I need jeans.').status_code==409
    assert client.get('/api/v1/chats/'+r.json()['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200

def test_retirement_keeps_later_edits_and_all_captured_history_media(bank):
    client,s,pid,_,_=bank
    from app.development.main_fixture.manage import retire
    from app.development.main_fixture.gateway import capabilities
    result=post(client,pid,'I need jeans.');assert result.status_code==201
    changed=s.catalog['garments'][0]['row']['id']
    with s.connection() as c:c.execute("update garments set name='later user edit' where id=?",(changed,))
    dry=retire();assert dry['dry_run'] and dry['media_deleted']==0
    done=retire(apply=True);assert sum(x['action']=='skip_later_edit' for x in done['items'])==1
    assert sum(x['action']=='archive_retain_history_and_media' for x in done['items'])==29
    assert not capabilities(s.catalog['owner_id'])['enabled']
    assert client.get('/api/v1/chats/'+result.json()['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200
    with s.connection() as c:assert c.execute('select name from garments where id=?',(changed,)).fetchone()[0]=='later user edit'
    assert all((s.media/e['media']['storage_key']).is_file() for e in s.catalog['garments'])
    repeat=retire(apply=True)
    assert repeat['media_deleted']==0 and sum(x['action']=='already_retired' for x in repeat['items'])==29

def test_live_source_image_tampering_fails_closed_without_changing_history(bank):
    client,s,pid,_,_=bank
    first=post(client,pid,'I need jeans.');assert first.status_code==201
    assert post(client,pid,'I am going shopping.').status_code==422
    e=s.catalog['garments'][0];media_id=e['media']['id'];path=s.media/e['media']['storage_key']
    assert client.get('/api/v1/media/'+media_id).status_code==200
    original=path.read_bytes();path.write_bytes(b'changed image bytes')
    assert client.get('/api/v1/media/'+media_id).status_code==409
    assert post(client,pid,'I need jeans.').status_code==409
    old=client.get('/api/v1/chats/'+first.json()['chat_id'],headers={'X-Wardrobe-Profile-Id':pid})
    assert old.status_code==200 and old.json()['request_text']=='I need jeans.'
    path.write_bytes(original);assert client.get('/api/v1/media/'+media_id).status_code==200

@pytest.mark.skipif(not os.environ.get('PHASE2ND_ARTIFACTS'),reason='Opt-in main UI check; disposable API only')
def test_authenticated_main_frontend_with_disposable_api(bank,monkeypatch):
    import os,subprocess,base64
    client,s,pid,email,password=bank
    from app.infrastructure.workflow_runtime import configure_local_workflow
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_LOCAL_PREFERENCE_PROFILE','request_local_bounded_preference_v1')
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_COMPOSITION_PROFILE','bounded_compositional_input_v1')
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_NORMALIZATION_PROFILE','disabled');configure_local_workflow()
    client.headers.clear()
    artifacts=Path(os.environ['PHASE2ND_ARTIFACTS']);env=os.environ.copy();env['PHASE2ND_TEST_EMAIL']=email;env['PHASE2ND_TEST_PASSWORD']=password
    child=subprocess.Popen(['node',str(artifacts/'browser_rpc.cjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',env=env)
    result=None
    try:
        for line in child.stdout:
            packet=json.loads(line)
            if not packet.get('rpc'):result=packet;continue
            headers={k:v for k,v in packet['headers'].items() if k.lower() not in ('host','connection','content-length','accept-encoding')}
            with (artifacts/'browser-progress.log').open('a') as f:f.write(packet['method']+' '+packet['path']+' begin\n')
            response=client.request(packet['method'],packet['path'],headers=headers,content=packet['body'])
            with (artifacts/'browser-progress.log').open('a') as f:f.write(str(response.status_code)+' done\n'+(json.dumps({'request':json.loads(packet['body']),'response':response.json()})+'\n' if packet['method']=='POST' and '/recommendations?' in packet['path'] and response.status_code!=201 else ''))
            reply={'id':packet['id'],'status':response.status_code,'headers':{k:v for k,v in response.headers.items() if k.lower() not in ('content-length','content-encoding','transfer-encoding')},'body':base64.b64encode(response.content).decode()}
            child.stdin.write(json.dumps(reply)+'\n');child.stdin.flush()
        code=child.wait(timeout=10);error=child.stderr.read()
        assert code==0,error
        assert result and result['result']=='PASS' and result['wardrobe_images']==30
        (artifacts/'BROWSER_VERIFICATION.json').write_text(json.dumps({**result,'scope':'Actual main frontend, genuine login/media/history against disposable in-process API; no live POST or live account credential'},indent=2))
    finally:
        if child.poll() is None:child.terminate()


def test_foreign_owner_and_wearer_cannot_use_fixture_or_read_history(bank,monkeypatch):
    client,s,pid,_,_=bank
    monkeypatch.setenv('SMART_WARDROBE_ENVIRONMENT','production')
    assert client.get('/api/v1/recommendations/capabilities').json()['synthetic_fixture']['enabled']
    with monkeypatch.context() as m:
        m.setenv('SMART_WARDROBE_DEVELOPMENT_FIXTURE_PROFILE','disabled')
        assert not client.get('/api/v1/recommendations/capabilities').json()['synthetic_fixture']['enabled']
        assert post(client,pid,'I need jeans.').status_code==503
    saved=post(client,pid,'I need jeans.');assert saved.status_code==201
    assert saved.json()['outcome']=='Selected'
    assert post(client,str(uuid.uuid4()),'I need jeans.').status_code==404
    assert client.post('/api/v1/recommendations?pipeline=synthetic_development_v1',json={'request_text':'I need jeans.','submission_key':uuid.uuid4().hex}).status_code==422
    foreign='other-'+uuid.uuid4().hex+'@example.test';password='Other-Disposable-'+uuid.uuid4().hex
    assert client.post('/api/v1/account/register',json={'email':foreign,'password':password,'password_confirmation':password,'display_name':'Other disposable owner'}).status_code==201
    login=client.post('/api/v1/account/login',json={'email':foreign,'password':password});assert login.status_code==200
    client.headers['Authorization']='Bearer '+login.json()['access_token']
    other=client.get('/api/v1/account/wardrobe-profiles').json()[0]['id']
    assert client.get('/api/v1/recommendations/capabilities').json()['synthetic_fixture']['enabled'] is False
    assert client.get('/api/v1/media/'+s.catalog['garments'][0]['media']['id']).status_code==404
    assert client.get('/api/v1/chats/'+saved.json()['chat_id'],headers={'X-Wardrobe-Profile-Id':other}).status_code==404
    assert post(client,other,'I need jeans.').status_code==403
    assert post(client,pid,'I need jeans.').status_code in (403,404)
