"""Run a local, attention-only CatVTON fine-tuning experiment on DressCode.

The pinned production assets are never changed.  Checkpoints and metrics are
written below ignored ``runs/``.  The manifest created by
``prepare_dresscode_finetuning.py`` is required so paired-test images can
never enter the optimizer or validation loop.
"""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import sys
import time

import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from app.infrastructure.ai.catvton_runtime import CatVTONRuntime

MASK_LABELS = {"upper_body": {4}, "lower_body": {5, 6}, "dresses": {7}}


def _load_example(row: dict, width: int, height: int):
    """Load one matched VTON target/condition/mask triple without modifying data."""
    vendor = BACKEND / "vendor" / "CatVTON"
    sys.path.insert(0, str(vendor))
    from utils import prepare_image, prepare_mask_image, resize_and_crop, resize_and_padding

    target = Image.open(row["person"]).convert("RGB")
    garment = Image.open(row["garment"]).convert("RGB")
    labels = np.asarray(Image.open(row["label_map"]).convert("L"))
    mask = Image.fromarray((np.isin(labels, list(MASK_LABELS[row["garment_group"]])) * 255).astype(np.uint8), mode="L")
    # Match the native inference geometry.  Nearest-neighbour preserves parser labels.
    target = resize_and_crop(target, (width, height))
    garment = resize_and_padding(garment, (width, height))
    mask = resize_and_crop(mask, (width, height))
    return prepare_image(target), prepare_image(garment), prepare_mask_image(mask)


def _trainable_parameters(pipeline):
    for parameter in pipeline.unet.parameters():
        parameter.requires_grad_(False)
    # CatVTON's published parameter-efficient recipe trains the attention
    # blocks, not the base UNet.  Deduplicate because named modules overlap.
    params = {}
    for module in pipeline.attn_modules:
        for parameter in module.parameters():
            parameter.requires_grad_(True)
            params[id(parameter)] = parameter
    return list(params.values())


def _loss(pipeline, row: dict, width: int, height: int) -> torch.Tensor:
    target, garment, mask = _load_example(row, width, height)
    device, dtype = pipeline.device, pipeline.weight_dtype
    target, garment, mask = target.to(device, dtype=dtype), garment.to(device, dtype=dtype), mask.to(device, dtype=dtype)
    with torch.no_grad():
        target_latent = pipeline.vae.encode(target.to(dtype=pipeline.vae.dtype)).latent_dist.sample() * pipeline.vae.config.scaling_factor
        garment_latent = pipeline.vae.encode(garment.to(dtype=pipeline.vae.dtype)).latent_dist.sample() * pipeline.vae.config.scaling_factor
        masked_target = target * (mask < 0.5)
        masked_latent = pipeline.vae.encode(masked_target.to(dtype=pipeline.vae.dtype)).latent_dist.sample() * pipeline.vae.config.scaling_factor
    mask_latent = F.interpolate(mask, size=target_latent.shape[-2:], mode="nearest")
    # This is the same vertical concatenation and channel layout used by the
    # pinned CatVTON inference pipeline.
    latent = torch.cat([target_latent, garment_latent], dim=-2)
    condition = torch.cat([masked_latent, garment_latent], dim=-2)
    mask_condition = torch.cat([mask_latent, torch.zeros_like(mask_latent)], dim=-2)
    noise = torch.randn_like(latent)
    timestep = torch.randint(0, pipeline.noise_scheduler.config.num_train_timesteps, (1,), device=device).long()
    noisy = pipeline.noise_scheduler.add_noise(latent, noise, timestep)
    prediction = pipeline.unet(torch.cat([noisy, mask_condition, condition], dim=1), timestep, encoder_hidden_states=None, return_dict=False)[0]
    if pipeline.noise_scheduler.config.prediction_type != "epsilon":
        raise RuntimeError("This training experiment supports epsilon prediction only.")
    return F.mse_loss(prediction.float(), noise.float())


def main() -> None:
    parser = ArgumentParser(description="Attention-only CatVTON DressCode fine-tuning experiment.")
    parser.add_argument("--manifest", type=Path, default=PROJECT / "storage" / "verification" / "finetuning" / "dresscode_split_manifest.json")
    parser.add_argument("--output-dir", type=Path, default=BACKEND / "runs" / "catvton_dresscode_attention")
    parser.add_argument("--max-steps", type=int, default=1, help="Start with one verified step; increase only after feasibility evidence is reviewed.")
    parser.add_argument("--width", type=int, default=384)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--seed", type=int, default=20261010)
    parser.add_argument("--checkpoint-every", type=int, default=25, help="Persist attention weights regularly so an interrupted laptop run remains usable.")
    parser.add_argument("--resume-from", type=Path, help="Optional prior experiment checkpoint.  Production CatVTON assets are never replaced.")
    args = parser.parse_args()
    if args.max_steps < 1 or args.checkpoint_every < 1 or args.width % 8 or args.height % 8:
        raise SystemExit("--max-steps and --checkpoint-every must be positive and dimensions must be divisible by 8.")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("status") != "ok" or not manifest.get("operator_license_confirmed_for_academic_finetuning"):
        raise SystemExit("A valid, operator-confirmed local training manifest is required.")
    records = manifest["records"]
    if not records["train"] or not records["validation"]:
        raise SystemExit("Training and validation records are both required.")
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.cuda.empty_cache()
    runtime = CatVTONRuntime(BACKEND / "models" / "vton", "cuda")
    runtime._load()  # The runtime verifies the pinned source and every asset hash first.
    pipeline = runtime._pipeline
    pipeline.unet.train()
    pipeline.vae.eval()
    pipeline.unet.enable_gradient_checkpointing()
    params = _trainable_parameters(pipeline)
    resumed_steps = 0
    if args.resume_from:
        if not args.resume_from.is_file():
            raise FileNotFoundError(f"Resume checkpoint not found: {args.resume_from}")
        resume = torch.load(args.resume_from, map_location="cpu", weights_only=True)
        state = resume.get("attention_state_dict")
        if not isinstance(state, dict):
            raise RuntimeError("Resume checkpoint does not contain attention_state_dict.")
        pipeline.attn_modules.load_state_dict(state, strict=True)
        resumed_steps = int(resume.get("steps", 0))
    optimizer = torch.optim.AdamW(params, lr=args.learning_rate)
    rng = random.Random(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    torch.cuda.reset_peak_memory_stats()
    started, losses = time.perf_counter(), []
    try:
        for step in range(args.max_steps):
            row = rng.choice(records["train"])
            optimizer.zero_grad(set_to_none=True)
            loss = _loss(pipeline, row, args.width, args.height)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            optimizer.step()
            losses.append(round(float(loss.detach().cpu()), 7))
            if (step + 1) % args.checkpoint_every == 0:
                torch.save({"attention_state_dict": pipeline.attn_modules.state_dict(), "steps": resumed_steps + step + 1, "seed": args.seed, "width": args.width, "height": args.height}, args.output_dir / f"attention_step_{resumed_steps + step + 1}.pt")
    except torch.OutOfMemoryError as exc:
        torch.cuda.empty_cache()
        raise RuntimeError("CUDA out of memory: do not begin a longer fine-tuning run at this profile.") from exc
    finally:
        pipeline.unet.eval()
    checkpoint = args.output_dir / "attention_experiment.pt"
    total_steps = resumed_steps + args.max_steps
    torch.save({"attention_state_dict": pipeline.attn_modules.state_dict(), "optimizer_state_dict": optimizer.state_dict(), "steps": total_steps, "seed": args.seed, "width": args.width, "height": args.height}, checkpoint)
    result = {"status": "feasible", "kind": "CatVTON attention-only local fine-tuning feasibility run", "completed_at": datetime.now(timezone.utc).isoformat(), "manifest": str(args.manifest), "test_examples_used": 0, "checkpoint": str(checkpoint), "resumed_from": str(args.resume_from) if args.resume_from else None, "configuration": {"max_steps": args.max_steps, "total_steps": total_steps, "width": args.width, "height": args.height, "learning_rate": args.learning_rate, "seed": args.seed}, "trainable_parameters": sum(parameter.numel() for parameter in params), "losses": losses, "latency_seconds": round(time.perf_counter() - started, 3), "peak_vram_bytes": torch.cuda.max_memory_allocated(), "limitations": ["This is a feasibility run, not a quality claim.", "The production CatVTON manifest and assets were not changed.", "Paired-test examples were not used in optimisation.", "Reconstruction metrics do not establish physical-fit accuracy."]}
    (args.output_dir / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
