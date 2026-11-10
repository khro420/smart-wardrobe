"""Immutable receipts survive changed policy; new reuse obeys current policy."""
import json,uuid
import pytest
from fastapi import HTTPException
from tests.test_wearer_category_policy import category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,set_gender
from tests.test_wearer_category_recommendation import submit
from app.infrastructure.persistence import postgresql_repository as db
from app.application.wardrobe.profile_service import profile_scope
from app.application.ports.assistant_runtime import assistant_service
from app.application.visualisation.outfit_identifier_validator import resolve_source
from app.domain.value_objects.wearer_category_eligibility import validate_evidence

def retained():
    with db.connection() as conn:
        return {t:[tuple(r) for r in conn.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in ('recommendations','recommendation_items','recommendation_metadata','recommendation_submissions','nlp_chats')}

def test_completed_receipt_and_history_are_immutable_but_reuse_denied(category_api,monkeypatch):
    client,male,female=category_api;key=uuid.uuid4().hex;text='i want a dress for shopping'
    root=submit(client,female,text,submission_key=key);assert root.status_code==201,root.text
    root=root.json();history=client.get('/api/v1/chats/'+root['chat_id'],headers={'X-Wardrobe-Profile-Id':female}).json();before=retained()
    set_gender(client,female,'male')
    monkeypatch.setattr(assistant_service().attribute_pipeline,'interpret',lambda *a:pytest.fail('Completed receipt reinterpreted'))
    replay=submit(client,female,text,submission_key=key);assert replay.status_code==200 and replay.json()['id']==root['id'],replay.text
    assert replay.json()['items']==root['items'] and replay.json()['provenance']==root['provenance']
    assert client.get('/api/v1/chats/'+root['chat_id'],headers={'X-Wardrobe-Profile-Id':female}).json()==history
    save=client.post('/api/v1/recommendations/'+root['id']+'/save-as-outfit',headers={'X-Wardrobe-Profile-Id':female},json={'name':'Blocked reuse'})
    assert save.status_code==409,save.text
    with db.connection() as conn,profile_scope(female):
        with pytest.raises(HTTPException) as error:resolve_source(conn,root['provenance']['wearer_category_eligibility']['owner_id'],recommendation_id=root['id'])
        assert error.value.status_code==409
    assert retained()==before

def test_stale_root_requires_fresh_request_even_after_gender_restored(category_api):
    client,male,_=category_api;root=submit(client,male).json();action=root['scoring_display']['refinement']['next_action']
    set_gender(client,male,'female');set_gender(client,male,'male');before=retained()
    child=submit(client,male,root['request_text'],submission_key=action['submission_key'],refinement=action['refinement'])
    assert child.status_code==409 and child.json()['outcome']=='WearerEligibilityChanged',child.text
    assert retained()==before
    assert submit(client,male).status_code==201

def test_new_archive_tampering_rejected(category_api):
    client,male,_=category_api;root=submit(client,male).json();evidence=root['provenance']['wearer_category_eligibility']
    for field,value in [('policy_sha256','0'*64),('gender_key','female'),('account_count',101),('scope_sha256','0'*64),('version','unknown')]:
        bad={**evidence,field:value}
        with pytest.raises(ValueError):validate_evidence(bad,evidence['owner_id'],male,root['items'])

def test_legacy_entry_uses_same_strict_policy(category_api):
    from app.application.recommendation.recommendation_service import create_recommendation
    client,male,_=category_api
    with profile_scope(male):
        with pytest.raises(HTTPException) as error:create_recommendation('style-owner','i want a dress for shopping',male)
        assert error.value.status_code==409
        result=create_recommendation('style-owner','Going shopping.',male)
        assert all(i['category']!='skirt' and not i['category'].endswith('_dress') for i in result['items'])
