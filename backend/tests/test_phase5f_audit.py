"""Diagnostic reproductions of deferred gaps; passing is NOT release approval."""
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.main import app
from app.application.recommendation import recommendation_service as legacy
from app.application.visualisation import outfit_identifier_validator as visualisation
from app.domain.value_objects.visualisation_plan import VTONConfiguration
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.security import issue_access_token
from tests.test_recommendation_persistence import store, connect, assistant


@pytest.mark.parametrize("change",["accepted","unlinked","foreign_job"])
def test_corrected_save_and_source_validation_reject_strict_gap(store,monkeypatch,change):
    from app.infrastructure.workflow_runtime import configure_local_workflow
    configure_local_workflow()
    path,repository,command = store
    record = repository.persist(assistant(command))
    with connect(path) as conn:
        if change == "accepted": conn.execute("UPDATE processing_items SET review_status='accepted'")
        elif change == "unlinked": conn.execute("UPDATE garments SET processing_item_id=NULL")
        else: conn.execute("UPDATE processing_jobs SET user_id='other'")
    assert SqliteConfirmedGarmentQuery().get_confirmed_available_garments("owner") == ()
    # Corrected source validation rejects before media/inference.
    # Only media is stubbed; the actual SQLite eligibility predicate is exercised.
    monkeypatch.setattr(visualisation,"runtime",lambda:SimpleNamespace(media=SimpleNamespace(path_for_owner=lambda *_:None),configuration=VTONConfiguration))
    with connect(path) as conn:
        with pytest.raises(HTTPException) as error:
            visualisation.resolve_source(conn,"owner",recommendation_id=record["id"])
        assert error.value.status_code == 409
    with pytest.raises(HTTPException) as error:
        legacy.save_as_outfit(record["id"],"owner","Audit diagnostic")
    assert error.value.status_code == 409
    with connect(path) as conn:
        assert conn.execute("SELECT status FROM recommendations WHERE id=?",(record["id"],)).fetchone()[0] == "available"


def test_disabled_contract_guard_blocks_all_generation(store,monkeypatch):
    monkeypatch.delenv("SMART_WARDROBE_ASSISTANT_ENABLED",raising=False)
    placeholder = Mock(return_value={"legacy":True})
    monkeypatch.setattr(legacy,"create_recommendation",placeholder)
    with TestClient(app) as client:
        headers={"Authorization":"Bearer "+issue_access_token("owner")}
        blocked=client.post("/api/v1/recommendations",headers=headers,json={"request_text":"Suggest an outfit"})
        assert blocked.status_code == 404 and blocked.json()['outcome'] == 'IntegrationDisabled'
        for mode,code in (("integrated",404),("other",422)):
            response=client.post("/api/v1/recommendations?pipeline="+mode,headers=headers,json={"request_text":"Suggest an outfit","submission_key":"audit"})
            assert response.status_code == code
        placeholder.assert_not_called()
        from app.infrastructure import security
        monkeypatch.setattr(security,"TOKEN_TTL_HOURS",-1)
        expired=issue_access_token("owner")  # Genuine signature, past expiry.
        assert client.get("/api/v1/recommendations/capabilities",headers={"Authorization":"Bearer "+expired}).status_code == 401


@pytest.mark.parametrize("interrupted",[False,True])
def test_real_http_boundary_discards_late_candidate_failure(store,interrupted):
    from app.application.ports.assistant_runtime import assistant_service
    from app.application.nlp.nlp_interpreter import NLPInterpreter
    from app.application.recommendation.candidate_generator import CandidateGenerator
    from app.application.recommendation.recommendation_engine import RecommendationEngine
    from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
    from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
    path,repository,_=store
    class LateFailure(CandidateGenerator):
        def enumerate(self,*args):
            yield from super().enumerate(*args)
            if interrupted: raise KeyboardInterrupt()
            raise RuntimeError("injected after valid candidate")
    engine=RequestCandidateEngine(structural_engine=RecommendationEngine(SqliteConfirmedGarmentQuery(),generator=LateFailure()))
    service=OutfitAssistantService(NLPInterpreter(),engine,SimpleNamespace(get_active_preferences=lambda _:()),repository,execution_engine="reference")  # Fault targets the reference generator.
    with TestClient(app) as client:
        app.dependency_overrides[assistant_service]=lambda:service
        try:
            headers={"Authorization":"Bearer "+issue_access_token("owner")}
            result=client.post("/api/v1/recommendations?pipeline=integrated",headers=headers,json={"request_text":"Suggest an outfit","submission_key":"late"})
            assert result.status_code==503
            assert result.json()["outcome"] == ("Interrupted" if interrupted else "ProcessingFailure")
            assert not result.json()["complete"] and "recommendation" not in result.json()
            assert client.get("/api/v1/recommendations/capabilities",headers=headers).status_code==200
            with connect(path) as conn:
                assert conn.execute("SELECT count(*) FROM nlp_chats").fetchone()[0]==0
                assert conn.execute("SELECT count(*) FROM recommendations").fetchone()[0]==0
                assert conn.execute("SELECT count(*) FROM garments").fetchone()[0]==1
        finally: app.dependency_overrides.pop(assistant_service,None)
