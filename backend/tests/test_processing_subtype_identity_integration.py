"""Pre-insert hints never stand in for persisted owner subtype evidence."""
import copy
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import uuid
import pytest
from fastapi import HTTPException
from app.application.wardrobe import wearer_category_service as policy
from app.application.wardrobe import verified_subtype_service as subtype
from app.application.garment_processing import garment_processing_orchestrator as processing
from app.domain.value_objects.detected_garment import DetectedGarment
from app.infrastructure.ai.garment_segmentation_adapter import DevelopmentGarmentAdapter
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.domain.value_objects import verified_garment_subtype as types
from tests.test_wearer_category_policy import (
    category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,
    expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle)
from tests.test_garment_workflow import png

MALE={
 'short_sleeve_top':'Unknown','long_sleeve_top':'Unknown','vest':'Permit','sling':'Permit',
 'shorts':'Permit','trousers':'Permit','skirt':'Deny','short_sleeve_dress':'Deny',
 'long_sleeve_dress':'Deny','vest_dress':'Deny','sling_dress':'Deny',
 'short_sleeve_outwear':'Permit','long_sleeve_outwear':'Permit'}


def _composition_bindings():
    from app.application.ports import (
        workflow_runtime,assistant_runtime,homepage_runtime,chat_history_runtime,
        recommendation_runtime,visualisation_repository)
    return (
        (workflow_runtime,'_runtime'),
        (assistant_runtime,'_service'),
        (homepage_runtime,'_service'),
        (chat_history_runtime,'_service'),
        (recommendation_runtime,'_query'),
        (recommendation_runtime,'_transaction_query_factory'),
        (visualisation_repository,'_runtime'))


def _composition_snapshot():
    return tuple((module,name,getattr(module,name)) for module,name in _composition_bindings())


@contextmanager
def _preserve_composition():
    previous=_composition_snapshot()
    try:
        yield previous
    finally:
        for module,name,value in previous:
            setattr(module,name,value)


@pytest.fixture(autouse=True)
def preserve_composed_runtime():
    # Autouse starts before category_api/lifecycle and ends after their client,
    # database-path and environment teardown. Capture before any dependency
    # configures v1/v2; restoring a newly constructed default would lose a valid
    # caller-owned active runtime and its exact adapters/services.
    with _preserve_composition():
        yield


@pytest.fixture
def transient_boundary(monkeypatch):
    selected=json.loads(policy.configure('gender_category_subtype_v2'))
    def cap(gender):
        monkeypatch.setattr(policy,'policy',lambda:selected)
        monkeypatch.setattr(policy,'capabilities',lambda *args:{
            'enabled':True,'configured':True,'gender_key':gender,
            'allowed_categories':selected['allowed'][gender]})
        monkeypatch.setattr(policy,'transaction_garment_query',lambda conn:SimpleNamespace(get_confirmed_available_garments=lambda owner:()))
    return cap

@pytest.mark.parametrize('gender',['male','female'])
@pytest.mark.parametrize('category',list(MALE))
def test_transient_hints_without_a_subject_have_no_event_lookup(transient_boundary,monkeypatch,gender,category):
    transient_boundary(gender)
    monkeypatch.setattr(subtype,'projection',lambda *args:pytest.fail('No persisted subject/event lookup exists before INSERT'))
    raw={'detected_category':category,'attributes_json':json.dumps({'source':'teammate','raw_nested':{'values':[1,'unaltered']}})}
    original=copy.deepcopy(raw)
    result=policy.annotations(None,'owner','wearer',[raw])[0]
    wanted='Permit' if gender=='female' else MALE[category]
    view=result['wearer_category_eligibility']
    assert view['usable']==(wanted=='Permit')
    assert view['reason']==(None if wanted=='Permit' else 'WearerSubtypeUnresolved' if wanted=='Unknown' else 'WearerCategoryNotPermitted')
    assert 'verified_subtype' not in result and 'id' not in result
    assert raw==original and result['attributes_json']==original['attributes_json']

@pytest.mark.parametrize('gender',['male','female'])
@pytest.mark.parametrize('attrs',['{', '[]','null','42','{"garment_type":"bottom","layering_index":0}'])
def test_malformed_or_contradictory_transient_cannot_gain_permission(transient_boundary,gender,attrs):
    transient_boundary(gender)
    result=policy.annotations(None,'owner','wearer',[{'detected_category':'short_sleeve_top','attributes_json':attrs}])[0]
    assert result['wearer_category_eligibility']['usable'] is False
    assert result['wearer_category_eligibility']['reason']=='WearerCategoryUnresolved'
    assert 'verified_subtype' not in result

@pytest.mark.parametrize('gender',['male','female'])
def test_unclassified_detection_stays_unresolved(transient_boundary,gender):
    transient_boundary(gender)
    result=policy.annotations(None,'owner','wearer',[{'detected_category':'Unclassified garment','attributes_json':'{}'}])[0]
    assert result['wearer_category_eligibility']['reason']=='WearerCategoryUnresolved'
    assert result['wearer_category_eligibility']['usable'] is False

@pytest.mark.parametrize('field',['verified_subtype','verified_subtype_evidence','garment_subtype_events_v1'])
def test_detector_subtype_claim_is_not_owner_evidence(transient_boundary,field):
    transient_boundary('male')
    attrs={'source':'teammate','style':['casual'],field:{'state':'Known','value':'t_shirt','events':['forged']}}
    raw={'detected_category':'short_sleeve_top','attributes_json':json.dumps(attrs)}
    result=policy.annotations(None,'owner','wearer',[raw])[0]
    assert result['wearer_category_eligibility']['reason']=='WearerSubtypeUnresolved'
    assert json.loads(result['attributes_json'])==attrs and 'verified_subtype' not in result

@pytest.mark.parametrize('extra',[{'category':'short_sleeve_top'},{'preferred_media_id':'fake'},{'name':'pending'}])
def test_an_idless_persisted_shape_is_not_accepted_as_an_extracted_view(transient_boundary,extra):
    transient_boundary('female')
    with pytest.raises(ValueError,match='pre-persistence'):
        policy.annotations(None,'owner','wearer',[{'detected_category':'short_sleeve_top','attributes_json':'{}',**extra}])

@pytest.mark.parametrize('identity',[None,'',' ',False,42])
def test_malformed_persisted_identity_is_refused(transient_boundary,identity):
    transient_boundary('female')
    with pytest.raises(ValueError,match='subject identity'):
        policy.annotations(None,'owner','wearer',[{'id':identity,'detected_category':'short_sleeve_top','attributes_json':'{}'}])

def test_persisted_annotation_still_uses_authoritative_projection(transient_boundary,monkeypatch):
    transient_boundary('male');calls=[]
    monkeypatch.setattr(subtype,'projection',lambda conn,owner,row:(calls.append((owner,row['id'])) or {'state':'Known','value':'blouse'}))
    monkeypatch.setattr(policy,'row_decision',lambda *args:'Deny')
    result=policy.annotations(None,'owner','wearer',[{'id':'real-persisted-item','detected_category':'short_sleeve_top','attributes_json':'{}'}])[0]
    assert calls==[('owner','real-persisted-item')]
    assert result['verified_subtype']=={'state':'Known','value':'blouse'}
    assert result['wearer_category_eligibility']['reason']=='WearerSubtypeNotPermitted'

@pytest.fixture
def subtype_processing_api(category_api,monkeypatch):
    from app.infrastructure.workflow_runtime import configure_local_workflow
    monkeypatch.setenv('SMART_WARDROBE_VERIFIED_SUBTYPE_PROFILE','verified_subtype_v1')
    monkeypatch.setenv(policy.ENVIRONMENT_KEY,'gender_category_subtype_v2')
    configure_local_workflow()
    return category_api

def upload(client,detector,monkeypatch):
    monkeypatch.setattr(processing,'get_garment_adapter',lambda:detector)
    response=client.post('/api/v1/processing/jobs',files={'file':('original.png',png('blue'),'image/png')})
    assert response.status_code==202,response.text
    response=client.get('/api/v1/processing/jobs/'+response.json()['id'])
    assert response.status_code==200,response.text
    return response.json()

def strict_ids():
    return {g.garment_id for g in SqliteConfirmedGarmentQuery().get_confirmed_available_garments('style-owner')}

def review(client,job,kind=None):
    item=job['items'][0]
    change={'item_id':item['id'],'decision':'accepted','category':'short_sleeve_top','primary_colour':'blue','attributes':{'style':['casual']}}
    if kind is not None:
        change['subtype_update']={'action_id':str(uuid.uuid4()),'expected_revision':None,'state':'Known','value':kind,'review_basis':'synthetic_fixture_declaration','reason':'Explicit authored test-owner declaration'}
    return client.post('/api/v1/processing/jobs/'+job['id']+'/review',json={'items':[change]})

def confirm(client,job):
    return client.post('/api/v1/processing/jobs/'+job['id']+'/confirm',json={'item_ids':[job['items'][0]['id']],'save_mode':'garments'})

def test_original_development_upload_reaches_real_persisted_item(subtype_processing_api,monkeypatch):
    client,male,female=subtype_processing_api;client.headers['X-Wardrobe-Profile-Id']=female
    before=strict_ids()
    job=upload(client,DevelopmentGarmentAdapter(),monkeypatch)
    assert job['status']=='review_required' and len(job['items'])==1,job
    item=job['items'][0];uuid.UUID(item['id'])
    with db.connection() as conn:
        actual=conn.execute('SELECT * FROM processing_items WHERE id=? AND job_id=?',(item['id'],job['id'])).fetchone()
        assert actual is not None and actual['review_status']=='pending'
        assert subtype.store().events(conn,'style-owner','processing_item',item['id'])==[]
    assert strict_ids()==before
    assert item['wearer_category_eligibility']['usable'] is False
    assert item['verified_subtype']['value'] is None
    assert confirm(client,job).status_code==409

def test_extracted_attributes_and_genuine_item_to_garment_identity(subtype_processing_api,monkeypatch):
    client,male,female=subtype_processing_api;client.headers['X-Wardrobe-Profile-Id']=female
    attrs={'source':'synthetic teammate payload','style':['casual'],'material':['cotton'],'pattern':'plain','raw_nested':{'scores':[.9,.1],'unknown':None}}
    expected=copy.deepcopy(attrs)
    detector=SimpleNamespace(analyse=lambda path:[DetectedGarment('short_sleeve_top',.9,copy.deepcopy(attrs),crop_png=png('blue'))])
    before=strict_ids();job=upload(client,detector,monkeypatch)
    assert job['status']=='review_required',job
    with db.connection() as conn:
        raw=json.loads(conn.execute('SELECT attributes_json FROM processing_items WHERE id=?',(job['items'][0]['id'],)).fetchone()[0])
        assert all(raw[k]==v for k,v in expected.items())
    response=review(client,job);assert response.status_code==200,response.text
    response=confirm(client,job);assert response.status_code==201,response.text
    gid=response.json()['garment_ids'][0];uuid.UUID(gid)
    assert gid!=job['items'][0]['id'] and strict_ids()==before|{gid}
    with db.connection() as conn:
        row=conn.execute('SELECT * FROM garments WHERE id=?',(gid,)).fetchone()
        assert row['processing_item_id']==job['items'][0]['id'] and row['status']=='available'
        saved=json.loads(row['attributes_json']);assert saved['raw_nested']==expected['raw_nested']
        assert subtype.source(conn,'style-owner',row)['state']=='Absent'
    scope=policy.capture('style-owner',male)
    assert gid not in {g.garment_id for g in scope.get_confirmed_available_garments('style-owner')}
    with db.connection() as conn:
        row=conn.execute('SELECT * FROM garments WHERE id=?',(gid,)).fetchone()
        with pytest.raises(HTTPException) as error:policy.require_categories(conn,'style-owner',male,[row])
        assert error.value.status_code==409 and error.value.detail['code']=='WearerSubtypeUnresolved'

@pytest.mark.parametrize('kind',['t_shirt','blouse'])
def test_owner_event_transfers_and_controls_male_eligibility(subtype_processing_api,monkeypatch,kind):
    client,male,female=subtype_processing_api;client.headers['X-Wardrobe-Profile-Id']=female
    job=upload(client,DevelopmentGarmentAdapter(),monkeypatch)
    assert job['status']=='review_required',job
    response=review(client,job,kind);assert response.status_code==200,response.text
    item=response.json()['items'][0]
    assert item['verified_subtype']['state']=='Known' and item['verified_subtype']['value']==kind
    response=confirm(client,job);assert response.status_code==201,response.text
    gid=response.json()['garment_ids'][0]
    with db.connection() as conn:
        row=conn.execute('SELECT * FROM garments WHERE id=?',(gid,)).fetchone()
        value=subtype.source(conn,'style-owner',row)
        assert value['state']=='Known' and value['value']==kind
        event=value['events'][0];assert event['event_kind']=='system_transfer'
        assert event['transfer_source']['subject_id']==item['id'] and event['subject_id']==gid
        assert event['origin']=='owner_selected'
    male_ids={g.garment_id for g in policy.capture('style-owner',male).get_confirmed_available_garments('style-owner')}
    female_ids={g.garment_id for g in policy.capture('style-owner',female).get_confirmed_available_garments('style-owner')}
    assert (gid in male_ids)==(kind=='t_shirt') and gid in female_ids

def test_male_cannot_accept_unknown_or_forged_subtype(subtype_processing_api,monkeypatch):
    client,male,female=subtype_processing_api
    job=upload(client,DevelopmentGarmentAdapter(),monkeypatch)
    assert job['status']=='review_required',job
    before=strict_ids();response=review(client,job)
    assert response.status_code==409 and response.json()['detail']['code']=='WearerSubtypeUnresolved',response.text
    assert strict_ids()==before
    forged={'items':[{'item_id':job['items'][0]['id'],'decision':'accepted','category':'short_sleeve_top','attributes':{'verified_subtype':{'state':'Known','value':'t_shirt'}}}]}
    response=client.post('/api/v1/processing/jobs/'+job['id']+'/review',json=forged)
    assert response.status_code==422 and strict_ids()==before,response.text
    response=review(client,job,'blouse')
    assert response.status_code==409 and response.json()['detail']['code']=='WearerSubtypeNotPermitted',response.text

def test_foreign_and_archived_scopes_cannot_reach_preinsert_permission(subtype_processing_api):
    client,male,female=subtype_processing_api
    with db.connection() as conn:
        with pytest.raises(HTTPException) as error:
            policy.annotations(conn,'foreign-account',female,[{'detected_category':'trousers','attributes_json':'{}'}])
        assert error.value.status_code==404
    response=client.post(f'/api/v1/account/wardrobe-profiles/{female}/archive',headers={'X-Wardrobe-Profile-Id':female})
    assert response.status_code==200,response.text
    with db.connection() as conn:
        with pytest.raises(HTTPException) as error:
            policy.annotations(conn,'style-owner',female,[{'detected_category':'trousers','attributes_json':'{}'}])
        assert error.value.status_code==409 and error.value.detail['code']=='WearerArchived'

def test_descendant_scope_retains_all_original_input_bytes():
    root=Path(__file__).resolve().parents[3]
    before=json.loads((root/'ANCESTOR_FILES.json').read_text())
    changed=[name for name,h in before.items() if hashlib.sha256((root/'source'/name).read_bytes()).hexdigest()!=h]
    assert changed==['backend/app/application/wardrobe/wearer_category_service.py']
    scope=json.loads((root/'PRE_EDIT_SCOPE.json').read_text())
    assert scope['production'][0]['before_sha256']==before[changed[0]]
    assert not scope['teammate_files_changed'] and not scope['schema_changes'] and not scope['shared_contract_changes']


@pytest.mark.parametrize('profile',['disabled','gender_category_v1','gender_category_subtype_v2'])
@pytest.mark.parametrize('interrupted',[False,True])
def test_composition_restores_exact_prior_configuration(subtype_processing_api,monkeypatch,profile,interrupted):
    import os
    from app.infrastructure.workflow_runtime import configure_local_workflow
    from app.application.ports import workflow_runtime
    def select(patch,value):
        patch.setenv(policy.ENVIRONMENT_KEY,value)
        patch.setenv('SMART_WARDROBE_VERIFIED_SUBTYPE_PROFILE','verified_subtype_v1' if value=='gender_category_subtype_v2' else 'disabled')
        configure_local_workflow()
    with monkeypatch.context() as incoming:
        select(incoming,profile)
        previous=_composition_snapshot()
        previous_policy=policy.policy()
        previous_subtype_store=workflow_runtime.runtime().subtype_store
        before_environment={name:os.getenv(name) for name in (policy.ENVIRONMENT_KEY,'SMART_WARDROBE_VERIFIED_SUBTYPE_PROFILE')}
        def exercise():
            with _preserve_composition():
                with monkeypatch.context() as temporary:
                    select(temporary,'disabled' if profile=='gender_category_subtype_v2' else 'gender_category_subtype_v2')
                    assert any(getattr(module,name) is not value for module,name,value in previous)
                    if interrupted:raise RuntimeError('deliberate runtime isolation interruption')
        if interrupted:
            with pytest.raises(RuntimeError,match='deliberate runtime isolation interruption'):
                exercise()
        else:exercise()
        assert all(getattr(module,name) is value for module,name,value in previous)
        assert policy.policy()==previous_policy
        assert workflow_runtime.runtime().subtype_store is previous_subtype_store
        assert {name:os.getenv(name) for name in before_environment}==before_environment


def test_composition_restores_genuinely_unconfigured_bindings(subtype_processing_api):
    from app.application.ports import workflow_runtime
    original=_composition_snapshot()
    with _preserve_composition():
        for module,name,_ in original:setattr(module,name,None)
        with _preserve_composition():
            for module,name,value in original:setattr(module,name,value)
            assert workflow_runtime.runtime() is original[0][2]
        assert all(getattr(module,name) is None for module,name,_ in original)
        with pytest.raises(RuntimeError,match='not been configured'):
            workflow_runtime.runtime()
    assert all(getattr(module,name) is value for module,name,value in original)
