"""Forward style states through actual review/confirm/PATCH and SQLite read-back.

Detector/attribute fixtures are synthetic; no model accuracy is claimed.
"""
from dataclasses import replace
from fractions import Fraction as F
import json
import sqlite3
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.application.garment_processing import garment_processing_orchestrator as processing
from app.domain.value_objects.garment_attributes import GarmentAttributes
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.recommendation.request_match_scorer import RequestMatchScorer
from app.application.recommendation.rule_based_compatibility_scorer import RuleBasedCompatibilityScorer
from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
from app.domain.value_objects.outfit_candidate import CandidateMember,OutfitCandidate
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from tests.test_garment_workflow import Detector,GeneratedVtoffStub,jpeg
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate

OMITTED=object()


@pytest.fixture
def lifecycle(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DATABASE_PATH',tmp_path/'styles.db')
    monkeypatch.setattr(processing,'get_garment_adapter',lambda:Detector())
    monkeypatch.setattr(processing,'get_standardisation_adapter',lambda:GeneratedVtoffStub())
    # Truly omitted creation field, rather than an implicit prediction/default.
    monkeypatch.setattr(processing,'get_attribute_adapter',lambda:SimpleNamespace(extract=lambda _:GarmentAttributes({})))
    with TestClient(app,headers={'X-User-Id':'style-owner'}) as client:
        def create(value=OMITTED):
            result=client.post('/api/v1/processing/jobs',files={'file':('garments.jpg',jpeg(),'image/jpeg')})
            assert result.status_code==202
            job=client.get('/api/v1/processing/jobs/'+result.json()['id']).json()
            item=job['items'][0]['id'];base='/api/v1/processing/jobs/'+job['id']
            attributes={'custom_tags':['ordinary note','rec:v1:occasion:campus:allow'],'fit':['regular','loose'],'material':['cotton','linen']}
            if value is not OMITTED: attributes['style']=value
            reviewed=client.post(base+'/review',json={'items':[{'item_id':item,'decision':'accepted','attributes':attributes}]})
            assert reviewed.status_code==200,reviewed.text
            current=next(i for i in reviewed.json()['items'] if i['id']==item)['attributes']
            if value is OMITTED: assert 'style' not in current
            else: assert current['style']==value
            result=client.post(base+'/confirm',json={'save_mode':'garments','item_ids':[item]})
            assert result.status_code==201,result.text
            return result.json()['garment_ids'][0]
        yield client,create


def read(identifier):
    with db.connection() as c:
        row=dict(c.execute('SELECT * FROM garments WHERE id=?',(identifier,)).fetchone())
    return row,json.loads(row['attributes_json'])


def snapshot(identifier):
    return next(g for g in SqliteConfirmedGarmentQuery().get_confirmed_available_garments('style-owner') if g.garment_id==identifier)


@pytest.mark.parametrize('value',[OMITTED,None,[],['vintage'],['vintage','classic'],'vintage'])
def test_creation_review_confirmation_persisted_and_snapshot(lifecycle,value):
    client,create=lifecycle;gid=create(value);row,attrs=read(gid)
    expected=None if value is OMITTED else [value] if isinstance(value,str) else value
    assert json.loads(row['style_tags'])==expected
    if value is OMITTED: assert 'style' not in attrs
    else: assert attrs['style']==value
    assert snapshot(gid).style_tags==(None if expected is None else tuple(expected))
    assert json.loads(row['custom_tags'])==attrs['custom_tags']
    assert attrs['fit']==['regular','loose'] and attrs['material']==['cotton','linen']


@pytest.mark.parametrize('value',[None,[],['vintage','classic'],'vintage'])
@pytest.mark.parametrize('patch',[{'primary_colour':'white'},{'category':'vest'},{'name':'Unrelated edit'},{'attributes':{'fit':'regular'}},{}])
def test_unrelated_update_preserves_exact_style_and_annotations(lifecycle,value,patch):
    client,create=lifecycle;gid=create(value);before=read(gid)
    response=client.patch('/api/v1/wardrobe/garments/'+gid,json=patch)
    assert response.status_code==200,response.text
    row,attrs=read(gid)
    for key in ('style_tags','custom_tags'): assert row[key]==before[0][key]
    for key in ('style','custom_tags','material'): assert attrs[key]==before[1][key]
    assert snapshot(gid).style_tags==(None if value is None else tuple([value] if isinstance(value,str) else value))


@pytest.mark.parametrize('start,end',[(None,[]),([],None),(['vintage'],['classic','vintage']),(['vintage'],None),([],['classic']),(None,'vintage')])
def test_explicit_transitions_and_legacy_string_payloads(lifecycle,start,end):
    client,create=lifecycle;gid=create(start)
    response=client.patch('/api/v1/wardrobe/garments/'+gid,json={'attributes':{'style':end}})
    assert response.status_code==200,response.text
    row,attrs=read(gid)
    assert attrs['style']==end
    expected=[end] if isinstance(end,str) else end
    assert json.loads(row['style_tags'])==expected
    assert snapshot(gid).style_tags==(None if expected is None else tuple(expected))
    assert attrs['custom_tags']==['ordinary note','rec:v1:occasion:campus:allow']


def test_omitted_update_does_not_reconcile_ambiguous_legacy_mirrors(lifecycle):
    client,create=lifecycle;gid=create(None)
    with db.connection() as c: c.execute("UPDATE garments SET style_tags='[]' WHERE id=?",(gid,))
    before=read(gid)
    assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'name':'Only name'}).status_code==200
    after=read(gid)
    assert after[0]['style_tags']==before[0]['style_tags']=='[]'
    assert after[1]['style'] is None
    assert snapshot(gid).style_tags==()  # No historical reinterpretation.


@pytest.mark.parametrize('value,state,mandatory',[(None,'Missing','Unknown'),([],'Known','Fail'),(['vintage'],'Known','Pass')])
def test_actual_snapshot_mandatory_and_compatibility_semantics(lifecycle,value,state,mandatory):
    client,create=lifecycle;gid=create(value);g=snapshot(gid)
    assert GarmentEvidenceMapper().classify(g).style.state==state
    # A second real confirmed garment supplies the other base slot after an owner category edit.
    bid=create(['vintage'])
    assert client.patch('/api/v1/wardrobe/garments/'+bid,json={'category':'trousers','primary_colour':'white'}).status_code==200
    bottom=snapshot(bid)
    candidate=OutfitCandidate((CandidateMember(g,'upper',1),CandidateMember(bottom,'lower',2)))
    # Role contract is Recommendation's canonical upper/lower for these value objects.
    result=RequestConstraintEvaluator().evaluate(OutfitCandidate((CandidateMember(g,'upper',1),CandidateMember(replace(bottom,style_tags=()),'lower',2))),StructuredOutfitRequest(style='vintage'))
    assert result.state==mandatory
    raw=RuleBasedCompatibilityScorer().evaluate(candidate)
    decision=CompatibilityDecisionPolicy.load().apply(raw,'top_bottom')
    assert decision.contribution==(F(1) if value else F(3,4))
    request=StructuredOutfitRequest(style='vintage')
    session=RequestCandidateEngine(SqliteConfirmedGarmentQuery()).generate_candidates('style-owner',request)
    gate=ScoringEligibilityGate(session,'style-owner',request)
    scores=[RequestMatchScorer().score(gate.verify(item)) for item in session]
    assert len(scores)==1
    assert scores[0].contribution==(F(1) if value else F(1,2))
    assert scores[0].summary.state==('Partial' if value is None else 'Available')


def test_history_unchanged_owner_isolation_and_atomic_rollback(lifecycle):
    client,create=lifecycle;gid=create(['vintage'])
    # Dress conversion is an ordinary owner edit; strict confirmation is retained.
    assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'category':'vest_dress'}).status_code==200
    # Explicit disposable repository, using the actual confirmed snapshot.
    # Synthetic valid score fixture is for archival preservation, not fashion evaluation.
    from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
    from app.domain.value_objects.recommendation_persistence import RecommendationWrite
    from tests.test_recommendation_persistence import assistant
    g=snapshot(gid)
    command=RecommendationWrite('style-owner','homepage','style-history','{}',OutfitCandidate((CandidateMember(g,'one_piece',1),)),'{"structure":"synthetic-archival-fixture-v1"}')
    SqliteRecommendationRepository(db.DATABASE_PATH).persist(assistant(command))
    outfit=client.post('/api/v1/wardrobe/outfits',json={'name':'Historical fixture','garment_ids':[gid]}).json()['id']
    person=client.post('/api/v1/media/person-images',files={'file':('person.jpg',jpeg(),'image/jpeg')}).json()['id']
    from app.application.visualisation.outfit_visualisation_service import create_visualisation
    create_visualisation('style-owner',person,outfit_id=outfit)
    tables=('recommendations','recommendation_items','recommendation_item_snapshots','recommendation_metadata','nlp_chats','visualisations','visualisation_items')
    def frozen():
        with db.connection() as c: return {t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in tables}
    before=frozen()
    assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'attributes':{'style':None}}).status_code==200
    assert frozen()==before
    row=read(gid)
    assert client.patch('/api/v1/wardrobe/garments/'+gid,headers={'X-User-Id':'intruder'},json={'attributes':{'style':[]}}).status_code==404
    assert read(gid)==row
    with db.connection() as c:
        c.execute("CREATE TRIGGER fail_style BEFORE UPDATE OF style_tags ON garments BEGIN SELECT RAISE(ABORT,'injected style failure'); END")
    with pytest.raises(sqlite3.IntegrityError,match='injected style failure'):
        client.patch('/api/v1/wardrobe/garments/'+gid,json={'name':'Must roll back','attributes':{'style':[]}})
    assert read(gid)==row and frozen()==before


@pytest.mark.parametrize('canonical',[False,True])
def test_omitted_style_preserves_legacy_additional_mirror_without_reconciliation(lifecycle,canonical):
    client,create=lifecycle;gid=create(None)
    row,attrs=read(gid)
    if not canonical: attrs.pop('style')
    extra={**attrs,'style':['vintage'],'custom_tags':['mirror note']}
    with db.connection() as c:
        c.execute('UPDATE garments SET attributes_json=?,additional_attributes=? WHERE id=?',(json.dumps(attrs),json.dumps(extra),gid))
    before=snapshot(gid).style_tags
    assert before==(None if canonical else ('vintage',))
    response=client.patch('/api/v1/wardrobe/garments/'+gid,json={'name':'Unrelated','attributes':{'fit':'regular'}})
    assert response.status_code==200,response.text
    after,values=read(gid)
    assert ('style' in values)==canonical
    assert json.loads(after['additional_attributes'])['style']==['vintage']
    assert json.loads(after['additional_attributes'])['custom_tags']==['mirror note']
    assert snapshot(gid).style_tags==before


def test_unrelated_edit_preserves_malformed_legacy_mirror(lifecycle):
    client,create=lifecycle;gid=create(None)
    with db.connection() as c:c.execute("UPDATE garments SET additional_attributes='malformed-mirror' WHERE id=?",(gid,))
    before=read(gid)
    # Existing serializer rejects corrupt JSON before any write; not repaired here.
    with pytest.raises(json.JSONDecodeError):
        client.patch('/api/v1/wardrobe/garments/'+gid,json={'name':'Name only'})
    assert read(gid)==before
    assert read(gid)[0]['additional_attributes']=='malformed-mirror'
    assert snapshot(gid).style_tags is None
    assert 'additional_attributes' in snapshot(gid).invalid_attributes



def test_partial_update_serializes_style_read_merge_write(lifecycle,monkeypatch):
    import threading
    from app.application.wardrobe import wardrobe_service as wardrobe
    client,create=lifecycle;gid=create(['vintage']);attempts=[]
    original=wardrobe._serialise_garment
    def observed(row):
        value=original(row)
        if not attempts:
            def competing():
                c=sqlite3.connect(db.DATABASE_PATH,timeout=.05)
                try:
                    c.execute("UPDATE garments SET style_tags='null' WHERE id=?",(gid,));c.commit();attempts.append('committed')
                except sqlite3.OperationalError as e:attempts.append(str(e))
                finally:c.close()
            thread=threading.Thread(target=competing);thread.start();thread.join()
        return value
    monkeypatch.setattr(wardrobe,'_serialise_garment',observed)
    assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'name':'Only name'}).status_code==200
    assert len(attempts)==1 and 'locked' in attempts[0]
    assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'attributes':{'style':None}}).status_code==200
    assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'name':'Another name'}).status_code==200
    assert snapshot(gid).style_tags is None
