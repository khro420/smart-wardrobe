"""Optional actions through authenticated disposable app.main and real SQLite."""
import uuid
import pytest
from tests.test_context_expansion_integration import expanded_api
from tests.test_context_relevance_integration import relative_api,automatic_api,everyday_api,release,lifecycle,wardrobe
from tests.test_automatic_garment_finalization import garments,upload
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.ports.assistant_runtime import assistant_service


@pytest.fixture
def refinement_api(expanded_api,monkeypatch):
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_REFINEMENT_PROFILE','optional_refinement_v1')
    configure_local_workflow()
    return expanded_api


def submit(client,text="I'm going shopping.",key=None,action=None):
    body=dict(request_text=text,submission_key=key or uuid.uuid4().hex)
    if action is not None:body['refinement']=action
    response=client.post('/api/v1/recommendations?pipeline=integrated',json=body)
    return response,response.json()


def initial(exclusions=()):
    return dict(version='assistant-refinement-request-1.0.0',kind='initial',excluded_categories=list(exclusions))


def next_action(client,result):
    descriptor=result['scoring_display']['refinement']['next_action']
    return submit(client,result['request_text'],descriptor['submission_key'],descriptor['refinement'])


def test_initial_and_casual_sequence_replay_history(refinement_api):
    client,_=refinement_api;wardrobe(client);before=garments(client)
    response,root=submit(client)
    assert response.status_code==201,root
    view=root['scoring_display'];assert view['version']=='assistant-scoring-display-2.2.0',view
    assert view['refinement']['ordinal']==0 and view['total']=={'numerator':'4','denominator':'5'}
    result=root;bases=[]
    for ordinal in range(4):
        bases.append(tuple(i['garment_id'] for i in result['items'] if i['garment_role']!='outerwear'))
        assert result['scoring_display']['refinement']['ordinal']==ordinal
        response,new=next_action(client,result)
        if ordinal==3:
            assert response.status_code==200 and new['outcome']=='RefinementExhausted',new
        else:
            assert response.status_code==201,new
            assert new['scoring_display']['total']=={'numerator':'7','denominator':'10'}
            replay_response,replay=next_action(client,result)
            assert replay_response.status_code==200 and replay['replayed'] and replay['id']==new['id']
            result=new
    assert len(set(bases))==4 and garments(client)==before
    historical=client.get('/api/v1/chats/'+root['chat_id']).json()['recommendation']
    assert historical['scoring_display']==root['scoring_display']


def test_exclusions_conflict_and_empty_intent_identity(refinement_api):
    client,_=refinement_api;ids=wardrobe(client)
    response,result=submit(client,action=initial(['trousers']))
    assert response.status_code==201,result
    expected_upper=min(('Blue T-shirt','Green Sweatshirt'),key=lambda name:ids[name])
    assert [i['name'] for i in result['items']]==[expected_upper,'Beige Shorts']
    assert result['scoring_display']['total']=={'numerator':'7','denominator':'10'}
    response,result=submit(client,'Suggest an outfit for shopping with trousers',action=initial(['trousers']))
    assert response.status_code==422 and result['outcome']=='RefinementConflict',result
    key=uuid.uuid4().hex
    assert submit(client,key=key)[0].status_code==201
    assert submit(client,key=key,action=initial())[0].status_code==409


def test_completed_replay_before_disabled_current_configuration(refinement_api,monkeypatch):
    client,_=refinement_api;wardrobe(client)
    _,root=submit(client)
    response,child=next_action(client,root);assert response.status_code==201,child
    service=assistant_service();service.refinement_profile='disabled';service.context_ranking_profile='disabled'
    monkeypatch.setattr(service.interpreter,'interpret',lambda _: (_ for _ in ()).throw(AssertionError('Replay reinterpreted')))
    response,replay=next_action(client,root)
    assert response.status_code==200 and replay['id']==child['id'] and replay['scoring_display']==child['scoring_display']
    assert next_action(client,child)[0].status_code==422


def test_changed_competitor_requires_fresh_root_but_old_replay_survives(refinement_api):
    client,_=refinement_api;ids=wardrobe(client)
    key=uuid.uuid4().hex;_,root=submit(client,key=key)
    assert client.patch('/api/v1/wardrobe/garments/'+ids['Green Sweatshirt'],json={'name':'Changed competitor'}).status_code==200
    response,result=next_action(client,root)
    assert response.status_code==409 and result['outcome']=='RefinementScopeChanged',result
    assert submit(client,key=key)[1]['scoring_display']==root['scoring_display']
    assert submit(client)[0].status_code==201


@pytest.mark.parametrize('bad',[{'version':'unknown','kind':'initial','excluded_categories':[]},
    initial(['dress']),initial(['shorts','shorts']),{**initial(),'owner':'forged'},
    {'version':'assistant-refinement-request-1.0.0','kind':'alternative','parent_recommendation_id':'not-a-uuid'}])
def test_strict_action_shape(refinement_api,bad):
    assert submit(refinement_api[0],action=bad)[0].status_code==422


def test_foreign_missing_parent_and_logout(refinement_api):
    from app.infrastructure.persistence import postgresql_repository as db
    from app.infrastructure.security import issue_access_token
    client,_=refinement_api;wardrobe(client);_,root=submit(client)
    original=client.headers['Authorization']
    db.ensure_user('refinement-other-owner');client.headers['Authorization']='Bearer '+issue_access_token('refinement-other-owner')
    assert next_action(client,root)[0].status_code==404
    action=dict(version='assistant-refinement-request-1.0.0',kind='alternative',parent_recommendation_id=str(uuid.uuid4()))
    assert submit(client,action=action)[0].status_code==404
    client.headers['Authorization']=original
    response=client.post('/api/v1/account/logout')
    assert response.status_code in (200,204),response.text
    assert next_action(client,root)[0].status_code==401


def test_reference_runtime_and_fifteen_ordinary_roots(refinement_api,monkeypatch):
    from tests.test_context_expansion_equivalence import TEXTS
    client,_=refinement_api;wardrobe(client)
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE','reference');configure_local_workflow()
    for text in [*TEXTS.values(),"I'm going shopping.","I'm going to class.","I'm going out with friends.","I'm going on a date tonight.","I'm meeting friends for dinner."]:
        response,result=submit(client,text)
        assert response.status_code==201,result
        assert result['scoring_display']['refinement']['ordinal']==0
        assert result['provenance']['scorer_implementation']=='reference-refinement-1.0.0'
    response,child=next_action(client,result)
    assert response.status_code==201 and child['scoring_display']['refinement']['ordinal']==1,child


def test_ten_limit_is_distinct_from_exhaustion(refinement_api):
    from tests.test_automatic_admission_integration import legacy
    from app.domain.value_objects.recommendation_refinement import step_key
    client,_=refinement_api
    for _ in range(11):legacy(client,'casual','vest_dress')
    _,root=submit(client);result=root;seen=set()
    for ordinal in range(10):
        assert result['scoring_display']['refinement']['ordinal']==ordinal,result
        seen.add(result['items'][0]['garment_id'])
        if ordinal<9:
            response,result=next_action(client,result);assert response.status_code==201,result
    assert len(seen)==10 and result['scoring_display']['refinement']['next_action'] is None
    action=dict(version='assistant-refinement-request-1.0.0',kind='alternative',parent_recommendation_id=result['id'])
    response,limited=submit(client,result['request_text'],'unused-cap-action',action)
    assert response.status_code==200 and limited['outcome']=='RefinementLimitReached' and limited['complete'] is False,limited


def test_generic_specialist_and_baseline_do_not_gain_roots(refinement_api):
    client,_=refinement_api;wardrobe(client)
    response,result=submit(client,'Suggest an outfit')
    assert response.status_code==201 and 'refinement' not in result['provenance']
    for text in ('Suggest an outfit',"I'm attending a wedding.","I have an employment interview."):
        response,result=submit(client,text,action=initial())
        assert response.status_code==422 and result['outcome']=='RefinementUnavailable',result
    response,result=submit(client,"I'm going shopping; the dress code is casual.")
    assert response.status_code==201 and 'refinement' not in result['provenance'],result
    response,result=submit(client,"I'm going shopping; the dress code is casual.",action=initial())
    assert response.status_code==422 and result['outcome']=='RefinementUnavailable',result



def test_step_keys_conflicts_and_reserved_initial_namespace(refinement_api,monkeypatch):
    client,_=refinement_api;wardrobe(client);_,root=submit(client);descriptor=root['scoring_display']['refinement']['next_action']
    for key in ('arbitrary-key',descriptor['submission_key'][:-2]+'02'):
        response,result=submit(client,root['request_text'],key,descriptor['refinement'])
        assert response.status_code==422 and result['outcome']=='RefinementUnavailable',result
    response,child=next_action(client,root);assert response.status_code==201
    service=assistant_service()
    def forbidden(*args,**kwargs):raise AssertionError('Conflicting completed intent reinterpreted')
    monkeypatch.setattr(service.interpreter,'interpret',forbidden)
    for text,action in [(root['request_text']+' ',descriptor['refinement']),
        (root['request_text'],initial()),(root['request_text'],{**descriptor['refinement'],'parent_recommendation_id':child['id']})]:
        response,result=submit(client,text,descriptor['submission_key'],action)
        assert response.status_code==409 and result['outcome']=='IdempotencyConflict',result
    response,result=submit(client,key='refine:v1:reserved')
    assert response.status_code==422 and result['outcome']=='RefinementUnavailable'


def test_canonical_exclusion_order_is_same_completed_intent(refinement_api):
    client,_=refinement_api;wardrobe(client);key=uuid.uuid4().hex
    response,root=submit(client,key=key,action=initial(['shorts','vest_dress']))
    assert response.status_code==201
    response,replay=submit(client,key=key,action=initial(['vest_dress','shorts']))
    assert response.status_code==200 and replay['id']==root['id']
    assert submit(client,key=key,action=initial(['shorts']))[0].status_code==409


@pytest.mark.parametrize('variable,value',[
    ('SMART_WARDROBE_ASSISTANT_REFINEMENT_PROFILE','future'),
    ('SMART_WARDROBE_ASSISTANT_CONTEXT_BUNDLE','legacy_8_v1'),
    ('SMART_WARDROBE_ASSISTANT_CONTEXT_RANKING_PROFILE','disabled'),
    ('SMART_WARDROBE_ASSISTANT_ENABLED','false'),
    ('SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED','false'),
    ('SMART_WARDROBE_ASSISTANT_SCORING_PROFILE','compatibility_deferred'),
    ('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE','disabled'),
])
def test_invalid_refinement_composition_rejects(refinement_api,monkeypatch,variable,value):
    monkeypatch.setenv(variable,value)
    with pytest.raises(ValueError):configure_local_workflow()


def test_default_off_and_legacy_history_are_not_retrofitted(expanded_api,monkeypatch):
    client,_=expanded_api;monkeypatch.delenv('SMART_WARDROBE_ASSISTANT_REFINEMENT_PROFILE',raising=False);configure_local_workflow();wardrobe(client)
    key=uuid.uuid4().hex;response,old=submit(client,key=key)
    assert response.status_code==201 and 'refinement' not in old['provenance']
    assert submit(client,action=initial())[0].status_code==422
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_REFINEMENT_PROFILE','optional_refinement_v1');configure_local_workflow()
    response,replay=submit(client,key=key)
    assert response.status_code==200 and replay['scoring_display']==old['scoring_display']
    action=dict(version='assistant-refinement-request-1.0.0',kind='alternative',parent_recommendation_id=old['id'])
    response,result=submit(client,action=action)
    assert response.status_code==422 and result['outcome']=='RefinementUnavailable',result



@pytest.mark.parametrize('change',['preferences','execution_contract','corrupt_policy'])
def test_current_preferences_and_ranking_contract_change_never_silent(refinement_api,monkeypatch,change):
    client,_=refinement_api;wardrobe(client);key=uuid.uuid4().hex;_,root=submit(client,key=key)
    if change=='preferences':
        response=client.put('/api/v1/account/preferences/colours',json={'preference_value':{'values':['green']},'weight':1})
        assert response.status_code==200,response.text
    elif change=='execution_contract':
        monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE','reference');configure_local_workflow()
    else:
        from app.application.recommendation.refinement_policy import RefinementPolicy
        def corrupt(*args,**kwargs):raise ValueError('Disposable corrupt policy test')
        monkeypatch.setattr(RefinementPolicy,'load',corrupt)
    response,result=next_action(client,root)
    assert response.status_code==(503 if change=='corrupt_policy' else 409),result
    assert result['outcome']==('ProcessingFailure' if change=='corrupt_policy' else 'RefinementScopeChanged'),result
    response,replay=submit(client,key=key)
    assert response.status_code==200 and replay['scoring_display']==root['scoring_display']
