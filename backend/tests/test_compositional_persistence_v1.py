"""Small authenticated disposable corpus, frozen scores and independent writes."""
import json,uuid,pytest
from fractions import Fraction as F
from tests.test_local_preference_activation import enabled,post
from tests.test_request_local_persistence import (local_store,category_api,language_api,palette_api,p2_api,attribute_api,
 refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle,runtime_boundary,counts,restrict)
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.ports.assistant_runtime import assistant_service
from app.application.nlp.compositional_request_v1 import ENVIRONMENT_KEY,PROFILE
from app.application.recommendation.compositional_workflow_v1 import KEY,CompositionalProof,verify
from app.domain.value_objects.attribute_conditions import encode,digest

@pytest.fixture
def composed(enabled,monkeypatch):
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_NORMALIZATION_PROFILE','disabled')
    monkeypatch.setenv(ENVIRONMENT_KEY,PROFILE);configure_local_workflow()
    client,_,owner,male,female=enabled;repo=assistant_service().repository
    from tests.test_attribute_persistence import qualify
    ids=restrict(client,repo,['Blue T-shirt','Blue Jeans','Black Trousers'])
    qualify(client,ids['Blue T-shirt'],primary_colour='white',style=['casual'],material=['cotton'])
    qualify(client,ids['Blue Jeans'],primary_colour='blue',style=['casual'],material=['denim'])
    qualify(client,ids['Black Trousers'],primary_colour='black',style=['casual'],material=['cotton'])
    return client,repo,owner,male,female,ids

CASES=[
 ('i dont want shorts, give me trousers instead',None),
 ('i want trousers but not blue ones','Black Trousers'),
 ('pls give me a white top and black pants','Black Trousers'),
 ('i need white top, not a grey shirt',None),
 ('i want a casual outfit but no jeans','Black Trousers'),
 ('id prefer a black shirt but i need jeans','Blue Jeans'),
 ('i want trousers preferably blue but no shorts',None),
 ('dont give me anything red, i prefer blue trousers',None),
 ('i need black trousers but id prefer a white shirt','Black Trousers'),
 ('i need a shirt thats either black or white',None),
 ('black or grey trousers please','Black Trousers'),
 ('no shorts or skirts',None),
]

@pytest.mark.parametrize('raw,required_lower',CASES)
def test_complete_compositions_reference_compact_and_history(composed,raw,required_lower):
    client,repo,owner,_,female,ids=composed;outputs=[]
    cap=client.get('/api/v1/recommendations/capabilities').json()
    assert cap['compositional_input']['enabled'] and not cap['input_normalization']['enabled']
    for engine in ('reference','compact_exhaustive'):
        assistant_service().input_composition.engine=engine
        key=uuid.uuid4().hex;reply=post(client,female,raw,key)
        assert reply.status_code==201,reply.json().get('outcome')
        v=reply.json();assert v['request_text']==raw and not v['replayed']
        proof=CompositionalProof(encode(v['provenance'][KEY]));verify(proof,owner,female,text=raw)
        from app.application.recommendation.decision_score_codec import score_from_json
        score=score_from_json(json.dumps(v['score_metadata']))
        assert score.weights==(F(3,5),F(1,5),F(1,5)) and score.total==sum(w*c.contribution for w,c in zip(score.weights,(score.request_match,score.compatibility,score.preference)))
        assert next(i['garment_id'] for i in v['items'] if i['garment_role']=='upper')==ids['Blue T-shirt']
        if required_lower:assert next(i['garment_id'] for i in v['items'] if i['garment_role']=='lower')==ids[required_lower]
        if proof.to_dict()['mode']=='soft':
            d=proof.to_dict()['evaluation']['decision']
            def fraction(x):return F(x['numerator'],x['denominator'])
            baseline=d['baseline']['score'];selected=d['selected']['score']
            assert fraction(baseline['total'])-fraction(selected['total'])<=F(1,50)
            assert v['scoring_display']['continuation_available'] is False
        outputs.append((v['items'],v['score_metadata'],proof.to_dict()['evaluation']['decision']))
        # One real replay/history check per expression; no extra ranking.
        if engine=='reference':
            before=counts(repo);again=post(client,female,raw,key)
            assert again.status_code==200 and again.json()['id']==v['id'] and again.json()['replayed']
            history=client.get('/api/v1/chats/'+v['chat_id'],headers={'X-Wardrobe-Profile-Id':female})
            assert history.status_code==200 and history.json()['request_text']==raw
            assert history.json()['recommendation']['scoring_display']==v['scoring_display']
            assert counts(repo)==before
    assert outputs[0]==outputs[1]

@pytest.mark.parametrize('change',['raw','wearer','typed','p2','c2','continuation'])
def test_conflicts_and_unsupported_combinations_do_not_write(composed,change):
    client,repo,_,male,female,_=composed;key=uuid.uuid4().hex;raw='I need trousers preferably blue but no shorts'
    root=post(client,female,raw,key);assert root.status_code==201,root.json().get('outcome')
    before=counts(repo);options={};wearer=female
    if change=='raw':raw=raw.upper()
    elif change=='wearer':wearer=male
    elif change=='typed':options['attribute_conditions']=root.json()['provenance'][KEY]['intent']['hard_intent']['conditions']
    elif change=='p2':options['preference_profile']='attribute_preference_decision_v2'
    elif change=='c2':options['compatibility_profile']='recorded_palette_compatibility_v1'
    else:options['refinement']={'version':'assistant-refinement-request-1.0.0','kind':'alternative','parent_recommendation_id':root.json()['id']}
    assert post(client,wearer,raw,key,**options).status_code==409
    assert counts(repo)==before
    if change in ('typed','p2','c2'):
        assert post(client,female,raw,**options).status_code==422 and counts(repo)==before
    if change=='continuation':
        r=post(client,female,raw,**options);assert r.status_code==422 and r.json()['context_reason']=='compositional_continuation_unavailable'
        assert counts(repo)==before

@pytest.mark.parametrize('stage',['compositional_revalidated','metadata','before_commit'])
def test_atomic_rollback(composed,stage):
    client,repo,_,_,female,_=composed;before=counts(repo)
    def fail(where,conn):
        if where==stage:raise RuntimeError('Disposable compositional rollback control')
    repo.checkpoint=fail
    assert post(client,female,'I need trousers preferably blue but no shorts').status_code==503
    assert counts(repo)==before

def test_locked_revalidation_does_not_trust_first_pass(composed):
    client,repo,_,_,female,_=composed;before=counts(repo)
    def change(stage,conn):
        if stage=='compositional_before_revalidation':conn.execute("UPDATE garments SET name='changed in disposable lock' WHERE name='Black Trousers'")
    repo.checkpoint=change
    result=post(client,female,'I need trousers preferably blue but no shorts')
    assert result.status_code==409 and result.json()['outcome']=='WardrobeChanged'
    assert counts(repo)==before
    with repo._connect() as conn:assert not conn.execute("SELECT 1 FROM garments WHERE name='changed in disposable lock'").fetchone()

def test_hard_unknown_optional_unknown_and_actual_conflict(enabled,monkeypatch):
    from tests.test_local_preference_diagnostics import clear_fixture_primary_sources
    monkeypatch.setenv(ENVIRONMENT_KEY,PROFILE);configure_local_workflow()
    client,_,_,_,female=enabled;repo=assistant_service().repository
    restrict(client,repo,['Blue T-shirt','Black Trousers']);clear_fixture_primary_sources(repo)
    before=counts(repo)
    hard=post(client,female,'I need black trousers but no shorts')
    assert hard.status_code==200 and hard.json()['outcome']=='InsufficientEvidence'
    assert counts(repo)==before
    conflicting=post(client,female,'I need black trousers but no shorts, I prefer blue trousers')
    assert conflicting.status_code==200 and conflicting.json()['outcome']=='InsufficientEvidence'
    assert conflicting.json()['optional_resolution']=='ContradictedByHard'
    assert conflicting.json()['context_reason']=='hard_evidence_unknown_conflicting_preference'
    assert counts(repo)==before
    soft=post(client,female,'I need trousers but no shorts, i prefer black trousers')
    assert soft.status_code==201,soft.json().get('outcome')
    assert soft.json()['scoring_display']['decision']['selected_optional']['state']=='Unverifiable'
    before=counts(repo);contradiction=post(client,female,'I need trousers but no trousers')
    assert contradiction.status_code==422 and contradiction.json()['outcome']=='AttributeConflict' and counts(repo)==before

def test_old_1_7_1_8_receipts_and_new_history_with_flag_off(composed,monkeypatch):
    client,repo,_,_,female,_=composed;raw='I need trousers preferably blue but no shorts';key=uuid.uuid4().hex
    root=post(client,female,raw,key);assert root.status_code==201
    monkeypatch.setenv(ENVIRONMENT_KEY,'disabled');configure_local_workflow()
    before=counts(repo);assert post(client,female,raw,key).status_code==200 and counts(repo)==before
    old_key=uuid.uuid4().hex;old=post(client,female,"I'd prefer black trousers.",old_key);assert old.status_code==201
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_NORMALIZATION_PROFILE','bounded_natural_input_v1');configure_local_workflow()
    nk=uuid.uuid4().hex;normal=post(client,female,'id prefer black trousers',nk);assert normal.status_code==201
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_NORMALIZATION_PROFILE','disabled');monkeypatch.setenv(ENVIRONMENT_KEY,PROFILE);configure_local_workflow()
    for text,k,expected in [(raw,key,root),("I'd prefer black trousers.",old_key,old),('id prefer black trousers',nk,normal)]:
        r=post(client,female,text,k);assert r.status_code==200 and r.json()['provenance']==expected.json()['provenance']

@pytest.mark.parametrize('change',['map','winner','budget','missing_proof','scalar'])
def test_proof_or_stored_metadata_tamper_is_rejected(composed,change):
    client,repo,owner,_,female,_=composed;root=post(client,female,'I need trousers preferably blue but no shorts')
    assert root.status_code==201;v=root.json();proof=json.loads(json.dumps(v['provenance'][KEY]))
    if change in ('map','winner','budget'):
        if change=='map':proof['intent']['normalization']['character_map'][0]=[0,0]
        elif change=='winner':proof['evaluation']['decision']['selected']['key'][0][1]=str(uuid.uuid4())
        else:proof['evaluation']['resources']['optional_policy']['T_loss']='1'
        proof['revision']='';proof['revision']=digest(proof)
        with pytest.raises(ValueError):verify(CompositionalProof(encode(proof)),owner,female)
    else:
        with repo._connect() as conn:
            if change=='missing_proof':conn.execute("UPDATE recommendation_metadata SET provenance_json='{}' WHERE recommendation_id=?",(v['id'],))
            else:conn.execute('UPDATE recommendations SET total_score=0.123 WHERE id=?',(v['id'],))
        r=client.get('/api/v1/chats/'+v['chat_id'],headers={'X-Wardrobe-Profile-Id':female})
        assert r.status_code==503

def test_unimplemented_context_and_modifiers_never_become_neutral(composed):
    client,repo,_,_,female,_=composed;before=counts(repo)
    expected=[('gimme an outfit for a job interview','compositional_context_role_required'),
        ('im going shopping pls suggest an outfit','compositional_context_contract_unavailable'),
        ('can u recommend something thats not too formal','unmodeled_compositional_modifier'),
        ('i need an outfit for a wedding but nothing too flashy','unmodeled_compositional_modifier')]
    for text,reason in expected:
        r=post(client,female,text);assert r.status_code==422 and r.json()['context_reason']==reason,r.json()
        assert counts(repo)==before

def test_cross_wearer_and_foreign_history_are_not_reassociated(composed):
    client,repo,_,male,female,_=composed;root=post(client,female,'I need trousers preferably blue but no shorts');assert root.status_code==201
    r=client.get('/api/v1/chats/'+root.json()['chat_id'],headers={'X-Wardrobe-Profile-Id':male})
    assert r.status_code==404
    from app.infrastructure.security import current_user_id
    from app.main import app
    app.dependency_overrides[current_user_id]=lambda:str(uuid.uuid4())
    try:assert client.get('/api/v1/chats/'+root.json()['chat_id']).status_code in (403,404)
    finally:app.dependency_overrides.pop(current_user_id,None)

def test_default_and_mutually_exclusive_opt_ins(enabled,monkeypatch):
    client,_,_,_,_=enabled
    assert client.get('/api/v1/recommendations/capabilities').json()['compositional_input']['enabled'] is False
    monkeypatch.setenv(ENVIRONMENT_KEY,PROFILE);monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_NORMALIZATION_PROFILE','bounded_natural_input_v1')
    with pytest.raises(ValueError,match='disabled 1.8'):configure_local_workflow()

@pytest.mark.parametrize('roles,names',[
 (['upper','lower'],['Blue T-shirt','Black Trousers']),
 (['upper','lower','outerwear'],['Blue T-shirt','Black Trousers','Grey Jacket']),
 (['one_piece'],['Navy Dress']),(['one_piece','outerwear'],['Navy Dress','Grey Jacket'])])
def test_four_structures_and_unmatched_optional_scope(enabled,monkeypatch,roles,names):
    monkeypatch.setenv(ENVIRONMENT_KEY,PROFILE);configure_local_workflow()
    client,_,_,_,female=enabled;repo=assistant_service().repository
    restrict(client,repo,names);results=[]
    for engine in ('reference','compact_exhaustive'):
        assistant_service().input_composition.engine=engine
        reply=post(client,female,'I prefer purple top');assert reply.status_code==201,reply.json().get('outcome')
        v=reply.json();assert [i['garment_role'] for i in v['items']]==roles
        decision=v['scoring_display']['decision'];assert decision['selected']['key']==decision['baseline']['key']
        results.append((v['items'],v['score_metadata'],decision))
    assert results[0]==results[1]

def test_male_eligibility_and_no_soft_legacy_winner(enabled,monkeypatch):
    client,_,_,male,_=enabled
    before=post(client,male,'Recommend an outfit.');assert before.status_code==201
    monkeypatch.setenv(ENVIRONMENT_KEY,PROFILE);configure_local_workflow()
    after=post(client,male,'Recommend an outfit.');assert after.status_code==201
    assert after.json()['items']==before.json()['items'] and after.json()['score_metadata']==before.json()['score_metadata']
    assert all(i['category'] not in ('skirt','vest_dress') for i in after.json()['items'])

def test_source_bounds_and_registered_older_policy_cannot_change_qualification(composed):
    from pathlib import Path
    client,_,owner,_,female,_=composed
    root=post(client,female,'I need trousers preferably blue but no shorts');assert root.status_code==201
    source=root.json()['provenance'][KEY]
    for kind in ('preferences','policy'):
        proof=json.loads(json.dumps(source))
        if kind=='preferences':proof['evaluation']['preferences']=[{}]*101
        else:
            older=json.loads((Path(__file__).parent/'fixtures/legacy_attribute_evidence_policy.v1.json').read_text())
            assert older!=proof['evaluation']['attribute_policy']
            proof['evaluation']['attribute_policy']=older
        proof['revision']='';proof['revision']=digest(proof)
        with pytest.raises(ValueError):verify(CompositionalProof(encode(proof)),owner,female)

@pytest.mark.parametrize('raw,lower',[
 ('PLS ID PREFER A BLACK SHIRT BUT PLEASE I NEED JEANS!!!','Blue Jeans'),
 ('pls dont give me anything red, please i prefer blue trousers',None),
])
def test_polite_soft_and_negative_compositions(composed,raw,lower):
    test_complete_compositions_reference_compact_and_history(composed,raw,lower)
