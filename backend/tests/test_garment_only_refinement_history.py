"""Completed receipts survive disabled feature/parser; old roots stay old."""
from tests.test_garment_only_refinement_persistence import garment_api,language_api,palette_api,p2_api,attribute_api,refinement_api,expanded_api,relative_api,automatic_api,everyday_api,release,lifecycle
from tests.test_b3_palette_integration import submit
from app.application.ports.assistant_runtime import assistant_service

def test_completed_root_replay_before_disabled_feature_and_parser(garment_api,monkeypatch):
    client,wearer=garment_api;key='garment-disabled-replay'
    response,root=submit(client,wearer,'I want an outfit without floral patterns.',key,True)
    assert response.status_code==201,root
    service=assistant_service();service.garment_refinement_profile='disabled'
    monkeypatch.setattr(service.attribute_pipeline,'interpret',lambda *a,**k:(_ for _ in ()).throw(AssertionError('Completed replay parsed')))
    response,replay=submit(client,wearer,root['request_text'],key,True)
    assert response.status_code==200 and replay['id']==root['id'] and replay['provenance']==root['provenance']
    action=root['garment_continuation']['next_action']
    response,result=submit(client,wearer,root['request_text'],action['submission_key'],True,action['refinement'])
    assert response.status_code==422 and result['outcome']=='RefinementUnavailable',result

def test_closed_proof_tampering_and_old_roots_not_promoted(garment_api):
    import copy
    from app.application.recommendation.garment_only_refinement_verifier import validate
    client,wearer=garment_api
    response,root=submit(client,wearer,'I want an outfit without floral patterns.',p2=True)
    assert response.status_code==201,root
    for field,value in [('version','unknown'),('root_R',{'numerator':'1','denominator':'1'}),('ordinal',True),('bindings_sha256','0'*64),('selected_base',[['one_piece','foreign']]),('preference_profile',None),('policy_sha256','0'*64)]:
        bad=copy.deepcopy(root);bad['provenance']['garment_refinement'][field]=value
        import pytest
        with pytest.raises((ValueError,KeyError,TypeError)):validate(bad)
    service=assistant_service();service.garment_refinement_profile='disabled'
    response,old=submit(client,wearer,'I want an outfit without floral patterns.',p2=True)
    assert response.status_code==201 and 'garment_continuation' not in old,old
    service.garment_refinement_profile='garment_only_refinement_v1'
    action={'version':'assistant-refinement-request-1.0.0','kind':'alternative','parent_recommendation_id':old['id']}
    response,result=submit(client,wearer,old['request_text'],'old-root-not-promoted',True,action)
    assert response.status_code==422 and result['outcome']=='RefinementUnavailable',result
