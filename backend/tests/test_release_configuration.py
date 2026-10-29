"""J12: real startup composition and authenticated routes, never profile injection."""
from fractions import Fraction as F
import json
import os
from pathlib import Path
import uuid

import pytest
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.persistence import active_preference_query_adapter as pref
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.infrastructure.security import issue_access_token
from app.application.ports.assistant_runtime import assistant_service,configure_assistant_service
from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
from app.infrastructure.persistence.chat_history_query_adapter import SqliteChatHistoryQuery
from tests.test_forward_style_semantics import lifecycle
from tests.test_scoring_acceptance import DATA,independent,expected_winner
from tests.test_suitability_assistant_e2e import make,tag

ENV={'SMART_WARDROBE_ASSISTANT_ENABLED':'true', 'SMART_WARDROBE_HOMEPAGE_ENABLED':'true',
     'SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE':'compact_exhaustive',
     'SMART_WARDROBE_ASSISTANT_SCORING_PROFILE':'experimental_compatibility_decision_v1',
     'SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED':'true'}


@pytest.fixture
def release(lifecycle,monkeypatch):
    client,create=lifecycle; previous=assistant_service()
    monkeypatch.setattr(pref,'DATABASE_PATH',db.DATABASE_PATH)
    monkeypatch.setattr(SqliteRecommendationRepository.__init__,'__defaults__',(db.DATABASE_PATH,None))
    monkeypatch.setattr(SqliteChatHistoryQuery.__init__,'__defaults__',(db.DATABASE_PATH,SqliteChatHistoryQuery.__init__.__defaults__[1]))
    for key,value in ENV.items(): monkeypatch.setenv(key,value)
    configure_local_workflow();db.ensure_user('style-owner')
    client.headers['Authorization']='Bearer '+issue_access_token('style-owner')
    service=assistant_service()
    assert service.execution_engine=='compact_exhaustive'
    assert service.scoring_profile=='experimental_compatibility_decision_v1'
    assert service.engine.evaluator_factory.__name__=='SuitabilityRequestEvaluator'
    yield client,create
    configure_assistant_service(previous)


def submit(client,text,key=None,explicit=True):
    response=client.post('/api/v1/recommendations'+('?pipeline=integrated' if explicit else ''),
                         json={'request_text':text,'submission_key':key or uuid.uuid4().hex})
    evidence=os.getenv('SMART_WARDROBE_RELEASE_EVIDENCE')
    if evidence:
        with Path(evidence).open('a',encoding='utf-8') as stream:
            stream.write(json.dumps({'request':text,'explicit':explicit,'http':response.status_code,'result':response.json()})+'\n')
    return response,response.json()


@pytest.mark.parametrize('case',DATA['cases'],ids=lambda case:case['id'])
def test_fixed_release_exact_oracle_four_structures_and_replay(release,case):
    client,create=release;ids={}
    for name,category,colour,styles in case['garments']:
        gid=make(client,create,category,[tag(),tag('formality','casual')]);ids[name]=gid
        assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'primary_colour':colour,'attributes':{'style':styles}}).status_code==200
    with db.connection() as c:
        for index,p in enumerate(case.get('preferences',[])):
            c.execute('INSERT INTO user_preferences VALUES(?,?,?,?,1,?,1,?,?)',(str(index),'style-owner',p['type'],json.dumps({'values':p['values']}),'synthetic','now','now'))
    expected=expected_winner(independent(case,ids),'experimental_compatibility_decision_v1')
    key=uuid.uuid4().hex
    response,result=submit(client,case['text'],key)
    assert response.status_code==201,result
    assert [i['garment_id'] for i in result['items']]==[ids[n] for n in expected['members']]
    metadata=result['score_metadata']
    def fraction(value): return F(value['numerator'],value['denominator']) if value is not None else F(0)
    assert fraction(metadata['request_match']['summary']['value'])==expected['r']
    assert fraction(metadata['preference']['summary']['value'])==expected['p']
    assert fraction(metadata['compatibility']['decision']['value'])==expected['c']
    assert [fraction(w) for w in metadata['weights']]==[F(3,5),F(1,5),F(1,5)]
    if result['request_match_score'] is None: assert metadata['request_match']['summary']['state']=='NotApplicable'
    if result['preference_score'] is None: assert metadata['preference']['summary']['state']=='NoPreferences'
    assert result['total_score']==float(F(3,5)*expected['r']+F(1,5)*expected['c']+F(1,5)*expected['p'])
    assert result['provenance']['scoring_profile']=='experimental_compatibility_decision_v1'
    assert result['provenance']['request_evaluator']=='SuitabilityRequestEvaluator'
    response,replayed=submit(client,case['text'],key,explicit=False)
    assert response.status_code==200 and replayed['replayed'] and replayed['id']==result['id']
    assert replayed['score_metadata']==result['score_metadata']
    _,fresh=submit(client,case['text'])
    assert [i['garment_id'] for i in fresh['items']]==[i['garment_id'] for i in result['items']]
    assert fresh['score_metadata']==result['score_metadata']
    assert client.get('/api/v1/chats/'+result['chat_id']).status_code==200
    assert client.get('/api/v1/chats/'+result['chat_id'],headers={'Authorization':'Bearer '+issue_access_token('foreign')}).status_code==404


def test_restart_configuration_replay_and_fail_closed(release,monkeypatch):
    client,create=release;make(client,create,tags=[tag(),tag('formality','casual')])
    text='Suggest a casual outfit for campus with vintage style using blue colours with a vest dress'
    key=uuid.uuid4().hex;response,first=submit(client,text,key)
    assert response.status_code==201,first
    for _ in range(2):
        configure_local_workflow()
        assert assistant_service().scoring_profile==ENV['SMART_WARDROBE_ASSISTANT_SCORING_PROFILE']
        response,replayed=submit(client,text,key)
        assert response.status_code==200 and replayed['score_metadata']==first['score_metadata']
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED','false');configure_local_workflow()
    assert client.get('/api/v1/recommendations/capabilities').json()['assistant_enabled'] is False
    with db.connection() as c: before=c.execute('SELECT COUNT(*) FROM recommendations').fetchone()[0]
    response,result=submit(client,text)
    assert response.status_code==404 and result['outcome']=='IntegrationDisabled'
    with db.connection() as c: assert c.execute('SELECT COUNT(*) FROM recommendations').fetchone()[0]==before
    # J-14: unqualified disabled generation now shares the explicit fail-closed contract.
    response,result=submit(client,'Suggest an outfit',explicit=False)
    assert response.status_code==404 and result['outcome']=='IntegrationDisabled'
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED','true')
    monkeypatch.delenv('SMART_WARDROBE_ASSISTANT_SCORING_PROFILE');monkeypatch.delenv('SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED')
    configure_local_workflow()
    assert assistant_service().scoring_profile=='compatibility_deferred'
    assert type(assistant_service().engine.evaluator_factory()).__name__=='RequestConstraintEvaluator'


def test_quota_full_state_does_not_change_release_history_scores_or_eligibility(release):
    client,create=release;gid=make(client,create,tags=[tag(),tag('formality','casual')])
    text='Suggest a casual outfit for campus with vintage style using blue colours with a vest dress'
    key=uuid.uuid4().hex;_,original=submit(client,text,key)
    with db.connection() as c:
        # Missing confirmation links deliberately count toward quota but never eligibility.
        c.executemany("INSERT INTO garments(id,user_id,preferred_media_id,name,category,attributes_json,status,created_at,updated_at) VALUES(?,'style-owner','invalid','Unverified','vest','{}','unavailable','now','now')",[(str(uuid.uuid4()),) for _ in range(99)])
    assert client.get('/api/v1/wardrobe/quota').json()['used']==100
    response,fresh=submit(client,text)
    assert response.status_code==201 and [i['garment_id'] for i in fresh['items']]==[gid]
    assert fresh['score_metadata']==original['score_metadata']
    response,replay=submit(client,text,key)
    assert response.status_code==200 and replay['score_metadata']==original['score_metadata']
    save=client.post('/api/v1/recommendations/'+original['id']+'/save-as-outfit',json={'name':'Full wardrobe save'})
    assert save.status_code==201,save.text
    assert client.get('/api/v1/wardrobe/quota').json()['used']==100
