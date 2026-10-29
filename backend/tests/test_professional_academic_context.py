"""Approved Phase 3 API labels; no graduation activation or private data."""
from dataclasses import replace
import json
import os
from pathlib import Path
import uuid
import pytest
from app.application.nlp.general_context_interpreter import GeneralContextInterpreter
from app.application.recommendation.general_context_evaluator import GeneralContextEvaluator
from app.domain.value_objects.general_context_evidence import KEY, project_appearance_evidence
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.security import issue_access_token
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.ports.assistant_runtime import assistant_service
from tests.test_contextual_wedding import reviewed, patch, review
from tests.test_suitability_controls import patch_tags
from tests.test_release_configuration import release, submit
from tests.test_forward_style_semantics import lifecycle

LABELS=json.loads((Path(__file__).with_name('fixtures')/'professional_academic_labels.v1.json').read_text(encoding='utf-8'))
ACTIVE=[c for c in LABELS['cases'] if c['scope']=='proposed_phase3']


@pytest.fixture
def professional_api(release,monkeypatch):
    monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE','general_context_v1')
    configure_local_workflow()
    return release


def appearance(client,gid,condition='clean_intact',features=None,withdraw=False):
    row=next(g for g in client.get('/api/v1/wardrobe/garments').json() if g['id']==gid)
    value={'withdraw':True} if withdraw else {'construction_features':features or {'collared_neckline':True,'tailored_cut':True,'structured_shape':True},'condition_observation':condition}
    return client.post('/api/v1/wardrobe/garments/'+gid+'/contextual-suitability',json={'revision':row['appearance_edit']['revision'],'appearance_review':value})


def write_result(case,response,result):
    folder=os.environ.get('SMART_WARDROBE_PROFESSIONAL_EVIDENCE')
    if folder:
        target=Path(folder)/('case-'+case['id']+'.json');assert not target.exists()
        target.write_text(json.dumps({'label':case,'http_status':response.status_code if response is not None else None,'response':result},indent=2)+'\n',encoding='utf-8')


@pytest.mark.parametrize('case',ACTIVE,ids=[c['id'] for c in ACTIVE])
def test_approved_api_matrix(professional_api,monkeypatch,case):
    client,create=professional_api
    identifier,fixture,text=case['id'],case['fixture'],case['request']
    style='casual' if fixture.startswith('A1') else 'smart casual'
    ids=[]
    def add(category='vest_dress',appearance_review=False):
        gid=create([style]);patch(client,gid,{'category':category,'primary_colour':'blue'})
        assert review(client,gid,review_style=True).status_code==200
        assert patch_tags(client,gid,[]).status_code==200
        if appearance_review: assert appearance(client,gid).status_code==200
        ids.append(gid);return gid
    base=add('long_sleeve_top' if identifier=='G05' else 'vest_dress',fixture.startswith(('I0','I4')) or identifier in ('P02','P03','P04','P06','P07'))
    if identifier in ('G06','G07','G08'):
        add('long_sleeve_top',True);add('trousers',True);outer=add('long_sleeve_outwear',True)
        if identifier=='G07': assert patch_tags(client,outer,['rec:v1:occasion:work:deny']).status_code==200
        if identifier=='G08': assert appearance(client,outer,withdraw=True).status_code==200
    tags={
      'D01':['rec:v1:occasion:work:deny'],'D02':['rec:v1:occasion:work:deny'],
      'D03':['rec:v1:occasion:work:allow'],'D04':['rec:v1:occasion:work:allow','rec:v1:occasion:work:deny'],
      'D05':['rec:v1:occasion:campus:deny'],'D06':['rec:v1:occasion:campus:deny'],'D07':['rec:v1:occasion:campus:allow'],
      'D08':['rec:v1:occasion:work:deny'],'D09':['rec:v1:occasion:campus:deny'],'D10':['rec:v1:formality:smart_casual:deny'],
      'D11':['rec:v1:formality:smart_casual:allow'],'D12':['rec:v1:formality:smart_casual:deny'],
      'D13':['rec:v1:occasion:work:deny','rec:v2:occasion:work:allow'],
      'D14':['rec:v1:occasion:work:allow','rec:v2:occasion:work:allow'],
      'D15':['rec:v1:occasion:interview:allow'],'D16':['rec:v1:occasion:date:deny']}.get(identifier,[])
    assert patch_tags(client,base,tags).status_code==200
    if identifier=='D16': assert review(client,base,wedding_choice='allow').status_code==200
    if identifier in ('I03','I04'):
        assert appearance(client,base,features={'collared_neckline':None,'tailored_cut':None,'structured_shape':False if identifier=='I04' else None}).status_code==200
    if identifier=='I05': assert appearance(client,base,'needs_attention').status_code==200
    if identifier=='I06': assert appearance(client,base,'unknown').status_code==200
    if identifier in ('I07','A08'): patch(client,base,{'category':'sling_dress'})
    if identifier=='I08':
        with db.connection() as conn:
            attrs=json.loads(conn.execute('SELECT additional_attributes FROM garments WHERE id=?',(base,)).fetchone()[0])
            attrs[KEY]['condition_observation']='unknown'
            conn.execute('UPDATE garments SET additional_attributes=? WHERE id=?',(json.dumps(attrs),base))
    if identifier=='I09': assert appearance(client,base,withdraw=True).status_code==200
    if identifier=='I10':
        patch(client,base,{'attributes':{'style':['classic']}});assert review(client,base,review_style=True).status_code==200
    if identifier in ('A07','D07'): assert review(client,base,review_style=False).status_code==200
    if identifier in ('G01','G02'):
        with db.connection() as conn:
            conn.execute('UPDATE garments SET status=? WHERE id=?',('archived' if identifier=='G01' else 'unavailable',base))
    if identifier=='G03':
        db.ensure_user('foreign-owner');client.headers['Authorization']='Bearer '+issue_access_token('foreign-owner')
    if identifier=='G04':
        with db.connection() as conn: conn.execute('UPDATE garments SET processing_item_id=NULL WHERE id=?',(base,))
    key=uuid.uuid4().hex
    if identifier=='P01':
        monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE','wedding_guest_v1');configure_local_workflow()
        text="I'm going to a wedding"
        _,previous=submit(client,text,key);assert previous['outcome']=='Selected'
        monkeypatch.setenv('SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE','general_context_v1');configure_local_workflow()
    if identifier in ('P02','P04'):
        text="I'm attending a job interview as a candidate; the dress code is smart casual."
        _,previous=submit(client,text,key);assert previous['outcome']=='Selected'
        if identifier=='P02':
            configure_local_workflow()
        else: text='Suggest an outfit for a job interview as a candidate; the dress code is smart casual.'
    if identifier=='P03':
        repository=assistant_service().repository;original=repository.persist_assistant
        def change(command):
            assert appearance(client,base,withdraw=True).status_code==200
            return original(command)
        monkeypatch.setattr(repository,'persist_assistant',change)
    if identifier=='P08':
        row=next(g for g in client.get('/api/v1/wardrobe/garments').json() if g['id']==base)
        bad=client.post('/api/v1/wardrobe/garments/'+base+'/contextual-suitability',json={'revision':'0'*64,'appearance_review':{'withdraw':True}})
        assert bad.status_code==409
        result={'outcome':'Controlled review outcomes','stale_status':bad.status_code,'owned_revision_present':bool(row['appearance_edit']['revision']),
                'additional_scope_evidence':'test_attribute_evidence_review: independent-owner denial, trigger rollback, validation and old action preservation'}
        write_result(case,bad,result);return
    if identifier=='P07':
        from tests.test_professional_academic_equivalence import preparation_observation
        counters=preparation_observation('interview',monkeypatch)
        write_result(case,None,{'outcome':'Selected','method':'pure kernel with 100 snapshots; no HTTP timing benchmark','counters':counters})
        return
    response,result=submit(client,text,key)
    write_result(case,response,result)
    assert result['outcome']==case['proposed_outcome'],result
    if identifier in ('P01','P02'):
        assert result['replayed'] and result['recommendation']==previous['recommendation']
    if identifier=='P03':
        with db.connection() as conn: assert conn.execute('SELECT count(*) FROM nlp_chats').fetchone()[0]==0
    if result['outcome']=='Selected' and identifier not in ('P01','P02'):
        proof=result['recommendation']['provenance']['general_context']
        assert proof['version']=='general-context-explanation-1.2.0'
        assert proof['role'] in ('candidate','interviewer','presenter','attendee')
        assert result['score_metadata']['total']==({'numerator':4,'denominator':5} if identifier in ('G06','G07','G08') else {'numerator':7,'denominator':10})
        if proof['parent_negative']=='work':
            assert all(m['appearance_current'] for m in proof['members'])
        if identifier=='D12': assert proof['formality'] is None


def test_graduation_assessment_labels_stay_outside_implementation():
    assert len(ACTIVE)==76
    assert sum(c['scope']=='graduation_assessment_only' for c in LABELS['cases'])==5
    for text in ("I'm attending a graduation", "I'm attending a graduation as a guest; the dress code is smart casual"):
        result=GeneralContextInterpreter().interpret(text)
        assert result.structured_request and not GeneralContextEvaluator().supports(result.structured_request)
    assert GeneralContextInterpreter().interpret("I'm attending a graduation ceremony").status=='UnsupportedRequest'
