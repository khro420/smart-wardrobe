"""Real disposable API persistence, disabled-language replay and owned isolation."""
import uuid,json
import pytest
from tests.test_b3_palette_integration import palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,populate,submit
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.ports.assistant_runtime import assistant_service

@pytest.fixture
def language_api(palette_api,monkeypatch):
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_LANGUAGE_PROFILE','conversational_language_v1');configure_local_workflow()
    client,wearer=palette_api;populate(client)
    from tests.test_attribute_persistence import qualify
    for garment in client.get('/api/v1/wardrobe/garments').json():qualify(client,garment['id'],pattern='plain')
    return client,wearer

@pytest.mark.parametrize('p2',[False,True])
@pytest.mark.parametrize('c2',[False,True])
@pytest.mark.parametrize('hard',[False,True],ids=['context','new_B1_intent'])
def test_completed_language_receipt_survives_disabled_parser(language_api,monkeypatch,p2,c2,hard):
    client,wearer=language_api;key=uuid.uuid4().hex
    profile='recorded_palette_compatibility_v1' if c2 else None
    text='Going shopping with no floral patterns.' if hard else 'Going shopping.'
    response,root=submit(client,wearer,text,key,p2,profile=profile)
    assert response.status_code==201 and root['outcome']=='Selected',root
    if hard:
        captured=root['provenance']['attribute_selection']['intent']['grammar_sha256']
        if captured=='03b41d02401e3e28c028cf907da6141f63d368e98d65d4cfbe963b5b8fe0c110':
            # Explicit approved current descendant; old v1 intent schema remains exact.
            assert root['provenance']['attribute_selection']['intent']['version']=='assistant-attribute-intent-1.0.0'
        else:
            assert root['provenance']['attribute_selection']['intent']['grammar_sha256']=='4fdf75bd573dfc920579bfb2bd88378e4f32068db75df17448400c975b542f26'

    action=root['scoring_display']['refinement']['next_action']
    response,child=submit(client,wearer,root['request_text'],action['submission_key'],p2,action['refinement'],profile=profile)
    assert response.status_code==201 and child['items']!=root['items'],child
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_LANGUAGE_PROFILE','disabled');configure_local_workflow()
    monkeypatch.setattr(assistant_service().attribute_pipeline,'interpret',lambda *a,**k:pytest.fail('Completed receipt was reinterpreted'))
    response,replay=submit(client,wearer,text,key,p2,profile=profile)
    assert response.status_code==200 and replay['id']==root['id'] and replay['scoring_display']==root['scoring_display']
    assert submit(client,wearer,'Different request.',key,p2,profile=profile)[0].status_code==409
    historical=client.get('/api/v1/chats/'+child['chat_id']);assert historical.status_code==200
    assert historical.json()['recommendation']['scoring_display']==child['scoring_display']
    other=client.post('/api/v1/account/wardrobe-profiles',json={'name':'Independent wearer'}).json()['id']
    assert client.get('/api/v1/chats/'+root['chat_id'],headers={'X-Wardrobe-Profile-Id':other}).status_code==404

def test_unknown_archive_grammar_digest_is_refused(language_api):
    from app.application.recommendation.attribute_selection_verifier import validate_selection
    from app.domain.value_objects.attribute_conditions import digest
    client,wearer=language_api
    response,root=submit(client,wearer,'Going shopping with no floral patterns.')
    assert response.status_code==201,root
    bad=json.loads(json.dumps(root['provenance']['attribute_selection']))
    bad['intent']['grammar_sha256']='0'*64
    bad['intent']['intent_sha256']=digest({**bad['intent'],'intent_sha256':''})
    bad['revision']=digest({**bad,'revision':''})
    with pytest.raises(ValueError,match='Unregistered archived attribute contract identity'):
        validate_selection(bad,'not_reached',wearer,root['provenance']['attribute_base_scope_sha256'])
