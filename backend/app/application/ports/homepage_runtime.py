"""Explicit opt-in composition boundary; no default Homepage activation."""
_service = None


def configure_homepage_service(service):
    global _service
    _service = service


def homepage_service():
    return _service
