"""Approved scenario contract through disposable APIs, with exact source disclosure."""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import uuid
import pytest
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.security import issue_access_token
from app.application.ports.assistant_runtime import assistant_service
from app.application.garment_processing import garment_processing_orchestrator as processing
from app.domain.value_objects.saved_attribute_evidence import KEY as SOURCE_KEY
from tests.test_automatic_garment_finalization import automatic_api,SyntheticDetector,upload,retry,garments
from tests.test_everyday_context import everyday_api
from tests.test_release_configuration import release,submit
from tests.test_forward_style_semantics import lifecycle
from tests.test_owner_style_confirmation import add,edit,garment
from tests.test_contextual_wedding import review
from tests.test_suitability_controls import patch_tags

LABELS=json.loads((Path(__file__).with_name('fixtures')/'automatic_admission_labels.v1.json').read_text(encoding='utf-8'))['contract']


def legacy(client,style='casual',category='vest_dress'):
    gid=add(client,None if style is None else style if isinstance(style,list) else [style],category,intent=False)
    with db.connection() as conn:
        for column in ('attributes_json','additional_attributes'):
            value=json.loads(conn.execute('SELECT '+column+' FROM garments WHERE id=?',(gid,)).fetchone()[0]);value.pop(SOURCE_KEY,None)
            conn.execute('UPDATE garments SET '+column+'=? WHERE id=?',(json.dumps(value),gid))
    return gid


def corrupt(client,gid,fn):
    with db.connection() as conn:
        for column in ('attributes_json','additional_attributes'):
            value=json.loads(conn.execute('SELECT '+column+' FROM garments WHERE id=?',(gid,)).fetchone()[0]);fn(value)
            conn.execute('UPDATE garments SET '+column+'=? WHERE id=?',(json.dumps(value),gid))


def stage(client,monkeypatch,rows=None):
    monkeypatch.setattr(processing,'get_garment_adapter',lambda:SyntheticDetector(rows))
    writer=processing.runtime().confirmed_writer
    with monkeypatch.context() as local:
        local.setattr(writer,'save_automatically_processed_candidates',lambda *args:None)
        return upload(client)


def capture(case,value):
    folder=os.getenv('SMART_WARDROBE_AUTOMATIC_EVIDENCE')
    if folder:
        path=Path(folder)/(case['id']+'.json');assert not path.exists()
        path.write_text(json.dumps({'approved_label':case,'observed':value},indent=2),encoding='utf-8')


@pytest.mark.parametrize('case',LABELS['scenarios'],ids=lambda c:c['id'])
def test_approved_scenarios(automatic_api,monkeypatch,case):
    client,_=automatic_api;identifier=case['id'];record={}
    if identifier[0] not in ('P','A'):
        gid=legacy(client,case['saved_style']);target,suffix=identifier.rsplit('-',1)
        if suffix=='D':assert patch_tags(client,gid,['rec:v1:occasion:'+target+':deny']).status_code==200
        if suffix=='X':corrupt(client,gid,lambda value:value.update(contextual_suitability_v1={'schema_version':'bad'}))
        before=garment(client,gid);_,result=submit(client,case['request']);record=result
        assert result['outcome']=={'Pass provisional':'Selected','Unknown':'InsufficientEvidence','Fail':'NoMatchingCandidates'}[case['expected_member_condition']],result
        assert garment(client,gid)==before
        if result['outcome']=='Selected':
            proof=result['recommendation']['provenance']['general_context'];assert proof['version']=='general-context-explanation-1.4.0'
            assert proof['members'][0]['conditions'][0]['basis']=='saved_attribute_provisional'
            assert proof['members'][0]['saved_attribute_evidence']['origin']=='unknown'
    elif identifier.startswith('P'):
        text="I'm going shopping";expected='Selected';gid=None
        if identifier in ('P01','P02','P03'):
            gid=legacy(client,'smart casual' if identifier=='P02' else 'casual')
            text+='; the dress code is '+('formal' if identifier=='P03' else 'casual')
            expected='PolicyUnavailable' if identifier=='P03' else 'InsufficientEvidence' if identifier=='P02' else 'Selected'
        elif identifier in ('P04','P06','P07','P08','P14'):
            gid=legacy(client)
            if identifier in ('P04','P07','P08'):assert review(client,gid,review_style=True).status_code==200
            if identifier=='P07':
                with db.connection() as conn:conn.execute("UPDATE garments SET category='sling_dress' WHERE id=?",(gid,))
            if identifier=='P08':assert review(client,gid,review_style=False).status_code==200
            if identifier=='P14':
                corrupt(client,gid,lambda value:value.update(contextual_suitability_v1={'schema_version':'bad'}))
                assert patch_tags(client,gid,['rec:v1:occasion:shopping:allow']).status_code==200
                expected='InsufficientEvidence'
        elif identifier=='P05':
            class ModelReported(SyntheticDetector):
                def analyse(self,path):
                    result=super().analyse(path);result[0].attributes['style_source']='model_reported';return result
            monkeypatch.setattr(processing,'get_garment_adapter',lambda:ModelReported());job=upload(client);gid=job['admission']['garment_ids'][0]
        elif identifier=='P09':
            job=upload(client);gid=job['admission']['garment_ids'][0]
            corrupt(client,gid,lambda value:value[SOURCE_KEY]['style'].update(media_id='stale-media'));expected='InsufficientEvidence'
        elif identifier=='P10':
            gid=legacy(client);legacy(client,category='long_sleeve_outwear')
        elif identifier in ('P11','P12'):
            gid=legacy(client,'smart casual');text="I'm going to a wedding" if identifier=='P11' else "I'm presenting my project at university";expected='InsufficientEvidence'
        elif identifier=='P13':
            for value in ([],['casual','classic'],['unknown-label']):legacy(client,value)
            expected='InsufficientEvidence'
        _,result=submit(client,text);assert result['outcome']==expected,result;record=result
        if expected=='Selected':
            m=result['recommendation']['provenance']['general_context']['members'][0]
            assert m['style_verification']==('owner_reviewed_current' if identifier=='P04' else 'saved_unreviewed')
            if identifier=='P05':assert m['saved_attribute_evidence']['origin']=='model_reported'
            if identifier=='P10':assert len(result['recommendation']['items'])==2 and result['recommendation']['total_score']==.8
        if identifier=='P12':assert submit(client,"I'm being interviewed for a job; the dress code is smart casual")[1]['outcome']=='InsufficientEvidence'
        if identifier=='P14':
            assert patch_tags(client,gid,['rec:v1:occasion:shopping:deny','rec:v1:occasion:shopping:allow']).status_code==200
            assert submit(client,text)[1]['outcome']=='NoMatchingCandidates'
    else:
        if identifier=='A01':
            monkeypatch.setattr(processing,'get_garment_adapter',lambda:SyntheticDetector([('long_sleeve_top','casual'),('trousers','casual')]))
            job=upload(client);assert job['status']=='completed' and len(garments(client))==2
            result=submit(client,"I'm going shopping")[1];assert result['outcome']=='Selected' and len(result['recommendation']['items'])==2
        elif identifier=='A02':
            monkeypatch.setattr(processing,'get_garment_adapter',lambda:SyntheticDetector([('vest_dress',None)]));job=upload(client)
            assert job['status']=='completed' and submit(client,"I'm going shopping")[1]['outcome']=='InsufficientEvidence'
        elif identifier in ('A03','A05','A12'):
            rows=[('Unclassified garment','casual')] if identifier!='A05' else [('vest_dress','casual'),('Unclassified garment',None)]
            monkeypatch.setattr(processing,'get_garment_adapter',lambda:SyntheticDetector(rows));job=upload(client)
            assert job['admission']['state']=='incomplete' and garments(client)==[]
            if identifier=='A12':
                r=client.post('/api/v1/processing/jobs/'+job['id']+'/review',json={'items':[{'item_id':job['items'][0]['id'],'decision':'accepted','category':'vest_dress'}]});assert r.status_code==200 and r.json()['status']=='completed'
                assert not garments(client)[0]['contextual_edit']['review_current']
        elif identifier=='A04':
            monkeypatch.setattr(processing,'get_garment_adapter',lambda:SimpleNamespace(analyse=lambda _:[]));job=upload(client);assert job['status']=='failed' and garments(client)==[]
        elif identifier=='A06':
            monkeypatch.setattr(processing,'get_garment_adapter',lambda:SyntheticDetector([('vest_dress',None)]*99));assert upload(client)['status']=='completed'
            monkeypatch.setattr(processing,'get_garment_adapter',lambda:SyntheticDetector([('long_sleeve_top','casual'),('trousers','casual')]))
            job=upload(client);assert job['admission']['reason']=='WardrobeQuotaExceeded' and len(garments(client))==99
            with db.connection() as conn:conn.execute("UPDATE garments SET status='archived' WHERE id=(SELECT id FROM garments LIMIT 1)")
            assert retry(client,job).status_code==201
            assert client.get('/api/v1/wardrobe/quota').json()['used']==100
        elif identifier in ('A07','A08','A09','A10'):
            job=stage(client,monkeypatch,[('long_sleeve_top','casual'),('trousers','casual')])
            if identifier=='A07':
                db.ensure_user('foreign-owner')
                with db.connection() as conn:conn.execute("UPDATE media_assets SET user_id='foreign-owner' WHERE id=?",(job['items'][0]['preferred_media_id'],))
                assert retry(client,job).status_code==409 and garments(client)==[]
            elif identifier=='A08':
                assert client.post('/api/v1/processing/jobs/'+job['id']+'/cancel').status_code==204
                assert retry(client,job).status_code==409 and garments(client)==[]
            elif identifier=='A09':
                with db.connection() as conn:conn.execute("CREATE TRIGGER matrix_auto_abort BEFORE INSERT ON garments WHEN (SELECT count(*) FROM garments)>0 BEGIN SELECT RAISE(ABORT,'synthetic'); END")
                with pytest.raises(sqlite3.IntegrityError):retry(client,job)
                assert garments(client)==[]
                with db.connection() as conn:conn.execute('DROP TRIGGER matrix_auto_abort')
                assert retry(client,job).status_code==201
            else:
                first=retry(client,job);second=retry(client,job)
                assert first.status_code==second.status_code==201 and second.json()['replayed']
                assert first.json()['garment_ids']==second.json()['garment_ids'] and len(garments(client))==2
        elif identifier=='A11':
            job=upload(client,None);assert job['status']=='review_required' and garments(client)==[]
        elif identifier=='A13':
            class Forged(SyntheticDetector):
                def analyse(self,path):
                    rows=super().analyse(path)
                    rows[0].attributes.update(owner_style_confirmation_v1={'owner_id':'forged'},contextual_suitability_v1={'schema_version':'1.0.0'},saved_attribute_sources_v1={'reviewed_at':'forged'},automatic_garment_admission_v1={'state':'saved'},custom_tags=['rec:v1:occasion:shopping:allow'])
                    return rows
            monkeypatch.setattr(processing,'get_garment_adapter',lambda:Forged());job=upload(client);g=garments(client)[0]
            assert 'owner_style_confirmation_v1' not in g['attributes'] and 'contextual_suitability_v1' not in g['attributes']
            assert not g['custom_tags'] and g['attributes'][SOURCE_KEY]['style']['origin']=='synthetic'
        elif identifier=='A14':
            job=upload(client)
            with db.connection() as conn:conn.execute("UPDATE processing_jobs SET status='processing' WHERE id=?",(job['id'],))
            assert submit(client,"I'm going shopping")[1]['outcome']=='NoEligibleGarments'
        elif identifier=='A15':
            job=upload(client);gid=garments(client)[0]['id'];service=assistant_service();original=service.repository.persist_assistant
            def changed(command):
                assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'attributes':{'style':['classic']}}).status_code==200
                return original(command)
            monkeypatch.setattr(service.repository,'persist_assistant',changed)
            assert submit(client,"I'm going shopping")[1]['outcome']=='WardrobeChanged'
            with db.connection() as conn:assert conn.execute('SELECT count(*) FROM nlp_chats').fetchone()[0]==0
        record={'job':client.get('/api/v1/processing/jobs/'+job['id']).json(),'garments':garments(client)}
    capture(case,record)


def test_eight_legacy_named_replicas_need_no_edit_or_review(everyday_api):
    client,_=everyday_api
    rows=[('Blue T-shirt','short_sleeve_top','blue','casual'),('White Shirt','long_sleeve_top','white','smart casual'),('Black Trousers','trousers','black','smart casual'),('Blue Jeans','trousers','blue','casual'),('Beige Shorts','shorts','beige','casual'),('Navy Dress','vest_dress','navy','smart casual'),('Grey Jacket','long_sleeve_outwear','grey','smart casual'),('Green Sweatshirt','long_sleeve_top','green','casual')]
    for name,category,colour,style in rows:
        gid=legacy(client,style,category)
        assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'name':name,'primary_colour':colour}).status_code==200
    before=garments(client)
    assert all(not g['contextual_edit']['review_current'] for g in before)
    for text in ("I'm going shopping","I'm going to class","I'm going out with friends","I'm going on a date","I'm meeting friends for dinner"):
        result=submit(client,text)[1];assert result['outcome']=='Selected',result
        assert result['recommendation']['provenance']['general_context']['version']=='general-context-explanation-1.4.0'
    assert garments(client)==before
