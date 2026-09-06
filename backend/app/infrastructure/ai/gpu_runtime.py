"""One process-wide admission lock for memory-intensive AI inference."""
from contextlib import contextmanager
from threading import Lock

_GPU_LOCK = Lock()


@contextmanager
def gpu_inference_slot():
    _GPU_LOCK.acquire()
    try:
        yield
    finally:
        _GPU_LOCK.release()
