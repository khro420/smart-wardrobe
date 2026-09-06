"""Injected infrastructure boundaries for garment processing and wardrobe services.

The composition root binds adapters once at startup. Application modules depend
on these contracts rather than importing a concrete database, media store or AI
library (Figure 4.8). The SQL session is the local repository's transaction port.
"""
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from app.application.ports.garment_attribute_port import GarmentAttributePort
from app.application.ports.garment_segmentation_port import GarmentSegmentationPort
from app.application.ports.garment_standardisation_port import GarmentStandardisationPort
from app.application.ports.confirmed_garment_writer import ConfirmedGarmentWriter


class DatabasePort(Protocol):
    def connection(self) -> AbstractContextManager[Any]: ...
    def utcnow(self) -> str: ...


class ProtectedMediaPort(Protocol):
    def path_for_owner(self, media_id: str, user_id: str) -> tuple[Path, str]: ...
    def store_bytes(self, payload: bytes, user_id: str, media_type: str, content_type: str = "image/png") -> str: ...
    async def store_image(self, upload: Any, user_id: str, media_type: str) -> str: ...


@dataclass(frozen=True)
class WorkflowRuntime:
    database: DatabasePort
    media: ProtectedMediaPort
    segmentation: Callable[[], GarmentSegmentationPort]
    standardisation: Callable[[], GarmentStandardisationPort]
    attributes: Callable[[], GarmentAttributePort]
    confirmed_writer: ConfirmedGarmentWriter
    embedding_dimension: int = 768


_runtime: WorkflowRuntime | None = None


def configure_workflow(runtime: WorkflowRuntime) -> None:
    global _runtime
    _runtime = runtime


def runtime() -> WorkflowRuntime:
    if _runtime is None:
        raise RuntimeError("The garment workflow has not been configured at startup.")
    return _runtime


def connection():
    return runtime().database.connection()


def utcnow():
    return runtime().database.utcnow()


def media_path_for_owner(media_id: str, user_id: str):
    return runtime().media.path_for_owner(media_id, user_id)


def store_media_bytes(payload: bytes, user_id: str, media_type: str):
    return runtime().media.store_bytes(payload, user_id, media_type)


def get_garment_adapter():
    return runtime().segmentation()


def get_standardisation_adapter():
    return runtime().standardisation()


def get_attribute_adapter():
    return runtime().attributes()
