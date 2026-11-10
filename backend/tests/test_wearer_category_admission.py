"""Real processing and wardrobe writes on disposable, authenticated SQLite."""
import json
import pytest
from tests.test_wearer_category_policy import category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,set_gender
from tests.test_automatic_garment_finalization import SyntheticDetector,upload,retry
from app.application.garment_processing import garment_processing_orchestrator as processing
from app.infrastructure.persistence import postgresql_repository as db

def count(client):return len(client.get('/api/v1/wardrobe/garments').json())

@pytest.mark.parametrize('category',['skirt','short_sleeve_dress','long_sleeve_dress','vest_dress','sling_dress'])
@pytest.mark.parametrize('automatic',[False,True])
def test_male_denied_at_review_and_materialisation(category_api,monkeypatch,category,automatic):
    client,male,_=category_api;before=count(client)
    monkeypatch.setattr(processing,'get_garment_adapter',lambda:SyntheticDetector([(category,'casual')]))
    job=upload(client,mode='automatic_structural_v1' if automatic else None)
    assert job['status']=='review_required' and count(client)==before
    item=job['items'][0];assert item['wearer_category_eligibility']['usable'] is False
    r=client.post(f"/api/v1/processing/jobs/{job['id']}/review",json={'items':[{'item_id':item['id'],'decision':'accepted','category':category}]})
    assert r.status_code==409 and r.json()['detail']['code']=='WearerCategoryNotPermitted',r.text
    # Bypass the review HTTP boundary: final writer must independently refuse.
    with db.connection() as conn:conn.execute("UPDATE processing_items SET review_status='accepted' WHERE id=?",(item['id'],))
    r=client.post(f"/api/v1/processing/jobs/{job['id']}/confirm",json={'item_ids':[item['id']],'save_mode':'garments','admission_mode':'automatic_structural_v1' if automatic else 'manual_review_v1'})
    assert r.status_code==409 and count(client)==before,r.text

@pytest.mark.parametrize('category',['long_sleeve_top','trousers'])
def test_male_allowed_admission(category_api,monkeypatch,category):
    client,male,_=category_api;before=count(client)
    monkeypatch.setattr(processing,'get_garment_adapter',lambda:SyntheticDetector([(category,'casual')]))
    job=upload(client);assert job['status']=='completed' and count(client)==before+1

@pytest.mark.parametrize('category',['skirt','vest_dress','trousers'])
def test_female_allowed_admission(category_api,monkeypatch,category):
    client,_,female=category_api;before=count(client)
    client.headers['X-Wardrobe-Profile-Id']=female
    monkeypatch.setattr(processing,'get_garment_adapter',lambda:SyntheticDetector([(category,'casual')]))
    job=upload(client);assert job['status']=='completed' and count(client)==before+1,job

def test_unknown_and_mixed_batch_no_partial_and_valid_correction(category_api,monkeypatch):
    client,male,_=category_api;before=count(client)
    monkeypatch.setattr(processing,'get_garment_adapter',lambda:SyntheticDetector([('trousers','casual'),('Unclassified garment','casual')]))
    job=upload(client);assert job['status']=='review_required' and count(client)==before
    unknown=next(i for i in job['items'] if i['detected_category']=='Unclassified garment')
    assert unknown['wearer_category_eligibility']['usable'] is False
    r=client.post(f"/api/v1/processing/jobs/{job['id']}/review",json={'items':[{'item_id':unknown['id'],'decision':'accepted','category':'long_sleeve_top'}]})
    assert r.status_code==200 and r.json()['status']=='completed',r.text
    assert count(client)==before+2

def test_direct_category_typed_and_shared_outfit_guards(category_api):
    client,male,female=category_api;garments=client.get('/api/v1/wardrobe/garments').json()
    top=next(g for g in garments if g['category']=='long_sleeve_top');dress=next(g for g in garments if g['category'].endswith('_dress'))
    path='/api/v1/wardrobe/garments/'+top['id']
    denied=client.patch(path,json={'category':'skirt'});assert denied.status_code==409,denied.text
    view=top['description']
    typed={'contract':'garment-description-update-1.0.0','expected_revision':view['revision'],'operations':{'category':{'kind':'set','value':'skirt'}}}
    denied=client.patch(path,json={'description_update':typed});assert denied.status_code==409,denied.text
    denied=client.post('/api/v1/wardrobe/outfits',json={'name':'Denied shared dress','garment_ids':[dress['id']]});assert denied.status_code==409,denied.text
    permitted=client.post('/api/v1/wardrobe/outfits',headers={'X-Wardrobe-Profile-Id':female},json={'name':'Female shared dress','garment_ids':[dress['id']]});assert permitted.status_code==201,permitted.text
    outfit=permitted.json();denied=client.patch('/api/v1/wardrobe/outfits/'+outfit['id'],json={'name':'Male reuse'})
    assert denied.status_code==409,denied.text
    assert client.get('/api/v1/wardrobe/garments').json()==garments

@pytest.mark.parametrize('gender',[None,'custom','non-binary','unknown'])
def test_unconfigured_upload_refused_before_creating_job(category_api,gender):
    from tests.test_garment_workflow import jpeg
    client,male,_=category_api;set_gender(client,male,gender)
    with db.connection() as conn:before=conn.execute('SELECT count(*) FROM processing_jobs').fetchone()[0]
    r=client.post('/api/v1/processing/jobs',files={'file':('test.jpg',jpeg(),'image/jpeg')});assert r.status_code==409,r.text
    with db.connection() as conn:assert conn.execute('SELECT count(*) FROM processing_jobs').fetchone()[0]==before
