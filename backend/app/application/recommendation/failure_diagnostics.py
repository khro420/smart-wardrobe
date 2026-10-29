"""Allowlisted technical failure events; never serialize exception messages/data."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

LOGGER = logging.getLogger("app.recommendation.failure")
_APP = Path(__file__).resolve().parents[2]
_OPERATIONS = frozenset(("assistant", "homepage"))
_STAGES = frozenset(("lookup", "configuration", "interpretation", "ranking", "validation", "generation", "persistence", "cleanup"))
_OUTCOMES = frozenset(("ProcessingFailure", "PersistenceFailure", "ProfileUnavailable", "Interrupted", "ProcessingError", "InvalidScoringInput", "InvalidPreferenceData"))
_REASONS = frozenset(("exception", "controlled_failure", "incomplete_selection", "cleanup"))
_ERROR_KINDS = {ValueError: "ValueError", TypeError: "TypeError", KeyError: "KeyError",
                AttributeError: "AttributeError", RuntimeError: "RuntimeError",
                OSError: "OSError", TimeoutError: "TimeoutError", AssertionError: "AssertionError",
                KeyboardInterrupt: "KeyboardInterrupt", GeneratorExit: "GeneratorExit"}


def log_failure(operation, stage, outcome, error=None, *, reason="exception"):
    """Emit a JSON event under ordinary logging configuration, plus structured extra.

    Exclude identities, keys, request/wardrobe/preferences, exception arguments,
    messages/chains/locals and absolute paths. Source locations are app-relative.
    Logging failure must not change an existing business response or transaction.
    """
    try:
        locations = []
        trace = error.__traceback__ if isinstance(error, BaseException) else None
        while trace is not None:
            try:
                path = Path(trace.tb_frame.f_code.co_filename).resolve().relative_to(_APP)
            except ValueError:
                pass
            else:
                locations.append({"file": path.as_posix(), "line": trace.tb_lineno})
            trace = trace.tb_next
        event = {"schema": "recommendation-failure-1.0.0", "event": "recommendation_failure",
                 "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                 "diagnostic_id": uuid4().hex,
                 "operation": operation if operation in _OPERATIONS else "unknown",
                 "stage": stage if stage in _STAGES else "unknown",
                 "outcome": outcome if outcome in _OUTCOMES else "ProcessingFailure",
                 "reason": reason if reason in _REASONS else "exception",
                 "error_kind": _ERROR_KINDS.get(type(error), "ApplicationError") if error is not None else "ControlledFailure",
                 "locations": locations[-6:]}
        # The JSON message remains useful with a plain %(message)s formatter.
        # No exc_info/stack_info: normal exception formatting would disclose data.
        LOGGER.error(json.dumps(event, sort_keys=True, separators=(",", ":")),
                     extra={"recommendation_failure": event})
    except Exception:
        # Do not turn a handler/formatter/storage failure into a different API outcome.
        pass
