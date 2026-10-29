"""Read-only history, literal search, cursor privacy and historical restoration."""
from dataclasses import replace
import json
import sqlite3
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.application.chat_history.chat_history_service import ChatHistoryService
from app.application.ports.chat_history_runtime import chat_history_service
from app.infrastructure.persistence.chat_history_query_adapter import SqliteChatHistoryQuery
from app.infrastructure.security import issue_access_token
from tests.test_recommendation_persistence import store,assistant,connect
from tests.test_outfit_assistant import assistant_store,service as assistant_pipeline


def save(store,text='Suggest an outfit',key='key'):
    return store[1].persist(replace(assistant(store[2]),request_text=text,submission_key=key))


def query(store):
    return SqliteChatHistoryQuery(store[0],cursor_secret='synthetic-test-secret')


def test_empty_and_case_insensitive_literal_search(store):
    q = query(store)
    assert q.search('owner')['status'] == 'NoResults'
    texts = ['Vintage 100% cotton_look!','Blue dress','CAFÉ Straße','literal \\ slash']
    saved = [save(store,text,str(index)) for index,text in enumerate(texts)]
    assert q.search('owner')['total'] == 4
    for term,expected in [('vInTaGe',1),('%',1),('_',1),('!',1),('café',1),('STRASSE',1),('\\',1),("%' OR 1=1 --",0),('no result',0)]:
        result = q.search('owner',term)
        assert result['total'] == expected
    assert q.search('other','Vintage')['items'] == []
    assert q.search('other')['total'] == 0


@pytest.mark.parametrize('change', ["UPDATE nlp_chats SET status='pending'", "UPDATE nlp_chats SET status='failed'", "UPDATE nlp_chats SET completed_at=NULL", "UPDATE recommendations SET status='failed'", "UPDATE recommendations SET chat_id=NULL", "DELETE FROM recommendation_item_snapshots; DELETE FROM recommendation_items", "UPDATE recommendations SET user_id='other'"])
def test_incomplete_or_incoherent_records_excluded(store,change):
    saved = save(store)
    with connect(store[0]) as c:
        c.executescript(change)
    assert query(store).search('owner')['total'] == 0
    with pytest.raises(LookupError): query(store).get('owner',saved['chat_id'])


def test_homepage_excluded_and_saved_assistant_retained(store):
    homepage = store[1].persist(store[2])
    saved = save(store)
    with connect(store[0]) as c:
        c.execute("UPDATE recommendations SET status='saved' WHERE id=?",(saved['id'],))
    result = query(store).search('owner')
    assert result['total'] == 1 and result['items'][0]['recommendation_status'] == 'saved'
    assert result['items'][0]['recommendation_id'] != homepage['id']
    assert query(store).get('owner',saved['chat_id'])['recommendation']['status'] == 'saved'


def test_structured_request_scores_and_snapshots_restore_without_reruns(store,monkeypatch):
    from app.application.nlp.nlp_interpreter import NLPInterpreter
    from app.application.recommendation.recommendation_scorer import RecommendationScorer
    fields = {'intent':'outfit_recommendation','occasion':None,'style':'vintage','colours':None,'garment_categories':None,'formality':None}
    command = replace(assistant(store[2]),request_json=json.dumps(fields),request_text='Original vintage request')
    saved = store[1].persist(command)
    monkeypatch.setattr(NLPInterpreter,'interpret',Mock(side_effect=AssertionError('no NLP')))
    monkeypatch.setattr(RecommendationScorer,'rank',Mock(side_effect=AssertionError('no rank')))
    with connect(store[0]) as c:
        c.execute("UPDATE garments SET name='Current changed name',status='archived'")
    result = query(store).get('owner',saved['chat_id'])
    assert result['request_text'] == 'Original vintage request' and result['structured_request'] == fields
    assert result['read_only'] and result['requires_action_revalidation']
    rec = result['recommendation']
    assert rec['id'] == saved['id'] and rec['score_metadata']['total'] == {'numerator':1,'denominator':1}
    item = rec['items'][0]
    assert (item['name'],item['garment_role'],item['item_order']) == ('Original dress','one_piece',1)
    assert not item['currently_eligible'] and item['preferred_media_id'] is None
    with pytest.raises(LookupError): query(store).get('other',saved['chat_id'])
    with pytest.raises(LookupError): query(store).get('owner','missing')


@pytest.mark.parametrize('change',["DELETE FROM garments", "UPDATE garments SET user_id='other',name='Foreign secret'", "UPDATE garments SET processing_item_id=NULL"])
def test_missing_foreign_or_unconfirmed_current_record_keeps_history(store,change):
    saved = save(store)
    with connect(store[0]) as c: c.execute(change)
    item = query(store).get('owner',saved['chat_id'])['recommendation']['items'][0]
    assert item['garment_id'] == 'garment' and item['name'] == 'Original dress'
    assert not item['currently_eligible'] and item['preferred_media_id'] is None
    assert 'Foreign secret' not in json.dumps(item)


@pytest.mark.parametrize('owner,status,accessible',[('owner','available',True),('other','available',False),('owner','archived',False)])
def test_historical_media_requires_actual_owner_and_availability(store,owner,status,accessible):
    saved = save(store)
    with connect(store[0]) as c:
        c.execute("INSERT INTO media_assets(id,user_id,media_type,storage_key,content_type,size_bytes,status,created_at) VALUES('media',?,'crop','private-key','image/png',1,?,'now')",(owner,status))
    item = query(store).get('owner',saved['chat_id'])['recommendation']['items'][0]
    assert item['historical_media_accessible'] == accessible
    assert (item['preferred_media_id'] is not None) == accessible


def test_valid_legacy_missing_snapshot_metadata_and_keyword_interpretation(store):
    with connect(store[0]) as c:
        c.execute("INSERT INTO nlp_chats VALUES('oldchat','owner','Legacy request','outfit_recommendation','{\"keywords\":[\"legacy\"]}','completed','now','now')")
        c.execute("INSERT INTO recommendations(id,user_id,chat_id,recommendation_type,status,created_at,total_score) VALUES('old','owner','oldchat','wardrobe_outfit','saved','now',0.5)")
        c.execute("INSERT INTO recommendation_items VALUES('old','garment','one_piece',1,'now')")
    result = query(store).get('owner','oldchat')
    assert result['structured_request'] is None and result['interpreted_entities'] == {'keywords':['legacy']}
    rec = result['recommendation']
    assert rec['score_metadata'] is None and rec['provenance'] is None and rec['total_score'] == .5
    assert not rec['items'][0]['snapshot_available'] and rec['items'][0]['name'] is None
    assert query(store).search('owner')['total'] == 1


def test_stable_keyset_pages_and_cursor_binding(store):
    saved = [save(store,'Same search',str(n)) for n in range(7)]
    with connect(store[0]) as c: c.execute("UPDATE nlp_chats SET created_at='2026-01-01T00:00:00Z'")
    expected = sorted(r['chat_id'] for r in saved)
    q = query(store)
    page = q.search('owner','Same',2)
    cursor = page['next_cursor']
    identifiers = [r['chat_id'] for r in page['items']]
    assert page['total'] == 7 and len(identifiers) == 2
    # A newer insertion must not shift the anchored remaining pages.
    save(store,'Same search','newer')
    while cursor:
        page = q.search('owner','Same',2,cursor)
        identifiers += [r['chat_id'] for r in page['items']]
        cursor = page['next_cursor']
    assert identifiers == expected
    for owner,term in [('other','Same'),('owner','changed')]:
        with pytest.raises(ValueError): q.search(owner,term,2,q.search('owner','Same',2)['next_cursor'])
    with pytest.raises(ValueError): q.search('owner','Same',2,'tampered.cursor')


def test_database_enforces_read_only_and_no_changes(store):
    saved = save(store)
    with connect(store[0]) as c: before = list(c.iterdump())
    q = query(store)
    with q._connection('owner') as c:
        assert c.execute('PRAGMA query_only').fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError): c.execute('DELETE FROM nlp_chats')
    q.search('owner')
    q.get('owner',saved['chat_id'])
    with connect(store[0]) as c: assert list(c.iterdump()) == before


def test_multiple_item_order_and_ambiguous_duplicate_chat(store):
    from tests.test_outfit_assistant import add_garment
    from app.domain.value_objects.outfit_candidate import OutfitCandidate,CandidateMember
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    add_garment(store,'outer','long_sleeve_outwear')
    garments = {g.garment_id:g for g in SqliteConfirmedGarmentQuery().get_confirmed_available_garments('owner')}
    candidate = OutfitCandidate((CandidateMember(garments['garment'],'one_piece',1),CandidateMember(garments['outer'],'outerwear',2)))
    saved = store[1].persist(replace(assistant(store[2]),candidate=candidate))
    items = query(store).get('owner',saved['chat_id'])['recommendation']['items']
    assert [(i['garment_id'],i['garment_role'],i['item_order']) for i in items] == [('garment','one_piece',1),('outer','outerwear',2)]
    with connect(store[0]) as c:
        c.execute('DROP INDEX rec_one_chat')
        c.execute("INSERT INTO recommendations(id,user_id,chat_id,recommendation_type,status,created_at) VALUES('duplicate','owner',?,'assistant','available','now')",(saved['chat_id'],))
    assert query(store).search('owner')['total'] == 0


def test_actual_composition_read_service(store,monkeypatch):
    saved = save(store)
    import app.infrastructure.persistence.chat_history_query_adapter as adapter
    monkeypatch.setattr(adapter,'SqliteChatHistoryQuery',lambda:query(store))
    with TestClient(app) as client:
        result = client.get('/api/v1/chats/'+saved['chat_id'],headers={'Authorization':'Bearer '+issue_access_token('owner')})
        assert result.status_code == 200 and result.json()['chat_id'] == saved['chat_id']


def test_corrupt_stored_metadata_is_an_operational_failure(store):
    saved = save(store)
    with connect(store[0]) as c: c.execute("UPDATE recommendation_metadata SET score_json='invalid JSON'")
    with pytest.raises(RuntimeError): query(store).get('owner',saved['chat_id'])


def test_actual_phase5c_record_and_malformed_interpretation(assistant_store,monkeypatch):
    from app.application.nlp.nlp_interpreter import NLPInterpreter
    saved = assistant_pipeline(assistant_store).recommend('owner','history-integration','Suggest an outfit with vintage style')
    assert saved['status'] == 'Selected'
    monkeypatch.setattr(NLPInterpreter,'interpret',Mock(side_effect=AssertionError('no replay NLP')))
    restored = query(assistant_store).get('owner',saved['chat_id'])
    assert restored['structured_request']['style'] == 'vintage'
    assert restored['recommendation']['total_score'] == .7
    assert restored['recommendation']['provenance']['scoring_profile'] == 'compatibility_deferred'
    with connect(assistant_store[0]) as c:
        c.execute("UPDATE nlp_chats SET extracted_entities_json='invalid JSON'")
    malformed = query(assistant_store).get('owner',saved['chat_id'])
    assert malformed['interpretation_state'] == 'Malformed' and malformed['structured_request'] is None


def test_api_auth_privacy_validation_and_read_only(store):
    saved = save(store)
    with TestClient(app) as client:
        app.dependency_overrides[chat_history_service] = lambda:ChatHistoryService(query(store))
        try:
            assert client.get('/api/v1/chats').status_code == 401
            headers = {'Authorization':'Bearer '+issue_access_token('owner')}
            assert client.get('/api/v1/chats',headers=headers).json()['total'] == 1
            result = client.get('/api/v1/chats/'+saved['chat_id'],headers=headers)
            assert result.status_code == 200 and result.json()['read_only']
            other = {'Authorization':'Bearer '+issue_access_token('other')}
            assert client.get('/api/v1/chats',headers=other).json()['total'] == 0
            assert client.get('/api/v1/chats/'+saved['chat_id'],headers=other).status_code == 404
            assert client.get('/api/v1/chats/missing',headers=headers).status_code == 404
            for params in ({'limit':0},{'limit':101},{'search':'x'*501},{'cursor':'bad'}):
                assert client.get('/api/v1/chats',headers=headers,params=params).status_code == 422
            assert client.post('/api/v1/chats',headers=headers,json={}).status_code == 405
            assert client.patch('/api/v1/chats/'+saved['chat_id'],headers=headers,json={}).status_code == 405
        finally: app.dependency_overrides.pop(chat_history_service,None)
