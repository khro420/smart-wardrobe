"""Portable current contracts adapted from the separate historical verification.

Original closed-route and capability assertions are retained. Synthetic function
fixtures replace the private demo copy; no historical source bridge is imported.
"""
from pathlib import Path
from io import BytesIO
import copy,json,os
import pytest
from app.infrastructure import security
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.ports.assistant_runtime import assistant_service
from app.application.ports.homepage_runtime import homepage_service
from app.application.wardrobe.profile_service import active_profile_id
from app.api import account_routes,wardrobe_routes,garment_processing_routes,recommendation_routes,visualisation_routes,chat_history_routes,media_routes
from tests.test_processing_subtype_identity_integration import (
    _preserve_composition,subtype_processing_api,category_api,language_api,
    palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,
    automatic_api,everyday_api,release,lifecycle)
SPEC=json.loads((Path(__file__).parent/'fixtures/authenticated_api_routes.current.v1.json').read_text())
OWNER='style-owner'
A=None
MODULES=(account_routes,wardrobe_routes,garment_processing_routes,recommendation_routes,visualisation_routes,chat_history_routes,media_routes)
ROUTES={m.__name__.split('.')[-1]+'.'+r.endpoint.__name__:r for m in MODULES for r in m.router.routes if hasattr(r,'dependant')}

@pytest.fixture(autouse=True)
def preserve_runtime_for_portable_contracts():
    with _preserve_composition():
        yield

def auth(token,wearer=None):
    return {'Authorization':'Bearer '+token,'X-Wardrobe-Profile-Id':wearer or A}

@pytest.fixture
def demo_api(subtype_processing_api,monkeypatch):
    global A
    client,male,female=subtype_processing_api
    # The retained active contract includes pure-garment continuation. The
    # inherited processing fixture deliberately does not enable that option.
    monkeypatch.setenv('SMART_WARDROBE_GARMENT_ONLY_REFINEMENT_PROFILE','garment_only_refinement_v1')
    configure_local_workflow()
    monkeypatch.setattr(__import__(__name__,fromlist=['A']),'A',male)
    client.headers.pop('Authorization',None)
    client.headers.pop('X-Wardrobe-Profile-Id',None)
    monkeypatch.setattr(security,'ALLOW_DEVELOPMENT_IDENTITY',False)
    token=security.issue_access_token(OWNER)
    revoked=security.issue_access_token(OWNER)
    assert client.post('/api/v1/account/logout',headers=auth(revoked)).status_code==204
    yield {'client':client,'token':token,'revoked':revoked,'values':{'wardrobe_profile_id':male}}

def snapshot():
    with db.connection() as c:
        tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {t:sorted([tuple(r) for r in c.execute('SELECT * FROM "'+t+'"')],key=repr) for t in tables}


def request_args(row,values=None):
    values={**row['path_values'],**(values or {})}
    url='/api/v1'+row['path'].format(**values)
    kw={}
    if row['json'] is not None:
        body=copy.deepcopy(row['json'])
        if 'garment_ids' in body and values.get('garment_id'):body['garment_ids']=[values['garment_id']]
        for name in ('person_image_id','recommendation_id'):
            if name in body and values.get(name):body[name]=values[name]
        if 'items' in body and values.get('item_id'):body['items'][0]['item_id']=values['item_id']
        if 'item_ids' in body and values.get('item_id'):body['item_ids']=[values['item_id']]
        kw['json']=body
    if row['multipart']:
        from PIL import Image
        payload=BytesIO();Image.new('RGB',(256,256),'blue').save(payload,'PNG')
        kw['files']={'file':('auth.png',payload.getvalue(),'image/png')}
    return url,kw


def test_closed_current_53_route_inventory_and_unique_logout_exception():
    actual=[]
    for module in MODULES:
        for route in module.router.routes:
            if not hasattr(route,'dependant'):continue
            deps=[d.call for d in route.dependant.dependencies]
            if security.current_user_id in deps:
                actual.append({'module':module.__name__,'name':route.endpoint.__name__,'path':route.path,'methods':sorted(route.methods)})
            if security.logout_bearer in deps:
                assert module is account_routes and route.endpoint is account_routes.logout
    expected=[{k:row[k] for k in ('module','name','path','methods')} for row in SPEC['routes']]
    assert len(actual)==SPEC['authenticated_dependencies']==53
    assert sorted(actual,key=repr)==sorted(expected,key=repr)
    logout=next(r for r in account_routes.router.routes if r.endpoint is account_routes.logout)
    assert [d.call for d in logout.dependant.dependencies]==[security.logout_bearer]


@pytest.mark.parametrize('row',SPEC['routes'],ids=lambda r:r['id'])
def test_every_current_route_uses_valid_schema_and_rejects_anonymous_and_revoked(demo_api,row):
    client=demo_api['client'];route=ROUTES[row['id']]
    url,kw=request_args(row,demo_api['values'])
    for field in route.dependant.body_params:
        if row['multipart']:continue
        model=field.field_info.annotation
        assert model.model_validate(kw['json']) is not None
    assert any(d.call is security.current_user_id for d in route.dependant.dependencies)
    before=snapshot()
    assert client.request(row['methods'][0],url,**kw).status_code==row['unauthenticated_status']
    assert client.request(row['methods'][0],url,headers=auth(demo_api['revoked']),**kw).status_code==row['revoked_status']
    assert snapshot()==before


def closed_capability(actual,expected):
    if type(expected) is dict:
        assert type(actual) is dict and set(actual)==set(expected),'closed capability keys'
        for k in expected:closed_capability(actual[k],expected[k])
    elif type(expected) is list:
        assert type(actual) is list and len(actual)==len(expected),'closed capability array'
        for a,b in zip(actual,expected):closed_capability(a,b)
    else:assert type(actual) is type(expected) and actual==expected,'closed capability value'


@pytest.mark.parametrize('engine',['reference','compact_exhaustive'])
def test_current_active_capabilities_are_exact_and_do_not_generate(demo_api,monkeypatch,engine):
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE',engine);configure_local_workflow()
    def forbidden(*a,**k):pytest.fail('Capability read generated a recommendation')
    monkeypatch.setattr(assistant_service(),'recommend',forbidden)
    monkeypatch.setattr(homepage_service(),'recommend',forbidden)
    before=snapshot()
    response=demo_api['client'].get('/api/v1/recommendations/capabilities',headers=auth(demo_api['token']))
    assert response.status_code==200
    closed_capability(response.json(),SPEC['capability_contract']['active'])
    assert snapshot()==before


def test_current_defaults_are_off_and_closed(demo_api,monkeypatch):
    for key in tuple(os.environ):
        if key.startswith('SMART_WARDROBE_') and key not in ('SMART_WARDROBE_AI_MODE','SMART_WARDROBE_DATA_DIR','SMART_WARDROBE_DATABASE','SMART_WARDROBE_TOKEN_SECRET','SMART_WARDROBE_ALLOW_DEV_IDENTITY'):
            monkeypatch.delenv(key)
    configure_local_workflow()
    value=recommendation_routes.capabilities(OWNER,homepage_service(),assistant_service())
    closed_capability(value,SPEC['capability_contract']['inactive'])
    assert homepage_service() is assistant_service() is None


@pytest.mark.parametrize('key',[
    'SMART_WARDROBE_ASSISTANT_LANGUAGE_PROFILE','SMART_WARDROBE_WEARER_CATEGORY_PROFILE',
    'SMART_WARDROBE_GARMENT_ONLY_REFINEMENT_PROFILE','SMART_WARDROBE_VERIFIED_SUBTYPE_PROFILE',
    'SMART_WARDROBE_ASSISTANT_PREFERENCE_PROFILE','SMART_WARDROBE_ASSISTANT_COMPATIBILITY_PROFILE'])
def test_unknown_current_profiles_fail_before_activation(demo_api,monkeypatch,key):
    monkeypatch.setenv(key,'unknown_profile')
    with pytest.raises(ValueError):configure_local_workflow()


@pytest.mark.parametrize('kind',['extra_root','extra_nested','unknown_profile','accidental_activation','missing_key','wrong_version'])
def test_current_capability_contract_rejects_targeted_invalid_values(kind):
    expected=SPEC['capability_contract']['inactive'];closed_capability(copy.deepcopy(expected),expected)
    bad=copy.deepcopy(expected)
    if kind=='extra_root':bad['unexpected']=True
    elif kind=='extra_nested':bad['garment_continuation']['surprise']=False
    elif kind=='unknown_profile':bad['garment_continuation']['profile']='unknown'
    elif kind=='accidental_activation':bad['assistant_enabled']=True
    elif kind=='missing_key':bad.pop('wearer_category_policy')
    else:bad['wearer_identity']['version']='unknown'
    with pytest.raises(AssertionError):closed_capability(bad,expected)
