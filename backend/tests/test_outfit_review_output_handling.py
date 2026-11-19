"""Transport duplicate normalization is not observation qualification."""
import copy
import json
import pytest
from jsonschema import Draft202012Validator
from app.application.outfit_review import output_handling as output, observation_v11 as visual, confirmation_v11 as flow
from app.application.outfit_review.contract import digest
from tests.test_outfit_review_v11 import modern, obs, judgments
from tests.test_outfit_review_observation import authority, observation
from tests.test_outfit_review_prototype import occasion, client, analyzed
from app.application.outfit_review import assessment
from tests.test_outfit_review_v11 import confirmed


def source(value=None):
    value = value or modern()
    value['items'][0]['pattern'] = {'state':'observed','values':['checked','checked','checked']}
    return json.dumps(value, ensure_ascii=False, indent=2)


def test_identical_duplicates_preserve_raw_source_and_exact_auditable_diff():
    raw = source(); base = observation()
    result = output.observe(base.image, base.run, raw)
    assert result.raw_response == raw
    assert result.prediction.items[0].pattern.values == ('checked',)
    assert result.normalization.changes[0].path == '/items/0/pattern/values'
    assert result.normalization.changes[0].before == ('checked','checked','checked')
    assert result.normalization.changes[0].after == ('checked',)
    expected = json.loads(raw); expected['items'][0]['pattern']['values'] = ['checked']
    assert result.prediction == visual.parse_prediction(json.dumps(expected))
    assert visual.parse_observation(result.model_dump_json()) == result
    # Historical reader still refuses the same invalid historical prediction.
    with pytest.raises(ValueError): visual.parse_prediction(raw)


@pytest.mark.parametrize('change', ['raw','prediction','normalization','remove_record','hash'])
def test_normalized_envelope_cannot_be_tampered_with(change):
    base = observation();value = json.loads(output.observe(base.image,base.run,source()).model_dump_json())
    if change == 'raw':value['raw_response'] = value['raw_response'].replace('checked','plain')
    elif change == 'prediction':value['prediction']['items'][0]['pattern']['values'] = ['plain']
    elif change == 'normalization':value['normalization']['changes'][0]['after'] = ['plain']
    elif change == 'remove_record':value.pop('normalization')
    else:value['normalization']['raw_sha256'] = '0'*64
    with pytest.raises(ValueError):visual.parse_observation(json.dumps(value))


@pytest.mark.parametrize('labels', [['checked','striped'],['checked','checked','striped'],['Checked','checked'],['checked']*5])
def test_distinct_unsupported_and_oversized_values_cannot_be_laundered(labels):
    value = modern();value['items'][0]['pattern'] = {'state':'observed','values':labels}
    with pytest.raises(ValueError):output.normalize(json.dumps(value))


def test_uncertain_alternatives_remain_distinct_and_category_conflicts_remain_issues():
    value = modern();value['items'][0]['pattern'] = {'state':'uncertain','values':['checked','checked','striped']}
    value['items'][0].update(role='lower',category_alternatives=['unknown'])
    prediction,record = output.normalize(json.dumps(value))
    assert prediction.items[0].pattern.state == 'uncertain'
    assert prediction.items[0].pattern.values == ('checked','striped')
    assert 'g1:category_role_conflict' in visual.issues(prediction)
    assert 'g1:invalid_category_alternatives' in visual.issues(prediction)
    assert len(record.changes) == 1


def test_unknown_and_malformed_json_stay_invalid():
    value = modern();value['items'][0]['pattern'] = {'state':'unknown','values':['checked','checked']}
    with pytest.raises(ValueError):output.normalize(json.dumps(value))
    with pytest.raises(ValueError,match='Duplicate JSON field'):output.normalize(source().replace('"scene":', '"scene":"unclear","scene":'))
    with pytest.raises(ValueError):output.normalize(source()[:-1])
    with pytest.raises(ValueError):output.normalize(' '*65537)


def test_decoding_schema_encodes_observed_cardinality_without_losing_uncertain_alternatives():
    schema = output.decoding_schema();Draft202012Validator.check_schema(schema)
    value = modern();Draft202012Validator(schema).validate(value)
    value['items'][0]['pattern'] = {'state':'observed','values':['checked','striped']}
    assert list(Draft202012Validator(schema).iter_errors(value))
    value['items'][0]['pattern']['state'] = 'uncertain'
    Draft202012Validator(schema).validate(value)
    value['items'][0]['pattern']['state'] = 'unknown'
    assert list(Draft202012Validator(schema).iter_errors(value))


def test_normalization_confirmation_replay_and_old_v11_digests_are_separate():
    old = obs();old_json = old.model_dump_json();old_hash = digest(old)
    base = observation();result = output.observe(base.image,base.run,source())
    review = flow.begin(result,authority(result))
    proof = flow.confirm(review,authority(result),digest(review),inventory_reviewed=True)
    restored = flow.parse_confirmation(proof.model_dump_json())
    assert restored == proof and restored.review.original.raw_response == source()
    assert visual.parse_observation(old_json).model_dump_json() == old_json
    assert digest(visual.parse_observation(old_json)) == old_hash
    assert all(v == 'ai_prediction_user_reviewed' for v in flow.provenance(review).values())


@pytest.fixture
def service():
    from app.application.outfit_review import assessment
    from app.application.outfit_review.service import ReviewService
    def observer(image,png):return output.observe(image,observation().run,source(modern(shoes=True)))
    def judge(proof,context):return assessment.assess(proof,context,json.dumps(judgments(proof)),proof.review.original.run)
    app = ReviewService(observer,occasion,judge=judge,cleanup=False)
    yield app
    app.close()


def test_authenticated_normalized_flow_keeps_original_labels_and_uses_ai_path(client,service):
    view = analyzed(service); id = view['id']
    assert view['normalization']['changes'][0]['before'] == ['checked']*3
    assert json.loads(view['original_model_response'])['items'][0]['pattern']['values'] == ['checked']*3
    assert view['prediction']['items'][0]['pattern']['values'] == ['checked']
    assert client.post(f'/api/v1/outfit-reviews/{id}/confirm',json={'revision':view['revision'],'inventory_reviewed':True}).status_code == 200
    response = client.post(f'/api/v1/outfit-reviews/{id}/review',json={'revision':view['revision'],'occasion':'Library','use_ai':True,'gpu_available':True})
    assert response.status_code == 202
    service.executor.submit(lambda:None).result(timeout=3)
    result = client.get(f'/api/v1/outfit-reviews/{id}').json()['result']
    assert result['feedback_source'] == 'local_model_grounded_anchors' and result['rubric']['score'] == 75


def test_model_adapter_preserves_raw_and_uses_bounded_decoding_schema(monkeypatch,tmp_path):
    from app.application.outfit_review import runtime
    captured = []
    def run(self,image,png,folder,executable,*,task=None):
        captured.append(task);return task['parse'](source(),observation().run)
    monkeypatch.setattr(runtime.QwenObserver,'_run',run)
    result = runtime.QwenObserverNormalized()._run(observation().image,b'png',tmp_path,tmp_path/'fixture.exe')
    assert result.version == output.VERSION and len(result.normalization.changes) == 1
    assert captured[0]['schema'] == output.decoding_schema()


def test_person_selection_false_item_and_dangling_layer_need_explicit_correction(client,service):
    value = modern(shoes=True); value['target_person_id'] = None
    duplicate = copy.deepcopy(value['items'][0]); duplicate.update(id='false-outer',category='jacket',role='outerwear')
    value['items'].append(duplicate); value['layering'] = [{'over':'false-outer','under':'g1','state':'uncertain'}]
    service.observer = lambda image,png: output.observe(image,observation().run,json.dumps(value))
    view = analyzed(service);id = view['id']
    assert 'target_selection_required' in view['issues']
    assert client.post(f'/api/v1/outfit-reviews/{id}/confirm',json={'revision':view['revision'],'inventory_reviewed':True}).status_code == 422
    p = copy.deepcopy(view['prediction']);p['target_person_id'] = 'p1';p['items'].pop()
    response = client.patch(f'/api/v1/outfit-reviews/{id}/inventory',json={'revision':view['revision'],'prediction':p,'selected_target':'p1',
        'changes':[{'operation':'select_target','subject':'scene','reason':'Explicit visible person selection.'},{'operation':'remove_item','subject':'false-outer','reason':'False extra clothing record.'}]})
    assert response.status_code == 200,response.text
    view = response.json();assert view['issues'] == ['invalid_layer_reference']
    assert client.post(f'/api/v1/outfit-reviews/{id}/confirm',json={'revision':view['revision'],'inventory_reviewed':True}).status_code == 422
    p['layering'] = []
    response = client.patch(f'/api/v1/outfit-reviews/{id}/inventory',json={'revision':view['revision'],'prediction':p,
        'changes':[{'operation':'review_relations','subject':'scene','reason':'Removed relation to explicitly removed false item.'}]})
    assert response.status_code == 200,response.text
    assert client.post(f'/api/v1/outfit-reviews/{id}/confirm',json={'revision':response.json()['revision'],'inventory_reviewed':True}).status_code == 200


def test_feedback_decoding_schema_forbids_decorated_and_incomplete_references():
    proof=confirmed(modern(shoes=True));context=occasion('Library')
    schema=assessment.decoding_schema(proof,context);Draft202012Validator.check_schema(schema)
    assert 'items' not in schema['properties']['dimensions']  # Pinned converter's tuple dispatch.
    good=judgments(proof);Draft202012Validator(schema).validate(good)
    for edit in ('decorated','partial','duplicate_dimension','invented_item'):
        value=copy.deepcopy(good)
        if edit=='decorated':value['dimensions'][1]['evidence_refs'][0]+=': black'
        elif edit=='partial':value['dimensions'][1]['evidence_refs'].pop()
        elif edit=='duplicate_dimension':value['dimensions'][0]['dimension']='colour_coordination'
        else:value['suggestions'][0]['item_refs'].append('item99')
        assert list(Draft202012Validator(schema).iter_errors(value)),edit
        with pytest.raises(ValueError):assessment.assess(proof,context,json.dumps(value),proof.review.original.run)


def test_feedback_schema_keeps_real_unknowns_and_requires_whole_outfit_colour_refs():
    value=modern(shoes=True)
    for i in value['items']:i['style']={'state':'unknown','values':[]};i['pattern']={'state':'unknown','values':[]}
    proof=confirmed(value);context=occasion('Library');schema=assessment.decoding_schema(proof,context)
    proposal=judgments(proof)
    for d in proposal['dimensions']:
        if d['dimension']!='colour_coordination':d.update(anchor='not_assessable',reason=assessment.REASONS[d['dimension']][-1],evidence_refs=[])
    proposal['suggestions']=[{'action':'resolve_unknown_details','item_refs':[]}]
    Draft202012Validator(schema).validate(proposal)
    result=assessment.assess(proof,context,json.dumps(proposal),proof.review.original.run)
    assert result['rubric']['score'] is None
    assert [d['score'] for d in result['rubric']['dimensions']]==[None,90,None,None]
