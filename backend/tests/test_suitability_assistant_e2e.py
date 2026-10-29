"""J-4 real confirmed wardrobes, authenticated HTTP, actual composition; no model claims."""
import json
import os
from pathlib import Path
import uuid
import pytest
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.persistence import active_preference_query_adapter as pref
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.infrastructure.security import issue_access_token
from app.application.ports.assistant_runtime import assistant_service, configure_assistant_service
from app.application.nlp.nlp_interpreter import NLPInterpreter
from tests.test_forward_style_semantics import lifecycle
from tests.test_suitability_controls import garment,patch_tags,tag

VALUES=[('occasion',v) for v in ('campus','work','casual_outing','shopping','dinner','party','date','travel')]+[('formality',v) for v in ('casual','smart_casual')]
TEXT={'casual_outing':'a casual outing','smart_casual':'smart-casual'}

def sentence(field,value):
    return 'Suggest an '+TEXT.get(value,value)+' outfit' if field=='formality' else 'Suggest an outfit for '+TEXT.get(value,value)

@pytest.fixture
def integrated(lifecycle,monkeypatch):
    client,create=lifecycle
    previous=assistant_service()
    monkeypatch.setattr(pref,'DATABASE_PATH',db.DATABASE_PATH)
    from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
    # Imported default argument otherwise points at the process-level test DB.
    monkeypatch.setattr(SqliteRecommendationRepository.__init__,'__defaults__',(db.DATABASE_PATH,None))
    for key,value in {'ASSISTANT_ENABLED':'true','ASSISTANT_SUITABILITY_ENABLED':'true','ASSISTANT_EXECUTION_ENGINE':'compact_exhaustive','ASSISTANT_SCORING_PROFILE':'compatibility_deferred'}.items():
        monkeypatch.setenv('SMART_WARDROBE_'+key,value)
    configure_local_workflow()
    db.ensure_user('style-owner')
    db.ensure_user('another-owner')
    client.headers['Authorization']='Bearer '+issue_access_token('style-owner')
    assert assistant_service().execution_engine=='compact_exhaustive'
    assert assistant_service().scoring_profile=='compatibility_deferred'
    yield client,create
    configure_assistant_service(previous)

def submit(client,text,key=None):
    response=client.post('/api/v1/recommendations?pipeline=integrated',json={'request_text':text,'submission_key':key or uuid.uuid4().hex})
    result=response.json()
    evidence=os.getenv('SMART_WARDROBE_SUITABILITY_EVIDENCE')
    if evidence:
        with Path(evidence).open('a',encoding='utf-8') as log:
            log.write(json.dumps({'request':text,'http':response.status_code,'result':result})+'\n')
    return response,result

def counts():
    with db.connection() as c:return tuple(c.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('nlp_chats','recommendations','recommendation_items'))

def make(client,create,category='vest_dress',tags=None):
    gid=create(['vintage'])
    assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'category':category,'primary_colour':'blue'}).status_code==200
    assert patch_tags(client,gid,tags or ['ordinary note']).status_code==200
    return gid

@pytest.mark.parametrize('field,value',VALUES)
@pytest.mark.parametrize('state',['allow','deny','unknown','conflict','malformed'])
def test_all_values_and_evidence_through_compact_http(integrated,field,value,state):
    client,create=integrated
    tags=['ordinary note']
    if state!='unknown':tags.append(tag(field,value,'deny' if state=='deny' else 'allow'))
    if state=='conflict':tags.append(tag(field,value,'deny'))
    if state=='malformed':tags.append('rec:v1:'+field+':'+value+':maybe')
    gid=make(client,create,tags=tags);text=sentence(field,value)
    interpreted=NLPInterpreter().interpret(text)
    assert interpreted.status=='Supported'
    assert getattr(interpreted.structured_request,field)==value
    response,result=submit(client,text)
    expected={'allow':'Selected','deny':'NoMatchingCandidates','unknown':'InsufficientEvidence','conflict':'InsufficientEvidence','malformed':'InsufficientEvidence'}[state]
    assert result['outcome']==expected,result
    if state=='allow':
        assert response.status_code==201 and result['complete']
        assert [i['garment_id'] for i in result['items']]==[gid]
        assert result['request_match_score']==1 and result['total_score']==.7
        assert result['compatibility_score'] is None
        assert counts()==(1,1,1)
    else:assert counts()==(0,0,0)

@pytest.mark.parametrize('categories,phrase',[
    (['short_sleeve_top','trousers'],'including a top and trousers'),
    (['short_sleeve_top','trousers','long_sleeve_outwear'],'including a top and trousers and outerwear'),
    (['vest_dress'],'including a vest dress'),
    (['vest_dress','long_sleeve_outwear'],'including a vest dress and outerwear')])
def test_four_structures_combined_five_fields(integrated,categories,phrase):
    client,create=integrated
    ids=[make(client,create,c,[tag(),tag('formality','casual')]) for c in categories]
    text='Suggest a casual outfit for campus with vintage style using blue colours with '+phrase
    interpreted=NLPInterpreter().interpret(text)
    assert interpreted.status=='Supported',interpreted
    req=interpreted.structured_request
    assert req.occasion=='campus' and req.formality=='casual' and req.style=='vintage' and req.colours==('blue',) and req.garment_categories
    response,result=submit(client,text)
    assert response.status_code==201,result
    assert set(i['garment_id'] for i in result['items'])==set(ids)
    assert result['request_match_score']==1 and result['total_score']==.7
    # Every member, including optional outerwear, is rechecked independently.
    for item in result['items']:
        tags=garment(client,item['garment_id'])['custom_tags']
        assert tag() in tags and tag('formality','casual') in tags

@pytest.mark.parametrize('categories',[['short_sleeve_top','trousers'],['vest_dress','long_sleeve_outwear']])
def test_deny_over_unknown_across_members(integrated,categories):
    client,create=integrated
    make(client,create,categories[0],[tag(decision='deny')]);make(client,create,categories[1])
    text='Suggest an outfit for campus'+(' including outerwear' if categories[0]=='vest_dress' else '')
    _,result=submit(client,text)
    assert result['outcome']=='NoMatchingCandidates',result
    assert counts()==(0,0,0)

def test_multiple_candidates_current_state_history_and_retry(integrated,monkeypatch):
    client,create=integrated
    good=make(client,create,tags=[tag()]);denied=make(client,create,tags=[tag(decision='deny')]);missing=make(client,create)
    text='Suggest an outfit for campus';key='same-completed-key'
    _,first=submit(client,text,key)
    assert first['outcome']=='Selected' and [i['garment_id'] for i in first['items']]==[good]
    historical=first['recommendation']
    assert patch_tags(client,good,[tag(decision='deny')]).status_code==200
    _,fresh=submit(client,text)
    assert fresh['outcome']=='InsufficientEvidence' and counts()==(1,1,1)
    # Startup captures evaluator selection; mutating environment alone is not hot reload.
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED','false')
    _,still=submit(client,text)
    assert still['outcome']=='InsufficientEvidence'
    configure_local_workflow()
    _,off=submit(client,text);assert off['outcome']=='PolicyUnavailable'
    _,replay=submit(client,text,key)
    assert replay['replayed'] and replay['id']==first['id']
    assert replay['score_metadata']==first['score_metadata']
    assert replay['provenance']==first['provenance']
    assert replay['items']==historical['items']
    assert counts()==(1,1,1)
    client.headers['Authorization']='Bearer '+issue_access_token('another-owner')
    _,foreign=submit(client,text,key)
    assert foreign['outcome']=='PolicyUnavailable' and counts()==(1,1,1)

@pytest.mark.parametrize('text,expected',[
 ('Suggest an outfit for exercise','PolicyUnavailable'),('Suggest a formal outfit','PolicyUnavailable'),
 ('What is the weather forecast?','UnsupportedRequest'),
 ('Suggest a blue top and black trousers outfit','UnsupportedRequest'),
 ('Suggest an outfit for campus with red colours','NoMatchingCandidates'),
 ('Suggest an outfit for campus with classic style','NoMatchingCandidates')])
def test_unsupported_and_other_mandatory_failures(integrated,text,expected):
    client,create=integrated;make(client,create,tags=[tag()])
    _,result=submit(client,text);assert result['outcome']==expected,result
    assert counts()==(0,0,0)

@pytest.mark.parametrize('enabled,suitable',[('true','false'),('false','true'),('TRUE','TRUE'),('1','1')])
def test_actual_composition_flags(integrated,monkeypatch,enabled,suitable):
    client,create=integrated;make(client,create,tags=[tag()])
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_ENABLED',enabled)
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED',suitable)
    configure_local_workflow()
    response,result=submit(client,'Suggest an outfit for campus')
    expected='IntegrationDisabled' if enabled.lower()!='true' else 'Selected' if suitable.lower()=='true' else 'PolicyUnavailable'
    assert result['outcome']==expected,result
    assert counts()==((1,1,1) if expected=='Selected' else (0,0,0))
    # Disabled case deliberately uses explicit integrated route: legacy remains untouched.


@pytest.mark.parametrize('index',[0,1,2])
@pytest.mark.parametrize('state',['allow','deny','unknown','conflict','malformed','deny_and_unknown'])
def test_each_member_aggregate_including_outerwear(integrated,index,state):
    client,create=integrated
    for position,category in enumerate(['short_sleeve_top','trousers','long_sleeve_outwear']):
        tags=[tag(),tag('formality','casual')]
        if position==index:
            if state=='deny':tags=[tag(decision='deny'),tag('formality','casual')]
            elif state=='unknown':tags=[tag('formality','casual')]
            elif state=='conflict':tags.append(tag(decision='deny'))
            elif state=='malformed':tags.append('rec:v1:occasion:campus:maybe')
            elif state=='deny_and_unknown':tags=[tag(decision='deny')]
        make(client,create,category,tags)
    # Maximum colour preference and matching style cannot rescue a mandatory failure.
    with db.connection() as c:c.execute("INSERT INTO user_preferences VALUES('p','style-owner','colours','{\"values\":[\"blue\"]}',1,'test',1,'now','now')")
    _,result=submit(client,'Suggest a casual outfit for campus with vintage style using blue colours with a top and trousers and outerwear')
    expected='Selected' if state=='allow' else 'NoMatchingCandidates' if state in ('deny','deny_and_unknown') else 'InsufficientEvidence'
    assert result['outcome']==expected,result
    assert counts()==((1,1,3) if state=='allow' else (0,0,0))
    if state=='allow':assert result['total_score']==1


def test_exhaustive_multiple_valid_and_invalid_candidates(integrated):
    client,create=integrated
    valid=[make(client,create,tags=[tag()]) for _ in range(2)]
    make(client,create,tags=[tag(decision='deny')]);make(client,create)
    _,result=submit(client,'Suggest an outfit for campus')
    assert result['outcome']=='Selected'
    assert result['provenance']['scored_count']==2
    assert result['items'][0]['garment_id'] in valid
    assert counts()==(1,1,1)


def test_other_occasion_and_hex_do_not_imply_positive_evidence(integrated):
    client,create=integrated
    gid=make(client,create,tags=[tag('occasion','dinner')])
    _,result=submit(client,'Suggest an outfit for campus')
    assert result['outcome']=='InsufficientEvidence'
    assert patch_tags(client,gid,[tag()]).status_code==200
    assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'primary_colour':'#123456'}).status_code==200
    _,result=submit(client,'Suggest an outfit for campus with blue colours')
    assert result['outcome']=='InsufficientEvidence' and counts()==(0,0,0)


def test_unsupported_combined_colour_binding_keeps_actual_outcome(integrated):
    client,create=integrated;make(client,create,tags=[tag(),tag('formality','casual')])
    _,result=submit(client,'Suggest a casual outfit for campus with vintage style and blue colours including a vest dress')
    assert result['outcome']=='UnsupportedRequest' and result['reason']=='garment_colour_binding'
    assert counts()==(0,0,0)


def test_inflight_capture_survives_test_only_composition_rebind(integrated,monkeypatch):
    client,create=integrated;make(client,create,tags=[tag()])
    selected_service=assistant_service()
    original=selected_service.preference_query.get_active_preferences
    def switch_after_capture(owner):
        rows=original(owner)
        monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED','false')
        configure_local_workflow()
        return rows
    monkeypatch.setattr(selected_service.preference_query,'get_active_preferences',switch_after_capture)
    text='Suggest an outfit for campus';key='captured-inflight'
    _,first=submit(client,text,key)
    assert first['outcome']=='Selected' and first['provenance']['suitability_policy']
    _,later=submit(client,text)
    assert later['outcome']=='PolicyUnavailable'
    _,retry=submit(client,text,key)
    assert retry['outcome']=='Selected' and retry['replayed']
    assert retry['id']==first['id'] and retry['score_metadata']==first['score_metadata']
    assert retry['provenance']==first['provenance'] and counts()==(1,1,1)
