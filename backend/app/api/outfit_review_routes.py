"""Dedicated authenticated, temporary Outfit Review routes; no wardrobe writes."""
from functools import lru_cache
from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, Response
from pydantic import Field, field_validator
from starlette.concurrency import run_in_threadpool
import json
from app.infrastructure.security import current_user_id
from app.application.outfit_review.contract import Frozen, Digest, Prediction
from app.application.outfit_review.observation_v11 import Prediction as PredictionV11,parse_prediction
from app.application.outfit_review.confirmation import Correction
from app.application.outfit_review.service import ReviewService, ReviewError
from app.application.outfit_review.runtime import QwenObserver, QwenObserverNormalized,QwenAssessor, enabled

def private_response(response: Response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"


router = APIRouter(prefix="/outfit-reviews", tags=["outfit-review"], dependencies=[Depends(private_response)])


async def owner(authorization: str | None = Header(default=None)):
    # Do not accept the optional development X-User-Id identity on these routes.
    if not authorization:
        raise HTTPException(401, "Sign in to use AI Outfit Review.")
    return await current_user_id(authorization=authorization, x_user_id=None)


@lru_cache(maxsize=1)
def _instance():
    return ReviewService(QwenObserverNormalized(),judge=QwenAssessor().generate)


def service():
    if not enabled():
        raise HTTPException(503, {"code": "Disabled", "message": "AI Outfit Review is disabled. Enable the isolated prototype explicitly before use."})
    return _instance()


def invoke(function, *args):
    try:
        return function(*args)
    except ReviewError as exc:
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message}) from None
    except ValueError:
        raise HTTPException(422, {"code": "InvalidReview", "message": "Resolve the listed inventory issues and record every correction before confirming."}) from None


class Analyze(Frozen):
    gpu_available: bool


class Correct(Frozen):
    revision: Digest
    prediction: Prediction|PredictionV11
    changes: tuple[Correction, ...] = Field(min_length=1, max_length=48)
    selected_target: str|None=None

    @field_validator("prediction", mode="before")
    @classmethod
    def json_prediction(cls, value):
        return value if isinstance(value, Prediction) else parse_prediction(json.dumps(value))

    @field_validator("changes", mode="before")
    @classmethod
    def json_changes(cls, value):
        if type(value) is list and len(value) <= 48:
            return tuple(Correction.model_validate_json(json.dumps(v)) for v in value)
        return value


class Confirm(Frozen):
    revision: Digest
    inventory_reviewed: bool


class Evaluate(Frozen):
    revision: Digest
    occasion: Annotated[str, Field(min_length=1, max_length=1600)]
    use_ai: bool=False
    gpu_available: bool=False


@router.get("/capabilities")
def capabilities(user: str = Depends(owner)):
    return {"version": "outfit-review-prototype-1.0.0", "enabled": enabled(), "candidate": "Qwen3-VL-4B-Instruct-Q4_K_M",
            "assets_present": QwenObserver().assets_available(), "gpu_confirmation_required": True,
            "numeric_scoring": "conditional_experimental", "ai_feedback":True,"observation_version":"outfit-review-observation-1.1.1", "saved_history": False, "photo_ttl_seconds": ReviewService.TTL}


@router.post("", status_code=201)
async def upload(file: UploadFile, user: str = Depends(owner), app: ReviewService = Depends(service)):
    try:
        payload = await file.read(ReviewService.MAX_IMAGE+1)
        if file.content_type not in ("image/jpeg", "image/png") or (file.content_type == "image/png") != payload.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(415, "Upload a JPEG/PNG matching its declared format.")
        return await run_in_threadpool(invoke, app.create, user, payload)
    finally:
        await file.close()


@router.get("/{id}")
def get(id: str, user: str = Depends(owner), app: ReviewService = Depends(service)):
    return invoke(app.view, id, user)


@router.get("/{id}/photo")
def photo(id: str, user: str = Depends(owner), app: ReviewService = Depends(service)):
    return Response(invoke(app.photo, id, user), media_type="image/png", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.delete("/{id}", status_code=204)
def delete(id: str, user: str = Depends(owner), app: ReviewService = Depends(service)):
    invoke(app.delete, id, user)
    return Response(status_code=204)


@router.post("/{id}/analyze", status_code=202)
def analyze(id: str, body: Analyze, user: str = Depends(owner), app: ReviewService = Depends(service)):
    invoke(app.analyze, id, user, body.gpu_available)
    return invoke(app.view, id, user)


@router.patch("/{id}/inventory")
def correct(id: str, body: Correct, user: str = Depends(owner), app: ReviewService = Depends(service)):
    return invoke(app.correct, id, user, body.revision, body.prediction, body.changes,body.selected_target)


@router.post("/{id}/confirm")
def confirm(id: str, body: Confirm, user: str = Depends(owner), app: ReviewService = Depends(service)):
    return invoke(app.confirm, id, user, body.revision, body.inventory_reviewed)


@router.post("/{id}/review", status_code=202)
def evaluate(id: str, body: Evaluate, user: str = Depends(owner), app: ReviewService = Depends(service)):
    invoke(app.evaluate, id, user, body.revision, body.occasion,body.use_ai,body.gpu_available)
    return invoke(app.view, id, user)
