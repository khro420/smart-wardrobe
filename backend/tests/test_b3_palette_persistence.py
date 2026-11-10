"""Essential C2 integrity, writer-race and wearer-bound history checks."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json,uuid
import pytest
from tests.test_b3_palette_integration import palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,populate,submit,save,qualify
from app.application.ports.assistant_runtime import assistant_service
from app.infrastructure.persistence import postgresql_repository as db
from app.domain.value_objects.palette_compatibility import PROFILE

def totals():
    with db.connection() as conn:return tuple(conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('recommendations','nlp_chats','recommendation_submissions'))

def test_full_collection_palette_race_is_atomic_even_for_unselected_member(palette_api,monkeypatch):
    client,wearer=palette_api;ids=populate(client);repository=assistant_service().repository;persist=repository.persist_assistant
    def changed(command):
        selected={m.garment.garment_id for m in command.candidate.members}
        gid=next(gid for gid in ids.values() if gid not in selected)
        qualify(client,gid,colour_palette=[{'hex':'#000000','coverage':'1'}])
        return persist(command)
    monkeypatch.setattr(repository,'persist_assistant',changed)
    reply,value=submit(client,wearer)
    assert reply.status_code==409 and value['outcome']=='RefinementScopeChanged',value
    assert totals()==(0,0,0)

@pytest.mark.parametrize('p2',[False,True])
def test_completed_replay_and_history_do_not_need_active_C2_or_vocabulary_loaders(palette_api,p2,monkeypatch):
    from app.application.recommendation.palette_compatibility_policy import PalettePolicy
    from app.application.nlp.vocabulary import Vocabulary
    client,wearer=palette_api;populate(client);key=uuid.uuid4().hex
    reply,root=submit(client,wearer,key=key,p2=p2);assert reply.status_code==201,root
    def blocked(*a,**k):raise AssertionError('Active loader called during C2 historical reconstruction')
    monkeypatch.setattr(PalettePolicy,'load',blocked);monkeypatch.setattr(Vocabulary,'load',blocked)
    assistant_service().compatibility_policy=None
    reply,replay=submit(client,wearer,key=key,p2=p2)
    assert reply.status_code==200 and replay['id']==root['id'],replay
    history=client.get('/api/v1/chats/'+root['chat_id']);assert history.status_code==200,history.text
    assert history.json()['recommendation']['score_metadata']==root['score_metadata']

@pytest.mark.parametrize('case',['policy','fraction','score','revision','wearer','missing_archive','relative_binding'])
def test_corrupt_archived_C2_is_visible_and_never_repaired(palette_api,case,monkeypatch):
    from app.application.recommendation.palette_compatibility_policy import digest
    client,wearer=palette_api;populate(client);key=uuid.uuid4().hex
    reply,root=submit(client,wearer,key=key);assert reply.status_code==201,root
    with db.connection() as conn:
        row=conn.execute('SELECT provenance_json,score_json FROM recommendation_metadata WHERE recommendation_id=?',(root['id'],)).fetchone()
        provenance=json.loads(row[0]);score=json.loads(row[1]);archive=provenance['palette_compatibility']
        if case=='policy':archive['policy_snapshot']['model_sources']=[{'unregistered':True}]
        elif case=='fraction':archive['selected'][0]['description']['fields']['colour_palette']['canonical_values'][0]['coverage']='0'
        elif case=='score':score['compatibility']['decision']['value']={'numerator':'0','denominator':'1'}
        elif case=='wearer':archive['wearer_id']=str(uuid.uuid4())
        elif case=='missing_archive':provenance.pop('palette_compatibility')
        elif case=='relative_binding':provenance['context_relevance']['compatibility_policy_sha256']='0'*64
        else:archive['revision']='0'*64
        if case not in ('revision','missing_archive'):
            body=dict(archive);body.pop('revision');archive['revision']=digest(body)
        raw=json.dumps(provenance);metadata=json.dumps(score)
        conn.execute('UPDATE recommendation_metadata SET provenance_json=?,score_json=? WHERE recommendation_id=?',(raw,metadata,root['id']))
    monkeypatch.setattr(assistant_service().attribute_pipeline,'interpret',lambda *a,**k:pytest.fail('Corrupt receipt reinterpreted'))
    reply,value=submit(client,wearer,key=key)
    assert reply.status_code==503 and value['outcome']=='PersistenceFailure',value
    assert totals()==(1,1,1)
    with db.connection() as conn:assert tuple(conn.execute('SELECT provenance_json,score_json FROM recommendation_metadata WHERE recommendation_id=?',(root['id'],)).fetchone())==(raw,metadata)

def test_same_parent_concurrency_coalesces_one_atomic_C2_child(palette_api):
    client,wearer=palette_api;populate(client);reply,root=submit(client,wearer);assert reply.status_code==201,root
    action=root['scoring_display']['refinement']['next_action']
    def call(_):return submit(client,wearer,root['request_text'],action['submission_key'],refinement=action['refinement'])
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(call,range(2)))
    assert sorted(reply.status_code for reply,value in responses)==[200,201],responses
    assert len({value['id'] for reply,value in responses})==1 and totals()==(2,2,2)

def test_shared_inventory_has_independent_C2_P2_wearer_preferences(palette_api):
    from tests.test_p2_preference_selection import family
    client,a=palette_api;ids=populate(client)
    b=client.post('/api/v1/account/wardrobe-profiles',json={'name':'Second wearer'}).json()['id']
    client.headers['X-Wardrobe-Profile-Id']=a;save(client,a,{'colour':family('primary_colour',['blue'])})
    key=uuid.uuid4().hex;reply,first=submit(client,a,key=key,p2=True);assert reply.status_code==201,first
    client.headers['X-Wardrobe-Profile-Id']=b;save(client,b,{'colour':family('primary_colour',['green'])})
    reply,second=submit(client,b,p2=True);assert reply.status_code==201,second
    assert first['items'][0]['garment_id']==ids['Blue T-shirt'] and second['items'][0]['garment_id']==ids['Green Sweatshirt']
    assert first['provenance']['attribute_preference']['snapshot']['wearer_id']==a
    assert second['provenance']['attribute_preference']['snapshot']['wearer_id']==b
    assert first['provenance']['palette_compatibility']['collection_sha256']==second['provenance']['palette_compatibility']['collection_sha256']
    # A completed action cannot be reassigned to a different wearer.
    reply,value=submit(client,b,key=key,p2=True)
    assert reply.status_code==409 and value['outcome']=='IdempotencyConflict',value

def test_wrong_mode_cannot_continue_an_existing_C1_or_C2_root(palette_api):
    client,wearer=palette_api;populate(client)
    for original,new in ((None,PROFILE),(PROFILE,None)):
        reply,root=submit(client,wearer,profile=original);assert reply.status_code==201,root
        action=root['scoring_display']['refinement']['next_action']
        reply,value=submit(client,wearer,root['request_text'],action['submission_key'],refinement=action['refinement'],profile=new)
        assert reply.status_code==409 and value['outcome']=='IdempotencyConflict',value

@pytest.mark.parametrize('engine,p2',[('compact_exhaustive',False),('reference',True)])
def test_ten_result_cap_Seen_and_original_R_floor_remain_effective(palette_api,engine,p2):
    from tests.test_automatic_admission_integration import legacy
    client,wearer=palette_api;populate(client);assistant_service().execution_engine=engine
    for _ in range(9):
        gid=legacy(client,'casual','vest')
        qualify(client,gid,colour_palette=[{'hex':'#0000ff','coverage':'1'}])
    reply,root=submit(client,wearer,p2=p2);assert reply.status_code==201,root
    current=root;seen=set()
    for ordinal in range(10):
        proof=current['provenance']['refinement'];assert proof['ordinal']==ordinal
        base=tuple((v['garment_role'],v['garment_id']) for v in current['items'] if v['garment_role']!='outerwear')
        assert base not in seen;seen.add(base)
        assert proof['root_R']==root['provenance']['refinement']['root_R']
        if ordinal<9:
            action=current['scoring_display']['refinement']['next_action']
            reply,current=submit(client,wearer,root['request_text'],action['submission_key'],p2,action['refinement'])
            assert reply.status_code==201,current
    assert current['scoring_display']['refinement']['next_action'] is None
    assert current['scoring_display']['refinement']['limit_reached'] is True
    action={'version':'assistant-refinement-request-1.0.0','kind':'alternative','parent_recommendation_id':current['id']}
    reply,value=submit(client,wearer,root['request_text'],'refine:v1:'+root['id']+':10',p2,action)
    assert reply.status_code==200 and value['outcome']=='RefinementLimitReached',value
    assert totals()==(10,10,10)

def test_archived_wearer_keeps_C2_receipt_and_historical_explanation(palette_api):
    client,wearer=palette_api;populate(client);key=uuid.uuid4().hex
    reply,root=submit(client,wearer,key=key,p2=True);assert reply.status_code==201,root
    assert client.post('/api/v1/account/wardrobe-profiles',json={'name':'Replacement wearer'}).status_code==201
    archived=client.post('/api/v1/account/wardrobe-profiles/'+wearer+'/archive');assert archived.status_code==200,archived.text
    reply,replay=submit(client,wearer,key=key,p2=True);assert reply.status_code==200 and replay['id']==root['id'],replay
    history=client.get('/api/v1/chats/'+root['chat_id'],params={'view':'historical','wearer_profile_id':wearer})
    assert history.status_code==200,history.text
    assert history.json()['recommendation']['scoring_display']==root['scoring_display']
