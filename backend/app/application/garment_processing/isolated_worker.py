"""Crash boundary for optional native garment-processing models.

Torch and vendor inference libraries can terminate a Python process without
raising an exception.  Run production processing in a child process so that a
native-model fault cannot take the API (and the rest of the wardrobe) down.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys


LOGGER = logging.getLogger(__name__)
FAILURE_MESSAGE = "Garment processing stopped unexpectedly in an isolated model worker. Your wardrobe service remains available; please retry after checking the installed AI runtime."


def enabled() -> bool:
    """Keep development/test processing synchronous while protecting production."""
    configured = os.getenv("SMART_WARDROBE_PROCESSING_ISOLATION", "auto").lower()
    if configured in {"0", "false", "off", "disabled"}:
        return False
    if configured in {"1", "true", "on", "enabled"}:
        return True
    return os.getenv("SMART_WARDROBE_AI_MODE", "production").lower() == "production"


def launch(job_id: str, user_id: str, profile_id: str | None, admission_mode: str) -> None:
    """Run one job in a child and turn an abnormal exit into a durable failure."""
    command = [sys.executable, "-B", "-m", "app.application.garment_processing.isolated_worker", job_id, user_id, profile_id or "", admission_mode]
    kwargs: dict[str, object] = {"cwd": os.getcwd()}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run(command, **kwargs)
    except OSError:
        LOGGER.exception("Could not start isolated garment worker for job %s", job_id)
        _mark_failed(job_id, "The isolated garment-processing worker could not start. Your wardrobe service remains available; please retry.")
        return
    if result.returncode:
        LOGGER.error("Isolated garment worker exited unexpectedly for job %s (exit code %s)", job_id, result.returncode)
        _mark_failed(job_id, FAILURE_MESSAGE)


def _mark_failed(job_id: str, message: str) -> None:
    # Import only after the child has exited.  This path never imports native
    # model code, so it remains safe after a worker crash.
    from app.application.ports.workflow_runtime import connection, utcnow

    with connection() as conn:
        conn.execute(
            "UPDATE processing_jobs SET status='failed', error_message=?, progress_message=?, updated_at=?, completed_at=? WHERE id=? AND status IN ('queued','processing')",
            (message, "Garment processing stopped safely; the wardrobe service is still available.", utcnow(), utcnow(), job_id),
        )


def _run_from_command_line(job_id: str, user_id: str, profile_id: str | None, admission_mode: str) -> None:
    from app.infrastructure.environment import load_local_environment
    load_local_environment()
    # A subprocess does not execute FastAPI's lifespan handler.  Recreate the
    # composition-root step it normally performs before touching the job store.
    from app.infrastructure.workflow_runtime import configure_local_workflow
    configure_local_workflow()
    from app.application.garment_processing.garment_processing_orchestrator import run_job
    run_job(job_id, user_id, profile_id or None, admission_mode)


if __name__ == "__main__":
    _, job_id, user_id, profile_id, admission_mode = sys.argv
    _run_from_command_line(job_id, user_id, profile_id, admission_mode)
