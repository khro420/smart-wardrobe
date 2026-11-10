"""Stored wearer names, archived reads and mixed legacy lineage mechanics."""
import json
import pytest
from dataclasses import replace
from tests.test_recommendation_refinement_integration import (
    refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,wardrobe,
)
from tests.test_phase_a_profile_archive import wearers,owner
from tests.test_phase_a_wearer_identity import request
from app.infrastructure.persistence import postgresql_repository as db
from app.application.ports.assistant_runtime import assistant_service


def test_name_snapshot_archive_history_and_completed_replay(refinement_api):
    client,_=refinement_api;a,b=wearers(client);wardrobe(client)
    response,root=request(client,a);assert response.status_code==201,root
    name=root['intended_wearer']['name_at_request']
    step=root['scoring_display']['refinement']['next_action']
    response,child=request(client,a,step['submission_key'],step['refinement']);assert response.status_code==201,child
    with db.connection() as conn:
        conn.execute('UPDATE wardrobe_profiles SET name=? WHERE id=?',('New name',a))
    assert client.post('/api/v1/account/wardrobe-profiles/'+a+'/archive').status_code==200
    client.headers['X-Wardrobe-Profile-Id']=b
    assert client.get('/api/v1/chats/'+root['chat_id']).status_code==404
    suffix='?view=historical&wearer_profile_id='+a
    page=client.get('/api/v1/chats'+suffix);assert page.status_code==200,page.text
    assert {row['chat_id'] for row in page.json()['items']}=={root['chat_id'],child['chat_id']}
    detail=client.get('/api/v1/chats/'+root['chat_id']+suffix);assert detail.status_code==200,detail.text
    restored=detail.json()['recommendation']
    assert restored['intended_wearer']['name_at_request']==name and restored['wearer_archived']
    assert restored['scoring_display']==root['scoring_display']
    assert client.get('/api/v1/chats?view=historical').status_code==422
    client.headers['X-Wardrobe-Profile-Id']=a
    response,replay=request(client,a,step['submission_key'],step['refinement'])
    assert response.status_code==200 and replay['id']==child['id']
    assert client.get('/api/v1/chats/'+root['chat_id']+'?view=historical&wearer_profile_id='+b).status_code==404


def test_legacy_association_bridges_without_rewriting_root(refinement_api,monkeypatch):
    client,_=refinement_api;a,b=wearers(client);wardrobe(client)
    repository=assistant_service().repository;original=repository.persist_assistant
    # Produce a genuinely old-format root using the unchanged trusted command branch.
    def old_command(command):return original(replace(command,wearer=None,refinement=replace(command.refinement,plan=replace(command.refinement.plan,wearer_profile_id=None))))
    monkeypatch.setattr(repository,'persist_assistant',old_command)
    response,root=request(client,a);assert response.status_code==201,root
    assert root['provenance']['refinement']['version']=='recommendation-refinement-evidence-1.0.0'
    with db.connection() as conn:
        before=conn.execute('SELECT provenance_json,score_json FROM recommendation_metadata WHERE recommendation_id=?',(root['id'],)).fetchone()[:]
    monkeypatch.setattr(repository,'persist_assistant',original)
    step=root['scoring_display']['refinement']['next_action']
    response,child=request(client,a,step['submission_key'],step['refinement']);assert response.status_code==201,child
    assert child['provenance']['lineage_wearer_authority']=='legacy_row_bridge'
    assert child['provenance']['refinement']['version']=='recommendation-refinement-evidence-1.1.0'
    with db.connection() as conn:
        assert conn.execute('SELECT provenance_json,score_json FROM recommendation_metadata WHERE recommendation_id=?',(root['id'],)).fetchone()[:]==before
    client.headers['X-Wardrobe-Profile-Id']=b
    assert request(client,b,step['submission_key'],step['refinement'])[0].status_code==409


def test_legacy_unrecorded_root_replays_but_cannot_be_reassigned(refinement_api,monkeypatch):
    client,_=refinement_api;a,b=wearers(client);wardrobe(client)
    repository=assistant_service().repository;original=repository.persist_assistant
    def old_command(command):return original(replace(command,wearer=None,refinement=replace(command.refinement,plan=replace(command.refinement.plan,wearer_profile_id=None))))
    monkeypatch.setattr(repository,'persist_assistant',old_command)
    response,root=request(client,a);assert response.status_code==201,root
    monkeypatch.setattr(repository,'persist_assistant',original)
    with db.connection() as conn:
        key=conn.execute('SELECT submission_key FROM recommendation_submissions WHERE recommendation_id=?',(root['id'],)).fetchone()[0]
        conn.execute('UPDATE recommendations SET profile_id=NULL WHERE id=?',(root['id'],))
        conn.execute('UPDATE nlp_chats SET profile_id=NULL WHERE id=?',(root['chat_id'],))
    step=root['scoring_display']['refinement']['next_action']
    response,result=request(client,a,step['submission_key'],step['refinement'])
    assert response.status_code==422 and result['refinement_summary']['reason']=='legacy_wearer_unrecorded',result
    assert request(client,a,key)[0].status_code==409
    client.headers.pop('X-Wardrobe-Profile-Id',None)
    response,replay=request(client,None,key)
    assert response.status_code==200 and replay['id']==root['id'],replay
    assert replay['wearer_intent_state']=='legacy_not_recorded'


@pytest.mark.parametrize('mutation',['proof_wearer','scope','fingerprint','sidecar_wearer','future_sidecar','unknown_proof_field'])
def test_new_archived_wearer_evidence_corruption_fails_visibly(refinement_api,mutation):
    client,_=refinement_api;a,b=wearers(client);wardrobe(client)
    response,root=request(client,a);assert response.status_code==201,root
    with db.connection() as conn:
        original=conn.execute('SELECT provenance_json FROM recommendation_metadata WHERE recommendation_id=?',(root['id'],)).fetchone()[0]
    corrupted=json.loads(original)
    if mutation=='proof_wearer':corrupted['refinement']['wearer_profile_id']=b
    elif mutation=='scope':corrupted['refinement']['wearer_scope_sha256']='f'*64
    elif mutation=='fingerprint':corrupted['refinement']['request_fingerprint_version']=2
    elif mutation=='sidecar_wearer':corrupted['intended_wearer']['profile_id']=b
    elif mutation=='future_sidecar':corrupted['intended_wearer']['version']='future'
    else:corrupted['refinement']['future_unknown']=True
    with db.connection() as conn:
        conn.execute('UPDATE recommendation_metadata SET provenance_json=? WHERE recommendation_id=?',(json.dumps(corrupted),root['id']))
    response=client.get('/api/v1/chats/'+root['chat_id']+'?view=historical&wearer_profile_id='+a)
    assert response.status_code==503 and response.json()['status']=='HistoryUnavailable'
    with db.connection() as conn:
        # Failed reads never repair, reinterpret or create a replacement record.
        assert json.loads(conn.execute('SELECT provenance_json FROM recommendation_metadata WHERE recommendation_id=?',(root['id'],)).fetchone()[0])==corrupted
        assert conn.execute('SELECT COUNT(*) FROM recommendations').fetchone()[0]==1
        assert conn.execute('SELECT COUNT(*) FROM recommendation_submissions').fetchone()[0]==1
        conn.execute('UPDATE recommendation_metadata SET provenance_json=? WHERE recommendation_id=?',(original,root['id']))
    assert client.get('/api/v1/chats/'+root['chat_id']+'?view=historical&wearer_profile_id='+a).json()['recommendation']['scoring_display']==root['scoring_display']
