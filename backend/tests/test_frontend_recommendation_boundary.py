"""Opt-in UI discovery and server-side prevention of disabled legacy fallback."""
from unittest.mock import Mock
from fastapi.testclient import TestClient
from app.main import app
from app.application.ports.assistant_runtime import assistant_service
from app.application.ports.homepage_runtime import homepage_service
from app.infrastructure.security import issue_access_token
from tests.test_recommendation_persistence import store,connect


def test_capabilities_and_disabled_integrated_submission_are_read_only(store,monkeypatch):
    monkeypatch.delenv('SMART_WARDROBE_ASSISTANT_ENABLED',raising=False)
    monkeypatch.delenv('SMART_WARDROBE_HOMEPAGE_ENABLED',raising=False)
    with TestClient(app) as client:
        headers = {'Authorization':'Bearer '+issue_access_token('owner')}
        assert client.get('/api/v1/recommendations/capabilities').status_code == 401
        result = client.get('/api/v1/recommendations/capabilities',headers=headers)
        assert result.json() == {'homepage_enabled':False,'assistant_enabled':False}
        blocked = client.post('/api/v1/recommendations?pipeline=integrated',headers=headers,json={'request_text':'Suggest an outfit','submission_key':'key'})
        assert blocked.status_code == 404 and blocked.json()['outcome'] == 'IntegrationDisabled'
        with connect(store[0]) as c:
            assert c.execute('SELECT count(*) FROM nlp_chats').fetchone()[0] == 0
            assert c.execute('SELECT count(*) FROM recommendations').fetchone()[0] == 0


def test_capabilities_reflect_composed_services_without_invoking_them(store):
    assistant,homepage = Mock(),Mock()
    with TestClient(app) as client:
        app.dependency_overrides[assistant_service] = lambda:assistant
        app.dependency_overrides[homepage_service] = lambda:homepage
        try:
            response = client.get('/api/v1/recommendations/capabilities',headers={'Authorization':'Bearer '+issue_access_token('owner')})
            assert response.json() == {'homepage_enabled':True,'assistant_enabled':True}
            assistant.recommend.assert_not_called()
            homepage.recommend.assert_not_called()
        finally:
            app.dependency_overrides.pop(assistant_service,None)
            app.dependency_overrides.pop(homepage_service,None)
