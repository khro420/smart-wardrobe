"""Bounded ephemeral, owner-scoped vertical slice; no application DB writes."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import RLock, Lock, Timer
import secrets
import time
from typing import Callable

from .contract import Observation, Prediction, ImageIdentity, digest
from .confirmation import Authority, Correction
from .confirmation_v11 import Confirmation,Review,begin,revise,confirm,current,confirmation_issues
from .observation_v11 import parse_observation
from .images import prepare_image
from .occasion import interpret, OccasionUnavailable
from .feedback import review_outfit


class ReviewError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


@dataclass
class Entry:
    id: str
    owner: str
    original: bytes
    preview: bytes
    image: ImageIdentity
    expires: float
    state: str = "uploaded"
    review: Review | None = None
    confirmation: Confirmation | None = None
    result: dict | None = None
    error: dict | None = None
    raw_failure: str | None = None
    failed_model_run: dict | None = None
    generation: int = 0


class ReviewService:
    TTL = 15 * 60
    MAX_IMAGE = 10 * 1024 * 1024
    MAX_BYTES = 96 * 1024 * 1024

    def __init__(self, observer: Callable, occasion=interpret, *, judge=None, clock=time.monotonic, cleanup=True):
        self.observer, self.occasion, self.clock = observer, occasion, clock
        self.judge=judge
        self.lock = RLock()
        self.image_lock = Lock()
        self.entries: dict[str, Entry] = {}
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="outfit-review")
        self.busy = False
        self.cleanup, self.timer = cleanup, None

    def prune(self):
        with self.lock:
            self.entries = {k: e for k, e in self.entries.items() if e.expires > self.clock()}

    def _tick(self):
        self.prune()
        with self.lock:
            self.timer = None
            if self.entries:
                self._schedule()

    def _schedule(self):
        if self.cleanup and self.timer is None:
            self.timer = Timer(30, self._tick)
            self.timer.daemon = True
            self.timer.start()

    def close(self):
        if self.timer:
            self.timer.cancel()
        self.executor.shutdown(wait=True, cancel_futures=True)
        with self.lock:
            self.entries.clear()

    def _get(self, id: str, owner: str) -> Entry:
        self.prune()
        e = self.entries.get(id)
        if e is None or e.owner != owner:
            raise ReviewError("NotFound", "Review unavailable or expired.", 404)
        return e

    def create(self, owner: str, payload: bytes) -> dict:
        if not self.image_lock.acquire(blocking=False):
            raise ReviewError("ImageValidationBusy", "Another photo is being decoded. Please try again shortly.")
        try:
            return self._create(owner, payload)
        finally:
            self.image_lock.release()

    def _create(self, owner: str, payload: bytes) -> dict:
        if len(payload) > self.MAX_IMAGE:
            raise ReviewError("InvalidImage", "Use a JPEG or PNG no larger than 10 MiB.", 413)
        try:
            image, png = prepare_image(payload)
        except Exception:
            raise ReviewError("InvalidImage", "Use a valid JPEG/PNG, at least 128px per side and at most 25 megapixels.", 422) from None
        size = len(payload) + len(png)
        if size > 20 * 1024 * 1024:
            raise ReviewError("InvalidImage", "The decoded photo is too large for this temporary prototype.", 413)
        with self.lock:
            self.prune()
            if sum(e.owner == owner for e in self.entries.values()) >= 2 or len(self.entries) >= 8 or sum(len(e.original)+len(e.preview) for e in self.entries.values()) + size > self.MAX_BYTES:
                raise ReviewError("Capacity", "Delete an earlier temporary review or wait for expiry.", 429)
            e = Entry(secrets.token_urlsafe(24), owner, payload, png, image, self.clock()+self.TTL)
            self.entries[e.id] = e
            self._schedule()
            return self.view(e.id, owner)

    def view(self, id: str, owner: str) -> dict:
        with self.lock:
            e = self._get(id, owner)
            return {"id": e.id, "state": e.state, "image": e.image.model_dump(mode="json"),
                    "expires_in_seconds": max(0, int(e.expires-self.clock())), "generation": e.generation,
                    "revision": digest(e.review) if e.review else None,
                    "prediction": current(e.review).model_dump(mode="json") if e.review else None,
                    "original_prediction": e.review.original.prediction.model_dump(mode="json") if e.review else None,
                    "original_model_response": e.review.original.raw_response if e.review else None,
                    "normalization": e.review.original.normalization.model_dump(mode="json") if e.review and hasattr(e.review.original,'normalization') else None,
                    "issues": list(confirmation_issues(e.review)) if e.review else [],
                    "confirmed": e.confirmation is not None, "result": e.result, "error": e.error, "raw_failed_proposal": e.raw_failure,
                    "failed_model_run": e.failed_model_run,
                    "privacy": "Temporary memory only; expires after 15 minutes or backend restart. Not saved to wardrobe/history."}

    def photo(self, id: str, owner: str) -> bytes:
        with self.lock:
            return self._get(id, owner).preview

    def delete(self, id: str, owner: str):
        with self.lock:
            self._get(id, owner)
            del self.entries[id]

    def _expected(self, e, revision):
        if e.review is None or revision != digest(e.review):
            raise ReviewError("StaleRevision", "The review changed. Reload its current details.")

    def analyze(self, id: str, owner: str, gpu_available: bool):
        if gpu_available is not True:
            raise ReviewError("GpuConfirmationRequired", "Close GPU-intensive games/work and explicitly confirm GPU availability.")
        with self.lock:
            e = self._get(id, owner)
            if self.busy or e.state not in ("uploaded", "failed"):
                raise ReviewError("Busy", "Another operation is active or this photo was already analyzed.")
            self.busy = True
            e.state, e.error = "analyzing", None
            e.generation += 1
            generation = e.generation
            future = self.executor.submit(self._analyze, id, owner, e.image, e.preview, generation)
            return future

    def _analyze(self, id, owner, image, png, generation):
        try:
            obs = self.observer(image, png)
            obs = parse_observation(obs.model_dump_json())
            if obs.image != image:
                raise ValueError("Wrong observation image")
            with self.lock:
                e = self._get(id, owner)
                if e.generation != generation:
                    raise ValueError("Stale analysis")
                authority = Authority(authenticated_user_id=owner, image_owner_id=e.owner, image_sha256=e.image.original_sha256)
                e.review, e.state = begin(obs, authority), "needs_review"
        except Exception as exc:
            self._failure(id, owner, exc)
        finally:
            with self.lock:
                self.busy = False

    def _failure(self, id, owner, exc):
        with self.lock:
            e = self.entries.get(id)
            if e is not None and e.owner == owner:
                e.state = "failed"
                e.raw_failure = getattr(exc, "raw_response", None)
                e.failed_model_run = getattr(exc, "model_run", None)
                e.error = {"code": exc.code, "message": exc.message} if isinstance(exc, ReviewError) else {
                    "code": "AnalysisFailed", "message": "The observation could not be validated. No review was confirmed. Try a clearer photograph; do not assume an outfit was recognized."}

    def correct(self, id, owner, revision, prediction: Prediction, changes: tuple[Correction, ...], selected_target=None):
        with self.lock:
            e = self._get(id, owner)
            self._expected(e, revision)
            if e.state in ("analyzing", "reviewing"):
                raise ReviewError("Busy", "Wait for the current operation.")
            authority = Authority(authenticated_user_id=owner, image_owner_id=e.owner, image_sha256=e.image.original_sha256)
            e.review = revise(e.review, authority, revision, prediction, changes, selected_target=selected_target)
            e.confirmation, e.result, e.error, e.state = None, None, None, "needs_review"
            return self.view(id, owner)

    def confirm(self, id, owner, revision, inventory_reviewed: bool):
        with self.lock:
            e = self._get(id, owner)
            self._expected(e, revision)
            if e.state in ("analyzing", "reviewing"):
                raise ReviewError("Busy", "Wait for the current operation.")
            e.confirmation = confirm(e.review, Authority(authenticated_user_id=owner, image_owner_id=e.owner,
                                     image_sha256=e.image.original_sha256), revision, inventory_reviewed=inventory_reviewed)
            e.result, e.error, e.state = None, None, "confirmed"
            return self.view(id, owner)

    def evaluate(self, id, owner, revision, occasion_text, use_ai=False, gpu_available=False):
        with self.lock:
            e = self._get(id, owner)
            self._expected(e, revision)
            if e.confirmation is None or e.state not in ("confirmed", "completed", "failed"):
                raise ReviewError("ConfirmationRequired", "Confirm the current outfit inventory before requesting feedback.")
            if self.busy:
                raise ReviewError("Busy", "Wait for the current operation.")
            if use_ai and (gpu_available is not True or self.judge is None):
                raise ReviewError('GpuConfirmationRequired','Confirm GPU availability before generating AI feedback, or choose the CPU-only basic summary.')
            self.busy = True
            e.state, e.error, e.result = "reviewing", None, None
            return self.executor.submit(self._evaluate, id, owner, revision, e.confirmation, occasion_text,use_ai)

    def _evaluate(self, id, owner, revision, confirmation, text,use_ai=False):
        try:
            occasion=self.occasion(text)
            result = self.judge(confirmation,occasion) if use_ai else review_outfit(confirmation,occasion)
            with self.lock:
                e = self._get(id, owner)
                self._expected(e, revision)
                e.result, e.state = result, "completed"
        except OccasionUnavailable:
            self._failure(id, owner, ReviewError("SemanticUnavailable", "The local MiniLM/spaCy assets are unavailable. Complete the existing semantic NLP setup before retrying.", 503))
        except ValueError:
            self._failure(id, owner, ReviewError("OccasionClarification", "Clarify the occasion, participant role, dress code and requirements. Unsupported meanings are not silently ignored.", 422))
        except Exception as exc:
            self._failure(id, owner, exc)
        finally:
            with self.lock:
                self.busy = False
