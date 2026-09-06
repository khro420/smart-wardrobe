"""Download pinned official TryOffDiff dependencies and record their hashes.

The API runtime is local-only: it never downloads models during a request.
Run this script explicitly once after installing ``requirements-vtoff.txt``.
"""

from argparse import ArgumentParser
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import requests

# Avoid Xet-specific transfer behaviour on Windows; ordinary HTTPS supports the
# same pinned repository revisions and is easier to resume and audit here.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from huggingface_hub import hf_hub_download


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

TRYOFF_REPO = "rizavelioglu/tryoffdiff"
TRYOFF_REVISION = "89228bb8768c3bb5d27826dad72d384df8b5fc18"
SIGLIP_REPO = "google/siglip-base-patch16-512"
SIGLIP_REVISION = "753a949581523b60257d93e18391e8c27f72eb22"
VAE_REPO = "stabilityai/sd-vae-ft-mse"
VAE_REVISION = "31f26fdeee1355a5c34592e401dd41e45d25a493"
CHECKPOINT_SIZE = 3_438_732_841
CHECKPOINT_SHA256 = "d170fbc3a1b1802cdf23eeef162d102e2e71fb0e1d3d994cd46b5916f88db442"
SIGLIP_WEIGHT_SIZE = 815_215_944
SIGLIP_WEIGHT_SHA256 = "4ef724068f6b603c8f15937d9b93b36bbda92677e747b599dd950b6b74721ca7"
VAE_WEIGHT_SIZE = 334_643_276
VAE_WEIGHT_SHA256 = "a1d993488569e928462932c8c38a0760b874d166399b14414135bd9c42df5815"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_weight(target: Path, url: str, expected_size: int, expected_sha256: str) -> Path:
    """Resume one pinned large model asset over ordinary HTTPS."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size == expected_size and sha256(target) == expected_sha256:
        return target
    offset = target.stat().st_size if target.exists() else 0
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    with requests.get(url, headers=headers, stream=True, timeout=(30, 120)) as response:
        response.raise_for_status()
        append = offset > 0 and response.status_code == 206
        with target.open("ab" if append else "wb") as stream:
            for chunk in response.iter_content(8 * 1024 * 1024):
                if chunk:
                    stream.write(chunk)
    if target.stat().st_size != expected_size:
        raise RuntimeError(f"Incomplete model asset: {target.stat().st_size} of {expected_size} bytes")
    if sha256(target) != expected_sha256:
        raise RuntimeError(f"SHA-256 mismatch for {target.name}")
    return target


def main() -> None:
    parser = ArgumentParser(description="Install pinned official TryOffDiff v2 model assets.")
    parser.add_argument("--model-dir", type=Path, default=BACKEND / "models" / "vtoff")
    args = parser.parse_args()
    model_dir = args.model_dir.resolve()
    model_dir.mkdir(parents=True, exist_ok=True)

    checkpoint = model_dir / "tryoffdiffv2_multi.pth"
    checkpoint = download_weight(
        checkpoint,
        f"https://huggingface.co/{TRYOFF_REPO}/resolve/{TRYOFF_REVISION}/tryoffdiffv2_multi.pth?download=true",
        CHECKPOINT_SIZE, CHECKPOINT_SHA256,
    )
    scheduler_download = Path(hf_hub_download(
        repo_id=TRYOFF_REPO, filename="scheduler/scheduler_config_v2.json", revision=TRYOFF_REVISION,
        local_dir=model_dir,
    ))
    scheduler = model_dir / "scheduler_config_v2.json"
    scheduler.write_bytes(scheduler_download.read_bytes())

    siglip_dir = model_dir / "siglip-base-patch16-512"
    for filename in ("config.json", "preprocessor_config.json"):
        hf_hub_download(repo_id=SIGLIP_REPO, filename=filename, revision=SIGLIP_REVISION, local_dir=siglip_dir)
    download_weight(
        siglip_dir / "model.safetensors",
        f"https://huggingface.co/{SIGLIP_REPO}/resolve/{SIGLIP_REVISION}/model.safetensors?download=true",
        SIGLIP_WEIGHT_SIZE, SIGLIP_WEIGHT_SHA256,
    )
    vae_dir = model_dir / "sd-vae-ft-mse"
    hf_hub_download(repo_id=VAE_REPO, filename="config.json", revision=VAE_REVISION, local_dir=vae_dir)
    download_weight(
        vae_dir / "diffusion_pytorch_model.safetensors",
        f"https://huggingface.co/{VAE_REPO}/resolve/{VAE_REVISION}/diffusion_pytorch_model.safetensors?download=true",
        VAE_WEIGHT_SIZE, VAE_WEIGHT_SHA256,
    )

    files = [
        checkpoint, scheduler,
        siglip_dir / "config.json", siglip_dir / "preprocessor_config.json", siglip_dir / "model.safetensors",
        vae_dir / "config.json", vae_dir / "diffusion_pytorch_model.safetensors",
    ]
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "models": [
            {"repository": TRYOFF_REPO, "revision": TRYOFF_REVISION},
            {"repository": SIGLIP_REPO, "revision": SIGLIP_REVISION},
            {"repository": VAE_REPO, "revision": VAE_REVISION},
        ],
        "files": [
            {"path": path.relative_to(model_dir).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(set(files))
        ],
    }
    (model_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"model_dir": str(model_dir), "files": len(manifest["files"]), "status": "ready"}, indent=2))


if __name__ == "__main__":
    main()
