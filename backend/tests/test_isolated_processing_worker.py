from types import SimpleNamespace
from unittest.mock import patch

from app.application.garment_processing import isolated_worker


def test_production_processing_is_isolated_by_default(monkeypatch):
    monkeypatch.delenv("SMART_WARDROBE_PROCESSING_ISOLATION", raising=False)
    monkeypatch.setenv("SMART_WARDROBE_AI_MODE", "production")
    assert isolated_worker.enabled() is True


def test_development_processing_stays_in_process(monkeypatch):
    monkeypatch.delenv("SMART_WARDROBE_PROCESSING_ISOLATION", raising=False)
    monkeypatch.setenv("SMART_WARDROBE_AI_MODE", "development")
    assert isolated_worker.enabled() is False


def test_worker_crash_marks_only_its_job_failed(monkeypatch):
    monkeypatch.setenv("SMART_WARDROBE_AI_MODE", "production")
    with patch.object(isolated_worker.subprocess, "run", return_value=SimpleNamespace(returncode=-1073741819)), \
         patch.object(isolated_worker, "_mark_failed") as mark_failed:
        isolated_worker.launch("job-1", "user-1", "profile-1", "manual_review_v1")
    mark_failed.assert_called_once_with("job-1", isolated_worker.FAILURE_MESSAGE)
