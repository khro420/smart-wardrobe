"""Independent owner-intent, currency and no-promotion API checks."""
import json
from pathlib import Path
import pytest
from tests.test_everyday_context import everyday_api
from tests.test_release_configuration import release, submit
from tests.test_forward_style_semantics import lifecycle
from tests.test_garment_workflow import jpeg
from app.infrastructure.persistence import postgresql_repository as db
from app.application.wardrobe.owner_style_confirmation import KEY, CONTRACT

LABELS = json.loads((Path(__file__).with_name('fixtures')/'owner_style_admission_labels.v1.json').read_text())


def prepare(client, style=None, category='vest_dress', intent=True):
    response = client.post('/api/v1/processing/jobs', files={'file': ('synthetic.jpg', jpeg(), 'image/jpeg')})
    assert response.status_code == 202, response.text
    job = client.get('/api/v1/processing/jobs/'+response.json()['id']).json()
    item = job['items'][0]
    update = {'item_id':item['id'], 'decision':'accepted', 'category':category,
              'primary_colour':'blue', 'attributes':{'style':style, 'custom_tags':[]}}
    if intent:
        update['style_confirmation'] = {'contract':CONTRACT, 'expected_revision':item['style_confirmation']['revision'],
                                        'style':style[0] if isinstance(style,list) and style else style}
    return job, item, update


def add(client, style=('casual',), category='vest_dress', intent=True):
    style = list(style) if isinstance(style, tuple) else style
    job,item,update = prepare(client,style,category,intent)
    r=client.post('/api/v1/processing/jobs/'+job['id']+'/review',json={'items':[update]})
    assert r.status_code==200,r.text
    r=client.post('/api/v1/processing/jobs/'+job['id']+'/confirm',json={'item_ids':[item['id']], 'save_mode':'garments'})
    assert r.status_code==201,r.text
    return r.json()['garment_ids'][0]


def garment(client,gid):
    return next(g for g in client.get('/api/v1/wardrobe/garments').json() if g['id']==gid)


def edit(client,gid,style,revision=None,**extra):
    g=garment(client,gid)
    return client.patch('/api/v1/wardrobe/garments/'+gid,json={**extra,'attributes':{'style':[style]},
        'style_confirmation':{'contract':CONTRACT,'expected_revision':revision or g['style_confirmation']['revision'],'style':style}})


@pytest.mark.parametrize('case',LABELS['cases'],ids=lambda c:c['id'])
def test_addition_labels(everyday_api,case):
    client,_=everyday_api;gid=add(client,case['style'],intent=case['intent']);g=garment(client,gid)
    assert g['contextual_edit']['review_current'] is case['expected_review']
    assert g['style_confirmation']['source']==('candidate_accept' if case['expected_review'] else None)
    assert g['attributes'].get('contextual_suitability_v1')==g['additional_attributes'].get('contextual_suitability_v1')


@pytest.mark.parametrize('style',[None,[],['casual','classic'],['unknown-label']])
def test_invalid_explicit_style_rejected_without_partial_review(everyday_api,style):
    client,_=everyday_api;job,item,update=prepare(client,['casual'])
    update['attributes']['style']=style
    r=client.post('/api/v1/processing/jobs/'+job['id']+'/review',json={'items':[update]})
    assert r.status_code==422
    after=client.get('/api/v1/processing/jobs/'+job['id']).json()['items'][0]
    assert after['attributes']==item['attributes'] and after['review_status']==item['review_status']


@pytest.mark.parametrize('mutation',['contract','extra','revision','mismatch','reject','omitted_style','forged_namespace'])
def test_strict_intent_and_revision(everyday_api,mutation):
    client,_=everyday_api;job,item,update=prepare(client,['casual'])
    if mutation=='contract': update['style_confirmation']['contract']='unapproved'
    if mutation=='extra': update['style_confirmation']['reviewer']='invented'
    if mutation=='revision': update['style_confirmation']['expected_revision']='0'*64
    if mutation=='mismatch': update['style_confirmation']['style']='smart casual'
    if mutation=='reject': update['decision']='rejected'
    if mutation=='omitted_style': update['attributes'].pop('style')
    if mutation=='forged_namespace': update['attributes'][KEY]={'event':'candidate_accept'}
    r=client.post('/api/v1/processing/jobs/'+job['id']+'/review',json={'items':[update]})
    assert r.status_code==(409 if mutation=='revision' else 422),r.text


@pytest.mark.parametrize('change',[{'name':'Different name'},{'primary_colour':'red'},{'attributes':{'fit':'regular'}}])
def test_unrelated_edits_preserve_and_withdrawal_does_not_resurrect(everyday_api,change):
    client,_=everyday_api;gid=add(client);before=garment(client,gid)
    assert client.patch('/api/v1/wardrobe/garments/'+gid,json=change).status_code==200
    current=garment(client,gid);assert current['contextual_edit']['review_current']
    assert current['attributes'][KEY]==before['attributes'][KEY]
    assert client.post('/api/v1/wardrobe/garments/'+gid+'/contextual-suitability',json={'revision':current['contextual_edit']['revision'],'review_style':False}).status_code==200
    assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'name':'Unrelated again'}).status_code==200
    current=garment(client,gid);assert not current['contextual_edit']['review_current'] and KEY not in current['attributes'] and KEY not in current['additional_attributes']
    assert edit(client,gid,'casual').status_code==200
    assert garment(client,gid)['contextual_edit']['review_current']


def test_normal_correction_and_stale_revision(everyday_api):
    client,_=everyday_api;gid=add(client,intent=False);old=garment(client,gid)
    r=edit(client,gid,'smart casual');assert r.status_code==200,r.text
    assert r.json()['style_confirmation']['source']=='garment_edit'
    before=garment(client,gid)
    assert edit(client,gid,'casual',old['style_confirmation']['revision']).status_code==409
    assert garment(client,gid)==before
    assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'category':'sling_dress'}).status_code==200
    assert not garment(client,gid)['contextual_edit']['review_current']
    assert edit(client,gid,'smart casual').status_code==200


@pytest.mark.parametrize('change',[{'category':'sling_dress'},{'attributes':{'style':['smart casual']}},{'preferred_media':'vtoff'}])
def test_pending_dependency_change_invalidates(everyday_api,change):
    client,_=everyday_api;job,item,update=prepare(client,['casual'])
    base='/api/v1/processing/jobs/'+job['id']
    if 'preferred_media' in change:
        # Provide a distinct owned synthetic representation; this test makes no model claim.
        _, other, _ = prepare(client,['casual'],intent=False)
        with db.connection() as conn:
            conn.execute('UPDATE processing_items SET vtoff_media_id=? WHERE id=?',(other['preferred_media_id'],item['id']))
        refreshed=client.get(base).json()['items'][0]
        assert refreshed['vtoff_media_id'] != refreshed['preferred_media_id']
        update['style_confirmation']['expected_revision']=refreshed['style_confirmation']['revision']
    assert client.post(base+'/review',json={'items':[update]}).status_code==200
    r=client.post(base+'/review',json={'items':[{'item_id':item['id'],'decision':'accepted',**change}]})
    assert r.status_code==200
    assert not r.json()['items'][0]['style_confirmation']['current']
    result=client.post(base+'/confirm',json={'item_ids':[item['id']],'save_mode':'garments'})
    assert result.status_code==201
    assert not garment(client,result.json()['garment_ids'][0])['contextual_edit']['review_current']


def test_stale_pending_proof_and_atomic_review_rollback(everyday_api):
    client,_=everyday_api;job,item,update=prepare(client,['casual']);base='/api/v1/processing/jobs/'+job['id']
    assert client.post(base+'/review',json={'items':[update]}).status_code==200
    with db.connection() as conn:
        attrs=json.loads(conn.execute('SELECT attributes_json FROM processing_items WHERE id=?',(item['id'],)).fetchone()[0]);attrs['style']=['smart casual']
        conn.execute('UPDATE processing_items SET attributes_json=? WHERE id=?',(json.dumps(attrs),item['id']))
    assert client.post(base+'/confirm',json={'item_ids':[item['id']],'save_mode':'garments'}).status_code==409
    assert client.get('/api/v1/wardrobe/garments').json()==[]


def test_malformed_mirror_and_declaration_barrier(everyday_api):
    client,_=everyday_api;gid=add(client,intent=False)
    with db.connection() as conn:
        conn.execute('UPDATE garments SET additional_attributes=? WHERE id=?',('{bad',gid))
    # Read revision directly: the ordinary view rejects malformed JSON already.
    from app.application.wardrobe.owner_style_confirmation import garment_revision
    with db.connection() as conn: rev=garment_revision(conn.execute('SELECT * FROM garments WHERE id=?',(gid,)).fetchone())
    from app.application.wardrobe.wardrobe_service import update_garment
    from fastapi import HTTPException
    with pytest.raises((HTTPException,ValueError)):
        update_garment(gid,'style-owner',{'attributes':{'style':['casual']},'style_confirmation':{'contract':CONTRACT,'expected_revision':rev,'style':'casual'}})


def test_automatic_adapter_cannot_create_pending_attestation(everyday_api,monkeypatch):
    from types import SimpleNamespace
    from app.application.garment_processing import garment_processing_orchestrator as processing
    from app.domain.value_objects.garment_attributes import GarmentAttributes
    monkeypatch.setattr(processing,'get_attribute_adapter',lambda:SimpleNamespace(extract=lambda _:GarmentAttributes({'style':['casual'],KEY:{'event':'candidate_accept'}})))
    client,_=everyday_api;job,item,update=prepare(client,['casual'],intent=False)
    assert KEY not in item['attributes']


def test_existing_source_transition():
    from tests import integration_source_guard as guard
    # Verify all final bytes, then independently reconcile each starting byte with
    # its latest frozen accepted manifest. Avoid recursively re-running every old
    # bundle audit for each individual path; no old manifest is repinned or skipped.
    manifest=guard.automatic_admission_manifest()
    assert manifest['version']=='automatic-admission-1.0.0'
    fixtures=Path(__file__).with_name('fixtures')
    names=('owner_style_admission_sources.v1.json','everyday_context_sources.v1.json','professional_academic_sources.v1.json',
           'date_dinner_context_sources.v1.json','general_context_sources.v1.json','contextual_wedding_sources.v1.json','wardrobe_quota_sources.v1.json')
    prior=[json.loads((fixtures/name).read_text(encoding='utf-8')) for name in names]
    archive=json.loads((fixtures/'compact_reference/manifest.json').read_text(encoding='utf-8'))
    for name,change in manifest['replacements'].items():
        previous=next((entry['replacements'][name]['after'] for entry in prior if name in entry['replacements']),archive.get(name.removeprefix('backend/')))
        assert change['before']==previous,name


def test_batch_review_rolls_back_when_later_item_is_invalid(everyday_api):
    client,_=everyday_api;job,item,update=prepare(client,['casual'])
    invalid={**update,'item_id':'missing-candidate'}
    response=client.post('/api/v1/processing/jobs/'+job['id']+'/review',json={'items':[update,invalid]})
    assert response.status_code==404
    current=client.get('/api/v1/processing/jobs/'+job['id']).json()['items'][0]
    assert current['attributes']==item['attributes'] and current['review_status']==item['review_status']
