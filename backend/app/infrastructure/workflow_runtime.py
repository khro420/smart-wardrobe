"""Concrete bindings used only by the FastAPI composition root."""
from app.application.ports.workflow_runtime import WorkflowRuntime, configure_workflow
from app.infrastructure.ai.garment_segmentation_adapter import get_garment_adapter
from app.infrastructure.ai.attribute_embedding_adapter import get_attribute_adapter
from app.infrastructure.ai.vtoff_adapter import get_standardisation_adapter
from app.infrastructure.media import protected_media_store
from app.infrastructure.persistence import postgresql_repository
from app.application.wardrobe.wardrobe_service import WardrobeWriter
from app.application.ports.visualisation_repository import (
    VisualisationRuntime,
    configure_visualisation,
)
from app.domain.value_objects.visualisation_plan import VTONConfiguration
from app.infrastructure.ai.gpu_runtime import gpu_inference_slot
from app.infrastructure.ai.vton_adapter import get_vton_adapter
from app.infrastructure.ai.vton_preprocessing import validate_generated_output
from app.infrastructure.config import (
    VTON_GUIDANCE_SCALE, VTON_HEIGHT, VTON_INFERENCE_STEPS,
    VTON_QUEUE_LIMIT, VTON_SEED, VTON_WIDTH,
)


class LocalWorkflowRepository:
    connection = staticmethod(postgresql_repository.connection)
    utcnow = staticmethod(postgresql_repository.utcnow)


class ProtectedMediaAdapter:
    path_for_owner = staticmethod(protected_media_store.media_path_for_owner)
    store_bytes = staticmethod(protected_media_store.store_media_bytes)
    store_image = staticmethod(protected_media_store.store_image)


def configure_local_workflow():
    configure_workflow(WorkflowRuntime(
        database=LocalWorkflowRepository(), media=ProtectedMediaAdapter(),
        segmentation=get_garment_adapter, standardisation=get_standardisation_adapter,
        attributes=get_attribute_adapter, confirmed_writer=WardrobeWriter(),
    ))
    configure_visualisation(VisualisationRuntime(
        repository=LocalWorkflowRepository(),
        media=ProtectedMediaAdapter(),
        adapter=get_vton_adapter,
        gpu_slot=gpu_inference_slot,
        configuration=lambda: VTONConfiguration(
            width=VTON_WIDTH, height=VTON_HEIGHT,
            steps=VTON_INFERENCE_STEPS, guidance=VTON_GUIDANCE_SCALE,
            seed=VTON_SEED,
        ),
        validate_output=validate_generated_output,
        queue_limit=VTON_QUEUE_LIMIT,
    ))
