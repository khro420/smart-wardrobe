"""Approved, pre-frozen EC scenarios through real disposable authenticated APIs."""
import json
import os
from pathlib import Path
import uuid
import pytest
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.security import issue_access_token
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.ports.assistant_runtime import assistant_service
from tests.test_release_configuration import release, submit
from tests.test_forward_style_semantics import lifecycle
from tests.test_contextual_wedding import patch, review
from tests.test_suitability_controls import patch_tags

LABELS=json.loads((Path(__file__).with_name('fixtures')/'everyday_context_labels.v1.json').read_text(encoding='utf-8'))


@pytest.fixture
def everyday_api(release,monkeypatch):
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE','general_context_v1')
    configure_local_workflow()
    return release


def add(client,create,style='casual',category='vest_dress',reviewed=True):
    gid=create([style]);patch(client,gid,{'category':category,'primary_colour':'blue'})
    assert patch_tags(client,gid,[]).status_code==200
    if reviewed: assert review(client,gid,review_style=True).status_code==200
    return gid


@pytest.mark.parametrize('case',LABELS['scenarios'],ids=lambda c:c['id'])
def test_approved_matrix(everyday_api,case):
    client,create=everyday_api;fixture,text=case['fixture'],case['text']
    style='smart casual' if fixture in ('R_smart','old_wedding') else 'classic' if fixture=='C' else 'casual'
    if fixture!='empty':
        gid=add(client,create,style,'long_sleeve_top' if fixture=='only_upper' else 'vest_dress',fixture not in ('U','A','legacy_formality_allow'))
        target='campus' if case['id'].startswith('CA') else 'shopping' if case['id'].startswith('SH') else 'casual_outing' if case['id'].startswith('CO') else 'shopping'
        tags=[]
        if fixture in ('A','D','X'): tags=['rec:v1:occasion:'+target+':'+d for d in (['allow'] if fixture=='A' else ['deny'] if fixture=='D' else ['allow','deny'])]
        if fixture=='M': tags=['rec:v2:occasion:'+target+':allow']
        if fixture=='occasion_allow_formality_deny': tags=['rec:v1:occasion:shopping:allow','rec:v1:formality:casual:deny']
        if fixture=='R_unrequested_formality_deny': tags=['rec:v1:formality:smart_casual:deny']
        if fixture=='legacy_formality_allow': tags=['rec:v1:formality:casual:allow']
        assert patch_tags(client,gid,tags).status_code==200
        if fixture=='R_red': patch(client,gid,{'primary_colour':'red'})
        if fixture=='R_stale': patch(client,gid,{'category':'sling_dress'})
        if fixture=='R_outer_unknown': outer=add(client,create,reviewed=False,category='long_sleeve_outwear')
    response,result=submit(client,text)
    folder=os.environ.get('SMART_WARDROBE_EVERYDAY_EVIDENCE')
    if folder:
        path=Path(folder)/('case-'+case['id']+'.json');assert not path.exists()
        path.write_text(json.dumps({'label':case,'http_status':response.status_code,'response':result},indent=2)+'\n',encoding='utf-8')
    expected='Selected' if case['expected']=='Preserved' else case['expected']
    # Approved 1.4 transition overlay; the frozen Phase 5 fixture is unchanged.
    if case['id'] in ('CA03','SH03','CO03','N17'): expected='Selected'
    assert result['outcome']==expected,result
    if expected=='Selected':
        assert response.status_code==201 and result['complete']
        if case['id'] not in ('N23','N24','N25','N32'):
            proof=result['recommendation']['provenance']['general_context']
            assert proof['version']=='general-context-explanation-1.4.0'
            assert proof['declaration_target'] in ('campus','shopping','casual_outing')
            assert all(c['state']=='Pass' for m in proof['members'] for c in m['conditions'])
            assert not any('appearance_observations' in m for m in proof['members'])
            assert 'provisional' in proof['limits_note']
            if 'dress code' not in text:
                assert proof['formality'] is None and proof['dress_code'] is None
            if case['id']=='N18':
                # Approved 1.4 transition: this outerwear has a valid saved style.
                assert {i['garment_id'] for i in result['recommendation']['items']}=={gid,outer}
                assert result['score_metadata']['total']=={'numerator':4,'denominator':5}
                member=next(m for m in proof['members'] if m['garment_id']==outer)
                assert all(c['basis']=='saved_attribute_provisional' for c in member['conditions'])
    else:
        assert 'recommendation' not in result
        with db.connection() as conn:
            assert conn.execute('SELECT count(*) FROM nlp_chats').fetchone()[0]==0


@pytest.mark.parametrize('state',['archived','unavailable','unconfirmed','foreign','processing_owner'])
def test_strict_real_query_exclusions(everyday_api,state):
    client,create=everyday_api;gid=add(client,create)
    if state=='foreign':
        db.ensure_user('foreign-owner');client.headers['Authorization']='Bearer '+issue_access_token('foreign-owner')
    else:
        with db.connection() as conn:
            if state in ('archived','unavailable'): conn.execute('UPDATE garments SET status=? WHERE id=?',(state,gid))
            elif state=='unconfirmed': conn.execute('UPDATE processing_items SET review_status=? WHERE id=(SELECT processing_item_id FROM garments WHERE id=?)',('pending',gid))
            else:
                db.ensure_user('foreign-owner')
                conn.execute('UPDATE processing_jobs SET user_id=? WHERE id=(SELECT job_id FROM processing_items WHERE id=(SELECT processing_item_id FROM garments WHERE id=?))',('foreign-owner',gid))
    _,result=submit(client,"I'm going shopping")
    assert result['outcome']=='NoEligibleGarments',result


@pytest.mark.parametrize('suffix',[" with vintage style"," with a long sleeve top"])
def test_hard_style_and_category_fail_before_scoring(everyday_api,suffix):
    client,create=everyday_api;add(client,create)
    _,result=submit(client,"Suggest an outfit for shopping"+suffix)
    assert result['outcome']=='NoMatchingCandidates',result


def test_snapshot_change_and_real_atomic_rollback_recovery(everyday_api,monkeypatch):
    client,create=everyday_api;gid=add(client,create)
    service=assistant_service();original=service.repository.persist_assistant
    def changed(command):
        assert review(client,gid,review_style=False).status_code==200
        return original(command)
    monkeypatch.setattr(service.repository,'persist_assistant',changed)
    _,result=submit(client,"I'm going shopping")
    assert result['outcome']=='WardrobeChanged'
    monkeypatch.setattr(service.repository,'persist_assistant',original)
    assert review(client,gid,review_style=True).status_code==200
    with db.connection() as conn:
        conn.execute("CREATE TRIGGER everyday_abort BEFORE INSERT ON recommendation_items BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
    key=uuid.uuid4().hex;_,result=submit(client,"I'm going shopping",key)
    assert result['outcome']=='PersistenceFailure'
    with db.connection() as conn:
        for table in ('nlp_chats','recommendations','recommendation_submissions','recommendation_items'):
            assert conn.execute('SELECT count(*) FROM '+table).fetchone()[0]==0
        conn.execute('DROP TRIGGER everyday_abort')
    _,selected=submit(client,"I'm going shopping",key);assert selected['outcome']=='Selected'
    _,replay=submit(client,"I'm going shopping",key);assert replay['replayed'] and replay['recommendation']==selected['recommendation']


def test_cross_profile_immutable_replay_and_logout(everyday_api,monkeypatch):
    client,create=everyday_api;gid=add(client,create);key=uuid.uuid4().hex;text='Suggest an outfit for shopping'
    _,selected=submit(client,text,key);assert selected['outcome']=='Selected'
    assert patch_tags(client,gid,['rec:v1:occasion:shopping:deny']).status_code==200
    for profile in ('disabled','wedding_guest_v1','general_context_v1'):
        monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE',profile);configure_local_workflow()
        _,replay=submit(client,text,key)
        assert replay['replayed'] and replay['recommendation']==selected['recommendation']
        _,fresh=submit(client,text);assert fresh['outcome']=='NoMatchingCandidates'
    _,conflict=submit(client,text+' with blue',key);assert conflict['outcome']=='IdempotencyConflict'
    assert client.get('/api/v1/wardrobe/quota').json()['limit']==100
    copied=client.headers['Authorization'];assert client.post('/api/v1/account/logout').status_code==204
    assert client.get('/api/v1/recommendations/capabilities',headers={'Authorization':copied}).status_code==401
