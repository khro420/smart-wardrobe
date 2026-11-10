"""Pure read/provenance tests; database collection checks are added at CP3."""
import copy
import json
import pytest
from tests.test_description_persistence import description_api, everyday_api, release, lifecycle
from app.application.wardrobe.description_policy import DescriptionPolicy
from app.application.wardrobe import description_projector as d
from app.application.wardrobe.description_normalizer import qualified
from app.domain.value_objects.garment_description_evidence import KEY, GarmentDescriptionEvidence


@pytest.fixture(scope='module')
def policy():return DescriptionPolicy.load()


def row(attrs=None,**extra):
    return {'id':'garment-A','processing_item_id':'item-A','user_id':'owner-A',
            'category':'vest','name':'Literal name','preferred_media_id':'media-A',
            'primary_colour':'blue','pattern':None,'attributes_json':json.dumps(attrs or {}),**extra}


def test_raw_silhouette_survives_separate_from_selection(policy):
    model={'fit':'loose','fashionpedia_visible_attributes':{'silhouette':{'value':'loose','confidence':0.8}}}
    captured=d.capture_suggestions(model)
    model['fit']=None;model['fashionpedia_visible_attributes'].clear()
    attrs={'fit':None,d.RAW_KEY:captured}
    field=d.project(row(attrs),'owner-A',policy).to_dict()['fields']['silhouette']
    assert field['canonical_values']==[] and field['possible_values']==['loose']
    assert field['suggestion']['origin']=='model_suggestion' and not qualified(field)
    assert captured['flattened_silhouette']=='loose'


def test_conflicts_bottoms_and_invalid_confidence(policy):
    record=d.project(row({'custom_tags':['neckline: crew','neckline: v-neck']}),'owner-A',policy).to_dict()
    assert record['fields']['neckline']['state']=='Conflicting'
    attrs={d.RAW_KEY:d.capture_suggestions({'fashionpedia_visible_attributes':{'neckline':{'value':'crew','confidence':0.7}}})}
    bottom=d.project(row(attrs,category='trousers'),'owner-A',policy).to_dict()['fields']['neckline']
    assert bottom['state']=='Inapplicable' and bottom['suggestion'] is not None
    attrs[d.RAW_KEY]['visible_attributes']['neckline']['confidence']='nan'
    assert d.project(row(attrs),'owner-A',policy).to_dict()['fields']['neckline']['state']=='Malformed'


def action(original,**operations):
    return {'description_update':{'contract':'garment-description-update-1.0.0','expected_revision':d.revision(original,'owner-A'),'operations':operations}}


def test_typed_replace_retains_raw_and_transfer_event(policy):
    attrs={'custom_tags':['neckline: crew','neckline: v-neck']}
    original=row(attrs)
    _,plan=d.prepare_update(original,'owner-A',action(original,neckline={'kind':'set','value':'square'}),policy)
    attrs['neckline']='square'
    d.finish_update(original,'owner-A',attrs,'vest','media-A',plan,policy,'2026-10-31T00:00:00Z')
    after=row(attrs)
    evidence=d.project(after,'owner-A',None).to_dict()
    field=evidence['fields']['neckline']
    assert field['state']=='Known' and field['canonical_values']==['square'] and qualified(field)
    assert attrs['custom_tags']==['neckline: crew','neckline: v-neck']
    with pytest.raises(ValueError):GarmentDescriptionEvidence.from_dict({**attrs[KEY],'contract':'future'})


def test_wrong_subject_mirror_and_stale_values(policy):
    attrs={};original=row(attrs)
    _,plan=d.prepare_update(original,'owner-A',action(original,pattern={'kind':'set','value':'plain'}),policy)
    attrs['pattern']='plain'
    d.finish_update(original,'owner-A',attrs,'vest','media-A',plan,policy,'2026-10-31T00:00:00Z',pattern='plain')
    current=row(attrs,pattern='plain')
    assert d.project(current,'owner-A',None).to_dict()['fields']['pattern']['state']=='Known'
    assert d.project({**current,'pattern':'floral'},'owner-A',None).to_dict()['fields']['pattern']['state']=='Stale'
    assert d.project({**current,'additional_attributes':'{}'},'owner-A',None).to_dict()['fields']['pattern']['state']=='Malformed'
    assert d.project(current,'other-owner',None).to_dict()['fields']['pattern']['state']=='Malformed'
    assert d.project(row(),'owner-A',None) is None


@pytest.mark.parametrize('mutation',[
    {'extra':True},{'contract':'future'},{'expected_revision':'0'*64},
    {'operations':{'neckline':{'kind':'set','value':'round-crew'}}},
    {'operations':{'material':{'kind':'set','value':['not sure']}}},
    {'operations':{'colour_dominance':{'kind':'set','value':0}}},
    {'operations':{'descriptive_tags':{'kind':'set','value':['rec:v1:any']}}},
    {'operations':{'category':{'kind':'clear'}}},
    {'operations':{'colour_palette':{'kind':'set','value':[{'hex':'#000000','coverage':0.5}]}}},
])
def test_strict_update_negatives(policy,mutation):
    original=row();payload=action(original,neckline={'kind':'set','value':'crew'})
    payload['description_update'].update(mutation)
    with pytest.raises(d.DescriptionUpdateError):d.prepare_update(original,'owner-A',payload,policy)
    assert KEY not in d.attributes(original)


def test_disabled_and_duplicate_legacy_updates(policy):
    original=row();payload=action(original,neckline={'kind':'set','value':'crew'})
    with pytest.raises(d.DescriptionUpdateError,match='DescriptionUnavailable'):d.prepare_update(original,'owner-A',payload,None)
    payload['attributes']={'neckline':'v-neck'}
    with pytest.raises(d.DescriptionUpdateError):d.prepare_update(original,'owner-A',payload,policy)


def test_parallel_strict_collection_uses_one_select_without_changing_snapshot(description_api,policy):
    from dataclasses import asdict
    from app.infrastructure.persistence import postgresql_repository as db
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    client,create=description_api;gid=create(['casual'])
    before=SqliteConfirmedGarmentQuery().get_confirmed_available_garments('style-owner')
    with db.connection() as conn:
        statements=[];conn.set_trace_callback(statements.append)
        captured=SqliteConfirmedGarmentQuery(conn).get_confirmed_garment_descriptions('style-owner',policy)
        assert len([s for s in statements if s.lstrip().upper().startswith('SELECT')])==1
    assert [asdict(v.snapshot) for v in captured]==[asdict(v) for v in before]
    assert {v.snapshot.garment_id for v in captured}=={gid}
    assert SqliteConfirmedGarmentQuery().get_confirmed_garment_descriptions('foreign-owner',policy)==()
    with db.connection() as conn:
        conn.execute("UPDATE processing_jobs SET user_id='foreign-owner' WHERE id=(SELECT job_id FROM processing_items WHERE id=(SELECT processing_item_id FROM garments WHERE id=?))",(gid,))
    assert SqliteConfirmedGarmentQuery().get_confirmed_garment_descriptions('style-owner',policy)==()


def test_parallel_projection_does_not_clip_over_capacity(description_api,policy):
    from app.infrastructure.persistence import postgresql_repository as db
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    client,create=description_api;gid=create(['casual'])
    with db.connection() as conn:
        source=dict(conn.execute('SELECT * FROM garments WHERE id=?',(gid,)).fetchone())
        item=dict(conn.execute('SELECT * FROM processing_items WHERE id=?',(source['processing_item_id'],)).fetchone())
        item_columns=list(item)
        item_sql='INSERT INTO processing_items ('+','.join(item_columns)+') VALUES ('+','.join('?' for _ in item_columns)+')'
        columns=list(source)
        sql='INSERT INTO garments ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')'
        for index in range(100):
            cloned_item={**item,'id':'synthetic-capacity-item-'+str(index)}
            conn.execute(item_sql,[cloned_item[c] for c in item_columns])
            clone={**source,'id':'synthetic-capacity-'+str(index),'processing_item_id':cloned_item['id']}
            conn.execute(sql,[clone[c] for c in columns])
    with pytest.raises(ValueError,match='DescriptionCapacityExceeded'):
        SqliteConfirmedGarmentQuery().get_confirmed_garment_descriptions('style-owner',policy)


@pytest.mark.parametrize('population',[0,1,100])
@pytest.mark.parametrize('extreme',[False,True])
def test_bounded_preparation_measurements(description_api,policy,monkeypatch,population,extreme):
    """Preparation/transport observations, never a formal rank-latency NFR."""
    import os,time,tracemalloc
    from pathlib import Path
    from app.infrastructure.persistence import postgresql_repository as db
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    client,create=description_api
    if population:
        gid=create(['casual'])
        with db.connection() as conn:
            source=dict(conn.execute('SELECT * FROM garments WHERE id=?',(gid,)).fetchone())
            if extreme:
                attrs=json.loads(source['attributes_json']);tags=[f'{i:02d}'+'\U0001f9e5'*98 for i in range(20)]
                attrs['custom_tags']=tags
                source.update(attributes_json=json.dumps(attrs),additional_attributes=json.dumps(attrs),custom_tags=json.dumps(tags))
                conn.execute('UPDATE garments SET attributes_json=?,additional_attributes=?,custom_tags=? WHERE id=?',(source['attributes_json'],source['additional_attributes'],source['custom_tags'],gid))
            item=dict(conn.execute('SELECT * FROM processing_items WHERE id=?',(source['processing_item_id'],)).fetchone())
            columns=list(source);item_columns=list(item)
            sql='INSERT INTO garments ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')'
            item_sql='INSERT INTO processing_items ('+','.join(item_columns)+') VALUES ('+','.join('?' for _ in item_columns)+')'
            for index in range(population-1):
                cloned_item={**item,'id':'measurement-item-'+str(index)}
                conn.execute(item_sql,[cloned_item[c] for c in item_columns])
                clone={**source,'id':'measurement-garment-'+str(index),'processing_item_id':cloned_item['id']}
                conn.execute(sql,[clone[c] for c in columns])
    normalizations=0;real=d.normalise_field
    def counted(*args,**kwargs):
        nonlocal normalizations
        normalizations+=1
        return real(*args,**kwargs)
    monkeypatch.setattr(d,'normalise_field',counted)
    with db.connection() as conn:
        statements=[];conn.set_trace_callback(statements.append)
        query=SqliteConfirmedGarmentQuery(conn);timings=[]
        for _ in range(5):
            started=time.perf_counter();captured=query.get_confirmed_garment_descriptions('style-owner',policy);timings.append(time.perf_counter()-started)
        tracemalloc.start()
        measured=query.get_confirmed_garment_descriptions('style-owner',policy)
        _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        conn.set_trace_callback(None)
    assert len(captured)==len(measured)==population
    assert normalizations==14*population*6
    assert len([s for s in statements if s.lstrip().upper().startswith('SELECT')])==6
    payload_bytes=sum(len(value.description.payload) for value in measured)
    assert all(len(value.description.payload)<=32768 for value in measured)
    assert payload_bytes<=3276800
    output=Path(os.environ['SMART_WARDROBE_DATA_DIR']).parent/'description-projection-measurements.json'
    observations=json.loads(output.read_text()) if output.exists() else []
    observations.append({'population':population,'extreme_unicode_tags':extreme,'preparation_seconds':timings,'traced_peak_bytes':peak,'new_projection_bytes':payload_bytes,'collection_selects':6,'field_normalizations':normalizations,'ranker_invocations':0,'formal_NFR_acceptance':False})
    output.write_text(json.dumps(observations,indent=2)+'\n')
