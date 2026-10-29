"""The fixed release profile preserves every supported suitability outcome."""
import pytest
from tests.test_release_configuration import release,submit,lifecycle
from tests.test_suitability_assistant_e2e import VALUES,make,tag,sentence
from app.application.ports.assistant_runtime import assistant_service
from app.infrastructure.persistence import postgresql_repository as db


@pytest.mark.parametrize('field,value',VALUES)
@pytest.mark.parametrize('state',['allow','deny','unknown'])
def test_fixed_release_supported_suitability(release,field,value,state):
    client,create=release
    tags=['ordinary note'] if state=='unknown' else [tag(field,value,state)]
    make(client,create,tags=tags)
    response,result=submit(client,sentence(field,value))
    expected={'allow':'Selected','deny':'NoMatchingCandidates','unknown':'InsufficientEvidence'}[state]
    assert result['outcome']==expected,result
    if state=='allow':
        assert response.status_code==201 and result['total_score']==.7
        assert result['provenance']['request_evaluator']=='SuitabilityRequestEvaluator'
        assert result['provenance']['scoring_profile']=='experimental_compatibility_decision_v1'
    else:
        assert result.get('id') is None and result.get('chat_id') is None


@pytest.mark.parametrize('text,expected',[
    ('Suggest an outfit for exercise','PolicyUnavailable'),
    ('Suggest a formal outfit','PolicyUnavailable'),
    ('What is the weather forecast?','UnsupportedRequest'),
    ('Suggest an outfit','NoEligibleGarments')])
def test_release_terminal_cases_do_not_invent_evidence(release,text,expected):
    client,_=release
    _,result=submit(client,text)
    assert result['outcome']==expected,result


@pytest.mark.parametrize('categories,phrase',[
    (['short_sleeve_top','trousers'],'including a top and trousers'),
    (['short_sleeve_top','trousers','long_sleeve_outwear'],'including a top and trousers and outerwear'),
    (['vest_dress'],'including a vest dress'),
    (['vest_dress','long_sleeve_outwear'],'including a vest dress and outerwear')])
def test_fixed_release_four_structures_combined_fields(release,categories,phrase):
    client,create=release
    ids=[make(client,create,category,[tag(),tag('formality','casual')]) for category in categories]
    response,result=submit(client,'Suggest a casual outfit for campus with vintage style using blue colours with '+phrase)
    assert response.status_code==201,result
    assert set(i['garment_id'] for i in result['items'])==set(ids)
    assert result['request_match_score']==1
    assert result['total_score']==(.7 if len(ids)==1 else .8)


def test_fixed_release_atomic_score_and_provenance_rollback(release):
    client,create=release;make(client,create,tags=[tag(),tag('formality','casual')])
    repository=assistant_service().repository;prior=repository.checkpoint
    def fail(stage,conn):
        if stage=='metadata':raise RuntimeError('J12 synthetic late metadata failure')
    repository.checkpoint=fail
    response,result=submit(client,'Suggest a casual outfit for campus','j12-rollback')
    assert response.status_code==503 and result['outcome']=='PersistenceFailure',result
    with db.connection() as c:
        for table in ['nlp_chats','recommendations','recommendation_items','recommendation_metadata','recommendation_submissions']:
            assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
    repository.checkpoint=prior
    response,result=submit(client,'Suggest a casual outfit for campus','j12-rollback')
    assert response.status_code==201 and result['provenance']['scoring_profile']=='experimental_compatibility_decision_v1'
