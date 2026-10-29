"""Four-way real service/API integration; all descriptors are synthetic."""
from dataclasses import replace,FrozenInstanceError
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.application.recommendation.assistant_execution_selection import AssistantExecutionSelection,REFERENCE,COMPACT,ENVIRONMENT_KEY
from app.application.recommendation.assistant_scoring_selection import DEFERRED,DECISION
from app.application.recommendation.compact_assistant_scorer import CompactAssistantScorer
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
from app.infrastructure.security import issue_access_token
from tests.test_outfit_assistant import assistant_store,service,add_garment,count
from tests.test_recommendation_persistence import store,connect


def configured(data,profile,engine,**kwargs):
    s=service(data,**kwargs);s.scoring_profile=profile;s.execution_engine=engine;return s


def semantic_provenance(value):
    value=dict(value);execution=value.pop('assistant_execution_selection',None)
    if execution:
        assert execution==AssistantExecutionSelection(COMPACT).provenance
        if value.get('scoring_profile')==DECISION:
            assert value['scorer_implementation']=='compact-exhaustive-1.0.0'
            value['scorer_implementation']='prepared-decision-1.0.0'
    return value


@pytest.mark.parametrize('profile',[DEFERRED,DECISION])
@pytest.mark.parametrize('structure',['pair','trio','dress','dress_outer'])
@pytest.mark.parametrize('evidence',['known','zero','partial','unknown'])
def test_four_way_full_persistence_equivalence(assistant_store,profile,structure,evidence):
    if structure in ('pair','trio'):add_garment(assistant_store,'bottom','trousers')
    if structure in ('trio','dress_outer'):add_garment(assistant_store,'outer','long_sleeve_outwear')
    with connect(assistant_store[0]) as c:
        if structure in ('pair','trio'):c.execute("UPDATE garments SET category='vest' WHERE id='garment'")
        if evidence=='zero':c.execute("UPDATE garments SET primary_colour='red',style_tags='[\"sporty\"]' WHERE id!='garment'")
        if evidence in ('partial','unknown'):
            attrs=json.dumps({'style':None})
            c.execute('UPDATE garments SET style_tags=NULL,attributes_json=?,additional_attributes=?',(attrs,attrs))
        if evidence=='unknown':c.execute('UPDATE garments SET primary_colour=NULL')
    text='Suggest an outfit'+(' including outerwear' if structure in ('trio','dress_outer') else '')
    old=configured(assistant_store,profile,REFERENCE).recommend('owner','reference',text)
    svc=configured(assistant_store,profile,COMPACT);new=svc.recommend('owner','compact',text)
    assert old['status']==new['status']=='Selected',(old,new)
    assert tuple(i['garment_role'] for i in new['items'])=={
        'pair':('upper','lower'),'trio':('upper','lower','outerwear'),
        'dress':('one_piece',),'dress_outer':('one_piece','outerwear')}[structure]
    for field in ('request_text','score_metadata','scoring_display','total_score','compatibility_score','extracted_entities'):
        if field in old:assert old[field]==new[field],field
    assert semantic_provenance(old['provenance'])==semantic_provenance(new['provenance'])
    assert [(i['garment_id'],i['garment_role'],i['item_order']) for i in old['items']]==[(i['garment_id'],i['garment_role'],i['item_order']) for i in new['items']]
    # A committed submission survives a subsequent executor/profile switch.
    svc.execution_engine=REFERENCE;svc.scoring_profile=DEFERRED if profile==DECISION else DECISION
    replay=svc.recommend('owner','compact',text)
    assert replay['replayed'] and replay['id']==new['id']
    assert replay['provenance']==new['provenance'] and replay['score_metadata']==new['score_metadata']


@pytest.mark.parametrize('engine',[REFERENCE,COMPACT])
@pytest.mark.parametrize('profile',[DEFERRED,DECISION])
def test_real_startup_api_security_history_and_client_cannot_select(assistant_store,monkeypatch,engine,profile):
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED','true')
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_SCORING_PROFILE',profile);monkeypatch.setenv(ENVIRONMENT_KEY,engine)
    # Import the real history reader before replacing a constructor in its source
    # module; otherwise an isolated run can capture the fixture lambda on import.
    import app.infrastructure.persistence.chat_history_query_adapter as history
    import app.infrastructure.persistence.recommendation_repository_adapter as adapter
    monkeypatch.setattr(adapter,'SqliteRecommendationRepository',lambda *a,**kw:assistant_store[1])
    original=history.SqliteChatHistoryQuery
    monkeypatch.setattr(history,'SqliteChatHistoryQuery',lambda:original(assistant_store[0],cursor_secret='test'))
    headers={'Authorization':'Bearer '+issue_access_token('owner')};body={'request_text':'Suggest an outfit','submission_key':'http'}
    with TestClient(app) as client:
        assert client.post('/api/v1/recommendations?pipeline=integrated',json=body).status_code==401
        assert client.post('/api/v1/recommendations?pipeline=integrated',headers=headers,json={**body,'execution_engine':'reference'}).status_code==422
        r=client.post('/api/v1/recommendations?pipeline=integrated&execution_engine=malicious&scoring_profile=malicious',headers=headers,json=body)
        assert r.status_code==201,r.text
        value=r.json();assert value['score_metadata']['profile_name']==profile
        assert ('assistant_execution_selection' in value['provenance'])==(engine==COMPACT)
        assert client.post('/api/v1/recommendations?pipeline=integrated',headers=headers,json=body).json()['replayed']
        path='/api/v1/chats/'+value['chat_id']
        assert client.get(path,headers={'Authorization':'Bearer '+issue_access_token('other')}).status_code==404
        restored=client.get(path,headers=headers).json()['recommendation']
        assert restored['score_metadata']==value['score_metadata'] and restored['provenance']==value['provenance']


@pytest.mark.parametrize('key',[ENVIRONMENT_KEY,'SMART_WARDROBE_ASSISTANT_SCORING_PROFILE'])
@pytest.mark.parametrize('enabled',['false','true'])
def test_invalid_configuration_aborts_startup(monkeypatch,key,enabled):
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED',enabled);monkeypatch.setenv(key,'unknown')
    with pytest.raises(ValueError,match='Unknown Assistant'):
        with TestClient(app):pass


@pytest.mark.parametrize('profile',[DEFERRED,DECISION])
@pytest.mark.parametrize('stage',['revalidated','chat','recommendation','item','snapshot','metadata','submission','before_commit'])
def test_actual_compact_atomic_rollback(assistant_store,profile,stage):
    from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
    def fail(current,c):
        if stage==current:raise RuntimeError('Synthetic write failure')
    svc=configured(assistant_store,profile,COMPACT,repo=SqliteRecommendationRepository(assistant_store[0],checkpoint=fail))
    assert svc.recommend('owner','rollback','Suggest an outfit')['status']=='PersistenceFailure'
    with connect(assistant_store[0]) as c:
        for table in ('nlp_chats','recommendations','recommendation_items','recommendation_metadata','recommendation_submissions','recommendation_item_snapshots'):
            assert c.execute('SELECT count(*) FROM '+table).fetchone()[0]==0


@pytest.mark.parametrize('text',['Suggest an outfit for campus','Suggest a formal outfit','Suggest an outfit with red colours','What is the capital of France?'])
@pytest.mark.parametrize('profile',[DEFERRED,DECISION])
def test_no_result_policy_and_unsupported_equivalence(assistant_store,profile,text):
    a=configured(assistant_store,profile,REFERENCE).recommend('owner','reference',text)
    b=configured(assistant_store,profile,COMPACT).recommend('owner','compact',text)
    assert (a['status'],a['complete'],a.get('diagnostics'))==(b['status'],b['complete'],b.get('diagnostics'))
    assert count(assistant_store)==(0,0,0)


@pytest.mark.parametrize('stage',['candidate','before_close','closed','reconstructed'])
@pytest.mark.parametrize('exception',[RuntimeError,KeyboardInterrupt])
def test_late_compact_failure_cannot_persist(assistant_store,monkeypatch,stage,exception):
    from app.application.recommendation.assistant_execution_selection import AssistantExecutionSelection
    def factory(selection,scoring,candidates,prefs,reference_factory):
        def kernel(*args,**kwargs):
            def checkpoint(current,*_):
                if current==stage:raise exception('Synthetic interruption')
            return CompactExhaustiveScorer(*args,**kwargs,checkpoint=checkpoint)
        return CompactAssistantScorer(candidates,prefs,scoring.profile,kernel_factory=kernel)
    monkeypatch.setattr(AssistantExecutionSelection,'scorer',factory)
    result=configured(assistant_store,DECISION,COMPACT).recommend('owner','late','Suggest an outfit')
    assert result['status']==('Interrupted' if exception==KeyboardInterrupt else 'ProcessingFailure')
    assert not result['complete'] and count(assistant_store)==(0,0,0)


def test_bridge_uses_metadata_without_faking_session_completion(assistant_store):
    from app.application.recommendation.outfit_assistant_service import CapturedCandidateEngine,CapturedPreferenceQuery
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
    svc=service(assistant_store);captured=CapturedCandidateEngine(svc.engine)
    adapter=CompactAssistantScorer(captured,CapturedPreferenceQuery(svc.preference_query),DECISION)
    request=StructuredOutfitRequest();result=adapter.rank('owner',request)
    assert result.complete and result.status=='Selected' and captured.session is None
    assert not adapter.kernel.public_session.result.complete
    assert adapter.prepared_context.request==request
    with pytest.raises(FrozenInstanceError):adapter.prepared_context.user_id='other'
    with pytest.raises(ValueError):replace(adapter.prepared_context,user_id='other').validate_winner('owner',request,result)


@pytest.mark.parametrize('name,arg',[
    ('test_actual_strict_query_excludes_ineligible_records',"UPDATE garments SET processing_item_id=NULL"),
    ('test_actual_strict_query_excludes_ineligible_records',"UPDATE processing_jobs SET user_id='other'"),
    ('test_actual_strict_query_excludes_ineligible_records',"UPDATE garments SET user_id='other'"),
    ('test_actual_strict_query_excludes_ineligible_records',"UPDATE garments SET status='archived'"),
    ('test_actual_strict_query_excludes_ineligible_records',"UPDATE processing_items SET review_status='accepted'"),
    ('test_actual_strict_query_excludes_ineligible_records',"UPDATE processing_items SET review_status='pending'"),
    ('test_actual_strict_query_excludes_ineligible_records',"UPDATE processing_items SET review_status='rejected'"),
    ('test_actual_concurrent_compact_submissions',True),('test_actual_concurrent_compact_submissions',False),
    ('test_history_is_not_rewritten_after_garment_changes',None)])
def test_existing_guarantees_through_actual_bridge(assistant_store,monkeypatch,name,arg):
    import tests.test_compact_integration as previous
    original=previous.service
    def actual(*args,**kwargs):
        svc=original(*args,**kwargs);svc.execution_engine=COMPACT;return svc
    monkeypatch.setattr(previous,'service',actual)
    test=getattr(previous,name)
    if arg is None:test(assistant_store)
    else:test(assistant_store,arg)


@pytest.mark.parametrize('change',["primary_colour='red'","style_tags='[]'","status='archived'","processing_item_id=NULL"])
def test_actual_bridge_revalidates_after_selection(assistant_store,monkeypatch,change):
    def factory(selection,scoring,candidates,prefs,reference_factory):
        def kernel(*args,**kwargs):
            def checkpoint(stage,*_):
                if stage=='reconstructed':
                    with connect(assistant_store[0]) as c:c.execute('UPDATE garments SET '+change)
            return CompactExhaustiveScorer(*args,**kwargs,checkpoint=checkpoint)
        return CompactAssistantScorer(candidates,prefs,scoring.profile,kernel_factory=kernel)
    monkeypatch.setattr(AssistantExecutionSelection,'scorer',factory)
    result=configured(assistant_store,DECISION,COMPACT).recommend('owner','changed','Suggest an outfit')
    assert result['status']=='WardrobeChanged' and count(assistant_store)==(0,0,0)


@pytest.mark.parametrize('profile',[DEFERRED,DECISION])
def test_actual_bridge_multiple_preferences(assistant_store,profile):
    with connect(assistant_store[0]) as c:
        for kind,values in (('colours',['blue']),('styles',['vintage']),('garment_categories',[{'kind':'group','value':'dress'}])):
            c.execute("INSERT INTO user_preferences VALUES(?,'owner',?,?,1,'synthetic',1,'now','now')",(kind,kind,json.dumps({'values':values})))
    a=configured(assistant_store,profile,REFERENCE).recommend('owner','pref-reference','Suggest a vintage outfit')
    b=configured(assistant_store,profile,COMPACT).recommend('owner','pref-compact','Suggest a vintage outfit')
    assert a['status']==b['status']=='Selected'
    assert a['score_metadata']==b['score_metadata']
    assert len(b['provenance']['preference_snapshot'])==3
    assert semantic_provenance(a['provenance'])==semantic_provenance(b['provenance'])


@pytest.mark.parametrize('engine',[REFERENCE,COMPACT])
@pytest.mark.parametrize('profile',[DEFERRED,DECISION])
def test_existing_save_and_visualisation_resolution(assistant_store,monkeypatch,engine,profile):
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.infrastructure.workflow_runtime import configure_local_workflow
    from app.application.recommendation import recommendation_service as actions
    from app.application.visualisation import outfit_identifier_validator as visual
    from app.domain.value_objects.visualisation_plan import VTONConfiguration
    configure_local_workflow()
    monkeypatch.setattr(visual,'runtime',lambda:SimpleNamespace(media=SimpleNamespace(path_for_owner=lambda *_:None),configuration=VTONConfiguration))
    record=configured(assistant_store,profile,engine).recommend('owner','actions','Suggest an outfit')
    assert record['status']=='Selected'
    saved=actions.save_as_outfit(record['id'],'owner','Existing action')
    assert actions.save_as_outfit(record['id'],'owner','Again')['id']==saved['id']
    with connect(assistant_store[0]) as c:
        visual.resolve_source(c,'owner',recommendation_id=record['id'])
        stored=c.execute('SELECT * FROM recommendation_metadata').fetchall()
        c.execute("UPDATE garments SET status='archived'")
    with pytest.raises(HTTPException):actions.save_as_outfit(record['id'],'owner','Archived')
    with connect(assistant_store[0]) as c:
        with pytest.raises(HTTPException):visual.resolve_source(c,'owner',recommendation_id=record['id'])
        assert [tuple(r) for r in c.execute('SELECT * FROM recommendation_metadata')]==[tuple(r) for r in stored]


@pytest.mark.parametrize('profile',[DEFERRED,DECISION])
@pytest.mark.parametrize('sql,text',[
    ("UPDATE garments SET style_tags='[17]'",'Suggest a vintage outfit'),
    ("UPDATE garments SET primary_colour='malformed'",'Suggest a blue outfit'),
    ("UPDATE garments SET style_tags='[]'",'Suggest a vintage outfit')])
def test_invalid_evidence_through_both_execution_engines(assistant_store,profile,sql,text):
    with connect(assistant_store[0]) as c:c.execute(sql)
    results=[configured(assistant_store,profile,e).recommend('owner',e,text) for e in (REFERENCE,COMPACT)]
    assert results[0]['status']==results[1]['status']
    assert results[0]['status'] in ('InsufficientEvidence','NoMatchingCandidates')
    assert count(assistant_store)==(0,0,0)


@pytest.mark.parametrize('profile',[DEFERRED,DECISION])
def test_actual_bridge_every_candidate_matches_public_oracle(assistant_store,monkeypatch,profile):
    from tests.test_compact_exhaustive import oracle_records
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    for identifier,category in [('t1','vest'),('t2','vest'),('b1','trousers'),('b2','trousers'),('o','long_sleeve_outwear')]:
        add_garment(assistant_store,identifier,category)
    with connect(assistant_store[0]) as c:
        c.execute("UPDATE garments SET style_tags='[\"classic\"]',primary_colour='red' WHERE id='t2'")
        c.execute("UPDATE garments SET style_tags=NULL,attributes_json='{}',additional_attributes=NULL WHERE id='b2'")
    svc=configured(assistant_store,profile,COMPACT);text='Suggest a vintage outfit'
    structured=svc.interpreter.interpret(text).structured_request
    rows=SqliteConfirmedGarmentQuery().get_confirmed_available_garments('owner')
    preferences=svc.preference_query.get_active_preferences('owner')
    expected=list(oracle_records(rows,structured,preferences,profile,None))
    actual=[]
    original=AssistantExecutionSelection.scorer
    def selected(selection,scoring,candidates,prefs,reference_factory):
        if selection.engine==REFERENCE:return original(selection,scoring,candidates,prefs,reference_factory)
        return CompactAssistantScorer(candidates,prefs,profile,kernel_factory=lambda *a,**kw:CompactExhaustiveScorer(*a,**kw,audit=actual.append))
    monkeypatch.setattr(AssistantExecutionSelection,'scorer',selected)
    old=configured(assistant_store,profile,REFERENCE).recommend('owner','audit-reference',text)
    result=svc.recommend('owner','audit-compact',text)
    assert result['status']==old['status']=='Selected'
    assert actual==expected and len(actual)==10
    assert result['provenance']['scored_count']==sum(r['verified'] for r in expected)
    assert result['score_metadata']==old['score_metadata']
    assert semantic_provenance(result['provenance'])==semantic_provenance(old['provenance'])


@pytest.mark.parametrize('engine',[REFERENCE,COMPACT])
@pytest.mark.parametrize('profile',[DEFERRED,DECISION])
def test_explicit_suitability_retains_all_five_fields(assistant_store,engine,profile):
    from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
    with connect(assistant_store[0]) as c:
        c.execute("UPDATE garments SET custom_tags='[\"rec:v1:occasion:campus:allow\",\"rec:v1:formality:casual:allow\"]'")
    text='Suggest a casual outfit for campus with vintage style using blue colours with a dress'
    assert configured(assistant_store,profile,engine).recommend('owner','off',text)['status']=='PolicyUnavailable'
    svc=configured(assistant_store,profile,engine,evaluator=SuitabilityRequestEvaluator)
    result=svc.recommend('owner','on',text)
    assert result['status']=='Selected'
    assert result['provenance']['request_evaluator']=='SuitabilityRequestEvaluator'
    with connect(assistant_store[0]) as c:
        fields=json.loads(c.execute('SELECT extracted_entities_json FROM nlp_chats').fetchone()[0])
    assert fields=={'intent':'outfit_recommendation','occasion':'campus','style':'vintage','colours':['blue'],'garment_categories':[{'kind':'group','value':'dress'}],'formality':'casual'}


@pytest.mark.parametrize('profile',[DEFERRED,DECISION])
def test_cross_engine_concurrent_same_key_has_one_durable_result(assistant_store,profile):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    ready=Barrier(2)
    def run(engine):
        svc=configured(assistant_store,profile,engine)
        ready.wait(timeout=10)
        return svc.recommend('owner','cross-engine','Suggest an outfit')
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,(REFERENCE,COMPACT)))
    assert all(r['status']=='Selected' for r in results)
    assert results[0]['id']==results[1]['id'] and sorted(r['replayed'] for r in results)==[False,True]
    assert results[0]['provenance']==results[1]['provenance']
    assert results[0]['score_metadata']==results[1]['score_metadata'] and count(assistant_store)==(1,1,1)
