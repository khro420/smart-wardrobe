"""Authenticated disposable API requests through the real composition root."""
from pathlib import Path
from fractions import Fraction as F
import json,uuid
import pytest
from tests.test_request_local_persistence import (
    local_store,category_api,language_api,palette_api,p2_api,attribute_api,
    refinement_api,expanded_api,relative_api,automatic_api,everyday_api,
    release,lifecycle,intent,counts,runtime_boundary,restrict)
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.ports.assistant_runtime import assistant_service
from app.application.recommendation.local_preference_assistant import ENVIRONMENT_KEY,PROFILE
from app.infrastructure import security


@pytest.fixture
def enabled(local_store,monkeypatch):
    client,_,_,owner,male,female=local_store
    monkeypatch.setattr(security,'ALLOW_DEVELOPMENT_IDENTITY',False)
    assert client.headers.get('Authorization','').startswith('Bearer ')
    monkeypatch.setenv(ENVIRONMENT_KEY,PROFILE);configure_local_workflow()
    return client,assistant_service().repository,owner,male,female


def post(client,wearer,text="I'd prefer black trousers.",key=None,**options):
    return client.post('/api/v1/recommendations?pipeline=integrated',headers={'X-Wardrobe-Profile-Id':wearer},json={'request_text':text,'submission_key':key or uuid.uuid4().hex,'wearer_profile_id':wearer,**options})


def test_disabled_by_default_and_normal_path_is_unchanged(local_store,monkeypatch):
    client,repo,_,owner,_,female=local_store
    assert client.get('/api/v1/recommendations/capabilities').json()['local_preferences']['enabled'] is False
    assert post(client,female).status_code==422
    before=post(client,female,'Recommend an outfit.');assert before.status_code==201,before.text
    monkeypatch.setenv(ENVIRONMENT_KEY,PROFILE);configure_local_workflow()
    after=post(client,female,'Recommend an outfit.');assert after.status_code==201,after.text
    a,b=before.json(),after.json()
    assert a['score_metadata']==b['score_metadata']
    assert [i['garment_id'] for i in a['items']]==[i['garment_id'] for i in b['items']]
    assert 'request_local_preference' not in b['provenance']


def test_capability_and_frozen_grammar_identities(enabled):
    client,_,_,_,_=enabled
    cap=client.get('/api/v1/recommendations/capabilities').json()
    assert cap['attributes']['grammar_version']=='conversational-attribute-grammar-1.6.0'
    assert cap['local_preferences']['enabled'] and cap['local_preferences']['grammar_version']=='conversational-attribute-grammar-1.7.0'
    assert cap['local_preferences']['continuation'] is False
    from app.application.nlp import request_local_soft_parser as current
    from tests import isolated_soft_preference_parser as prior
    assert Path(current.__file__).read_bytes()==Path(prior.__file__).read_bytes()
    assert current.isolated_fingerprint()==prior.isolated_fingerprint()==cap['local_preferences']['grammar_sha256']


@pytest.mark.parametrize('engine',['reference','compact_exhaustive'])
@pytest.mark.parametrize('text',["I'd prefer black trousers.",'I need trousers, preferably black.','Black trousers would be nice, but anything is fine.'])
def test_real_recommendation_receipt_and_history(enabled,engine,text):
    client,repo,_,_,female=enabled;assistant_service().local_preferences.engine=engine
    key=uuid.uuid4().hex;before=counts(repo);reply=post(client,female,text,key)
    assert reply.status_code==201,reply.text
    v=reply.json();assert v['outcome']=='Selected' and not v['replayed']
    assert any(i['name']=='Black Trousers' for i in v['items'])
    from app.application.recommendation.decision_score_codec import score_from_json
    score=score_from_json(json.dumps(v['score_metadata']))
    assert score.weights==(F(3,5),F(1,5),F(1,5)) and score.total==sum(w*c.contribution for w,c in zip(score.weights,(score.request_match,score.compatibility,score.preference)))
    proof=v['provenance']['request_local_preference'];assert proof['version']=='request-local-selection-proof-2.0.0'
    assert v['scoring_display']['decision']['selected_optional']['state']=='Satisfied'
    assert v['scoring_display']['continuation_available'] is False and 'refinement' not in v['scoring_display']
    count=counts(repo);assert count[0]==before[0]+1
    replay=post(client,female,text,key);assert replay.status_code==200 and replay.json()['id']==v['id'] and replay.json()['replayed']
    history=client.get('/api/v1/chats/'+v['chat_id'],headers={'X-Wardrobe-Profile-Id':female})
    assert history.status_code==200 and history.json()['recommendation']['scoring_display']==v['scoring_display']
    assert counts(repo)==count


@pytest.mark.parametrize('option',['p2','c2','typed','initial','material','context','multiple'])
def test_unsupported_modes_refuse_without_writes(enabled,option):
    client,repo,_,_,female=enabled;before=counts(repo);extra={};text="I'd prefer black trousers."
    if option=='p2':extra['preference_profile']='attribute_preference_decision_v2'
    elif option=='c2':extra['compatibility_profile']='recorded_palette_compatibility_v1'
    elif option=='typed':extra['attribute_conditions']=intent('I need trousers, preferably black.').hard.conditions.to_dict()
    elif option=='initial':extra['refinement']={'version':'assistant-refinement-request-1.0.0','kind':'initial','excluded_categories':[]}
    elif option=='material':text="I'd prefer a cotton shirt."
    elif option=='context':text='Going shopping, preferably black.'
    else:text="I'd prefer black trousers and a blue shirt."
    reply=post(client,female,text,**extra)
    assert reply.status_code==422,reply.text
    assert reply.json()['outcome'] in ('SoftProfileUnavailable','UnsupportedSoftPreference','SoftContinuationUnavailable')
    assert counts(repo)==before


@pytest.mark.parametrize('change',['text','wearer','p2','c2','refinement'])
def test_receipt_conflicts_never_rewrite_the_original(enabled,change):
    client,repo,_,male,female=enabled;key=uuid.uuid4().hex;root=post(client,female,key=key).json();before=counts(repo)
    text="I'd prefer blue trousers." if change=='text' else root['request_text'];extra={}
    if change=='p2':extra['preference_profile']='attribute_preference_decision_v2'
    elif change=='c2':extra['compatibility_profile']='recorded_palette_compatibility_v1'
    elif change=='refinement':extra['refinement']={'version':'assistant-refinement-request-1.0.0','kind':'alternative','parent_recommendation_id':root['id']}
    conflict=post(client,male if change=='wearer' else female,text,key,**extra)
    assert conflict.status_code==409,conflict.text
    assert post(client,female,key=key).json()['id']==root['id'] and counts(repo)==before


def test_soft_parent_continuation_refused_even_with_changed_text(enabled):
    client,repo,_,_,female=enabled;root=post(client,female).json();before=counts(repo)
    for text in (root['request_text'],'Recommend an outfit.'):
        reply=post(client,female,text,refinement={'version':'assistant-refinement-request-1.0.0','kind':'alternative','parent_recommendation_id':root['id']})
        assert reply.status_code==422 and reply.json()['outcome']=='SoftContinuationUnavailable'
    assert counts(repo)==before


def test_disabled_parser_and_changed_current_wardrobe_do_not_reinterpret_receipt(enabled,monkeypatch):
    client,repo,_,_,female=enabled;key=uuid.uuid4().hex;root=post(client,female,key=key).json();before=counts(repo)
    monkeypatch.setenv(ENVIRONMENT_KEY,'disabled');configure_local_workflow()
    from app.application.nlp.request_local_soft_parser import IsolatedSoftPreferenceParser
    monkeypatch.setattr(IsolatedSoftPreferenceParser,'interpret',lambda *a,**k:pytest.fail('Replay reinterpreted'))
    with repo._connect() as c:c.execute("UPDATE garments SET status='archived'")
    replay=post(client,female,key=key);assert replay.status_code==200,replay.text
    assert replay.json()['id']==root['id'] and replay.json()['scoring_display']==root['scoring_display']
    assert counts(repo)==before


def test_hard_unknown_is_not_a_parse_failure_or_a_match(enabled):
    client,repo,_,_,female=enabled;before=counts(repo)
    reply=post(client,female,'I want a cotton shirt, preferably blue.')
    assert reply.status_code==200 and reply.json()['outcome']=='InsufficientEvidence',reply.text
    assert counts(repo)==before


def test_empty_wardrobe_is_an_availability_refusal_not_an_encoding_error(enabled):
    client,repo,_,_,female=enabled;before=counts(repo)
    with repo._connect() as c:c.execute("UPDATE garments SET status='archived'")
    reply=post(client,female)
    assert reply.status_code==200 and reply.json()['outcome']=='NoEligibleGarments',reply.text
    assert counts(repo)==before


@pytest.mark.parametrize('case',['single_role','known_nonmatch'])
def test_no_structure_and_known_nonmatch_remain_distinct(enabled,case):
    client,repo,_,_,female=enabled;before=counts(repo)
    if case=='single_role':
        restrict(client,repo,['Blue T-shirt'])
        reply=post(client,female);expected='NoStructuralCandidates'
    else:
        reply=post(client,female,'I need purple trousers, preferably black.');expected='NoMatchingCandidates'
    assert reply.status_code==200 and reply.json()['outcome']==expected,reply.text
    assert counts(repo)==before


def test_optional_unknown_is_saved_as_unverified_not_as_a_match(enabled):
    from app.application.wardrobe import description_projector as b0
    from app.application.wardrobe.description_normalizer import normalise_field
    from app.application.wardrobe.description_policy import DescriptionPolicy
    client,repo,_,_,female=enabled;ids=restrict(client,repo,['Blue T-shirt','Black Trousers']);gid=ids['Black Trousers']
    garment=next(g for g in client.get('/api/v1/wardrobe/garments').json() if g['id']==gid)
    doc=garment['description']['evidence']
    doc['fields']['primary_colour']=normalise_field('primary_colour',None,DescriptionPolicy.load(),origin='model_suggestion',category=garment['category'],media_id=garment['preferred_media_id']).to_dict()
    doc=b0._document(doc['subject'],doc['fields']).to_dict()
    with repo._connect() as c:
        row=c.execute('SELECT attributes_json,additional_attributes FROM garments WHERE id=?',(gid,)).fetchone()
        values=[json.loads(raw) for raw in row]
        for v in values:
            v[b0.KEY]=doc;v.pop('primary_colour',None);v.pop('primary_color',None)
        c.execute('UPDATE garments SET primary_colour=NULL,attributes_json=?,additional_attributes=? WHERE id=?',(*(json.dumps(v) for v in values),gid))
    reply=post(client,female);assert reply.status_code==201,reply.text
    chosen=reply.json()['scoring_display']['decision']['selected_optional']
    assert chosen['state']=='Unverifiable' and chosen['support']==0 and chosen['value'] is None


def test_source_change_under_write_lock_is_refused_and_rolled_back(enabled,monkeypatch):
    client,repo,_,_,female=enabled;workflow=assistant_service().local_preferences.workflow
    original=workflow.revalidate;before=counts(repo)
    with repo._connect() as c:name=c.execute('SELECT name FROM garments ORDER BY id LIMIT 1').fetchone()[0]
    def changed(conn,command):
        assert conn.in_transaction
        conn.execute("UPDATE garments SET name='changed under lock' WHERE id=(SELECT id FROM garments ORDER BY id LIMIT 1)")
        return original(conn,command)
    monkeypatch.setattr(workflow,'revalidate',changed)
    reply=post(client,female);assert reply.status_code==409 and reply.json()['outcome']=='WardrobeChanged',reply.text
    assert counts(repo)==before
    with repo._connect() as c:assert c.execute('SELECT name FROM garments ORDER BY id LIMIT 1').fetchone()[0]==name


def test_conflicting_preference_does_not_override_hard_black_requirement(enabled):
    client,_,_,_,female=enabled;reply=post(client,female,'I need black trousers, preferably blue.')
    assert reply.status_code==201,reply.text
    v=reply.json();assert any(i['name']=='Black Trousers' for i in v['items'])
    assert v['scoring_display']['optional_intent']['resolution']['state']=='ContradictedByHard'


@pytest.mark.parametrize('stage',['local_preference_revalidated','metadata','before_commit'])
def test_api_atomic_rollback_and_same_key_recovery(enabled,stage):
    client,repo,_,_,female=enabled;before=counts(repo);key=uuid.uuid4().hex
    def fail(where,conn):
        if where==stage:raise RuntimeError('deliberate disposable rollback')
    repo.checkpoint=fail
    failed=post(client,female,key=key);assert failed.status_code==503 and counts(repo)==before
    repo.checkpoint=lambda *a:None
    assert post(client,female,key=key).status_code==201


def test_bearer_auth_foreign_ownership_and_client_capability_spoofing(enabled):
    from app.infrastructure.persistence import postgresql_repository as db
    client,repo,_,_,female=enabled;root=post(client,female).json();before=counts(repo)
    assert client.get('/api/v1/recommendations/capabilities',headers={'Authorization':''}).status_code==401
    assert post(client,female,local_preferences={'enabled':True}).status_code==422
    db.ensure_user('foreign-soft-owner');token=security.issue_access_token('foreign-soft-owner')
    reply=client.get('/api/v1/chats/'+root['chat_id'],headers={'Authorization':'Bearer '+token,'X-Wardrobe-Profile-Id':female})
    assert reply.status_code==404,reply.text
    assert counts(repo)==before


@pytest.mark.parametrize('setting,value',[(ENVIRONMENT_KEY,'unknown'),('SMART_WARDROBE_ASSISTANT_ENABLED','false'),('SMART_WARDROBE_DESCRIPTION_PROFILE','disabled'),('SMART_WARDROBE_ASSISTANT_LANGUAGE_PROFILE','disabled'),('SMART_WARDROBE_WEARER_CATEGORY_PROFILE','disabled')])
def test_startup_dependency_validation_fails_closed(enabled,monkeypatch,setting,value):
    monkeypatch.setenv(setting,value)
    with pytest.raises(ValueError):configure_local_workflow()
