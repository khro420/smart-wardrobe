"""Versioned hosiery, explicit correction, model grounding and rubric controls."""
import copy,json
import pytest
from pydantic import ValidationError
from tests.test_outfit_review_observation import prediction,item,fact,observation,authority
from tests.test_outfit_review_prototype import occasion
from app.application.outfit_review import observation_v11 as visual,confirmation_v11 as flow,assessment
from app.application.outfit_review import confirmation as original
from app.application.outfit_review.contract import digest


def modern(shoes=False):
    value=prediction();value.update(version=visual.VERSION,feet_observation='shoes_visible' if shoes else 'socks_only_visible',footwear_visibility='visible' if shoes else 'not_visible')
    specs=[('jersey','upper',['black','red'],[80,100,900,400]),('shorts','lower',['black'],[100,410,850,650]),('socks','hosiery',['white'],[150,660,800,780])]
    if shoes:specs.append(('footwear','footwear',['white'],[130,790,840,980]))
    value['items']=[item(f'g{n}',category=category,role=role,colours={'state':'observed','values':colours},region={'xyxy':box},
                         pattern=fact('plain'),style=fact('sporty'),unit='pair' if category=='socks' else 'footwear_pair' if category=='footwear' else 'single') for n,(category,role,colours,box) in enumerate(specs,1)]
    return value


def obs(value=None):
    value=value or modern();base=observation()
    return visual.Observation(image=base.image,run=base.run,raw_response=json.dumps(value),prediction=visual.parse_prediction(json.dumps(value)))


def confirmed(value=None):
    source=obs(value);review=flow.begin(source,authority(source))
    return flow.confirm(review,authority(source),digest(review),inventory_reviewed=True)


def judgments(confirmation,anchors=None):
    p,facts,aliases=assessment.catalog(confirmation)
    fields=[('category','style'),('colours',),('category','style'),('pattern',)]
    reasons=['activity_alignment','palette_contrast','style_alignment','pattern_balance']
    anchors=anchors or ['coherent','strong','coherent','mixed']
    return {'version':'outfit-review-judgments-1.0.0','dimensions':[
        {'dimension':name,'anchor':anchor,'reason':reason,'evidence_refs':[f'{alias}.{field}' for alias in aliases for field in group]}
        for name,anchor,reason,group in zip(assessment.DIMENSIONS,anchors,reasons,fields)],
        'suggestions':[{'action':'repeat_recorded_colour','item_refs':['item1','item2']}]}


def test_legacy_reader_roundtrips_remain_unchanged():
    source=observation();review=original.begin(source,authority(source));proof=original.confirm(review,authority(source),digest(review),inventory_reviewed=True)
    assert visual.parse_observation(source.model_dump_json())==source
    assert flow.parse_confirmation(proof.model_dump_json())==proof
    assert flow.parse_confirmation(proof.model_dump_json()).model_dump_json()==proof.model_dump_json()


def test_jersey_shorts_socks_are_not_visible_shoes_and_need_no_shoe_subtype_guess():
    source=obs()
    assert not visual.issues(source.prediction)
    proof=confirmed()
    assert flow.parse_confirmation(proof.model_dump_json())==proof
    assert proof.review.original.prediction.items[2].category=='socks'
    assert proof.review.original.prediction.footwear_visibility=='not_visible'
    assert not assessment.evidence_requirements(proof.review.original.prediction,occasion('Library'))['occasion_suitability'][0]


def test_conflicting_foot_region_is_refused_until_explicitly_corrected():
    value=modern(shoes=True);value['feet_observation']='socks_only_visible'
    source=obs(value);review=flow.begin(source,authority(source))
    assert 'feet_observation_conflict' in flow.confirmation_issues(review)
    with pytest.raises(ValueError):flow.confirm(review,authority(source),digest(review),inventory_reviewed=True)


def test_category_correction_records_role_and_alternatives_without_other_repairs():
    value=modern();value['items'][0].update(category='jersey',role='lower',category_alternatives=['shirt','jacket'],unit='unresolved')
    source=obs(value);review=flow.begin(source,authority(source));before=digest(source)
    value['items'][0].update(role='upper',category_alternatives=[])
    changed=visual.parse_prediction(json.dumps(value))
    review=flow.revise(review,authority(source),digest(review),changed,(flow.Correction(operation='replace_item',subject='g1',reason='I explicitly confirmed the jersey type.'),))
    assert 'g1:unresolved_identity' in flow.confirmation_issues(review)
    assert digest(review.original)==before
    assert flow.current(review).items[0].colours==source.prediction.items[0].colours
    assert flow.provenance(review)['g1.role']=='user_correction_not_model_verified'
    assert flow.provenance(review)['g1.colours']=='ai_prediction_user_reviewed'


def test_same_preselected_person_can_be_explicitly_confirmed_without_fake_changes():
    value=modern();value.update(scene='multiple_people',people=[*value['people'],{'id':'p2','region':{'xyxy':[500,0,1000,1000]}}])
    source=obs(value);review=flow.begin(source,authority(source))
    assert 'user_target_selection_required' in flow.confirmation_issues(review)
    review=flow.revise(review,authority(source),digest(review),source.prediction,(flow.Correction(operation='select_target',subject='scene',reason='I choose the first visible person.'),),selected_target='p1')
    flow.confirm(review,authority(source),digest(review),inventory_reviewed=True)
    assert review.revisions[0].selected_target=='p1'
    with pytest.raises(ValueError):flow.revise(review,authority(source),'0'*64,source.prediction,(),selected_target='p2')


def test_duplicate_ids_resolve_by_explicit_removal_without_losing_original_records():
    value=modern();value['items'].append(copy.deepcopy(value['items'][0]))
    source=obs(value);review=flow.begin(source,authority(source));value['items'].pop()
    review=flow.revise(review,authority(source),digest(review),visual.parse_prediction(json.dumps(value)),(flow.Correction(operation='replace_item',subject='g1',reason='Removed duplicate AI record.'),))
    flow.confirm(review,authority(source),digest(review),inventory_reviewed=True)
    assert len(review.original.prediction.items)==4 and len(flow.current(review).items)==3


def test_unresolved_skirt_shorts_stays_unknown_without_ground_truth_relabel():
    value=modern();value['items'][1].update(category='unknown',role='lower',category_alternatives=[])
    proof=confirmed(value)
    assert proof.review.original.prediction.items[1].category=='unknown'
    assert not assessment.evidence_requirements(proof.review.original.prediction,occasion('Library'))['style_consistency'][0]


def test_a_visible_pair_can_keep_unknown_type_without_guessing_socks_or_shoes():
    value=modern();value['feet_observation']='uncertain'
    value['items'][2].update(category='unknown',role='unknown',unit='pair')
    proof=confirmed(value)
    assert proof.review.original.prediction.items[2].category=='unknown'
    assert not assessment.evidence_requirements(proof.review.original.prediction,occasion('Library'))['occasion_suitability'][0]


def test_exact_experimental_weighted_score_and_model_provenance():
    proof=confirmed(modern(shoes=True));value=judgments(proof)
    result=assessment.assess(proof,occasion('Library'),json.dumps(value),proof.review.original.run)
    assert result['rubric']['score']==75.0 and result['rubric']['exact_score']=='75'
    assert [d['score'] for d in result['rubric']['dimensions']]==[75,90,75,50]
    assert [d['weight_percent'] for d in result['rubric']['dimensions']]==[40,25,20,15]
    assert result['rubric']['weights_redistributed'] is False
    assert result['feedback_source']=='local_model_grounded_anchors'


def test_socks_only_withholds_overall_without_redistributing_other_scores():
    proof=confirmed();value=judgments(proof)
    result=assessment.assess(proof,occasion('Library'),json.dumps(value),proof.review.original.run)
    assert result['rubric']['score'] is None
    assert result['rubric']['dimensions'][0]['score'] is None
    assert result['rubric']['dimensions'][1]['score']==90


@pytest.mark.parametrize('tamper',['invented_ref','missing_item','duplicate_dimension','overall_number','wrong_reason','fabric_claim','uncertain_score'])
def test_ungrounded_or_unconstrained_model_output_is_rejected(tamper):
    proof=confirmed(modern(shoes=True));value=judgments(proof)
    if tamper=='invented_ref':value['dimensions'][0]['evidence_refs'].append('item99.material')
    elif tamper=='missing_item':value['dimensions'][1]['evidence_refs'].pop()
    elif tamper=='duplicate_dimension':value['dimensions'][0]['dimension']='colour_coordination'
    elif tamper=='overall_number':value['overall_score']=100
    elif tamper=='wrong_reason':value['dimensions'][0]['reason']='palette_contrast'
    elif tamper=='fabric_claim':value['suggestions'][0]['material']='cotton'
    else:value['dimensions'][1]['reason']='colour_uncertain'
    with pytest.raises(ValueError):assessment.assess(proof,occasion('Library'),json.dumps(value),proof.review.original.run)


def test_unknown_styles_and_patterns_never_produce_scores_or_false_claims():
    value=modern(shoes=True)
    for i in value['items']:i['style']=fact();i['pattern']=fact()
    proof=confirmed(value);output=judgments(proof)
    for dimension in output['dimensions']:
        if dimension['dimension']!='colour_coordination':
            dimension.update(anchor='not_assessable',reason=assessment.REASONS[dimension['dimension']][-1],evidence_refs=[])
    result=assessment.assess(proof,occasion('Library'),json.dumps(output),proof.review.original.run)
    assert result['rubric']['score'] is None
    assert [d['score'] for d in result['rubric']['dimensions']]==[None,90,None,None]


def test_revision_and_confirmation_tampering_still_fails():
    proof=confirmed();value=json.loads(proof.model_dump_json());value['confirmed_by']='foreign'
    with pytest.raises(ValueError):flow.parse_confirmation(json.dumps(value))


def test_changed_physical_scope_does_not_relabel_old_ai_attributes_as_verified():
    source=obs();review=flow.begin(source,authority(source));value=modern();value['items'][2]['unit']='single'
    review=flow.revise(review,authority(source),digest(review),visual.parse_prediction(json.dumps(value)),(flow.Correction(operation='replace_item',subject='g3',reason='Only one sock is visible.'),))
    assert flow.provenance(review)['g3.colours']=='user_scope_review_not_model_verified'
    assert source.prediction.items[2].unit=='pair'


def test_explicit_dress_code_cannot_be_ignored_by_a_general_activity_judgment():
    from app.application.outfit_review.occasion import Occasion
    proof=confirmed(modern(shoes=True));context=Occasion(original_text='A formal interview.',context='professional.job_interview',role='candidate',dress_code='formal',formality='formal',grammar='fixture',interpretation_sha256='a'*64,requirements=())
    value=judgments(proof)
    with pytest.raises(ValueError,match='dress requirement'):assessment.assess(proof,context,json.dumps(value),proof.review.original.run)
    value['dimensions'][0]['reason']='dress_code_alignment'
    assert assessment.assess(proof,context,json.dumps(value),proof.review.original.run)['rubric']['score']==75


@pytest.fixture
def service():
    from app.application.outfit_review.service import ReviewService
    def observe(image,png):
        source=obs(modern(shoes=True))
        assert source.image==image
        return source
    def judge(proof,context):return assessment.assess(proof,context,json.dumps(judgments(proof)),proof.review.original.run)
    instance=ReviewService(observe,occasion,judge=judge,cleanup=False)
    yield instance
    instance.close()


from tests.test_outfit_review_prototype import client,analyzed


def test_authenticated_v11_correction_and_ai_review_require_explicit_gpu_ack(client,service):
    view=analyzed(service);id=view['id']
    assert view['prediction']['version']==visual.VERSION
    changed=copy.deepcopy(view['prediction']);changed['items'][0]['style']=fact('casual')
    response=client.patch(f'/api/v1/outfit-reviews/{id}/inventory',json={'revision':view['revision'],'prediction':changed,
        'changes':[{'operation':'replace_item','subject':'g1','reason':'Explicit appearance correction.'}]})
    assert response.status_code==200,response.text
    view=response.json();assert view['original_prediction']['items'][0]['style']['values']==['sporty']
    assert client.post(f'/api/v1/outfit-reviews/{id}/confirm',json={'revision':view['revision'],'inventory_reviewed':True}).status_code==200
    body={'revision':view['revision'],'occasion':'Library','use_ai':True,'gpu_available':False}
    assert client.post(f'/api/v1/outfit-reviews/{id}/review',json=body).status_code==409
    body['gpu_available']=True
    assert client.post(f'/api/v1/outfit-reviews/{id}/review',json=body).status_code==202
    service.executor.submit(lambda:None).result(timeout=3)
    result=client.get(f'/api/v1/outfit-reviews/{id}').json()['result']
    assert result['rubric']['score']==75.0
    assert result['provenance']['g1.style']=='user_correction_not_model_verified'
    assert result['feedback_source']=='local_model_grounded_anchors'
    assert client.post(f'/api/v1/outfit-reviews/{id}/review',json={'revision':view['revision'],'occasion':'Library'}).status_code==202
    service.executor.submit(lambda:None).result(timeout=3)
    basic=client.get(f'/api/v1/outfit-reviews/{id}').json()['result']
    assert basic['feedback_source']=='descriptive_cpu_summary' and basic['rubric']['score'] is None


def test_foreign_access_and_failed_judgment_leave_no_score(client,service):
    from app.infrastructure.security import issue_access_token
    from app.application.outfit_review.service import ReviewError
    view=analyzed(service);id=view['id'];service.confirm(id,'alice',view['revision'],True)
    client.headers['Authorization']='Bearer '+issue_access_token('bob')
    assert client.get(f'/api/v1/outfit-reviews/{id}').status_code==404
    def fail(*args):raise ReviewError('InvalidAssessment','The model judgment was not grounded.',422)
    service.judge=fail
    service.evaluate(id,'alice',view['revision'],'Library',True,True).result(timeout=3)
    failed=service.view(id,'alice')
    assert failed['result'] is None and failed['error']['code']=='InvalidAssessment'


def test_v11_model_adapter_uses_additive_schema_and_keeps_the_old_adapter_default(monkeypatch,tmp_path):
    from app.application.outfit_review import runtime
    captured=[]
    def run(self,image,png,folder,executable,*,task=None):
        captured.append(task)
        return task['parse'](json.dumps(modern()),observation().run)
    monkeypatch.setattr(runtime.QwenObserver,'_run',run)
    result=runtime.QwenObserverV11()._run(observation().image,b'png',tmp_path,tmp_path/'fixture.exe')
    assert result.version==visual.VERSION
    schema=captured[0]['schema']
    assert schema['properties']['version']['const']==visual.VERSION
    assert 'socks' in schema['$defs']['Item']['properties']['category']['enum']


def test_pretrained_assessor_prompt_receives_only_confirmed_typed_facts(monkeypatch,tmp_path):
    from app.application.outfit_review import runtime
    from app.application.outfit_review.occasion import Occasion
    proof=confirmed(modern(shoes=True));captured=[]
    def run(self,image,png,folder,executable,*,task=None):
        captured.append(task)
        return task['parse'](json.dumps(judgments(proof)),proof.review.original.run)
    monkeypatch.setattr(runtime.QwenObserver,'_run',run)
    monkeypatch.setattr(runtime.QwenAssessor,'guarded',lambda self,execute:execute(tmp_path,tmp_path/'fixture.exe'))
    context=Occasion(original_text='Untrusted source text must not become model instructions.',context='academic.library_study',role='unspecified',dress_code=None,formality=None,grammar='fixture',interpretation_sha256='a'*64,requirements=())
    result=runtime.QwenAssessor().generate(proof,context)
    assert result['rubric']['score']==75
    model_input=json.loads(captured[0]['messages'][1]['content'])
    assert context.original_text not in captured[0]['messages'][1]['content']
    assert 'item1.colours' in model_input['facts']
    assert 'overall_score' not in captured[0]['schema']['properties']


def test_model_cannot_invent_a_colour_contrast_or_style_mixture():
    proof=confirmed(modern(shoes=True));value=judgments(proof)
    value['dimensions'][2]['reason']='style_mixture'
    with pytest.raises(ValueError,match='mixture'):assessment.assess(proof,occasion('Library'),json.dumps(value),proof.review.original.run)


def test_basic_summary_keeps_auditable_references_but_hides_ids_in_prose():
    from app.application.outfit_review.feedback import review_outfit
    proof=confirmed();result=review_outfit(proof,occasion('Library'))
    assert result['sections'][3]['item_ids']==['g1','g2','g3']
    assert 'g1' not in result['sections'][3]['text']
    assert result['rubric']['score'] is None and result['feedback_source']=='descriptive_cpu_summary'
