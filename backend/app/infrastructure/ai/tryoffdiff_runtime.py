"""Inference runtime for the official multi-garment TryOffDiff v2 checkpoint.

Architecture and preprocessing follow the authors' official Hugging Face Space.
Weights are loaded locally with ``weights_only=True``; request handling never
downloads code or model files. Modules move through the GPU sequentially to fit
laptop VRAM, and classifier-free guidance uses two batch-one passes.
"""

from dataclasses import dataclass
from io import BytesIO
import gc
import hashlib
import json
import os
import time

import numpy as np
from PIL import Image


os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_FLAX", "0")


MODEL_REPOSITORY = "rizavelioglu/tryoffdiff"
MODEL_REVISION = "89228bb8768c3bb5d27826dad72d384df8b5fc18"
MODEL_FILENAME = "tryoffdiffv2_multi.pth"
MODEL_SHA256 = "d170fbc3a1b1802cdf23eeef162d102e2e71fb0e1d3d994cd46b5916f88db442"
MODEL_CLASS = "TryOffDiffv2"

CATEGORY_LABELS = {
    "short_sleeve_top": 0, "long_sleeve_top": 0,
    "short_sleeve_outwear": 0, "long_sleeve_outwear": 0,
    "vest": 0, "sling": 0,
    "shorts": 1, "trousers": 1, "skirt": 1,
    "short_sleeve_dress": 2, "long_sleeve_dress": 2,
    "vest_dress": 2, "sling_dress": 2,
}


@dataclass(frozen=True)
class GeneratedGarment:
    png_bytes: bytes
    latency_seconds: float
    peak_vram_bytes: int | None
    seed: int
    inference_steps: int
    guidance_scale: float


def _tryoff_model_class():
    import torch
    from diffusers import UNet2DConditionModel

    class TryOffDiffV2(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.unet = UNet2DConditionModel(
                sample_size=64, in_channels=4, out_channels=4, layers_per_block=2,
                block_out_channels=(320, 640, 1280, 1280),
                down_block_types=("CrossAttnDownBlock2D", "CrossAttnDownBlock2D", "CrossAttnDownBlock2D", "DownBlock2D"),
                up_block_types=("UpBlock2D", "CrossAttnUpBlock2D", "CrossAttnUpBlock2D", "CrossAttnUpBlock2D"),
                cross_attention_dim=768, class_embed_type=None, num_class_embeds=3,
            )
            self.proj = torch.nn.Linear(1024, 77)
            self.norm = torch.nn.LayerNorm(768)

        def forward(self, noisy_latents, timestep, conditioning, class_labels):
            conditioning = self.proj(conditioning.transpose(1, 2))
            conditioning = self.norm(conditioning.transpose(1, 2))
            return self.unet(noisy_latents, timestep, encoder_hidden_states=conditioning, class_labels=class_labels).sample

    return TryOffDiffV2


def _pad_to_square(image: Image.Image) -> Image.Image:
    rgb = np.asarray(image.convert("RGB"))
    height, width = rgb.shape[:2]
    side = max(height, width)
    top, left = (side - height) // 2, (side - width) // 2
    padded = np.pad(rgb, ((top, side - height - top), (left, side - width - left), (0, 0)), mode="edge")
    return Image.fromarray(padded).resize((512, 512), Image.Resampling.BILINEAR)


class TryOffDiffRuntime:
    """Lazy local-only generator intended to be shared behind an inference lock."""

    def __init__(self, model_dir, device: str = "cuda"):
        import torch

        self.model_dir = model_dir
        self.device = torch.device(device)
        if self.device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("VTOFF requires a CUDA-capable GPU in this configuration.")
        self.dtype = torch.float16 if self.device.type == "cuda" else torch.float32
        self._model = self._encoder = self._processor = self._vae = self._scheduler_config = None

    def _load(self):
        if self._model is not None:
            return
        import torch
        from diffusers import AutoencoderKL
        from transformers import SiglipImageProcessor, SiglipVisionModel

        checkpoint = self.model_dir / MODEL_FILENAME
        encoder_dir = self.model_dir / "siglip-base-patch16-512"
        vae_dir = self.model_dir / "sd-vae-ft-mse"
        scheduler_file = self.model_dir / "scheduler_config_v2.json"
        required = (checkpoint, encoder_dir / "config.json", vae_dir / "config.json", scheduler_file)
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise FileNotFoundError("VTOFF assets are incomplete: " + ", ".join(missing))
        digest = hashlib.sha256()
        with checkpoint.open("rb") as stream:
            for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != MODEL_SHA256:
            raise RuntimeError("VTOFF checkpoint SHA-256 does not match the pinned official asset.")

        model_type = _tryoff_model_class()
        with torch.device("meta"):
            model = model_type()
        state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
        state = {key.replace("_orig_mod.", ""): value for key, value in state.items()}
        model.load_state_dict(state, strict=True, assign=True)
        self._model = model.eval()
        self._model.unet.set_attention_slice("auto")
        del state

        self._processor = SiglipImageProcessor.from_pretrained(encoder_dir, local_files_only=True)
        self._encoder = SiglipVisionModel.from_pretrained(
            encoder_dir, local_files_only=True, torch_dtype=self.dtype, low_cpu_mem_usage=True
        ).eval()
        self._vae = AutoencoderKL.from_pretrained(
            vae_dir, local_files_only=True, torch_dtype=self.dtype, low_cpu_mem_usage=True
        ).eval()
        self._vae.enable_slicing()
        self._scheduler_config = json.loads(scheduler_file.read_text(encoding="utf-8"))

    def _release_cuda(self, module):
        import torch
        if self.device.type == "cuda":
            module.to("cpu")
            gc.collect()
            torch.cuda.empty_cache()

    def generate(self, source_path, category: str, *, seed: int = 42, guidance_scale: float = 2.0,
                 inference_steps: int = 20) -> GeneratedGarment:
        import torch
        from diffusers import EulerDiscreteScheduler

        if category not in CATEGORY_LABELS:
            raise ValueError(f"Unsupported VTOFF category: {category}")
        if not 1 <= inference_steps <= 100:
            raise ValueError("VTOFF inference steps must be between 1 and 100.")
        if not 1.0 <= guidance_scale <= 5.0:
            raise ValueError("VTOFF guidance scale must be between 1 and 5.")

        started = time.perf_counter()
        self._load()
        if self.device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(self.device)
        with Image.open(source_path) as source:
            conditioned = _pad_to_square(source)
        inputs = self._processor(images=conditioned, return_tensors="pt", do_resize=False)

        self._encoder.to(self.device, dtype=self.dtype)
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        try:
            with torch.inference_mode(), torch.autocast(device_type=self.device.type, dtype=self.dtype, enabled=self.device.type == "cuda"):
                conditioning = self._encoder(**inputs).last_hidden_state
        finally:
            self._release_cuda(self._encoder)

        scheduler = EulerDiscreteScheduler.from_config(self._scheduler_config)
        scheduler.set_timesteps(inference_steps, device=self.device)
        scheduler.is_scale_input_called = True
        generator = torch.Generator(device=self.device).manual_seed(seed)
        latent = torch.randn((1, 4, 64, 64), generator=generator, device=self.device, dtype=self.dtype)
        label = torch.tensor([CATEGORY_LABELS[category]], device=self.device, dtype=torch.int64)
        unconditional = torch.zeros_like(conditioning)

        self._model.to(self.device, dtype=self.dtype)
        try:
            with torch.inference_mode(), torch.autocast(device_type=self.device.type, dtype=self.dtype, enabled=self.device.type == "cuda"):
                for timestep in scheduler.timesteps:
                    if guidance_scale > 1:
                        unconditioned_noise = self._model(latent, timestep, unconditional, label)
                        conditioned_noise = self._model(latent, timestep, conditioning, label)
                        noise = unconditioned_noise + guidance_scale * (conditioned_noise - unconditioned_noise)
                    else:
                        noise = self._model(latent, timestep, conditioning, label)
                    scheduler_output = scheduler.step(noise, timestep, latent)
                    latent = scheduler_output.prev_sample
            prediction = scheduler_output.pred_original_sample
        finally:
            self._release_cuda(self._model)

        self._vae.to(self.device, dtype=self.dtype)
        try:
            with torch.inference_mode(), torch.autocast(device_type=self.device.type, dtype=self.dtype, enabled=self.device.type == "cuda"):
                decoded = self._vae.decode(prediction / self._vae.config.scaling_factor).sample
        finally:
            self._release_cuda(self._vae)
        if not torch.isfinite(decoded).all():
            raise RuntimeError("VTOFF produced non-finite pixels.")
        pixels = ((decoded[0] / 2 + 0.5).clamp(0, 1) * 255).byte().permute(1, 2, 0).cpu().numpy()

        if not np.isfinite(pixels).all() or pixels.std() < 2.0:
            raise RuntimeError("VTOFF produced an invalid or near-blank image.")
        output = BytesIO()
        Image.fromarray(pixels, "RGB").save(output, "PNG", optimize=True)
        peak = torch.cuda.max_memory_allocated(self.device) if self.device.type == "cuda" else None
        return GeneratedGarment(output.getvalue(), time.perf_counter() - started, peak, seed, inference_steps, guidance_scale)
