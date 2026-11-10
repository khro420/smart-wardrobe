"""Actual disposable API; original completion, modes and strict write gates."""
import uuid,json
import pytest
from tests.test_conversational_history import language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle
from tests.test_b3_palette_integration import submit
from app.application.ports.assistant_runtime import assistant_service
from app.infrastructure.workflow_runtime import configure_local_workflow

@pytest.fixture
def garment_api(language_api,monkeypatch):
    monkeypatch.setenv('SMART_WARDROBE_GARMENT_ONLY_REFINEMENT_PROFILE','garment_only_refinement_v1')
    configure_local_workflow()
    return language_api

def base(value):return tuple((m['garment_role'],m['garment_id']) for m in value['items'] if m['garment_role']!='outerwear')

@pytest.mark.parametrize('engine',['reference','compact_exhaustive'])
@pytest.mark.parametrize('p2',[False,True])
@pytest.mark.parametrize('c2',[False,True])
def test_eight_mode_root_child_replay_history(garment_api,engine,p2,c2):
    client,wearer=garment_api;assistant_service().execution_engine=engine
    profile='recorded_palette_compatibility_v1' if c2 else None
    response,root=submit(client,wearer,'I want an outfit without floral patterns.',p2=p2,profile=profile)
    assert response.status_code==201,root
    assert root['score_metadata']['request_match']['summary']['state']=='NotApplicable'
    action=root['garment_continuation']['next_action']
    response,child=submit(client,wearer,root['request_text'],action['submission_key'],p2,action['refinement'],profile=profile)
    assert response.status_code==201,child
    assert base(child)!=base(root) and child['garment_continuation']['ordinal']==1
    response,replay=submit(client,wearer,root['request_text'],action['submission_key'],p2,action['refinement'],profile=profile)
    assert response.status_code==200 and replay['id']==child['id'] and replay['provenance']==child['provenance'],replay
    history=client.get('/api/v1/chats/'+child['chat_id']);assert history.status_code==200,history.text
    assert history.json()['recommendation']['garment_continuation']==child['garment_continuation']

def next_result(client,wearer,value,p2=True,c2=True):
    action=value['garment_continuation']['next_action']
    return submit(client,wearer,value['request_text'],action['submission_key'],p2,action['refinement'],profile='recorded_palette_compatibility_v1' if c2 else None)

def counts():
    from app.infrastructure.persistence import postgresql_repository as db
    with db.connection() as conn:return tuple(conn.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('nlp_chats','recommendations','recommendation_items','recommendation_metadata','recommendation_submissions'))

@pytest.mark.parametrize('change',['selected','unselected','preference','insert_race'])
def test_full_scope_changes_before_commit_refuse_without_partial_child(garment_api,monkeypatch,change):
    from app.infrastructure.persistence import postgresql_repository as db
    client,wearer=garment_api;_,root=submit(client,wearer,'I want an outfit without floral patterns.',p2=True)
    assert root.get('outcome')=='Selected',root
    service=assistant_service();original=service.repository.persist_assistant;before=counts()
    def changed(command):
        with db.connection() as conn:
            if change=='preference':conn.execute("UPDATE user_preferences SET weight=0.5 WHERE is_active=1")
            else:
                selected={m['garment_id'] for m in root['items']}
                gid=command.candidate.members[0].garment.garment_id if change=='selected' else next(r['id'] for r in conn.execute('SELECT id FROM garments') if r['id'] not in selected)
                conn.execute("UPDATE garments SET updated_at='garment-scope-race' WHERE id=?",(gid,))
        return original(command)
    if change=='preference':
        # Ensure there is an actual captured P1 row to mutate.
        assert client.put('/api/v1/account/preferences/colours',json={'preference_value':{'values':['blue']},'weight':1}).status_code==200
        _,root=submit(client,wearer,'I want an outfit without floral patterns.',p2=True);before=counts()
    with monkeypatch.context() as m:
        m.setattr(service.repository,'persist_assistant',changed)
        response,value=next_result(client,wearer,root)
    assert response.status_code==409 and value['outcome'] in ('RefinementScopeChanged','WardrobeChanged'),value
    assert counts()==before

def test_same_parent_concurrency_coalesces_and_late_write_fault_rolls_back(garment_api,monkeypatch):
    from threading import Barrier
    from concurrent.futures import ThreadPoolExecutor
    from app.application.recommendation.wearer_identity import resolve_wearer
    client,wearer_id=garment_api;_,root=submit(client,wearer_id,'I want an outfit without floral patterns.',p2=True)
    assert root.get('outcome')=='Selected',root
    service=assistant_service();barrier=Barrier(2);original=service.repository.persist_assistant
    def simultaneous(command):barrier.wait(timeout=20);return original(command)
    action=root['garment_continuation']['next_action'];wearer=resolve_wearer(root['user_id'],wearer_id)
    with monkeypatch.context() as m:
        m.setattr(service.repository,'persist_assistant',simultaneous)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(service.recommend,root['user_id'],action['submission_key'],root['request_text'],action['refinement'],wearer=wearer,preference_profile='attribute_preference_decision_v2',compatibility_profile='recorded_palette_compatibility_v1') for _ in range(2)]
            results=[f.result(timeout=40) for f in futures]
    assert all(r['status']=='Selected' for r in results),results
    assert {r['replayed'] for r in results}=={False,True} and results[0]['id']==results[1]['id']
    before=counts();child=results[0]
    def fault(stage,conn):
        if stage=='metadata':raise RuntimeError('synthetic post-metadata failure')
    with monkeypatch.context() as m:
        m.setattr(service.repository,'checkpoint',fault)
        response,failed=next_result(client,wearer_id,child)
    assert response.status_code==503 and failed['outcome']=='PersistenceFailure',failed
    assert counts()==before
    assert next_result(client,wearer_id,child)[0].status_code==201

def test_one_base_exhaustion_unknown_and_impossible_are_distinct(garment_api):
    from tests.test_attribute_conditions import request
    from tests.test_attribute_persistence import qualify
    client,wearer=garment_api
    inventory=client.get('/api/v1/wardrobe/garments').json()
    # Exact name is supported immutable evidence, giving one real one-piece base.
    dress=next(g for g in inventory if g['category'].endswith('_dress'))
    typed=request('garment_name','exact_text',[dress['name']],role='one_piece')
    response,root=submit(client,wearer,'Recommend an outfit.',typed=typed)
    assert response.status_code==201,root
    action=root['garment_continuation']['next_action'];before=counts()
    response,result=submit(client,wearer,root['request_text'],action['submission_key'],False,action['refinement'],typed=typed)
    assert response.status_code==200 and result['outcome']=='GarmentRefinementExhausted',result
    assert counts()==before
    impossible=request('garment_name','exact_text',['NO_SYNTHETIC_GARMENT_HAS_THIS_NAME'])
    response,result=submit(client,wearer,'Recommend an outfit.',typed=impossible)
    assert response.status_code==200 and result['outcome']=='NoMatchingCandidates',result
    # No source fabrication: a requested missing fine description is Unknown.
    unknown=request('sleeve_length','in',['wrist-length'],role='upper')
    response,result=submit(client,wearer,'Recommend an outfit.',typed=unknown)
    assert response.status_code==200 and result['outcome']=='InsufficientEvidence',result

def test_ten_results_is_limit_not_global_exhaustion(garment_api):
    from tests.test_automatic_admission_integration import legacy
    from tests.test_attribute_persistence import qualify
    client,wearer=garment_api
    for i in range(12):
        gid=legacy(client,'casual','short_sleeve_top')
        qualify(client,gid,pattern='plain',colour_palette=[{'hex':'#0000ff','coverage':'1'}])
    response,value=submit(client,wearer,'I want an outfit without floral patterns.',p2=True)
    assert response.status_code==201,value
    bases=[base(value)]
    for index in range(1,10):
        response,value=next_result(client,wearer,value)
        assert response.status_code==201 and value['garment_continuation']['ordinal']==index,value
        bases.append(base(value))
    assert len(set(bases))==10 and value['garment_continuation']['next_action'] is None
    from app.domain.value_objects.garment_only_refinement import step_key
    action={'version':'assistant-refinement-request-1.0.0','kind':'alternative','parent_recommendation_id':value['id']}
    response,result=submit(client,wearer,value['request_text'],'attempt-beyond-limit',True,action)
    assert response.status_code==200 and result['outcome']=='RefinementLimitReached',result

@pytest.mark.parametrize('engine',['reference','compact_exhaustive'])
def test_unseen_unknown_never_claims_exhaustion(garment_api,engine):
    from tests.test_attribute_persistence import qualify
    from tests.test_attribute_conditions import request
    client,wearer=garment_api;assistant_service().execution_engine=engine
    top=next(g for g in client.get('/api/v1/wardrobe/garments').json() if g['category'] in ('short_sleeve_top','vest'))
    qualify(client,top['id'],material=['cotton'])
    typed=request('material','contains_any',['cotton'],role='upper')
    response,value=submit(client,wearer,'Recommend an outfit.',p2=True,typed=typed)
    assert response.status_code==201,value
    for _ in range(8):
        action=value['garment_continuation']['next_action'];before=counts()
        response,new=submit(client,wearer,value['request_text'],action['submission_key'],True,action['refinement'],typed=typed)
        if response.status_code!=201:
            assert response.status_code==200 and new['outcome']=='GarmentRefinementInsufficientEvidence',new
            assert counts()==before;return
        value=new
    pytest.fail('Small synthetic fixture should reach its unresolved remaining base.')

@pytest.mark.parametrize('p2',[False,True])
@pytest.mark.parametrize('c2',[False,True])
def test_both_engines_agree_on_exact_scores_counts_bases_and_four_structures(garment_api,p2,c2,monkeypatch):
    from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
    client,wearer=garment_api;service=assistant_service();results=[];seen_structures=set();original=CompactExhaustiveScorer.rank
    def audit(row):
        if row['verified']:seen_structures.add(tuple(pair[0] for pair in row['key']))
    def instrument(self,*args,**kwargs):self.audit=audit;return original(self,*args,**kwargs)
    monkeypatch.setattr(CompactExhaustiveScorer,'rank',instrument)
    profile='recorded_palette_compatibility_v1' if c2 else None
    for engine in ('compact_exhaustive','reference'):
        service.execution_engine=engine
        response,root=submit(client,wearer,'I want an outfit without floral patterns.',p2=p2,profile=profile)
        assert response.status_code==201,root
        response,child=next_result(client,wearer,root,p2,c2)
        assert response.status_code==201,child
        results.append([(base(v),v['score_metadata'],v['provenance']['scored_count']) for v in (root,child)])
    assert results[0]==results[1]
    assert seen_structures=={('upper','lower'),('upper','lower','outerwear'),('one_piece',),('one_piece','outerwear')}

def test_denied_account_row_change_invalidates_garment_chain(garment_api,monkeypatch):
    from tests.test_wearer_category_policy import set_gender
    from app.infrastructure.persistence import postgresql_repository as db
    client,wearer=garment_api;set_gender(client,wearer,'male')
    monkeypatch.setenv('SMART_WARDROBE_WEARER_CATEGORY_PROFILE','gender_category_v1');configure_local_workflow()
    key=uuid.uuid4().hex
    response,root=submit(client,wearer,'I want an outfit without floral patterns.',key,True)
    assert response.status_code==201 and all(not m['category'].endswith('_dress') for m in root['items']),root
    before=counts()
    with db.connection() as conn:
        gid=conn.execute("SELECT id FROM garments WHERE category LIKE '%dress' LIMIT 1").fetchone()['id']
        conn.execute("UPDATE garments SET updated_at='changed-denied-account-row' WHERE id=?",(gid,))
    response,result=next_result(client,wearer,root)
    assert response.status_code==409 and result['outcome']=='WearerEligibilityChanged',result
    assert counts()==before
    response,replay=submit(client,wearer,root['request_text'],key,True)
    assert response.status_code==200 and replay['id']==root['id']

@pytest.mark.parametrize('stage',['before_close','closed','reconstructed'])
def test_late_ranking_interrupt_never_saves_partial_work(garment_api,monkeypatch,stage):
    from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
    client,wearer=garment_api;before=counts();original=CompactExhaustiveScorer._event
    def fault(self,name,*args):
        if name==stage:raise KeyboardInterrupt('owned synthetic late interruption')
        return original(self,name,*args)
    monkeypatch.setattr(CompactExhaustiveScorer,'_event',fault)
    response,value=submit(client,wearer,'I want an outfit without floral patterns.',p2=True)
    assert response.status_code==503 and value['outcome']=='Interrupted',value
    assert counts()==before
