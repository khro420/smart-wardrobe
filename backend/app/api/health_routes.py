from fastapi import APIRouter
from app.infrastructure.config import DATABASE_PATH

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "database": str(DATABASE_PATH)}
