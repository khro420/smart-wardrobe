"""Injected transaction, protected-media and inference boundaries."""
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from app.application.ports.vton_port import VTONPort
from app.application.ports.workflow_runtime import ProtectedMediaPort
from app.domain.value_objects.visualisation_plan import VTONConfiguration


class VisualisationRepository(Protocol):
    def connection(self) -> AbstractContextManager[Any]: ...
    def utcnow(self) -> str: ...


@dataclass(frozen=True)
class VisualisationRuntime:
    repository: VisualisationRepository
    media: ProtectedMediaPort
    adapter: Callable[[], VTONPort]
    gpu_slot: Callable[[], AbstractContextManager]
    configuration: Callable[[], VTONConfiguration]
    validate_output: Callable
    queue_limit: int = 8


_runtime: VisualisationRuntime | None = None


def configure_visualisation(value: VisualisationRuntime) -> None:
    global _runtime
    _runtime = value


def runtime() -> VisualisationRuntime:
    if _runtime is None:
        raise RuntimeError("Visualisation runtime has not been configured.")
    return _runtime


def connection():
    return runtime().repository.connection()


def utcnow() -> str:
    return runtime().repository.utcnow()


def get_vton_adapter() -> VTONPort:
    return runtime().adapter()
