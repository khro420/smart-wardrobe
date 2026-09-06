"""UploadValidator application responsibility from the package design."""

from fastapi import UploadFile
from app.application.ports.workflow_runtime import runtime


async def validate_and_store_wardrobe_image(upload: UploadFile, user_id: str) -> str:
    """Validate a decoded JPEG/PNG and store it through ProtectedMediaStore."""
    return await runtime().media.store_image(upload, user_id, "wardrobe_source")
