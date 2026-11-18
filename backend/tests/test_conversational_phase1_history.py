"""Phase 1 grammar identities through real disposable history and alternatives."""
import uuid
import pytest
from tests.test_conversational_history import (
    language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,
    relative_api,automatic_api,everyday_api,release,lifecycle,submit,
)
from app.application.ports.assistant_runtime import assistant_service
from app.infrastructure.workflow_runtime import configure_local_workflow


@pytest.mark.parametrize('engine',['compact_exhaustive','reference'])
@pytest.mark.parametrize('p2',[False,True])
@pytest.mark.parametrize('c2',[False,True])
def test_new_grammar_persists_replays_and_continues(language_api,monkeypatch,engine,p2,c2):
    client,wearer=language_api;assistant_service().execution_engine=engine
    text='Going shopping with no striped tops.';key=uuid.uuid4().hex
    profile='recorded_palette_compatibility_v1' if c2 else None
    reply,root=submit(client,wearer,text,key,p2,profile=profile)
    assert reply.status_code==201 and root['outcome']=='Selected',root
    intent=root['provenance']['attribute_selection']['intent']
    assert intent['grammar_sha256']=='14b41df8fe4f815e655b7b593afc66326c70896f58d699e6174b977b8cf51a14'
    group=intent['conditions']['groups'][0]
    assert group['role']=='upper' and group['quantifier']=='none'
    assert group['conditions'][0]['values']==['stripe']
    action=root['scoring_display']['refinement']['next_action']
    reply,child=submit(client,wearer,text,action['submission_key'],p2,action['refinement'],profile=profile)
    assert reply.status_code==201 and child['items']!=root['items'],child
    refinement=child['provenance']['refinement']
    assert refinement['ordinal']==1 and refinement['parent_id']==root['id']
    assert refinement['root_R']==root['provenance']['refinement']['root_R']
    history=client.get('/api/v1/chats/'+child['chat_id'])
    assert history.status_code==200
    assert history.json()['recommendation']['scoring_display']==child['scoring_display']
    assert history.json()['recommendation']['provenance']==child['provenance']
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_LANGUAGE_PROFILE','disabled')
    configure_local_workflow()
    monkeypatch.setattr(assistant_service().attribute_pipeline,'interpret',lambda *a,**k:pytest.fail('Replay must not reinterpret'))
    reply,replay=submit(client,wearer,text,key,p2,profile=profile)
    assert reply.status_code==200 and replay['id']==root['id']
    assert replay['score_metadata']==root['score_metadata']
    assert replay['scoring_display']==root['scoring_display']
    assert submit(client,wearer,text+' Changed.',key,p2,profile=profile)[0].status_code==409
    other=client.post('/api/v1/account/wardrobe-profiles',json={'name':'Other wearer'}).json()['id']
    assert client.get('/api/v1/chats/'+root['chat_id'],headers={'X-Wardrobe-Profile-Id':other}).status_code==404
