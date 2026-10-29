"""Composition binding for authenticated read-only history."""
_service = None


def configure_chat_history_service(service):
    global _service
    _service = service


def chat_history_service():
    if _service is None:
        raise RuntimeError('History service is not configured.')
    return _service
