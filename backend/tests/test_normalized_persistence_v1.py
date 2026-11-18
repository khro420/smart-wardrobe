"""Authenticated disposable v8 receipts, exact raw history and independent proofs."""
import json,uuid,pytest
from tests.test_local_preference_activation import enabled,post
from tests.test_request_local_persistence import (local_store,category_api,language_api,palette_api,p2_api,attribute_api,
    refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,runtime_boundary,counts)
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.ports.assistant_runtime import assistant_service
from app.application.nlp.normalized_request_v1 import ENVIRONMENT_KEY,PROFILE
from app.domain.value_objects.attribute_conditions import encode,digest
from app.application.recommendation.normalized_workflow_v1 import KEY,NormalizedProof,verify

@pytest.fixture
def normalized(enabled,monkeypatch):
    monkeypatch.setenv(ENVIRONMENT_KEY,PROFILE);configure_local_workflow()
    client,_,owner,male,female=enabled
    return client,assistant_service().repository,owner,male,female

@pytest.mark.parametrize('engine',['reference','compact_exhaustive'])
@pytest.mark.parametrize('raw,canonical',[
    ('pls suggest an outfit','please suggest an outfit'),
    ('I NEED BLACK TROUSERS PLS','I need black trousers.'),
    ('id prefer black trousers',"I'd prefer black trousers."),
    ('i need trousers preferably black','I need trousers, preferably black.')])
def test_persist_exact_original_compare_base_winner_and_replay(normalized,engine,raw,canonical):
    client,repo,owner,_,female=normalized;service=assistant_service();service.input_normalization.engine=engine
    service.execution_engine=engine;service.local_preferences.engine=engine
    cap=client.get('/api/v1/recommendations/capabilities').json()
    assert cap['input_normalization']['enabled'] and cap['input_normalization']['grammar_version']=='conversational-normalized-grammar-1.8.0'
    key=uuid.uuid4().hex;result=post(client,female,raw,key)
    assert result.status_code==201,result.json().get('outcome')
    saved=result.json();assert saved['request_text']==raw and saved['input_normalization']['grammar_version'].endswith('1.8.0')
    proof=NormalizedProof(encode(saved['provenance'][KEY]));assert proof.to_dict()['intent']['normalization']['original_text']==raw
    active=service.input_normalization;service.input_normalization=None
    try:baseline=post(client,female,canonical)
    finally:service.input_normalization=active
    assert baseline.status_code==201,baseline.json().get('outcome')
    assert [i['garment_id'] for i in saved['items']]==[i['garment_id'] for i in baseline.json()['items']]
    assert saved['score_metadata']==baseline.json()['score_metadata']
    before=counts(repo);replay=post(client,female,raw,key)
    assert replay.status_code==200 and replay.json()['replayed'] and replay.json()['id']==saved['id']
    history=client.get('/api/v1/chats/'+saved['chat_id'],headers={'X-Wardrobe-Profile-Id':female})
    assert history.status_code==200,history.text
    assert history.json()['request_text']==raw
    assert history.json()['recommendation']['input_normalization']==saved['input_normalization']
    assert counts(repo)==before
    with repo._connect() as conn:assert conn.execute('SELECT request_text FROM nlp_chats WHERE id=?',(saved['chat_id'],)).fetchone()[0]==raw

def test_gray_and_grey_select_identically_with_correct_lower_binding(normalized):
    from tests.test_attribute_persistence import qualify
    client,repo,_,_,female=normalized
    ids={g['name']:g['id'] for g in client.get('/api/v1/wardrobe/garments',headers={'X-Wardrobe-Profile-Id':female}).json()}
    qualify(client,ids['Blue T-shirt'],primary_colour='grey')
    # A grey upper cannot satisfy the lower garment's colour.
    before=counts(repo)
    for text in ('I need gray trousers.','I need grey trousers.'):
        reply=post(client,female,text);assert reply.status_code==200 and reply.json()['outcome']=='NoMatchingCandidates',reply.text
    assert counts(repo)==before
    qualify(client,ids['Black Trousers'],primary_colour='grey')
    results=[post(client,female,text) for text in ('I need gray trousers.','I need grey trousers.')]
    assert all(r.status_code==201 for r in results),[r.json().get('outcome') for r in results]
    assert [i['garment_id'] for i in results[0].json()['items']]==[i['garment_id'] for i in results[1].json()['items']]
    assert next(i['garment_id'] for i in results[0].json()['items'] if i['garment_role']=='lower')==ids['Black Trousers']
    assert results[0].json()['score_metadata']==results[1].json()['score_metadata']

@pytest.mark.parametrize('change',['text','wearer','typed','p2','action'])
def test_raw_receipt_conflicts_do_not_reparse_or_write(normalized,change):
    client,repo,_,male,female=normalized;key=uuid.uuid4().hex
    root=post(client,female,'id prefer black trousers',key);assert root.status_code==201,root.text
    before=counts(repo);text='id prefer black trousers';extra={};wearer=female
    if change=='text':text="I'd prefer black trousers."
    elif change=='wearer':wearer=male
    elif change=='typed':extra['attribute_conditions']={'version':'attribute-conditions-1.0.0','groups':[{'id':'g01','role':'lower','quantifier':'exists','conditions':[{'id':'c01','attribute':'category','operator':'in','values':['trousers']}]}]}
    elif change=='p2':extra['preference_profile']='attribute_preference_decision_v2'
    else:extra['refinement']={'version':'assistant-refinement-request-1.0.0','kind':'alternative','parent_recommendation_id':root.json()['id']}
    result=post(client,wearer,text,key,**extra);assert result.status_code==409,result.text
    assert counts(repo)==before

def test_disabled_flag_preserves_new_and_old_history(normalized,monkeypatch):
    client,repo,_,_,female=normalized;key=uuid.uuid4().hex;root=post(client,female,'id prefer black trousers',key)
    assert root.status_code==201,root.text
    monkeypatch.setenv(ENVIRONMENT_KEY,'disabled');configure_local_workflow()
    before=counts(repo);replayed=post(client,female,'id prefer black trousers',key)
    assert replayed.status_code==200 and replayed.json()['id']==root.json()['id']
    assert post(client,female,'id prefer black trousers').status_code==422
    assert counts(repo)==before
    oldkey=uuid.uuid4().hex;old=post(client,female,"I'd prefer black trousers.",oldkey);assert old.status_code==201
    monkeypatch.setenv(ENVIRONMENT_KEY,PROFILE);configure_local_workflow()
    oldreplay=post(client,female,"I'd prefer black trousers.",oldkey)
    assert oldreplay.status_code==200 and oldreplay.json()['provenance']==old.json()['provenance']

@pytest.mark.parametrize('stage',['normalized_revalidated','metadata','before_commit'])
def test_atomic_rollback_and_same_key_recovery(normalized,stage):
    client,repo,_,_,female=normalized;before=counts(repo);key=uuid.uuid4().hex
    def fail(where,conn):
        if where==stage:raise RuntimeError('Disposable normalized rollback control')
    repo.checkpoint=fail
    reply=post(client,female,'id prefer black trousers',key);assert reply.status_code==503,reply.text
    assert counts(repo)==before
    repo.checkpoint=lambda *a:None
    assert post(client,female,'id prefer black trousers',key).status_code==201

def test_locked_source_change_is_not_trusted(normalized):
    client,repo,_,_,female=normalized;before=counts(repo)
    def changed(stage,conn):
        if stage=='normalized_before_revalidation':conn.execute("UPDATE garments SET name='changed under lock' WHERE id=(SELECT id FROM garments ORDER BY id LIMIT 1)")
    repo.checkpoint=changed
    result=post(client,female,'id prefer black trousers');assert result.status_code==409 and result.json()['outcome']=='WardrobeChanged',result.text
    assert counts(repo)==before
    with repo._connect() as conn:assert not conn.execute("SELECT 1 FROM garments WHERE name='changed under lock'").fetchone()

def test_tampered_source_and_mapping_fail_after_recomputed_revision(normalized):
    client,repo,owner,_,female=normalized;root=post(client,female,'i need trousers preferably black')
    assert root.status_code==201,root.text
    original=root.json()['provenance'][KEY]
    for change in ('map','winner'):
        value=json.loads(json.dumps(original))
        if change=='map':value['intent']['normalization']['character_map'][0]=[0,0]
        else:value['evaluation']['decision']['selected']['key'][0][1]=str(uuid.uuid4())
        value['revision']='';value['revision']=digest(value)
        with pytest.raises(ValueError):verify(NormalizedProof(encode(value)),owner,female)

def test_unsupported_scopes_are_explicit_refusals_without_writes(normalized):
    client,repo,_,_,female=normalized;before=counts(repo)
    for text in ('pls no shorts, preferably black trousers','im going shopping pls suggest an outfit'):
        reply=post(client,female,text);assert reply.status_code==422,reply.text
    assert counts(repo)==before

def test_mandatory_unknown_refuses_but_optional_unknown_can_keep_baseline(normalized):
    from tests.test_local_preference_diagnostics import clear_fixture_primary_sources
    from tests.test_request_local_persistence import restrict
    client,repo,_,_,female=normalized
    restrict(client,repo,['Blue T-shirt','Black Trousers']);clear_fixture_primary_sources(repo);before=counts(repo)
    hard=post(client,female,'pls suggest black trousers')
    assert hard.status_code==200 and hard.json()['outcome']=='InsufficientEvidence',hard.text
    assert counts(repo)==before
    soft=post(client,female,'id prefer black trousers');assert soft.status_code==201,soft.text
    decision=soft.json()['scoring_display']['decision']
    assert decision['selected_optional']['state']=='Unverifiable' and decision['selected_optional']['support']==0
    assert decision['selected']['key']==decision['baseline']['key']

def test_current_context_requests_stay_on_original_path(normalized):
    client,_,_,_,female=normalized
    reply=post(client,female,'im going shopping')
    assert reply.status_code==201,reply.text
    assert KEY not in reply.json()['provenance']
    assert reply.json()['score_metadata']['profile_name']=='context_relevance_decision_v1'

def test_cross_owner_history_never_exposes_new_proof(normalized):
    from app.infrastructure.persistence import postgresql_repository as db
    from app.infrastructure.security import issue_access_token
    client,repo,_,_,female=normalized;root=post(client,female,'id prefer black trousers');assert root.status_code==201
    db.ensure_user('normalized-other-owner')
    reply=client.get('/api/v1/chats/'+root.json()['chat_id'],headers={'Authorization':'Bearer '+issue_access_token('normalized-other-owner'),'X-Wardrobe-Profile-Id':female})
    assert reply.status_code in (403,404),reply.text

@pytest.mark.parametrize('engine',['reference','compact_exhaustive'])
@pytest.mark.parametrize('kind',['negative','compound'])
def test_normalized_negative_and_compound_hard_admission(normalized,engine,kind):
    from tests.test_attribute_persistence import qualify
    client,repo,_,_,female=normalized;assistant_service().input_normalization.engine=engine
    ids={g['name']:g['id'] for g in client.get('/api/v1/wardrobe/garments',headers={'X-Wardrobe-Profile-Id':female}).json()}
    if kind=='compound':qualify(client,ids['Blue T-shirt'],pattern='plain',material=['cotton'])
    raw='DONT GIVE ME SHORTS!!!' if kind=='negative' else 'I NEED A PLAIN COTTON TOP WITH BLACK TROUSERS.'
    reply=post(client,female,raw);assert reply.status_code==201,reply.text
    result=reply.json();assert result['request_text']==raw
    if kind=='negative':assert all(i['category']!='shorts' for i in result['items'])
    else:
        items={i['garment_role']:i['garment_id'] for i in result['items']}
        assert items['upper']==ids['Blue T-shirt'] and items['lower']==ids['Black Trousers']

def test_default_disabled_and_invalid_dependencies_do_not_activate(local_store,monkeypatch):
    client,_,_,_,_,_=local_store
    assert client.get('/api/v1/recommendations/capabilities').json()['input_normalization']['enabled'] is False
    monkeypatch.setenv(ENVIRONMENT_KEY,PROFILE)
    with pytest.raises(ValueError,match='dependency bundle'):configure_local_workflow()

def test_persisted_tampering_cannot_drop_proof_or_change_display_scalars(normalized):
    client,repo,_,_,female=normalized;root=post(client,female,'id prefer black trousers')
    assert root.status_code==201,root.text
    saved=root.json()
    with repo._connect() as conn:
        metadata=tuple(conn.execute('SELECT provenance_json,score_json FROM recommendation_metadata WHERE recommendation_id=?',(saved['id'],)).fetchone())
        total=conn.execute('SELECT total_score FROM recommendations WHERE id=?',(saved['id'],)).fetchone()[0]
    for change in ('missing_proof','scalar'):
        with repo._connect() as conn:
            if change=='missing_proof':conn.execute("UPDATE recommendation_metadata SET provenance_json='{}' WHERE recommendation_id=?",(saved['id'],))
            else:conn.execute('UPDATE recommendations SET total_score=0.999 WHERE id=?',(saved['id'],))
        reply=client.get('/api/v1/chats/'+saved['chat_id'],headers={'X-Wardrobe-Profile-Id':female})
        assert reply.status_code==503,reply.text
        with repo._connect() as conn:
            conn.execute('UPDATE recommendation_metadata SET provenance_json=?,score_json=? WHERE recommendation_id=?',(*metadata,saved['id']))
            conn.execute('UPDATE recommendations SET total_score=? WHERE id=?',(total,saved['id']))
    assert client.get('/api/v1/chats/'+saved['chat_id'],headers={'X-Wardrobe-Profile-Id':female}).status_code==200

def test_leading_spaces_and_punctuation_are_kept_exactly_in_database_history(normalized):
    client,repo,_,_,female=normalized;raw='  PLZ   SUGGEST  AN OUTFIT!!!  '
    reply=post(client,female,raw);assert reply.status_code==201,reply.text
    assert reply.json()['request_text']==raw
    history=client.get('/api/v1/chats/'+reply.json()['chat_id'],headers={'X-Wardrobe-Profile-Id':female})
    assert history.status_code==200 and history.json()['request_text']==raw
