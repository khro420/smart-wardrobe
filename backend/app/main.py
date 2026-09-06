"""Smart Wardrobe FastAPI modular-monolith entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import account_routes, garment_processing_routes, health_routes, media_routes, recommendation_routes, visualisation_routes, wardrobe_routes
from app.infrastructure.persistence.postgresql_repository import initialise_database
from app.infrastructure.workflow_runtime import configure_local_workflow
from app.application.garment_processing.processing_job_service import recover_interrupted_jobs
from app.application.visualisation.outfit_visualisation_service import recover_interrupted_visualisations


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_local_workflow()
    initialise_database()
    recover_interrupted_jobs()
    recover_interrupted_visualisations()
    yield


app = FastAPI(
    title="Smart Wardrobe API",
    version="3.0.0",
    description="Processing, digital wardrobe, protected media and outfit visualisation API.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-User-Id"],
)
app.include_router(health_routes.router)
app.include_router(account_routes.router, prefix="/api/v1")
app.include_router(media_routes.router, prefix="/api/v1")
app.include_router(garment_processing_routes.router, prefix="/api/v1")
app.include_router(wardrobe_routes.router, prefix="/api/v1")
app.include_router(recommendation_routes.router, prefix="/api/v1")
app.include_router(visualisation_routes.router, prefix="/api/v1")
