"""Actual strict query/atomic repository and unchanged Assistant service."""
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
import pytest
from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer,EXPERIMENTAL,DEFERRED
from app.application.recommendation.aggregated_decision_scorer import AggregatedDecisionRecommendationScorer
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.application.recommendation.compact_mandatory_verifier import CompactMandatoryFacts
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from tests.compact_service_adapter import factory
from tests.test_outfit_assistant import assistant_store,service as original_service
from tests.test_recommendation_persistence import store
from tests.test_compact_exhaustive import signature
from tests.test_rule_based_compatibility import g,Preferences
from tests.test_structural_candidates import Query
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest


def service(*args, **kwargs):
    # This archived bridge suite injects reference-factory checkpoints. Keep
    # exercising them explicitly after the production default changes.
    value=original_service(*args, **kwargs)
    value.execution_engine='reference'
    return value


@pytest.mark.parametrize('profile',[DEFERRED,EXPERIMENTAL])
def test_actual_service_persistence_replay_and_provenance(assistant_store,profile):
    a=service(assistant_store);a.scoring_profile=profile
    if profile==EXPERIMENTAL:a.scorer_factory=AggregatedDecisionRecommendationScorer
    b=service(assistant_store);b.scoring_profile=profile;b.scorer_factory=factory(profile)
    old=a.recommend('owner','old','Suggest an outfit with vintage style')
    new=b.recommend('owner','new','Suggest an outfit with vintage style')
    assert old['status']==new['status']=='Selected'
    for field in ('score_metadata','provenance','scoring_display','total_score','compatibility_score'):
        assert old[field]==new[field],field
    assert [(x['garment_id'],x['garment_role']) for x in old['items']]==[(x['garment_id'],x['garment_role']) for x in new['items']]
    replay=b.recommend('owner','new','Suggest an outfit with vintage style')
    assert replay['replayed'] and replay['id']==new['id'] and replay['score_metadata']==new['score_metadata']
    assert b.recommend('other','new','Suggest an outfit with vintage style')['status']!='Selected'


@pytest.mark.parametrize('stage',['revalidated','chat','recommendation','item','snapshot','metadata','submission','before_commit'])
def test_compact_atomic_write_failure(assistant_store,stage):
    from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
    from tests.test_recommendation_persistence import connect
    def fail(current,conn):
        if current==stage:raise RuntimeError('Synthetic failure')
    svc=service(assistant_store);svc.scoring_profile=EXPERIMENTAL;svc.scorer_factory=factory(EXPERIMENTAL)
    svc.repository=SqliteRecommendationRepository(assistant_store[0],checkpoint=fail)
    result=svc.recommend('owner','failed','Suggest an outfit with vintage style')
    assert result['status']=='PersistenceFailure'
    with connect(assistant_store[0]) as c:
        for table in ('nlp_chats','recommendations','recommendation_items','recommendation_metadata','recommendation_submissions','recommendation_item_snapshots'):
            assert c.execute('SELECT count(*) FROM '+table).fetchone()[0]==0


def test_independent_facts_immutable_and_duplicate_owner_checks():
    rows=[g('t','vest'),g('b','trousers')]; request=StructuredOutfitRequest(style='classic')
    facts=CompactMandatoryFacts(rows,request,RequestConstraintEvaluator)
    with pytest.raises(AttributeError):facts.tables=()
    assert signature(CompactExhaustiveScorer(Query(rows+[rows[0]]),Preferences()).rank('owner',request))==signature(CompactExhaustiveScorer(Query(rows),Preferences()).rank('owner',request))
    conflict=replace(rows[0],primary_colour='red')
    assert CompactExhaustiveScorer(Query(rows+[conflict]),Preferences()).rank('owner',request).status=='ProcessingFailure'
    assert CompactExhaustiveScorer(Query([replace(rows[0],user_id='foreign'),rows[1]]),Preferences()).rank('owner',request).status=='InsufficientStructure'


@pytest.mark.parametrize('sql',[
    "UPDATE processing_items SET review_status='accepted'",
    "UPDATE processing_items SET review_status='pending'",
    "UPDATE processing_items SET review_status='rejected'",
    "UPDATE garments SET processing_item_id=NULL",
    "UPDATE processing_jobs SET user_id='other'",
    "UPDATE garments SET status='archived'",
    "UPDATE garments SET user_id='other'",
])
def test_actual_strict_query_excludes_ineligible_records(assistant_store,sql):
    from tests.test_recommendation_persistence import connect
    with connect(assistant_store[0]) as c:c.execute(sql)
    svc=service(assistant_store);svc.scoring_profile=EXPERIMENTAL;svc.scorer_factory=factory(EXPERIMENTAL)
    assert svc.recommend('owner','strict','Suggest an outfit')['status']=='NoEligibleGarments'
    with connect(assistant_store[0]) as c:assert c.execute('SELECT count(*) FROM nlp_chats').fetchone()[0]==0


@pytest.mark.parametrize('change',["primary_colour='red'","style_tags='[]'","status='archived'","processing_item_id=NULL"])
def test_selection_to_write_changes_are_revalidated(assistant_store,change):
    from tests.test_recommendation_persistence import connect
    def checkpoint(stage,*args):
        if stage=='reconstructed':
            with connect(assistant_store[0]) as c:c.execute('UPDATE garments SET '+change)
    svc=service(assistant_store);svc.scoring_profile=EXPERIMENTAL;svc.scorer_factory=factory(EXPERIMENTAL,checkpoint=checkpoint)
    assert svc.recommend('owner','change','Suggest an outfit')['status']=='WardrobeChanged'
    with connect(assistant_store[0]) as c:
        assert c.execute('SELECT count(*) FROM nlp_chats').fetchone()[0]==0
        assert c.execute('SELECT count(*) FROM recommendations').fetchone()[0]==0


@pytest.mark.parametrize('same',[True,False])
def test_actual_concurrent_compact_submissions(assistant_store,same):
    from threading import Barrier
    from tests.test_recommendation_persistence import connect
    barrier=Barrier(2)
    def checkpoint(stage,*args):
        if stage=='before_close':barrier.wait(timeout=15)
    def submit(i):
        svc=service(assistant_store);svc.scoring_profile=EXPERIMENTAL;svc.scorer_factory=factory(EXPERIMENTAL,checkpoint=checkpoint)
        return svc.recommend('owner','same' if same else str(i),'Suggest an outfit')
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(submit,range(2)))
    assert all(x['status']=='Selected' for x in results)
    assert len({x['id'] for x in results})==(1 if same else 2)
    with connect(assistant_store[0]) as c:
        for table in ('nlp_chats','recommendations'):assert c.execute('SELECT count(*) FROM '+table).fetchone()[0]==(1 if same else 2)


def test_history_is_not_rewritten_after_garment_changes(assistant_store):
    from tests.test_recommendation_persistence import connect
    svc=service(assistant_store);svc.scoring_profile=EXPERIMENTAL;svc.scorer_factory=factory(EXPERIMENTAL)
    old=svc.recommend('owner','history','Suggest an outfit')
    with connect(assistant_store[0]) as c:c.execute("UPDATE garments SET name='Edited',status='archived'")
    replay=svc.recommend('owner','history','Suggest an outfit')
    assert replay['id']==old['id'] and replay['score_metadata']==old['score_metadata'] and replay['provenance']==old['provenance']
    assert replay['items'][0]['name']==old['items'][0]['name'] and not replay['items'][0]['currently_eligible']
