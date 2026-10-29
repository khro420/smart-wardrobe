"""Actual API-confirmed wardrobe records, content CAS and opt-in suitability only."""
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import json
import sqlite3
import pytest
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.application.recommendation.suitability_evidence_mapper import SuitabilityEvidenceParser
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.suitability_policy import SuitabilityPolicy
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest,GarmentCategoryConstraint
from tests.test_forward_style_semantics import lifecycle,read,snapshot

VALUES=[('occasion',v) for v in SuitabilityPolicy.load().enabled_occasions]+[('formality',v) for v in SuitabilityPolicy.load().enabled_formality]


def garment(client,gid):return next(g for g in client.get('/api/v1/wardrobe/garments').json() if g['id']==gid)
def tag(field='occasion',value='campus',decision='allow'):return f'rec:v1:{field}:{value}:{decision}'
def patch_tags(client,gid,tags,revision=None,**fields):
    revision=revision if revision is not None else garment(client,gid)['tag_edit']['revision']
    return client.patch('/api/v1/wardrobe/garments/'+gid,headers={'If-Match':revision},json={**fields,'attributes':{'custom_tags':tags}})


@pytest.mark.parametrize('field,value',VALUES)
@pytest.mark.parametrize('choice',['unknown','allow','deny'])
def test_all_declared_values_real_persistence_and_mapper(lifecycle,field,value,choice):
    client,create=lifecycle;gid=create(None)
    tags=['ordinary note','sporty']+([] if choice=='unknown' else [tag(field,value,choice)])
    response=patch_tags(client,gid,tags)
    assert response.status_code==200,response.text
    fetched=garment(client,gid);row,attrs=read(gid)
    assert fetched['custom_tags']==json.loads(row['custom_tags'])==attrs['custom_tags']==tags
    assert attrs['style'] is None and snapshot(gid).style_tags is None
    evidence=SuitabilityEvidenceParser().parse(snapshot(gid))
    assert evidence.state_for(field,value)=={'unknown':'Unknown','allow':'Pass','deny':'Fail'}[choice]
    for declaration in fetched['tag_edit']['declarations']:
        expected=choice if (declaration['field'],declaration['value'])==(field,value) else 'unknown'
        assert declaration['choice']==expected
    assert len(fetched['tag_edit']['colour_names'])==14


def test_conflicts_malformed_and_ordinary_tags_preserve_unknown(lifecycle):
    client,create=lifecycle;gid=create([])
    tags=['ordinary note',tag(),tag(decision='deny'),tag('formality','casual'),'rec:v2:occasion:campus:allow']
    assert patch_tags(client,gid,tags).status_code==200
    view=garment(client,gid)['tag_edit']
    campus=next(d for d in view['declarations'] if d['value']=='campus')
    assert campus['conflict'] and campus['malformed'] and campus['choice']=='unknown'
    assert view['malformed']==[{'index':4,'fields':['occasion']}]
    # Unrelated edits and same-content saves do not resolve anything.
    assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'primary_colour':'white','category':'vest'}).status_code==200
    assert garment(client,gid)['custom_tags']==tags and snapshot(gid).style_tags==()
    # Unknown removes only the exact valid pair; malformed evidence remains.
    remaining=[t for t in tags if t not in (tag(),tag(decision='deny'))]
    assert patch_tags(client,gid,remaining).status_code==200
    assert garment(client,gid)['custom_tags']==remaining
    assert SuitabilityEvidenceParser().parse(snapshot(gid)).state_for('occasion','campus')=='Unknown'
    # Explicit malformed removal + explicit Allow is an owner correction.
    corrected=[t for t in remaining if not t.startswith('rec:v2:')]+[tag()]
    assert patch_tags(client,gid,corrected).status_code==200
    assert SuitabilityEvidenceParser().parse(snapshot(gid)).state_for('occasion','campus')=='Pass'
    assert tag('formality','casual') in garment(client,gid)['custom_tags']


def test_stale_and_missing_revisions_reject_entire_edit(lifecycle):
    client,create=lifecycle;gid=create(['vintage']);before=read(gid)
    assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'attributes':{'custom_tags':[]}}).status_code==428
    assert read(gid)==before
    revision=garment(client,gid)['tag_edit']['revision']
    assert patch_tags(client,gid,['other session',tag('occasion','work')],revision).status_code==200
    saved=read(gid)
    assert patch_tags(client,gid,[tag()],revision,name='Must not apply').status_code==409
    assert read(gid)==saved
    assert client.patch('/api/v1/wardrobe/garments/'+gid,headers={'If-Match':'*'},json={'attributes':{'custom_tags':[]}}).status_code==409
    # Foreign owner cannot discover collection revisions or modify the garment.
    assert client.patch('/api/v1/wardrobe/garments/'+gid,headers={'X-User-Id':'intruder','If-Match':revision},json={'attributes':{'custom_tags':[]}}).status_code==404


def test_actual_concurrent_connections_allow_one_write_not_silent_loss(lifecycle):
    from app.application.wardrobe.wardrobe_service import update_garment
    client,create=lifecycle;gid=create(None)
    assert patch_tags(client,gid,['ordinary note']).status_code==200
    revision=garment(client,gid)['tag_edit']['revision']
    def submit(value):
        try:
            update_garment(gid,'style-owner',{'attributes':{'custom_tags':['ordinary note',tag('occasion',value)]}},revision)
            return 200
        except Exception as exc:return getattr(exc,'status_code',str(exc))
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(submit,['campus','work']))
    assert sorted(results)==[200,409]
    final=garment(client,gid)['custom_tags'];assert final[0]=='ordinary note' and len(final)==2
    # Re-read/review before intentionally combining the second edit.
    missing=tag('occasion','work' if tag() in final else 'campus')
    assert patch_tags(client,gid,final+[missing]).status_code==200
    assert set(garment(client,gid)['custom_tags'])=={'ordinary note',tag(),tag('occasion','work')}


def test_failed_tag_write_rolls_back_other_fields_and_styles(lifecycle):
    client,create=lifecycle;gid=create([]);before=read(gid);revision=garment(client,gid)['tag_edit']['revision']
    with db.connection() as c:c.execute("CREATE TRIGGER fail_tags BEFORE UPDATE OF custom_tags ON garments BEGIN SELECT RAISE(ABORT,'tag failure'); END")
    with pytest.raises(sqlite3.IntegrityError,match='tag failure'):
        client.patch('/api/v1/wardrobe/garments/'+gid,headers={'If-Match':revision},json={'name':'Not saved','attributes':{'style':None,'custom_tags':[tag()]}})
    assert read(gid)==before and snapshot(gid).style_tags==()


@pytest.mark.parametrize('role',['upper','lower','outerwear'])
@pytest.mark.parametrize('state',['allow','deny','unknown','conflict','malformed'])
def test_explicit_opt_in_all_members_including_outerwear(lifecycle,role,state):
    client,create=lifecycle;ids=[create(['vintage']) for _ in range(3)]
    for gid,category in zip(ids,['vest','trousers','long_sleeve_outwear']):
        assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'category':category,'primary_colour':'blue'}).status_code==200
        tags=[tag(),tag('formality','casual')]
        if {'upper':0,'lower':1,'outerwear':2}[role]==ids.index(gid):
            if state=='deny':tags[0]=tag(decision='deny')
            elif state=='unknown':tags.pop(0)
            elif state=='conflict':tags.append(tag(decision='deny'))
            elif state=='malformed':tags.append('rec:v1:occasion:campus:maybe')
        assert patch_tags(client,gid,tags).status_code==200
    request=StructuredOutfitRequest(occasion='campus',formality='casual',style='vintage',colours=('blue',),garment_categories=(GarmentCategoryConstraint('group','outerwear'),))
    session=RequestCandidateEngine(SqliteConfirmedGarmentQuery(),evaluator_factory=SuitabilityRequestEvaluator).generate_candidates('style-owner',request)
    result=list(session)
    assert session.result.complete
    if state=='allow':assert len(result)==1 and len(result[0].candidate.members)==3
    else:
        assert not result
        assert session.result.status==('NoMatchingCandidates' if state=='deny' else 'InsufficientEvidence')
    # Opt-in is explicit, not a changed default evaluator.
    default=RequestCandidateEngine(SqliteConfirmedGarmentQuery()).generate_candidates('style-owner',request)
    assert list(default)==[] and default.result.status=='PolicyUnavailable'


@pytest.mark.parametrize('outfit_request',[StructuredOutfitRequest(occasion='exercise'),StructuredOutfitRequest(formality='formal')])
def test_unavailable_policy_stays_unavailable(lifecycle,outfit_request):
    client,create=lifecycle;create(['vintage'])
    session=RequestCandidateEngine(SqliteConfirmedGarmentQuery(),evaluator_factory=SuitabilityRequestEvaluator).generate_candidates('style-owner',outfit_request)
    assert list(session)==[] and session.result.status=='PolicyUnavailable'


def test_nontext_collection_not_sanitized_or_trusted(lifecycle):
    client,create=lifecycle;gid=create(None)
    response=patch_tags(client,gid,[None,tag()])
    assert response.status_code==200
    assert not response.json()['tag_edit']['editable']
    assert all(d['state']=='Unknown' for d in response.json()['tag_edit']['declarations'])
    assert 'custom_tags' in snapshot(gid).invalid_attributes


def test_successful_tag_edit_preserves_archived_recommendations_and_visualisation(lifecycle):
    from tests.test_forward_style_semantics import jpeg
    from app.domain.value_objects.outfit_candidate import OutfitCandidate, CandidateMember
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
    assert patch_tags(client,gid,['ordinary note',tag('occasion','work')]).status_code==200
    assert frozen()==before
