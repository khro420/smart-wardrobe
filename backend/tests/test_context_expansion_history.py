import copy,json,uuid
import pytest
from tests.test_context_expansion_integration import expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle
from tests.test_automatic_garment_finalization import upload
from tests.test_release_configuration import submit
from tests.test_context_expansion_equivalence import TEXTS,rank
from app.application.ports.assistant_runtime import assistant_service
from app.application.recommendation.context_relevance_verifier import validate_evidence
from app.application.recommendation.context_relevance_policy import ContextRelevancePolicy
from app.application.recommendation.context_bundle import ContextBundle

@pytest.mark.parametrize('field',['bundle_sha256','policy_sha256','catalogue_sha256','context_plan','version'])
def test_forged_proof_rejected(field):
    result,_,_=rank(TEXTS['academic.library_study']);assert result.status=='Selected'
    proof=json.loads(result.ranking_evidence)
    proof[field]='forged'
    with pytest.raises((ValueError,TypeError,KeyError,AttributeError)):validate_evidence(proof,result.winner.score)

def test_history_replay_never_loads_live_bundle(expanded_api,monkeypatch):
    client,_=expanded_api;upload(client);key=uuid.uuid4().hex;text=TEXTS['academic.library_study']
    response,original=submit(client,text,key);assert response.status_code==201,original
    def unavailable(*args,**kwargs):raise AssertionError('History must not load active configuration')
    monkeypatch.setattr(ContextBundle,'load',unavailable);monkeypatch.setattr(ContextRelevancePolicy,'load',unavailable)
    assistant_service().context_ranking_profile='disabled'
    response,replayed=submit(client,text,key);assert response.status_code==200 and replayed['replayed']
    assert replayed['provenance']==original['provenance']
    assert replayed['scoring_display']==original['scoring_display']
    history=client.get('/api/v1/chats/'+original['chat_id']).json()['recommendation']
    assert history['scoring_display']==original['scoring_display']

@pytest.mark.parametrize('slot,value',[('activity','invented'),('style','casual'),('formality','formal'),('situation','social.date')])
def test_forged_archived_request_projection_rejected(slot,value):
    result,_,_=rank(TEXTS['academic.library_study']);proof=json.loads(result.ranking_evidence)
    frame=proof['context_plan']['request']['context']
    frame[slot]=dict(state='Known',values=[value],spans=frame['situation']['spans'])
    with pytest.raises((ValueError,KeyError,TypeError)):validate_evidence(proof,result.winner.score)
