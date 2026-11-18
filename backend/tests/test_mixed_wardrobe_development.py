"""Disposable authenticated mixed-source workflow; never opens main data."""
from pathlib import Path
import json,uuid,os,copy
import pytest
from tests.test_phase2nd_main_fixture import bank,composition_boundary,SOURCE
from tests.test_wearer_category_policy import category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle
from tests.test_context_relevance_integration import wardrobe
from tests.test_attribute_persistence import qualify
from app.development.mixed_wardrobe import gateway
from app.development.mixed_wardrobe.core import select,OriginalRow,rows_from_catalog,fact
from app.development.mixed_wardrobe.store import FixtureError

@pytest.fixture
def mixed(bank,monkeypatch):
    client,_,pid,email,password=bank
    # Normal API processing/confirmation creates original-source fixture rows.
    ids=wardrobe(client)
    for name,gid in ids.items():qualify(client,gid,pattern='plain')
    for name in ('Blue T-shirt','Blue Jeans'):
        r=client.patch('/api/v1/wardrobe/garments/'+ids[name],json={'primary_colour':'purple'});assert r.status_code==200,r.text
    monkeypatch.setenv(gateway.ENV,'phase2nd_mixed_v1')
    s=gateway.open_store(enabled=True)
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app,headers=dict(client.headers),client=('127.0.0.1',51731)) as local:
        yield local,s,pid,ids,email,password

def post(client,pid,raw,key=None,**extra):
    return client.post('/api/v1/recommendations?pipeline=integrated',headers={'X-Wardrobe-Profile-Id':pid},json={'request_text':raw,'wearer_profile_id':pid,'submission_key':key or uuid.uuid4().hex,**extra})

def test_complete_union_original_synthetic_mixed_and_semantics(mixed):
    client,s,pid,ids,_,_=mixed
    with s.connection() as c:v=s.capture(c,s.catalog['owner_id'],pid)
    count=gateway.counts(v);assert count['original_confirmed']==len(ids) and count['synthetic_declared']==30
    assert count['available_inventory']==len(ids)+30
    cap=client.get('/api/v1/recommendations/capabilities').json();assert cap['mixed_wardrobe']['enabled']
    cases=[('I need a purple top and purple trousers.',{'normal_B0_B1'}),('I need a striped cotton top and denim trousers.',{'synthetic_fixture_declaration'}),('I need a purple top and denim trousers.',{'normal_B0_B1','synthetic_fixture_declaration'})]
    cases += [(raw,None) for raw in ['I need jeans','I want a cotton shirt.','Suggest a striped top.','I need a long-sleeved shirt.','I want black trousers.',"I don't want shorts, give me trousers instead.",'I need trousers, preferably black.',"I need a shirt that's either black or white.",'I need grey trousers, not a grey shirt.']]
    for raw,wanted in cases:
        first=select(v,raw,pid,'reference');compact=select(v,raw,pid,'compact_exhaustive');independent=select(v,raw,pid,independent=True)
        assert first==compact==independent and first['status']=='Selected',raw
        if wanted:assert {i['source'] for i in first['items']}==wanted
    # A Jeans name cannot qualify unknown original material.
    original=next(r for r in rows_from_catalog(v,'female') if isinstance(r,OriginalRow) and r.snapshot.garment_id==ids['Blue Jeans'])
    assert fact(original,'material','scope','contains_any').state not in ('Known','KnownEmpty')

def test_mixed_persistence_receipts_history_and_images(mixed):
    client,s,pid,ids,_,_=mixed
    r=post(client,pid,'I need a purple top and denim trousers.');assert r.status_code==201,r.text
    data=r.json();assert data['outcome']=='Selected' and data['mixed_wardrobe_display']['contains_synthetic']
    assert {x['source'] for x in data['mixed_wardrobe_display']['items']}=={'normal_B0_B1','synthetic_fixture_declaration'}
    history=client.get('/api/v1/chats/'+data['chat_id'],headers={'X-Wardrobe-Profile-Id':pid});assert history.status_code==200,history.text
    assert history.json()['recommendation']['mixed_wardrobe_display']==data['mixed_wardrobe_display']
    for item in data['items']:assert client.get('/api/v1/media/'+item['preferred_media_id']).status_code==200
    assert post(client,pid,'I need a purple top and denim trousers.',data['provenance']['phase2nd_mixed_selection']['receipt']).json()['replayed']

def test_locked_revalidation_rollback_tamper_and_old_history(mixed,monkeypatch):
    client,s,pid,ids,_,_=mixed;owner=s.catalog['owner_id']
    def state():
        with s.connection() as c:return tuple(c.execute('select count(*) from '+t).fetchone()[0] for t in ('recommendations','nlp_chats','recommendation_metadata','recommendation_submissions'))
    before=state();original=gateway.mirror
    def fail(c,*args):original(c,*args);raise ValueError('injected after mixed mirror')
    with monkeypatch.context() as m:
        m.setattr(gateway,'mirror',fail);r=post(client,pid,'I need jeans');assert r.status_code==503
    assert state()==before
    def corrupt(c,*args):
        original(c,*args);c.execute('update recommendations set total_score=1 where id=?',(args[1]['id'],))
    with monkeypatch.context() as m:
        m.setattr(gateway,'mirror',corrupt);r=post(client,pid,'I need jeans');assert r.status_code==503
    assert state()==before
    first=post(client,pid,'I need jeans');assert first.status_code==201,first.text
    key=first.json()['provenance']['phase2nd_mixed_selection']['receipt'];assert post(client,pid,'I want black trousers.',key).status_code==409
    def changed():
        with s.connection() as c:c.execute("update garments set name='changed during selection' where id=?",(ids['Blue Jeans'],))
    with pytest.raises(FixtureError,match='ChangedFixtureSource'):s.recommend(owner,pid,'I need jeans',uuid.uuid4().hex,before_lock=changed)
    assert client.get('/api/v1/chats/'+first.json()['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200
    e=s.catalog['garments'][0];p=s.media/e['media']['storage_key'];wire=p.read_bytes();p.write_bytes(b'changed')
    assert post(client,pid,'I need jeans').status_code==409
    p.write_bytes(wire)
    with s.connection() as c:
        row=c.execute('select * from phase2nd_mixed_proofs limit 1').fetchone();d=json.loads(row['proof_json']);d['decision']['selected']['score']['total']={'numerator':1,'denominator':1}
        c.execute('update phase2nd_mixed_proofs set proof_json=? where id=?',(json.dumps(d),row['id']))
    with s.connection() as c:
        with pytest.raises(FixtureError):s.verify_record(c,c.execute('select * from phase2nd_mixed_proofs limit 1').fetchone(),owner)
    from app.development.mixed_wardrobe.core import digest
    with s.connection() as c:c.execute('update phase2nd_mixed_proofs set proof_sha256=?,signature=? where id=?',(digest(d),s.sign(d),row['id']))
    with s.connection() as c:
        with pytest.raises(FixtureError,match='IndependentFixtureHistoryMismatch'):s.verify_record(c,c.execute('select * from phase2nd_mixed_proofs where id=?',(row['id'],)).fetchone(),owner)

def test_server_profile_and_ownership_bounds(mixed,monkeypatch):
    client,s,pid,ids,_,_=mixed
    with monkeypatch.context() as m:
        m.setenv(gateway.ENV,'disabled');assert not client.get('/api/v1/recommendations/capabilities').json()['mixed_wardrobe']['enabled']
    assert not gateway.capabilities(s.catalog['owner_id'],'192.0.2.1')['enabled']
    with pytest.raises(FixtureError,match='LocalDevelopmentOnly'):gateway.submit(s.catalog['owner_id'],None,None,'192.0.2.1')
    assert post(client,pid,'I need jeans',preference_profile='attribute_preference_decision_v2').status_code==422
    assert post(client,pid,'Going shopping.').status_code==422
    assert post(client,str(uuid.uuid4()),'I need jeans').status_code==404
    rows=client.get('/api/v1/wardrobe/garments?include_wearer_eligibility=true',headers={'X-Wardrobe-Profile-Id':pid}).json()
    fixture=[r for r in rows if 'development_evidence' in r];assert len(fixture)==30 and all(r['development_evidence']['eligible'] for r in fixture)
    assert all(not r['wearer_category_eligibility']['usable'] for r in fixture)
    assert all('development_evidence' not in r for r in rows if r['id'] in ids.values())

def test_bound_alternatives_and_soft_refusal(mixed):
    client,s,pid,_,_,_=mixed
    root=post(client,pid,'I need jeans');assert root.status_code==201,root.text
    r=root.json();bases=[]
    for n in range(10):
        bases.append(tuple((i['garment_role'],i['garment_id']) for i in r['items'] if i['garment_role']!='outerwear'))
        d=r['development_continuation'];assert d['ordinal']==n
        if n==9:assert d['next_action'] is None and d['limit_reached'];break
        a=d['next_action'];child=post(client,pid,r['request_text'],a['submission_key'],refinement=a['refinement']);assert child.status_code==201,child.text
        assert post(client,pid,r['request_text'],a['submission_key'],refinement=a['refinement']).json()['replayed']
        r=child.json()
    assert len(set(bases))==10
    soft=post(client,pid,'I need trousers, preferably black.');assert soft.status_code==201,soft.text
    assert soft.json()['development_continuation']['next_action'] is None


def test_preexisting_normal_and_fixture_receipts_keep_original_readers(mixed,monkeypatch):
    client,s,pid,ids,_,_=mixed
    with monkeypatch.context() as m:
        m.setenv(gateway.ENV,'disabled');normal=post(client,pid,'Recommend an outfit.');assert normal.status_code==201,normal.text
    old=normal.json();key=client.get('/api/v1/chats/'+old['chat_id'],headers={'X-Wardrobe-Profile-Id':pid});assert key.status_code==200
    # Receipt identity is in the captured request payload, not derived from winner.
    with s.connection() as c:nkey=c.execute('select submission_key from recommendation_submissions where recommendation_id=?',(old['id'],)).fetchone()[0]
    replay=post(client,pid,'Recommend an outfit.',nkey);assert replay.status_code==200 and replay.json()['id']==old['id']
    from tests.test_phase2nd_main_fixture import post as old_fixture_post
    fkey=uuid.uuid4().hex
    with monkeypatch.context() as m:
        m.setenv(gateway.ENV,'disabled');fixture=old_fixture_post(client,pid,'I need jeans',fkey);assert fixture.status_code==201,fixture.text
    assert old_fixture_post(client,pid,'I need jeans').status_code==409
    replay=post(client,pid,'I need jeans',fkey);assert replay.status_code==200 and replay.json()['id']==fixture.json()['id']
    assert post(client,pid,'I want black trousers.',fkey).status_code==409
    assert client.get('/api/v1/chats/'+fixture.json()['chat_id'],headers={'X-Wardrobe-Profile-Id':pid}).status_code==200

@pytest.mark.skipif(not os.environ.get('PHASE2ND_ARTIFACTS'),reason='Opt-in browser check; disposable authenticated API only')
def test_main_ui_unified_pool_without_source_selector(mixed,monkeypatch):
    import subprocess,base64
    client,s,pid,ids,email,password=mixed
    from app.infrastructure.workflow_runtime import configure_local_workflow
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_LOCAL_PREFERENCE_PROFILE','request_local_bounded_preference_v1')
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_COMPOSITION_PROFILE','bounded_compositional_input_v1')
    configure_local_workflow();client.headers.clear()
    artifacts=Path(os.environ['PHASE2ND_ARTIFACTS']);env=os.environ.copy();env['PHASE2ND_TEST_EMAIL']=email;env['PHASE2ND_TEST_PASSWORD']=password
    child=subprocess.Popen(['node',str(artifacts/'browser_rpc.cjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',env=env)
    result=None
    try:
        for line in child.stdout:
            packet=json.loads(line)
            if not packet.get('rpc'):result=packet;continue
            headers={k:v for k,v in packet['headers'].items() if k.lower() not in ('host','connection','content-length','accept-encoding')}
            response=client.request(packet['method'],packet['path'],headers=headers,content=packet['body'])
            reply={'id':packet['id'],'status':response.status_code,'headers':{k:v for k,v in response.headers.items() if k.lower() not in ('content-length','content-encoding','transfer-encoding')},'body':base64.b64encode(response.content).decode()}
            child.stdin.write(json.dumps(reply)+'\n');child.stdin.flush()
        code=child.wait(timeout=10);error=child.stderr.read()
        assert code==0,error
        assert result and result['result']=='PASS' and result['wardrobe_images']==30
        (artifacts/'BROWSER_VERIFICATION.json').write_text(json.dumps({**result,'scope':'Actual main frontend; genuine login and disposable API only'},indent=2))
    finally:
        if child.poll() is None:child.terminate()


def test_locked_fixture_authority_is_revalidated(mixed):
    client,s,pid,_,_,_=mixed
    def changed():
        with s.connection() as c:c.execute("update phase2nd_instance set catalog_sha256=?",('0'*64,))
    with pytest.raises(FixtureError,match='ChangedFixtureAuthority'):s.recommend(s.catalog['owner_id'],pid,'I need jeans',uuid.uuid4().hex,before_lock=changed)
    with s.connection() as c:
        if c.execute("select 1 from sqlite_master where name='phase2nd_mixed_proofs'").fetchone():assert c.execute('select count(*) from phase2nd_mixed_proofs').fetchone()[0]==0
