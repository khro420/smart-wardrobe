"""Normal authenticated writes, equivalent scoring, strict gates and immutable replay."""
import json
import sqlite3
import uuid
import pytest
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.security import issue_access_token
from app.application.ports.assistant_runtime import assistant_service
from tests.test_owner_style_confirmation import add, edit, garment, prepare, KEY, CONTRACT
from tests.test_everyday_context import everyday_api
from tests.test_release_configuration import release, submit
from tests.test_forward_style_semantics import lifecycle
from tests.test_contextual_wedding import review
from tests.test_suitability_controls import patch_tags


@pytest.mark.parametrize('style',['casual','smart casual'])
@pytest.mark.parametrize('text',[
    "I'm going shopping", "I'm going to class", "I'm going out with friends",
    "I'm going on a date tonight", "I'm meeting friends for dinner", "I'm going to a wedding",
    "I'm presenting my project at university", "I have a university presentation",
    "I'm being interviewed for a job; the dress code is smart casual",
    "I'm going shopping; the dress code is casual", "I'm going shopping; the dress code is formal",
])
def test_same_garment_new_intent_and_legacy_review_have_identical_decisions_scores(everyday_api,style,text):
    client,_=everyday_api;gid=add(client,[style])
    _,first=submit(client,text)
    expected='PolicyUnavailable' if text in ("I have a university presentation","I'm going shopping; the dress code is formal") else (
        'InsufficientEvidence' if ('interviewed' in text or style=='casual' and ('wedding' in text or 'presenting' in text) or style=='smart casual' and 'code is casual' in text) else 'Selected')
    assert first['outcome']==expected,first
    assert review(client,gid,review_style=False).status_code==200
    assert review(client,gid,review_style=True).status_code==200
    _,second=submit(client,text)
    assert second['outcome']==first['outcome']
    if expected=='Selected':
        a,b=first['recommendation'],second['recommendation']
        assert [i['garment_id'] for i in a['items']]==[i['garment_id'] for i in b['items']]==[gid]
        assert a['score_metadata']==b['score_metadata']
        assert (a['request_match_score'],a['compatibility_score'],a['preference_score'],a['total_score'])==(b['request_match_score'],b['compatibility_score'],b['preference_score'],b['total_score'])
        assert all(c['state']=='Pass' for m in a['provenance']['general_context']['members'] for c in m['conditions'])


def test_two_piece_and_optional_unknown_outerwear(everyday_api):
    client,_=everyday_api
    top=add(client,category='long_sleeve_top');bottom=add(client,category='trousers')
    outer=add(client,None,category='long_sleeve_outwear',intent=False)  # Missing style, not merely missing review.
    _,result=submit(client,"I'm going shopping")
    assert result['outcome']=='Selected'
    assert {i['garment_id'] for i in result['recommendation']['items']}=={top,bottom}
    assert outer not in str(result['recommendation']['items'])
    assert result['recommendation']['total_score']==.8


@pytest.mark.parametrize('tags,expected',[
    (['rec:v1:occasion:shopping:deny'],'NoMatchingCandidates'),
    (['rec:v1:occasion:shopping:deny','rec:v1:occasion:shopping:allow'],'NoMatchingCandidates'),
    (['rec:v2:occasion:shopping:allow'],'InsufficientEvidence'),
    (['rec:v1:occasion:shopping:deny','rec:v2:occasion:shopping:allow'],'NoMatchingCandidates'),
    (['rec:v1:occasion:shopping:allow','rec:v1:formality:casual:deny'],'NoMatchingCandidates'),
])
def test_normal_edit_preserves_declarations_and_precedence(everyday_api,tags,expected):
    client,_=everyday_api;gid=add(client,intent=False)
    # Malformed tags are a controlled synthetic persisted input, not silently repaired by a style edit.
    with db.connection() as conn:
        row=conn.execute('SELECT * FROM garments WHERE id=?',(gid,)).fetchone()
        attrs=json.loads(row['attributes_json']);attrs['custom_tags']=tags
        conn.execute('UPDATE garments SET attributes_json=?,additional_attributes=?,custom_tags=? WHERE id=?',(json.dumps(attrs),json.dumps(attrs),json.dumps(tags),gid))
    assert edit(client,gid,'casual').status_code==200
    assert garment(client,gid)['custom_tags']==tags
    _,result=submit(client,"I'm going shopping; the dress code is casual")
    assert result['outcome']==expected


def test_context_root_malformed_and_existing_override_preserved(everyday_api):
    client,_=everyday_api;gid=add(client,intent=False)
    assert review(client,gid,wedding_choice='deny').status_code==200
    assert edit(client,gid,'smart casual').status_code==200
    assert garment(client,gid)['contextual_edit']['wedding_choice']=='deny'
    _,result=submit(client,"I'm going to a wedding");assert result['outcome']=='NoMatchingCandidates'
    with db.connection() as conn:
        row=conn.execute('SELECT * FROM garments WHERE id=?',(gid,)).fetchone();attrs=json.loads(row['attributes_json'])
        attrs['contextual_suitability_v1']={'schema_version':'bad'}
        conn.execute('UPDATE garments SET attributes_json=?,additional_attributes=? WHERE id=?',(json.dumps(attrs),json.dumps(attrs),gid))
    before=garment(client,gid)
    assert edit(client,gid,'casual').status_code==422
    assert garment(client,gid)==before


@pytest.mark.parametrize('state',['archived','unavailable','unconfirmed','foreign','processing_owner'])
def test_new_proof_does_not_change_strict_eligibility(everyday_api,state):
    client,_=everyday_api;gid=add(client)
    db.ensure_user('other-owner')
    if state=='foreign':client.headers['Authorization']='Bearer '+issue_access_token('other-owner')
    else:
        with db.connection() as conn:
            if state in ('archived','unavailable'):conn.execute('UPDATE garments SET status=? WHERE id=?',(state,gid))
            elif state=='unconfirmed':conn.execute("UPDATE processing_items SET review_status='pending' WHERE id=(SELECT processing_item_id FROM garments WHERE id=?)",(gid,))
            else:conn.execute("UPDATE processing_jobs SET user_id='other-owner' WHERE id=(SELECT job_id FROM processing_items WHERE id=(SELECT processing_item_id FROM garments WHERE id=?))",(gid,))
    assert submit(client,"I'm going shopping")[1]['outcome']=='NoEligibleGarments'


def test_candidate_confirmation_and_edit_transactions_rollback(everyday_api):
    client,_=everyday_api;job,item,update=prepare(client,['casual']);base='/api/v1/processing/jobs/'+job['id']
    assert client.post(base+'/review',json={'items':[update]}).status_code==200
    with db.connection() as conn:conn.execute("CREATE TRIGGER owner_style_abort BEFORE INSERT ON garments BEGIN SELECT RAISE(ABORT,'synthetic'); END")
    with pytest.raises(sqlite3.IntegrityError):client.post(base+'/confirm',json={'item_ids':[item['id']],'save_mode':'garments'})
    assert client.get('/api/v1/wardrobe/garments').json()==[]
    assert client.get(base).json()['items'][0]['review_status']=='accepted'
    with db.connection() as conn:conn.execute('DROP TRIGGER owner_style_abort')
    response=client.post(base+'/confirm',json={'item_ids':[item['id']],'save_mode':'garments'});assert response.status_code==201
    gid=response.json()['garment_ids'][0];before=garment(client,gid)
    with db.connection() as conn:conn.execute("CREATE TRIGGER owner_edit_abort BEFORE UPDATE ON garments BEGIN SELECT RAISE(ABORT,'synthetic'); END")
    with pytest.raises(sqlite3.IntegrityError):edit(client,gid,'smart casual')
    assert garment(client,gid)==before


def test_rank_commit_currency_history_and_logout(everyday_api,monkeypatch):
    client,_=everyday_api;gid=add(client);service=assistant_service();original=service.repository.persist_assistant
    def changed(command):
        assert edit(client,gid,'classic').status_code==200
        return original(command)
    monkeypatch.setattr(service.repository,'persist_assistant',changed)
    assert submit(client,"I'm going shopping")[1]['outcome']=='WardrobeChanged'
    with db.connection() as conn:assert conn.execute('SELECT count(*) FROM nlp_chats').fetchone()[0]==0
    monkeypatch.setattr(service.repository,'persist_assistant',original)
    assert edit(client,gid,'casual').status_code==200
    key=uuid.uuid4().hex;text="I'm going shopping";_,saved=submit(client,text,key)
    assert saved['outcome']=='Selected'
    assert patch_tags(client,gid,['rec:v1:occasion:shopping:deny']).status_code==200
    assert edit(client,gid,'smart casual').status_code==200
    _,replay=submit(client,text,key);assert replay['replayed'] and replay['recommendation']==saved['recommendation']
    assert submit(client,text)[1]['outcome']=='NoMatchingCandidates'
    assert submit(client,text+' with blue',key)[1]['outcome']=='IdempotencyConflict'
    assert client.get('/api/v1/wardrobe/quota').json()['limit']==100
    token=client.headers['Authorization'];assert client.post('/api/v1/account/logout').status_code==204
    assert client.get('/api/v1/wardrobe/garments',headers={'Authorization':token}).status_code==401


def test_owner_isolation_for_new_intent(everyday_api,monkeypatch):
    client,_=everyday_api;gid=add(client);g=garment(client,gid);job,item,update=prepare(client,['casual'])
    db.ensure_user('other-owner');client.headers['Authorization']='Bearer '+issue_access_token('other-owner')
    assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'attributes':{'style':['casual']},'style_confirmation':{'contract':CONTRACT,'expected_revision':g['style_confirmation']['revision'],'style':'casual'}}).status_code==404
    assert client.post('/api/v1/processing/jobs/'+job['id']+'/review',json={'items':[update]}).status_code==404
    from app.infrastructure import security
    monkeypatch.setattr(security,'ALLOW_DEVELOPMENT_IDENTITY',False);client.headers.pop('Authorization')
    assert client.get('/api/v1/wardrobe/garments').status_code==401
