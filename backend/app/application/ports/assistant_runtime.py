"""Default-off Assistant integration binding."""
_service = None


def configure_assistant_service(service):
    global _service
    _service = service


def assistant_service():
    return _service
