"""Current authenticated disposable workflow, not a model-quality evaluation."""
from dataclasses import replace
import json
from types import SimpleNamespace
import pytest
from tests.test_description_persistence import description_api, everyday_api, release, lifecycle
from tests.test_garment_workflow import jpeg, Detector
from app.application.garment_processing import garment_processing_orchestrator as processing
from app.domain.value_objects.garment_attributes import GarmentAttributes
from app.infrastructure.persistence import postgresql_repository as db
from app.application.wardrobe import description_projector as d


def upload(client,automatic=False):
    response=client.post('/api/v1/processing/jobs'+('?admission_mode=automatic_structural_v1' if automatic else ''),files={'file':('synthetic.jpg',jpeg(),'image/jpeg')})
    assert response.status_code==202,response.text
    return client.get('/api/v1/processing/jobs/'+response.json()['id']).json()


def test_capture_precedes_null_merge_and_bottom_cleanup(description_api,monkeypatch):
    client,_=description_api
    detector=Detector()
    monkeypatch.setattr(processing,'get_garment_adapter',lambda:SimpleNamespace(analyse=lambda path:[replace(item,attributes={**item.attributes,'fit':None}) for item in detector.analyse(path)]))
    raw={'fit':'loose','fashionpedia_visible_attributes':{'silhouette':{'value':'loose','confidence':0.8},'neckline':{'value':'crew','confidence':0.8},'sleeve_length':{'value':'short','confidence':0.8}}}
    monkeypatch.setattr(processing,'get_attribute_adapter',lambda:SimpleNamespace(extract=lambda _:GarmentAttributes(raw)))
    job=upload(client)
    assert job['status']=='review_required'
    for item in job['items']:
        assert item['attributes']['fit'] is None
        assert item['attributes'][d.RAW_KEY]['flattened_silhouette']=='loose'
        field=item['description']['evidence']['fields']['silhouette']
        assert field['suggestion']['value']==['loose'] and not field['canonical_values']
        if item['detected_category']=='trousers':
            assert 'neckline' not in item['attributes']['fashionpedia_visible_attributes']
            assert item['attributes'][d.RAW_KEY]['visible_attributes']['neckline']['value']=='crew'
            assert item['description']['evidence']['fields']['neckline']['state']=='Inapplicable'


def test_typed_candidate_event_transfers_without_fabricating_confirmation(description_api):
    client,_=description_api;job=upload(client);item=job['items'][0];base='/api/v1/processing/jobs/'+job['id']
    update={'item_id':item['id'],'decision':'accepted','description_update':{'contract':'garment-description-update-1.0.0','expected_revision':item['description']['revision'],
            'operations':{'neckline':{'kind':'set','value':'crew'},'material':{'kind':'unsure'}}}}
    response=client.post(base+'/review',json={'items':[update]})
    assert response.status_code==200,response.text
    candidate=response.json()['items'][0]
    old=candidate['description']['evidence']['fields']['neckline']['selected']
    saved=client.post(base+'/confirm',json={'save_mode':'garments','item_ids':[item['id']]})
    assert saved.status_code==201,saved.text
    g=next(g for g in client.get('/api/v1/wardrobe/garments').json() if g['id']==saved.json()['garment_ids'][0])
    assert g['description']['evidence']['fields']['neckline']['selected']==old
    assert g['description']['source_qualified']['neckline']
    assert g['description']['evidence']['subject']['source_processing_item_id']==item['id']
    assert g['description']['evidence']['subject']['garment_id']==g['id']
    assert g['style_confirmation']['source'] is None


def test_automatic_missing_optional_facts_adds_no_review(description_api,monkeypatch):
    client,_=description_api
    from app.application.garment_processing import review_service
    monkeypatch.setattr(review_service,'review_job',lambda *a,**k: (_ for _ in ()).throw(AssertionError('mandatory review')))
    monkeypatch.setattr(processing,'get_attribute_adapter',lambda:SimpleNamespace(extract=lambda _:GarmentAttributes({'style':None,'fit':None,'material':None})))
    job=upload(client,automatic=True)
    assert job['status']=='completed',job
    assert all(item['review_status']=='confirmed' for item in job['items'])
    assert len(client.get('/api/v1/wardrobe/garments').json())==3
    for item in job['items']:
        fields=item['description']['evidence']['fields']
        assert fields['style']['state']=='Absent' and fields['material']['state']=='Absent'


def test_legacy_disabled_capability_is_explicit(everyday_api):
    client,_=everyday_api
    capability=client.get('/api/v1/processing/jobs/capabilities').json()
    assert capability['description']['enabled'] is False
    assert capability['description']['fields']==[]


def test_review_batch_failure_rolls_back_prior_item(description_api):
    client,_=description_api;job=upload(client)
    before={item['id']:item['attributes'] for item in job['items']}
    updates=[]
    for index,item in enumerate(job['items'][:2]):
        updates.append({'item_id':item['id'],'decision':'accepted','description_update':{'contract':'garment-description-update-1.0.0',
            'expected_revision':item['description']['revision'] if index==0 else '0'*64,'operations':{'material':{'kind':'set','value':['cotton']}}}})
    response=client.post('/api/v1/processing/jobs/'+job['id']+'/review',json={'items':updates})
    assert response.status_code==409,response.text
    after=client.get('/api/v1/processing/jobs/'+job['id']).json()
    assert {item['id']:item['attributes'] for item in after['items']}==before
