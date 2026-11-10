"""Disposable authenticated writes, source binding, concurrency and rollback."""
from concurrent.futures import ThreadPoolExecutor
import json
import pytest
from fastapi import HTTPException
from tests.test_everyday_context import everyday_api, release, lifecycle
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.infrastructure.persistence import postgresql_repository as db
from app.application.wardrobe import description_projector as d


@pytest.fixture
def description_api(everyday_api,monkeypatch):
    monkeypatch.setenv('SMART_WARDROBE_DESCRIPTION_PROFILE','description_evidence_v1')
    configure_local_workflow()
    return everyday_api


def garment(client,gid):
    return next(g for g in client.get('/api/v1/wardrobe/garments').json() if g['id']==gid)


def body(g,operations):
    return {'description_update':{'contract':'garment-description-update-1.0.0',
            'expected_revision':g['description']['revision'],'operations':operations}}


def read_row(gid):
    with db.connection() as conn:return dict(conn.execute('SELECT * FROM garments WHERE id=?',(gid,)).fetchone())


def test_explicit_observations_replace_only_selected_channels(description_api):
    client,create=description_api;gid=create(['casual']);g=garment(client,gid)
    response=client.patch('/api/v1/wardrobe/garments/'+gid,json=body(g,{
        'neckline':{'kind':'set','value':'square'},'material':{'kind':'unsure'},
        'colour_temperature':{'kind':'set','value':'neutral'},'colour_dominance':{'kind':'set','value':False}}))
    assert response.status_code==200,response.text
    data=response.json();fields=data['description']['evidence']['fields']
    assert fields['neckline']['canonical_values']==['square'] and data['description']['source_qualified']['neckline']
    assert fields['material']['state']=='Unsure'
    assert fields['colour_temperature']['canonical_values']==['neutral']
    assert fields['colour_dominance']['canonical_values']==[False]
    row=read_row(gid)
    assert json.loads(row['attributes_json'])[d.KEY]==json.loads(row['additional_attributes'])[d.KEY]


def test_primary_dependency_and_exact_palette_do_not_change_old_encoding(description_api):
    client,create=description_api;gid=create(['casual']);g=garment(client,gid)
    response=client.patch('/api/v1/wardrobe/garments/'+gid,json=body(g,{
        'secondary_colour':{'kind':'set','value':'white'},
        'colour_palette':{'kind':'set','value':[{'hex':'#0000ff','coverage':'0.500000'},{'hex':'#ffffff','coverage':'0.250000'}]},
        'colour_temperature':{'kind':'set','value':'cool'},'colour_dominance':{'kind':'set','value':True}}))
    assert response.status_code==200,response.text
    g=response.json();palette=g['description']['evidence']['fields']['colour_palette']
    assert palette['canonical_values'][0]['coverage']=='0.500000'
    assert g['attributes']['color_palette'][0]['coverage']==0.5
    assert g['secondary_colour']=='white'
    response=client.patch('/api/v1/wardrobe/garments/'+gid,json=body(g,{'primary_colour':{'kind':'set','value':'red'}}))
    assert response.status_code==200,response.text
    g=response.json()
    for field in ('secondary_colour','colour_palette','colour_temperature','colour_dominance'):
        assert g['description']['evidence']['fields'][field]['state']=='Stale',field
    response=client.patch('/api/v1/wardrobe/garments/'+gid,json=body(g,{'secondary_colour':{'kind':'clear'}}))
    assert response.status_code==200,response.text
    assert response.json()['secondary_colour'] is None
    assert response.json()['description']['evidence']['fields']['secondary_colour']['state']=='Absent'


def test_stale_revision_race_one_commit(description_api):
    client,create=description_api;gid=create(['casual']);g=garment(client,gid)
    payload=body(g,{'neckline':{'kind':'set','value':'crew'}})
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies=list(pool.map(lambda _:client.patch('/api/v1/wardrobe/garments/'+gid,json=payload),range(2)))
    assert sorted(r.status_code for r in replies)==[200,409]
    assert garment(client,gid)['description']['evidence']['fields']['neckline']['canonical_values']==['crew']


@pytest.mark.parametrize('checkpoint',['event','mirror'])
def test_faults_leave_exact_previous_row(description_api,monkeypatch,checkpoint):
    client,create=description_api;gid=create(['casual']);g=garment(client,gid);before=read_row(gid)
    if checkpoint=='event':
        real=d.finish_update
        def fail(*args,**kwargs):real(*args,**kwargs);raise HTTPException(507,'synthetic event fault')
        monkeypatch.setattr(d,'finish_update',fail)
    else:
        from app.application.wardrobe import wardrobe_service as wardrobe
        real=wardrobe._write_representation
        def fail(*args,**kwargs):real(*args,**kwargs);raise HTTPException(507,'synthetic mirror fault')
        monkeypatch.setattr(wardrobe,'_write_representation',fail)
    response=client.patch('/api/v1/wardrobe/garments/'+gid,json=body(g,{'neckline':{'kind':'set','value':'crew'}}))
    assert response.status_code==507,response.text
    assert read_row(gid)==before


def test_disabled_creation_stored_reader_and_no_repair(description_api,monkeypatch):
    client,create=description_api;gid=create(['casual']);g=garment(client,gid)
    response=client.patch('/api/v1/wardrobe/garments/'+gid,json=body(g,{'pattern':{'kind':'set','value':'plain'}}))
    assert response.status_code==200,response.text
    before=read_row(gid)
    monkeypatch.setenv('SMART_WARDROBE_DESCRIPTION_PROFILE','disabled');configure_local_workflow()
    g=garment(client,gid)
    assert g['description']['evidence']['fields']['pattern']['canonical_values']==['plain']
    response=client.patch('/api/v1/wardrobe/garments/'+gid,json=body(g,{'pattern':{'kind':'set','value':'floral'}}))
    assert response.status_code==422 and 'DescriptionUnavailable' in response.text
    assert read_row(gid)==before


def test_literal_tag_edit_cannot_remove_existing_context_declarations(description_api):
    client,create=description_api;gid=create(['casual']);g=garment(client,gid)
    existing=g['attributes']['custom_tags']
    protected=[tag for tag in existing if tag.casefold().startswith('rec:')]
    assert protected
    response=client.patch('/api/v1/wardrobe/garments/'+gid,json=body(g,{'descriptive_tags':{'kind':'set','value':['literal new note']}}))
    assert response.status_code==200,response.text
    g=response.json()
    assert all(tag in g['attributes']['custom_tags'] for tag in protected)
    assert g['description']['evidence']['fields']['descriptive_tags']['canonical_values']==['literal new note']
    assert g['description']['source_qualified']['descriptive_tags']


@pytest.mark.parametrize('operations',[
    {'material':{'kind':'set','value':['not sure']}},
    {'silhouette':{'kind':'set','value':'loose (fit)'}},
    {'sleeve_length':{'kind':'set','value':'long'}},
    {'colour_dominance':{'kind':'set','value':0}},
    {'descriptive_tags':{'kind':'set','value':['rec:v1:occasion:campus:allow']}},
    {'neckline':{'kind':'set','value':'x'*33000}},
])
def test_invalid_updates_are_atomic(description_api,operations):
    client,create=description_api;gid=create(['casual']);g=garment(client,gid);before=read_row(gid)
    response=client.patch('/api/v1/wardrobe/garments/'+gid,json=body(g,operations))
    assert response.status_code==422,response.text
    assert read_row(gid)==before
