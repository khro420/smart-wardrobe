"""Internal verified writes against genuine authenticated disposable wardrobe rows."""
from dataclasses import replace
from pathlib import Path
from fractions import Fraction as F
import json,sqlite3,uuid,time,tracemalloc
import pytest
from fastapi import HTTPException
from tests.test_wearer_category_policy import category_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle
from tests.test_processing_subtype_identity_integration import _preserve_composition
from tests.isolated_soft_preference_parser import IsolatedSoftPreferenceParser
from app.application.ports.assistant_runtime import assistant_service
from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
from app.application.recommendation.request_local_soft_workflow import InternalLocalPreferenceWorkflow
from app.application.recommendation.request_local_selection_verifier import verify
from app.application.recommendation.scoring_display import with_scoring_display
from app.domain.value_objects.request_local_selection import LocalSelectionProof,LocalPreferenceWriteDraft,MAX_PROOF
from app.domain.value_objects.recommendation_persistence import WardrobeChanged,PersistenceConflict
from app.domain.value_objects.attribute_conditions import encode,digest

@pytest.fixture(autouse=True)
def runtime_boundary():
    with _preserve_composition():yield

@pytest.fixture
def local_store(category_api):
    client,male,female=category_api;service=assistant_service();workflow=InternalLocalPreferenceWorkflow()
    repo=SqliteRecommendationRepository(service.repository.database_path,description_policy=service.repository.description_policy,_local_preference_workflow=workflow)
    with repo._connect() as conn:owner=conn.execute('SELECT user_id FROM wardrobe_profiles WHERE id=?',(female,)).fetchone()[0]
    return client,repo,workflow,owner,male,female

def intent(text="I'd prefer black trousers."):return IsolatedSoftPreferenceParser().interpret(text).local_intent
def counts(repo):
    with repo._connect() as c:return tuple(c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('recommendations','nlp_chats','recommendation_items','recommendation_item_snapshots','recommendation_metadata','recommendation_submissions'))

def test_internal_write_and_history_smoke(local_store):
    client,repo,workflow,owner,male,female=local_store
    command=workflow.prepare(repo,owner,female,intent(),uuid.uuid4().hex)
    saved,replayed=repo.persist_assistant(command)
    assert not replayed and saved['provenance']['request_local_preference']==command.local_preference.proof.to_dict()
    display=with_scoring_display(saved)['scoring_display'];assert display['version']=='request-local-preference-display-1.0.0'
    assert display['continuation_available'] is False and display['decision']['selected_optional']['state']=='Satisfied'
    actual=client.get('/api/v1/chats/'+saved['chat_id'],headers={'X-Wardrobe-Profile-Id':female})
    assert actual.status_code==200,actual.text
    assert actual.json()['recommendation']['scoring_display']==display

@pytest.mark.parametrize('text',["I'd prefer black trousers.",'I need trousers, preferably black.',
 'I want a cotton shirt, preferably blue.','I need black trousers, preferably blue.','I need black trousers, preferably black.'])
def test_reference_compact_and_actual_predecessor_scores(local_store,text):
    client,repo,workflow,owner,male,female=local_store
    from tests.test_attribute_persistence import qualify
    for g in client.get('/api/v1/wardrobe/garments').json():
        if g['category'] in ('short_sleeve_top','long_sleeve_top'):qualify(client,g['id'],material=['cotton'])
    parsed=IsolatedSoftPreferenceParser().interpret(text);out=[]
    for engine in ('reference','compact_exhaustive'):
        command=workflow.prepare(repo,owner,female,parsed.local_intent,uuid.uuid4().hex,engine=engine)
        out.append(command.local_preference.proof.to_dict()['decision'])
        saved,_=repo.persist_assistant(command)
        assert saved['score_metadata']==out[-1]['selected']['score']
    assert out[0]==out[1]
    from tests.soft_preference_isolated_support import rank_actual
    with repo._connect() as c:scope,_,preferences=workflow.capture(c,owner,command.wearer)
    old,_,_=rank_actual(scope.usable_descriptions,parsed,'reference',preferences=preferences,wearer_scope=female)
    from app.application.recommendation.request_local_selection_engine import decision_document
    # Phase 2C wrapped the score JSON string in another JSON encoding. The new
    # proof embeds the very same exact object. Normalize this representation,
    # including the commitment, without changing any score or expected winner.
    import hashlib
    old_document=decision_document(old)
    for name in ('baseline','selected'):old_document[name]['score']=json.loads(old_document[name]['score'])
    normalized=[replace(p.primary,certificate=json.loads(p.primary.certificate).encode()) for p in old.optional_ledger]
    old_document['scope_digest']=hashlib.sha256(b''.join(sorted(p.identity() for p in normalized))).hexdigest()
    assert old_document==out[0]

@pytest.mark.parametrize('wish',["I'd prefer a black skirt.","I'd prefer a purple top."])
def test_no_match_or_denied_wearer_falls_back_not_eligibility(local_store,wish):
    client,repo,workflow,owner,male,female=local_store
    command=workflow.prepare(repo,owner,male,intent(wish),uuid.uuid4().hex)
    saved=repo.persist(command);proof=saved['provenance']['request_local_preference']
    assert proof['decision']['selected']==proof['decision']['baseline']
    assert all(i['category'] not in ('skirt','vest_dress') for i in saved['items'])
    assert proof['decision']['selected_optional']['support']==0

def test_replay_uses_archive_and_conflicts_do_not_write(local_store,monkeypatch):
    client,repo,workflow,owner,male,female=local_store;key=uuid.uuid4().hex;i=intent()
    saved,replayed=workflow.submit(repo,owner,female,i,key);assert not replayed
    before=counts(repo)
    from app.application.recommendation import request_local_soft_workflow as module
    monkeypatch.setattr(module,'first_selection',lambda *a,**k:pytest.fail('Replay must not rank'))
    monkeypatch.setattr(workflow,'capture',lambda *a,**k:pytest.fail('Replay must not acquire current sources/preferences'))
    monkeypatch.setattr(IsolatedSoftPreferenceParser,'interpret',lambda *a,**k:pytest.fail('History must not parse'))
    reply,replayed=workflow.submit(repo,owner,female,i,key);assert replayed and reply==saved
    assert repo.get(owner,saved['id'])['provenance']==saved['provenance']
    # Use valid intents authored before parser is disabled.
    v=i.to_dict();v['optional']['spans'][0]['text']=v['optional']['spans'][0]['text']
    from app.domain.value_objects.request_local_preference import RequestLocalPreferenceIntent
    v['optional']['predicates'][0]['values']=['blue'];v['revision']=digest({**v,'revision':''});different=RequestLocalPreferenceIntent(encode(v))
    with pytest.raises(PersistenceConflict):repo.find_local_submission(owner,female,different,key)
    with pytest.raises(PersistenceConflict):repo.find_local_submission(owner,male,i,key)
    with pytest.raises(PersistenceConflict):repo.find_local_submission(owner,female,i,key,policy={'version':'different-policy'})
    with pytest.raises(PersistenceConflict):repo.find_assistant_submission(owner,key,i.to_dict()['original_text'],wearer_profile_id=female)
    assert counts(repo)==before

@pytest.mark.parametrize('stage',['local_preference_revalidated','revalidated','chat','recommendation','item','snapshot','metadata','submission','before_commit'])
def test_every_atomic_stage_rolls_back(local_store,stage):
    client,repo,workflow,owner,male,female=local_store
    command=workflow.prepare(repo,owner,female,intent(),uuid.uuid4().hex);before=counts(repo)
    def fail(where,conn):
        if where==stage:raise RuntimeError('deliberate atomic rollback')
    repo.checkpoint=fail
    with pytest.raises(RuntimeError,match='deliberate'):repo.persist(command)
    assert counts(repo)==before

@pytest.mark.parametrize('mutation',['selected_colour','unselected_description','availability','wrong_media_owner','processing_link','wearer','preferences','media_bytes'])
def test_changed_sources_abort_without_partial_rows(local_store,mutation):
    client,repo,workflow,owner,male,female=local_store
    command=workflow.prepare(repo,owner,female,intent(),uuid.uuid4().hex);before=counts(repo);selected=command.candidate.members[0].garment.garment_id
    proof=command.local_preference.proof.to_dict();unselected=next(s['snapshot']['garment_id'] for s in proof['sources'] if s['snapshot']['garment_id'] not in {m.garment.garment_id for m in command.candidate.members})
    with repo._connect() as c:
        if mutation=='selected_colour':c.execute("UPDATE garments SET primary_colour='red' WHERE id=?",(selected,))
        elif mutation=='unselected_description':c.execute("UPDATE garments SET name='Changed unselected garment' WHERE id=?",(unselected,))
        elif mutation=='availability':c.execute("UPDATE garments SET status='archived' WHERE id=?",(selected,))
        elif mutation=='wrong_media_owner':c.execute("UPDATE media_assets SET user_id='foreign' WHERE id=?",(command.candidate.members[0].garment.preferred_media_id,))
        elif mutation=='processing_link':c.execute("UPDATE processing_items SET review_status='pending' WHERE id=(SELECT processing_item_id FROM garments WHERE id=?)",(selected,))
        elif mutation=='wearer':c.execute("UPDATE wardrobe_profile_details_v1 SET revision=? WHERE profile_id=?",('f'*64,female))
        elif mutation=='preferences':c.execute("INSERT INTO user_preferences(id,user_id,profile_id,preference_type,preference_value_json,weight,source,is_active,created_at,updated_at) VALUES(?,?,?,'colours',?,1,'owner',1,'now','now')",(str(uuid.uuid4()),owner,female,json.dumps({'values':['blue']})))
    if mutation=='media_bytes':
        from app.application.ports.workflow_runtime import runtime
        path,_=runtime().media.path_for_owner(command.candidate.members[0].garment.preferred_media_id,owner);path.write_bytes(path.read_bytes()+b'disposable mutation')
    with pytest.raises((ValueError,HTTPException)):repo.persist(command)
    assert counts(repo)==before

@pytest.mark.parametrize('mutation',['baseline','selected_score','counts','promotable','optional_ledger','missing_source','settings','budget','grammar'])
def test_forged_proof_refused_even_with_recomputed_revision(local_store,mutation):
    client,repo,workflow,owner,male,female=local_store
    command=workflow.prepare(repo,owner,female,intent(),uuid.uuid4().hex);v=command.local_preference.proof.to_dict();before=counts(repo)
    if mutation=='baseline':v['decision']['baseline']['key']=v['decision']['selected']['key'][::-1]
    elif mutation=='selected_score':v['decision']['selected']['score']['total']={'numerator':1,'denominator':1}
    elif mutation=='counts':v['decision']['mandatory']['passed']+=1
    elif mutation=='promotable':v['decision']['promotable']=[]
    elif mutation=='optional_ledger':v['decision']['selected_optional']['support']=0
    elif mutation=='missing_source':v['sources'].pop()
    elif mutation=='settings':v['settings']['preference']='P2'
    elif mutation=='budget':v['policy']['T_loss']='1/10'
    elif mutation=='grammar':v['intent']['grammar_sha256']='0'*64;v['intent']['revision']=digest({**v['intent'],'revision':''})
    v['revision']=digest({**v,'revision':''})
    with pytest.raises((ValueError,HTTPException)):
        bad=replace(command,local_preference=LocalPreferenceWriteDraft(LocalSelectionProof(encode(v))))
        repo.persist(bad)
    assert counts(repo)==before

def test_disabled_writer_normal_route_and_soft_continuation(local_store):
    client,repo,workflow,owner,male,female=local_store
    command=workflow.prepare(repo,owner,female,intent(),uuid.uuid4().hex);before=counts(repo)
    with pytest.raises(ValueError,match='disabled'):SqliteRecommendationRepository(repo.database_path).persist(command)
    assert counts(repo)==before
    saved=repo.persist(command)
    with pytest.raises(ValueError):repo.refinement_continuation(owner,saved['id'],saved['request_text'],uuid.uuid4().hex,command.wearer)
    assert assistant_service().attribute_pipeline.capabilities()['grammar_version']=='conversational-attribute-grammar-1.6.0'
    reply=client.post('/api/v1/recommendations?pipeline=integrated',json={'request_text':"I'd prefer black trousers.",'submission_key':uuid.uuid4().hex,'wearer_profile_id':female})
    assert reply.status_code==422
    assert counts(repo)[0]==before[0]+1

def test_proof_limits_and_observed_cost(local_store,record_property):
    client,repo,workflow,owner,male,female=local_store
    start=time.perf_counter();tracemalloc.start()
    try:
        command=workflow.prepare(repo,owner,female,intent(),uuid.uuid4().hex,engine='compact_exhaustive')
        repo.persist(command);_,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop()
    record_property('instrumented_prepare_and_commit_seconds',time.perf_counter()-start)
    record_property('traced_python_peak_bytes',peak);record_property('proof_bytes',len(command.local_preference.proof.payload))
    record_property('candidate_count',command.local_preference.proof.to_dict()['decision']['mandatory']['examined'])
    assert len(command.local_preference.proof.payload)<=MAX_PROOF
    with pytest.raises(ValueError):LocalSelectionProof(b' '*(MAX_PROOF+1))

def restrict(client,repo,names):
    garments=client.get('/api/v1/wardrobe/garments').json();ids={g['name']:g['id'] for g in garments}
    keep=tuple(ids[n] for n in names)
    with repo._connect() as c:
        c.execute('UPDATE garments SET status=? WHERE id NOT IN ('+','.join('?' for _ in keep)+')',('archived',*keep))
    return ids

@pytest.mark.parametrize('within',[True,False])
def test_real_C1_tradeoff_inside_and_outside_exact_budget(local_store,within):
    client,repo,workflow,owner,male,female=local_store
    ids=restrict(client,repo,['Blue T-shirt','Blue Jeans','Black Trousers'])
    from tests.test_attribute_persistence import qualify
    styles=['casual','classic','formal','sporty','streetwear']
    qualify(client,ids['Blue T-shirt'],style=styles,primary_colour='white')
    qualify(client,ids['Blue Jeans'],style=styles,primary_colour='blue')
    qualify(client,ids['Black Trousers'],style=styles[:4 if within else 1],primary_colour='black')
    command=workflow.prepare(repo,owner,female,intent(),uuid.uuid4().hex,engine='compact_exhaustive')
    v=command.local_preference.proof.to_dict()['decision'];selected=v['selected']['key'][-1][1]
    assert v['baseline']['key'][-1][1]==ids['Blue Jeans']
    assert selected==ids['Black Trousers' if within else 'Blue Jeans']
    raw=v['baseline']['score']['total'];baseline=F(raw['numerator'],raw['denominator'])
    assert baseline==F(1,5)
    if within:assert command.score.total==F(17,90) and baseline-command.score.total==F(1,90)
    repo.persist(command)

@pytest.mark.parametrize('state',['missing','unqualified','stale','conflicting'])
def test_optional_uncertainty_is_preserved_in_real_archive(local_store,state):
    client,repo,workflow,owner,male,female=local_store
    ids=restrict(client,repo,['Blue T-shirt','Black Trousers']);gid=ids['Black Trousers']
    from app.application.wardrobe import description_projector as b0
    from app.application.wardrobe.description_normalizer import normalise_field
    from app.application.wardrobe.description_policy import DescriptionPolicy
    g=next(g for g in client.get('/api/v1/wardrobe/garments').json() if g['id']==gid)
    document=g['description']['evidence']
    if state in ('stale','conflicting'):
        document['fields']['primary_colour']=b0._changed(document['fields']['primary_colour'],state.title(),'category_or_media_changed' if state=='stale' else 'competing_legacy_field_tags')
    else:
        document['fields']['primary_colour']=normalise_field('primary_colour',None if state=='missing' else 'black',DescriptionPolicy.load(),origin='model_suggestion',category=g['category'],media_id=g['preferred_media_id']).to_dict()
    document=b0._document(document['subject'],document['fields']).to_dict()
    with repo._connect() as c:
        row=c.execute('SELECT attributes_json,additional_attributes FROM garments WHERE id=?',(gid,)).fetchone()
        attrs=json.loads(row[0]);extra=json.loads(row[1]);attrs[b0.KEY]=document;extra[b0.KEY]=document
        if state in ('missing','unqualified'):
            for container in (attrs,extra):
                container.pop('primary_colour',None);container.pop('primary_color',None)
        c.execute('UPDATE garments SET primary_colour=?,attributes_json=?,additional_attributes=? WHERE id=?',(None if state in ('missing','unqualified') else 'black',json.dumps(attrs),json.dumps(extra),gid))
    if state in ('missing','unqualified'):
        from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
        with repo._connect() as c:assert next(g for g in SqliteConfirmedGarmentQuery(c).get_confirmed_available_garments(owner) if g.garment_id==gid).primary_colour is None
    command=workflow.prepare(repo,owner,female,intent(),uuid.uuid4().hex)
    saved=repo.persist(command);optional=saved['provenance']['request_local_preference']['decision']['selected_optional']
    assert optional['state']=='Unverifiable' and optional['support']==0 and optional['value'] is None

@pytest.mark.parametrize('roles,names',[
 (['upper','lower'],['Blue T-shirt','Black Trousers']),
 (['upper','lower','outerwear'],['Blue T-shirt','Black Trousers','Grey Jacket']),
 (['one_piece'],['Navy Dress']),(['one_piece','outerwear'],['Navy Dress','Grey Jacket'])])
def test_all_four_selected_structures_persist_exactly(local_store,roles,names):
    client,repo,workflow,owner,male,female=local_store;ids=restrict(client,repo,names)
    from tests.test_attribute_persistence import qualify
    for name in names:qualify(client,ids[name],style=['casual'] if name=='Blue T-shirt' else ['casual','formal'] if name=='Grey Jacket' else ['formal'])
    for engine in ('reference','compact_exhaustive'):
        command=workflow.prepare(repo,owner,female,intent(),uuid.uuid4().hex,engine=engine)
        assert [m.role for m in command.candidate.members]==roles
        repo.persist(command)

def test_archived_replay_after_current_wardrobe_and_settings_change(local_store,monkeypatch):
    client,repo,workflow,owner,male,female=local_store;i=intent();key=uuid.uuid4().hex
    saved,_=workflow.submit(repo,owner,female,i,key);display=with_scoring_display(saved)['scoring_display']
    with repo._connect() as c:
        c.execute("UPDATE garments SET status='archived',name='Current renamed garment'")
        c.execute("INSERT INTO user_preferences(id,user_id,profile_id,preference_type,preference_value_json,weight,source,is_active,created_at,updated_at) VALUES(?,?,?,'colours',?,1,'owner',1,'now','now')",(str(uuid.uuid4()),owner,female,json.dumps({'values':['red']})))
    from app.application.nlp.conversational_context_interpreter import ConversationalContextInterpreter
    from app.application.recommendation import request_local_soft_workflow as m
    monkeypatch.setattr(ConversationalContextInterpreter,'interpret',lambda *a,**k:pytest.fail('Archived request must not be reinterpreted'))
    monkeypatch.setattr(m,'first_selection',lambda *a,**k:pytest.fail('Archive must not call first ranking coordinator'))
    monkeypatch.setattr(workflow,'capture',lambda *a,**k:pytest.fail('Archive must not capture active source facts'))
    replay,replayed=workflow.submit(repo,owner,female,i,key);assert replayed
    assert replay['score_metadata']==saved['score_metadata'] and replay['provenance']==saved['provenance']
    assert with_scoring_display(replay)['scoring_display']==display
    assert all(not item['currently_eligible'] and item['preferred_media_id'] is None for item in replay['items'])

def test_changed_source_inside_write_lock_and_preferences_revision_abort(local_store):
    client,repo,workflow,owner,male,female=local_store
    command=workflow.prepare(repo,owner,female,intent(),uuid.uuid4().hex);before=counts(repo)
    def mutate(stage,conn):
        if stage=='local_preference_before_revalidation':conn.execute("UPDATE wardrobe_profiles SET updated_at='changed inside lock' WHERE id=?",(female,))
    repo.checkpoint=mutate
    with pytest.raises(WardrobeChanged):repo.persist(command)
    assert counts(repo)==before
    with repo._connect() as c:assert c.execute('SELECT updated_at FROM wardrobe_profiles WHERE id=?',(female,)).fetchone()[0]!='changed inside lock'

def test_complete_scope_does_not_depend_on_acquisition_order(local_store,monkeypatch):
    client,repo,workflow,owner,male,female=local_store;i=intent()
    first=workflow.prepare(repo,owner,female,i,uuid.uuid4().hex)
    from app.application.wardrobe import wearer_category_service as service
    original=service.capture
    def reverse(*a,**k):
        scope=original(*a,**k)
        return replace(scope,account_rows=tuple(reversed(scope.account_rows)),account_descriptions=tuple(reversed(scope.account_descriptions)),usable_rows=tuple(reversed(scope.usable_rows)),usable_descriptions=tuple(reversed(scope.usable_descriptions)))
    monkeypatch.setattr(service,'capture',reverse)
    second=workflow.prepare(repo,owner,female,i,uuid.uuid4().hex,engine='compact_exhaustive')
    assert first.local_preference.proof.to_dict()['decision']==second.local_preference.proof.to_dict()['decision']
    repo.persist(second)

def test_foreign_owner_wrong_wearer_and_mandatory_unknown_never_write(local_store):
    client,repo,workflow,owner,male,female=local_store;before=counts(repo)
    with pytest.raises((ValueError,HTTPException)):workflow.prepare(repo,'foreign',female,intent(),uuid.uuid4().hex)
    with pytest.raises((ValueError,HTTPException)):workflow.prepare(repo,owner,str(uuid.uuid4()),intent(),uuid.uuid4().hex)
    with pytest.raises(ValueError,match='No mandatory'):workflow.prepare(repo,owner,female,intent('I want a cotton shirt, preferably blue.'),uuid.uuid4().hex)
    assert counts(repo)==before

@pytest.mark.parametrize('change',['source_extra','revision_extra','integer_setting','changed_grammar_receipt'])
def test_closed_nested_contracts_and_distinct_grammar_receipt(local_store,change):
    client,repo,workflow,owner,male,female=local_store;command=workflow.prepare(repo,owner,female,intent(),uuid.uuid4().hex)
    v=command.local_preference.proof.to_dict();before=counts(repo)
    if change=='changed_grammar_receipt':
        repo.persist(command)
        from app.shared_contracts.isolated_soft_preference_grammar import REGISTRY,GRAMMAR_VERSION
        from app.domain.value_objects.request_local_preference import RequestLocalPreferenceIntent
        i=v['intent'];i['grammar_sha256']=next(h for h in REGISTRY[GRAMMAR_VERSION] if h!=i['grammar_sha256']);i['revision']=digest({**i,'revision':''})
        with pytest.raises(PersistenceConflict):repo.find_local_submission(owner,female,RequestLocalPreferenceIntent(encode(i)),command.submission_key)
        return
    if change=='source_extra':v['sources'][0]['links']['unregistered']='extra'
    elif change=='revision_extra':v['source_revisions']['unregistered']='extra'
    else:v['settings']['contextual']=0
    v['revision']=digest({**v,'revision':''})
    with pytest.raises(ValueError):
        proof=LocalSelectionProof(encode(v));verify(proof,owner,female)
    assert counts(repo)==before

def test_real_saved_P1_preferences_and_revision_revalidation(local_store):
    client,repo,workflow,owner,male,female=local_store
    response=client.put('/api/v1/account/preferences/colours',headers={'X-Wardrobe-Profile-Id':female},json={'preference_value':{'values':['blue']},'weight':0.5})
    assert response.status_code==200,response.text
    i=intent();reference=workflow.prepare(repo,owner,female,i,uuid.uuid4().hex)
    compact=workflow.prepare(repo,owner,female,i,uuid.uuid4().hex,engine='compact_exhaustive')
    assert reference.local_preference.proof.to_dict()['decision']==compact.local_preference.proof.to_dict()['decision']
    assert compact.score.preference.contribution>0
    before=counts(repo)
    with repo._connect() as c:c.execute("UPDATE user_preferences SET updated_at='new-revision' WHERE user_id=? AND profile_id=?",(owner,female))
    with pytest.raises(WardrobeChanged):repo.persist(compact)
    assert counts(repo)==before
    fresh=workflow.prepare(repo,owner,female,i,uuid.uuid4().hex,engine='compact_exhaustive');saved=repo.persist(fresh)
    assert saved['provenance']['request_local_preference']['preferences']
    assert repo.find_local_submission(owner,female,i,fresh.submission_key)['score_metadata']==saved['score_metadata']

def test_existing_v2_subtype_restrictions_remain_active(local_store,monkeypatch):
    client,repo,workflow,owner,male,female=local_store
    from app.domain.value_objects.verified_garment_subtype import ENVIRONMENT_KEY,PROFILE
    from app.infrastructure.workflow_runtime import configure_local_workflow
    monkeypatch.setenv(ENVIRONMENT_KEY,PROFILE)
    monkeypatch.setenv('SMART_WARDROBE_WEARER_CATEGORY_PROFILE','gender_category_subtype_v2')
    configure_local_workflow();i=intent()
    command=workflow.prepare(repo,owner,female,i,uuid.uuid4().hex,engine='compact_exhaustive')
    proof=command.local_preference.proof.to_dict()
    assert proof['eligibility']['version']=='wearer-category-eligibility-evidence-2.0.0'
    assert len(proof['eligibility']['subtype_sources'])==len(proof['sources'])
    repo.persist(command);before=counts(repo)
    # The generic upper types in this ordinary fixture have unresolved subtypes
    # for a male wearer. Optional colour cannot make those sources eligible.
    with pytest.raises(ValueError,match='No mandatory'):workflow.prepare(repo,owner,male,i,uuid.uuid4().hex)
    assert counts(repo)==before
