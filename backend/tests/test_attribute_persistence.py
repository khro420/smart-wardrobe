"""Authenticated disposable Phase A+B0 application, exact B1 requests/receipts."""
import uuid
import pytest
from tests.test_recommendation_refinement_integration import refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,wardrobe
from tests.test_description_persistence import body,garment
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.ports.assistant_runtime import assistant_service


@pytest.fixture
def attribute_api(refinement_api,monkeypatch):
    monkeypatch.setenv('SMART_WARDROBE_DESCRIPTION_PROFILE','description_evidence_v1')
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ATTRIBUTE_PROFILE','attribute_requests_v1')
    configure_local_workflow()
    return refinement_api


def qualify(client,gid,**values):
    g=garment(client,gid)
    reply=client.patch('/api/v1/wardrobe/garments/'+gid,json=body(g,{k:{'kind':'set','value':v} for k,v in values.items()}))
    assert reply.status_code==200,reply.text
    return reply.json()


def submit(client,text="I'm going shopping and want a plain cotton v-neck top.",key=None,typed=None,action=None,wearer=None):
    value={'request_text':text,'submission_key':key or uuid.uuid4().hex}
    if typed is not None:value['attribute_conditions']=typed
    if action is not None:value['refinement']=action
    if wearer is not None:value['wearer_profile_id']=wearer
    response=client.post('/api/v1/recommendations?pipeline=integrated',json=value)
    return response,response.json()


def test_current_nlp_conditions_filter_real_rows_and_replay(attribute_api,monkeypatch):
    client,_=attribute_api;ids=wardrobe(client)
    qualify(client,ids['Blue T-shirt'],pattern='plain',material=['cotton'],neckline='v-neck')
    key=uuid.uuid4().hex;response,root=submit(client,key=key)
    assert response.status_code==201,root
    assert root['outcome']=='Selected' and root['scoring_display']['total']=={'numerator':'4','denominator':'5'}
    assert [i['garment_id'] for i in root['items']]==[ids['Blue T-shirt'],ids['Blue Jeans']]
    assert root['provenance']['refinement']['request_fingerprint_version']==4
    assert root['provenance']['refinement']['version']=='recommendation-refinement-evidence-1.2.0'
    assert root['provenance']['context_relevance']['version']=='context-relevance-evidence-1.3.0'
    assert root['attribute_display']['version']=='assistant-attribute-display-1.0.0'
    service=assistant_service();service.attribute_pipeline=None
    monkeypatch.setattr(service.interpreter,'interpret',lambda *_:pytest.fail('Completed replay interpreted again'))
    response,replay=submit(client,key=key)
    assert response.status_code==200 and replay['id']==root['id'] and replay['attribute_display']==root['attribute_display']


def test_missing_descriptions_do_not_fabricate_a_match(attribute_api):
    client,_=attribute_api;wardrobe(client)
    response,result=submit(client)
    assert response.status_code==200 and result['outcome']=='InsufficientEvidence',result


def test_ordinary_request_retains_fingerprint3_and_original_score(attribute_api):
    client,_=attribute_api;wardrobe(client)
    response,result=submit(client,"I'm going shopping.")
    assert response.status_code==201,result
    assert 'attribute_selection' not in result['provenance']
    assert result['provenance']['refinement']['request_fingerprint_version']==3
    assert result['scoring_display']['total']=={'numerator':'4','denominator':'5'}


def test_typed_change_same_key_conflicts_before_ranking(attribute_api,monkeypatch):
    from tests.test_attribute_conditions import request
    client,_=attribute_api;ids=wardrobe(client)
    qualify(client,ids['Blue T-shirt'],material=['cotton'])
    key=uuid.uuid4().hex;typed=request()
    response,root=submit(client,"I'm going shopping.",key,typed)
    assert response.status_code==201,root
    service=assistant_service()
    monkeypatch.setattr(service.attribute_pipeline,'interpret',lambda *a,**k:pytest.fail('Changed key reached interpretation'))
    changed=request(values=['linen'])
    response,result=submit(client,"I'm going shopping.",key,changed)
    assert response.status_code==409 and result['outcome']=='IdempotencyConflict',result


def test_dated_construction_and_condition_use_existing_authenticated_review(attribute_api):
    from tests.test_attribute_conditions import request
    client,_=attribute_api;ids=wardrobe(client);gid=ids['Blue T-shirt']
    current=garment(client,gid)
    response=client.post('/api/v1/wardrobe/garments/'+gid+'/contextual-suitability',json={
        'revision':current['appearance_edit']['revision'],'appearance_review':{
            'construction_features':{'collared_neckline':False,'structured_shape':True,'tailored_cut':False},
            'condition_observation':'clean_intact'}})
    assert response.status_code==200,response.text
    typed=request('construction_collared','bool_eq',[False])
    typed['groups'][0]['conditions'].extend([
        {'id':'c02','attribute':'construction_structured','operator':'bool_eq','values':[True]},
        {'id':'c03','attribute':'condition','operator':'in','values':['clean_intact']}])
    response,result=submit(client,"I'm going shopping.",typed=typed)
    assert response.status_code==201,result
    assert result['items'][0]['garment_id']==gid
    assert any(m['source_kind']=='dated_reviewed_observation' for g in result['attribute_display']['groups'] for m in g['member_results'])
    assert result['scoring_display']['total']=={'numerator':'4','denominator':'5'}


def test_acquisition_loop_call_counts_and_stage_measurements(attribute_api,monkeypatch,tmp_path):
    import json,time,tracemalloc
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
    from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
    client,_=attribute_api;ids=wardrobe(client)
    for name in ('Blue T-shirt','Green Sweatshirt'):qualify(client,ids[name],pattern='plain',material=['cotton'],neckline='v-neck')
    service=assistant_service();pipeline=service.attribute_pipeline
    original_query=SqliteConfirmedGarmentQuery.get_confirmed_garment_descriptions
    original_fact=AttributeEvidencePolicy.fact;original_rank=CompactExhaustiveScorer.rank;original_event=CompactExhaustiveScorer._event
    original_interpret=pipeline.interpret;original_prepare=pipeline.prepare;original_write=service.repository.persist_assistant
    counts={'paired_queries':0,'nlp':0,'loop_source_calls':0};loop={'active':False};measurements=[]
    def query(self,*args,**kwargs):
        assert not loop['active'];counts['paired_queries']+=1
        start=time.perf_counter();result=original_query(self,*args,**kwargs)
        measurements.append({'stage':'paired_snapshot_and_description','seconds':time.perf_counter()-start,'garments':len(result)})
        return result
    def fact(self,*args,**kwargs):
        counts['loop_source_calls']+=int(loop['active']);return original_fact(self,*args,**kwargs)
    def event(self,name,*args):
        if name=='candidate':loop['active']=True
        if name=='closed':loop['active']=False
        return original_event(self,name,*args)
    def rank(self,*args,**kwargs):
        self.instrument=True;result=original_rank(self,*args,**kwargs)
        loop['active']=False;measurements.append({'stage':'compact_rank','timings':dict(self.timings),'examined':result.examined_count if hasattr(result,'examined_count') else None})
        return result
    def timed(label,operation):
        def run(*args,**kwargs):
            if label=='nlp':counts['nlp']+=1
            start=time.perf_counter();result=operation(*args,**kwargs)
            measurements.append({'stage':label,'seconds':time.perf_counter()-start});return result
        return run
    monkeypatch.setattr(SqliteConfirmedGarmentQuery,'get_confirmed_garment_descriptions',query)
    monkeypatch.setattr(AttributeEvidencePolicy,'fact',fact)
    monkeypatch.setattr(CompactExhaustiveScorer,'_event',event);monkeypatch.setattr(CompactExhaustiveScorer,'rank',rank)
    monkeypatch.setattr(pipeline,'interpret',timed('nlp',original_interpret));monkeypatch.setattr(pipeline,'prepare',timed('hard_filter_preparation',original_prepare))
    monkeypatch.setattr(service.repository,'persist_assistant',timed('persist_commit',original_write))
    tracemalloc.start();start=time.perf_counter();response,root=submit(client);assert response.status_code==201,root
    assert counts=={'paired_queries':2,'nlp':1,'loop_source_calls':0}
    step=root['scoring_display']['refinement']['next_action'];response,child=submit(client,root['request_text'],step['submission_key'],action=step['refinement'])
    assert response.status_code==201,child
    assert counts=={'paired_queries':4,'nlp':1,'loop_source_calls':0}
    response,replay=submit(client,root['request_text'],step['submission_key'],action=step['refinement'])
    assert response.status_code==200 and replay['id']==child['id']
    assert counts=={'paired_queries':4,'nlp':1,'loop_source_calls':0}
    elapsed=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    (tmp_path/'stage-measurements.json').write_text(json.dumps(dict(counts=counts,stages=measurements,
        root_timings=root['timings'],alternative_timings=child['timings'],replay_timings=replay['timings'],
        total_seconds=elapsed,traced_peak_bytes=peak,
        limits='Disposable warm-process engineering observation, not private-user latency, cold-start or formal NFR acceptance.'),indent=2),encoding='utf-8')
