"""Lazy, local-only CatVTON inference with pinned source and assets."""
import hashlib
import json
from pathlib import Path
import sys
import time

from app.domain.value_objects.generated_visualisation import GeneratedVisualisation, VTONFailure
from app.domain.value_objects.visualisation_plan import VisualisationPlan
from app.infrastructure.ai.vton_preprocessing import encode_png, prepare_garment, prepare_person

CATVTON_SOURCE_REVISION = "7818397f25613beedb3d861a34769f607cfcf3b1"
CATVTON_MODEL_REVISION = "2969fcf85fe62f2036605716f0b56f0b81d01d79"
BASE_MODEL_REVISION = "8a4288a76071f7280aedbdb3253bdb9e9d5d84bb"
VAE_REVISION = "31f26fdeee1355a5c34592e401dd41e45d25a493"
MODEL_VERSION = f"CatVTON-mix@{CATVTON_MODEL_REVISION[:12]}"


def _source_tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(
        path for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


class CatVTONRuntime:
    def __init__(self, model_dir: Path, device: str):
        self.model_dir = Path(model_dir)
        self.device_name = device
        self._pipeline = None
        self._masker = None

    def _load(self):
        if self._pipeline is not None:
            return
        manifest_path = self.model_dir / "manifest.json"
        if not manifest_path.is_file():
            raise VTONFailure("unavailable")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = {
            "catvton_source_revision": CATVTON_SOURCE_REVISION,
            "catvton_model_revision": CATVTON_MODEL_REVISION,
            "base_model_revision": BASE_MODEL_REVISION,
            "vae_revision": VAE_REVISION,
        }
        if any(manifest.get(key) != value for key, value in expected.items()):
            raise VTONFailure("unavailable")
        assets = self.model_dir / "assets"
        for recorded in manifest.get("files", []):
            path = self.model_dir / recorded["path"]
            if not path.is_file() or path.stat().st_size != recorded["size_bytes"]:
                raise VTONFailure("unavailable")
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != recorded["sha256"]:
                raise VTONFailure("unavailable")
        source_dir = Path(__file__).resolve().parents[3] / "vendor" / "CatVTON"
        if (
            not source_dir.is_dir()
            or manifest.get("catvton_source_sha256") != _source_tree_sha256(source_dir)
        ):
            raise VTONFailure("unavailable")
        for relative in (
            "catvton/mix-48k-1024/attention/model.safetensors",
            "catvton/SCHP/exp-schp-201908261155-lip.pth",
            "catvton/SCHP/exp-schp-201908301523-atr.pth",
            "catvton/DensePose/model_final_162be9.pkl",
            "base/unet/config.json",
            "base/unet/diffusion_pytorch_model.fp16.safetensors",
            "base/safety_checker/config.json",
            "base/safety_checker/model.fp16.safetensors",
            "vae/config.json",
            "vae/diffusion_pytorch_model.safetensors",
        ):
            if not (assets / relative).is_file():
                raise VTONFailure("unavailable")
        try:
            import torch
            if self.device_name != "cuda" or not torch.cuda.is_available():
                raise VTONFailure("unavailable")
            sys.path.insert(0, str(source_dir))
            from model.cloth_masker import AutoMasker
            from model.pipeline import CatVTONPipeline
            import model.pipeline as pipeline_module

            # Upstream hard-codes the online VAE identifier. Keep request-time
            # inference local and select only the installed FP16 safetensors.
            original_vae = pipeline_module.AutoencoderKL.from_pretrained
            original_unet = pipeline_module.UNet2DConditionModel.from_pretrained
            original_safety = pipeline_module.StableDiffusionSafetyChecker.from_pretrained
            pipeline_module.AutoencoderKL.from_pretrained = lambda *a, **kw: original_vae(
                assets / "vae", local_files_only=True,
                torch_dtype=kw.get("torch_dtype"),
            )
            pipeline_module.UNet2DConditionModel.from_pretrained = lambda *a, **kw: original_unet(
                assets / "base", subfolder="unet", variant="fp16",
                use_safetensors=True, local_files_only=True,
                torch_dtype=kw.get("torch_dtype"),
            )
            pipeline_module.StableDiffusionSafetyChecker.from_pretrained = lambda *a, **kw: original_safety(
                assets / "base", subfolder="safety_checker", variant="fp16",
                use_safetensors=True, local_files_only=True,
                torch_dtype=kw.get("torch_dtype"),
            )
            try:
                self._pipeline = CatVTONPipeline(
                    base_ckpt=str(assets / "base"),
                    attn_ckpt=str(assets / "catvton"),
                    attn_ckpt_version="mix",
                    weight_dtype=torch.bfloat16,
                    device=self.device_name,
                    compile=False,
                    skip_safety_check=False,
                    use_tf32=True,
                )
            finally:
                pipeline_module.AutoencoderKL.from_pretrained = original_vae
                pipeline_module.UNet2DConditionModel.from_pretrained = original_unet
                pipeline_module.StableDiffusionSafetyChecker.from_pretrained = original_safety
            self._masker = AutoMasker(
                densepose_ckpt=str(assets / "catvton" / "DensePose"),
                schp_ckpt=str(assets / "catvton" / "SCHP"),
                device=self.device_name,
            )
        except VTONFailure:
            raise
        except Exception as exc:
            raise VTONFailure("unavailable") from exc

    def generate(
        self, plan: VisualisationPlan, person_payload: bytes, garment_payload: bytes
    ) -> GeneratedVisualisation:
        self._load()
        import torch
        size = (plan.configuration.width, plan.configuration.height)
        person = prepare_person(person_payload, size)
        garment = prepare_garment(garment_payload, size)
        started = time.perf_counter()
        try:
            torch.cuda.reset_peak_memory_stats()
            mask = self._masker(person, plan.mode)["mask"]
            if mask.size != person.size or mask.getbbox() is None:
                raise VTONFailure("unprocessable")
            generator = torch.Generator(device=self.device_name).manual_seed(
                plan.configuration.seed
            )
            result = self._pipeline(
                image=person,
                condition_image=garment,
                mask=mask,
                num_inference_steps=plan.configuration.steps,
                guidance_scale=plan.configuration.guidance,
                generator=generator,
                height=plan.configuration.height,
                width=plan.configuration.width,
            )[0]
        except torch.OutOfMemoryError as exc:
            torch.cuda.empty_cache()
            raise VTONFailure("out_of_memory") from exc
        except VTONFailure:
            raise
        except Exception as exc:
            raise VTONFailure("inference_failed") from exc
        return GeneratedVisualisation(
            image=encode_png(result),
            width=plan.configuration.width,
            height=plan.configuration.height,
            model_version=MODEL_VERSION,
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
            metadata={
                "peak_vram_bytes": torch.cuda.max_memory_allocated(),
                "device": torch.cuda.get_device_name(),
                "mode": plan.mode,
                "source_revision": CATVTON_SOURCE_REVISION,
                "model_revision": CATVTON_MODEL_REVISION,
            },
        )
