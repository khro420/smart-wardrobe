"""Authenticated disposable combined application, explicit P2 actions only."""
import uuid,json
import pytest
from tests.test_p2_preference_storage import p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,url,action,pattern
from tests.test_attribute_persistence import wardrobe,qualify
from app.application.ports.assistant_runtime import assistant_service
from app.infrastructure.persistence import postgresql_repository as db
from app.domain.value_objects.attribute_preferences import PROFILE


def submit_p2(client,wearer,text="I'm going shopping.",key=None,refinement=None,typed=None,profile=PROFILE):
    payload={'request_text':text,'submission_key':key or uuid.uuid4().hex,'wearer_profile_id':wearer}
    if profile is not None:payload['preference_profile']=profile
    if refinement is not None:payload['refinement']=refinement
    if typed is not None:payload['attribute_conditions']=typed
    response=client.post('/api/v1/recommendations?pipeline=integrated',json=payload)
    return response,response.json()


def save(client,wearer,families):
    response=client.put(url(wearer),json=action(client.get(url(wearer)).json(),families));assert response.status_code==200,response.text


@pytest.mark.parametrize('text',["I'm going shopping.",'Recommend an outfit.'])
@pytest.mark.parametrize('engine',['compact_exhaustive','reference'])
def test_actual_api_explicit_P2_stored_score_replay_and_omitted_P1(p2_api,engine,text,monkeypatch):
    client,a=p2_api;wardrobe(client);service=assistant_service();service.execution_engine=engine
    save(client,a,{'colour':{'mode':'override','importance':'1','axes':{'primary_colour':{'scope':'all_selected','importance':'1','liked':['blue'],'avoided':[]}}}})
    key=uuid.uuid4().hex;response,result=submit_p2(client,a,text,key)
    assert response.status_code==201,result
    assert result['score_metadata']['profile_name']==PROFILE
    assert result['scoring_display']['kind']=='AttributePreference',result['scoring_display']
    assert result['score_metadata']['preference']['summary']['value']=={'numerator':'1','denominator':'1'}
    service.preference_policy=None;service.attribute_pipeline=None
    monkeypatch.setattr(service.interpreter,'interpret',lambda *args:pytest.fail('Receipt replay interpreted'))
    response,replay=submit_p2(client,a,text,key)
    assert response.status_code==200 and replay['id']==result['id'] and replay['score_metadata']==result['score_metadata'],replay
    assert submit_p2(client,a,text,key,profile=None)[0].status_code==409


def test_P1_remains_default_and_P2_unavailable_never_falls_back(p2_api):
    client,a=p2_api;wardrobe(client)
    response,p1=submit_p2(client,a,profile=None);assert response.status_code==201,p1
    assert 'attribute_preference' not in p1['provenance'] and p1['provenance']['refinement']['request_fingerprint_version']==3
    service=assistant_service();service.preference_policy=None
    response,result=submit_p2(client,a)
    assert response.status_code==422 and result['outcome']=='PreferenceUnavailable',result


def test_B1_hard_conditions_and_P2_mask_are_separate(p2_api):
    client,a=p2_api;ids=wardrobe(client)
    for name in ('Blue T-shirt','Green Sweatshirt'):qualify(client,ids[name],pattern='plain',material=['cotton'],neckline='v-neck')
    save(client,a,pattern())
    response,result=submit_p2(client,a,"I'm going shopping and want a plain cotton v-neck top.")
    assert response.status_code==201,result
    assert result['attribute_display']['outcome']=='Selected'
    assert result['scoring_display']['kind']=='AttributePreference',result['scoring_display']
    # A top-only requirement does not imply plain for all selected members.
    assert result['provenance']['attribute_preference']['ledger']['configured_denominator']=={'numerator':'1','denominator':'1'}


def test_preference_commit_race_writes_no_result_or_receipt(p2_api,monkeypatch):
    client,a=p2_api;wardrobe(client);save(client,a,pattern())
    repository=assistant_service().repository;original=repository.persist_assistant
    def changed(command):save(client,a,pattern('stripe'));return original(command)
    monkeypatch.setattr(repository,'persist_assistant',changed)
    response,result=submit_p2(client,a)
    assert response.status_code==409 and result['outcome']=='RefinementScopeChanged',result
    with db.connection() as conn:
        for table in ('recommendations','nlp_chats','recommendation_submissions'):assert conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0


@pytest.mark.parametrize('case',['version','wearer','policy','ledger','snapshot','selected_source','unknown_field','ranking_ledger'])
def test_corrupt_P2_receipt_is_visible_no_repair_or_new_result(p2_api,monkeypatch,case):
    from app.domain.value_objects.attribute_preferences import digest
    client,a=p2_api;wardrobe(client);save(client,a,pattern());key=uuid.uuid4().hex
    response,root=submit_p2(client,a,key=key);assert response.status_code==201,root
    with db.connection() as conn:
        row=conn.execute('SELECT provenance_json FROM recommendation_metadata WHERE recommendation_id=?',(root['id'],)).fetchone()[0]
        data=json.loads(row);p=data['attribute_preference']
        if case=='version':p['contract']='attribute-preference-evidence-99.0.0'
        elif case=='wearer':p['snapshot']['wearer_id']=str(uuid.uuid4())
        elif case=='policy':p['snapshot']['archive']['policy_snapshot']['model_sources']=[{'unregistered':True}]
        elif case=='ledger':p['ledger']['decision']={'numerator':'1','denominator':'1'}
        elif case=='snapshot':p['snapshot']['legacy_digest']='0'*64
        elif case=='selected_source':p['selected'][0]['description']['fields']['material']['state']='Known'
        elif case=='unknown_field':p['extra']=True
        else:data['context_relevance']['preference_ledger_sha256']='0'*64
        p['revision']=digest({**p,'revision':''});bad=json.dumps(data)
        conn.execute('UPDATE recommendation_metadata SET provenance_json=? WHERE recommendation_id=?',(bad,root['id']))
    monkeypatch.setattr(assistant_service().attribute_pipeline,'interpret',lambda *args:pytest.fail('Corrupt completed request reinterpreted'))
    response,result=submit_p2(client,a,key=key)
    assert response.status_code==503 and result['outcome']=='PersistenceFailure',result
    with db.connection() as conn:
        assert conn.execute('SELECT COUNT(*) FROM recommendations').fetchone()[0]==1
        assert conn.execute('SELECT provenance_json FROM recommendation_metadata WHERE recommendation_id=?',(root['id'],)).fetchone()[0]==bad


@pytest.mark.parametrize('engine',['compact_exhaustive','reference'])
def test_actual_P2_all18_contexts_preserve_P1_admission_R_C_and_specialist_negatives(p2_api,engine):
    from tests.test_p2_preference_values import CONTEXT_TEXTS
    from fractions import Fraction
    client,a=p2_api;wardrobe(client);save(client,a,pattern());assistant_service().execution_engine=engine
    selected=0
    for sid,text in CONTEXT_TEXTS.items():
        before,p1=submit_p2(client,a,text,profile=None);after,p2=submit_p2(client,a,text)
        assert before.status_code==after.status_code,(sid,p1,p2)
        assert p1['outcome']==p2['outcome'],(sid,p1,p2)
        if p1['outcome']=='Selected':
            selected+=1
            assert [i['garment_id'] for i in p1['items']]==[i['garment_id'] for i in p2['items']],sid
            assert p2['scoring_display']['kind']=='AttributePreference',(sid,p2['scoring_display'])
            for key in ('request_match','compatibility'):
                assert p1['score_metadata'][key]==p2['score_metadata'][key],(sid,key)
            assert p2['score_metadata']['preference']['summary']['value'] is None  # Unqualified fine pattern stays Unknown.
            history=client.get('/api/v1/chats/'+p2['chat_id']);assert history.status_code==200,history.text
            assert history.json()['recommendation']['scoring_display']==p2['scoring_display']
    assert selected==15
