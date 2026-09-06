"""Versioned SigLIP visual embeddings behind the report's replaceable AI port."""

from __future__ import annotations

from functools import lru_cache
import hashlib
import math
import os
from pathlib import Path
from threading import Lock
import time

from PIL import Image, ImageOps

from app.application.ports.garment_attribute_port import GarmentAttributePort
from app.domain.value_objects.garment_attributes import GarmentAttributes
from app.infrastructure.config import EMBEDDING_DEVICE, EMBEDDING_ENABLED, EMBEDDING_MODEL_DIR
from app.infrastructure.ai.gpu_runtime import gpu_inference_slot


EMBEDDING_DIMENSION = 768
EMBEDDING_MODEL_REPOSITORY = "google/siglip-base-patch16-512"
EMBEDDING_MODEL_REVISION = "753a949581523b60257d93e18391e8c27f72eb22"
EMBEDDING_MODEL_SHA256 = "4ef724068f6b603c8f15937d9b93b36bbda92677e747b599dd950b6b74721ca7"
EMBEDDING_PREPROCESSING_VERSION = "rgb-white-alpha-pad-512-bicubic-siglip-v1"


def _prepare_image(path: str | Path) -> Image.Image:
    """Apply stable alpha handling, colour conversion, aspect padding and size."""
    with Image.open(path) as source:
        rgba = source.convert("RGBA")
        white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        white.alpha_composite(rgba)
        rgb = white.convert("RGB")
    return ImageOps.pad(rgb, (512, 512), Image.Resampling.BICUBIC, color="white", centering=(0.5, 0.5))


class DevelopmentAttributeAdapter(GarmentAttributePort):
    """Explicit unavailable result for deterministic development-mode tests."""

    def extract(self, image_path: str) -> GarmentAttributes:
        return GarmentAttributes({"embedding": None, "embedding_status": "unavailable", "source": "pipeline-managed"})


class SiglipEmbeddingAdapter(GarmentAttributePort):
    """Extract a finite, L2-normalised, fixed-width visual garment vector."""

    def __init__(self, model_dir: Path = EMBEDDING_MODEL_DIR, device: str = EMBEDDING_DEVICE):
        self.model_dir = Path(model_dir)
        self.device_name = device
        self._model = None
        self._processor = None
        self._device = None
        self._dtype = None
        self._load_lock = Lock()
        self._inference_lock = Lock()

    def _load(self) -> None:
        if self._model is not None:
            return
        with self._load_lock:
            if self._model is not None:
                return
            import torch
            from transformers import SiglipImageProcessor, SiglipVisionModel

            config_path = self.model_dir / "config.json"
            weights_path = self.model_dir / "model.safetensors"
            processor_path = self.model_dir / "preprocessor_config.json"
            missing = [str(path) for path in (config_path, weights_path, processor_path) if not path.is_file()]
            if missing:
                raise FileNotFoundError("Visual embedding assets are incomplete: " + ", ".join(missing))
            digest = hashlib.sha256()
            with weights_path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != EMBEDDING_MODEL_SHA256:
                raise RuntimeError("Visual embedding weight SHA-256 does not match the pinned asset.")
            if self.device_name == "cuda" and not torch.cuda.is_available():
                raise RuntimeError("Visual embedding is configured for CUDA but CUDA is unavailable.")
            self._device = torch.device(self.device_name)
            self._dtype = torch.float16 if self._device.type == "cuda" else torch.float32
            self._processor = SiglipImageProcessor.from_pretrained(self.model_dir, local_files_only=True)
            self._model = SiglipVisionModel.from_pretrained(
                self.model_dir, local_files_only=True, torch_dtype=self._dtype, low_cpu_mem_usage=True,
            ).eval().to(self._device)
            if int(self._model.config.hidden_size) != EMBEDDING_DIMENSION:
                raise RuntimeError(f"Expected {EMBEDDING_DIMENSION}-D SigLIP output, got {self._model.config.hidden_size}.")

    def extract(self, image_path: str) -> GarmentAttributes:
        import torch

        self._load()
        prepared = _prepare_image(image_path)
        started = time.perf_counter()
        with gpu_inference_slot(), self._inference_lock:
            if self._device.type == "cuda":
                torch.cuda.reset_peak_memory_stats(self._device)
            inputs = self._processor(images=prepared, return_tensors="pt", do_resize=False)
            inputs = {key: value.to(self._device) for key, value in inputs.items()}
            with torch.inference_mode(), torch.autocast(
                device_type=self._device.type, dtype=self._dtype, enabled=self._device.type == "cuda"
            ):
                pooled = self._model(**inputs).pooler_output[0].float()
                pooled = torch.nn.functional.normalize(pooled, p=2, dim=0)
            vector = pooled.cpu().tolist()
            peak = torch.cuda.max_memory_allocated(self._device) if self._device.type == "cuda" else None
        if len(vector) != EMBEDDING_DIMENSION or any(not math.isfinite(value) for value in vector):
            raise RuntimeError("Visual embedding output is incorrectly sized or non-finite.")
        return GarmentAttributes({
            "embedding": vector,
            "embedding_status": "available",
            "embedding_dimension": EMBEDDING_DIMENSION,
            "embedding_l2_normalized": True,
            "embedding_model_repository": EMBEDDING_MODEL_REPOSITORY,
            "embedding_model_revision": EMBEDDING_MODEL_REVISION,
            "embedding_model_sha256": EMBEDDING_MODEL_SHA256,
            "embedding_preprocessing_version": EMBEDDING_PREPROCESSING_VERSION,
            "embedding_device": str(self._device),
            "embedding_latency_seconds": round(time.perf_counter() - started, 6),
            "embedding_peak_vram_bytes": peak,
        })


@lru_cache(maxsize=1)
def get_attribute_adapter() -> GarmentAttributePort:
    mode = os.getenv("SMART_WARDROBE_AI_MODE", "production").lower()
    if mode == "development" or EMBEDDING_ENABLED in {"0", "false", "off", "disabled"}:
        return DevelopmentAttributeAdapter()
    if EMBEDDING_ENABLED == "auto" and not (EMBEDDING_MODEL_DIR / "model.safetensors").is_file():
        return DevelopmentAttributeAdapter()
    return SiglipEmbeddingAdapter()
