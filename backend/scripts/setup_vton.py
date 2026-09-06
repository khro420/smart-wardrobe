"""Download pinned CatVTON assets explicitly and record every file hash."""
from argparse import ArgumentParser
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from huggingface_hub import snapshot_download

BACKEND = Path(__file__).resolve().parents[1]
CATVTON_REPO = "zhengchong/CatVTON"
CATVTON_REVISION = "2969fcf85fe62f2036605716f0b56f0b81d01d79"
BASE_REPO = "stable-diffusion-v1-5/stable-diffusion-inpainting"
BASE_REVISION = "8a4288a76071f7280aedbdb3253bdb9e9d5d84bb"
VAE_REPO = "stabilityai/sd-vae-ft-mse"
VAE_REVISION = "31f26fdeee1355a5c34592e401dd41e45d25a493"
SOURCE_REVISION = "7818397f25613beedb3d861a34769f607cfcf3b1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_tree_sha256(root: Path) -> str:
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


def main() -> None:
    parser = ArgumentParser(description="Install pinned CatVTON inference assets.")
    parser.add_argument("--model-dir", type=Path, default=BACKEND / "models" / "vton")
    args = parser.parse_args()
    model_dir = args.model_dir.resolve()
    assets = model_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    sources = (
        (
            CATVTON_REPO, CATVTON_REVISION, assets / "catvton",
            ["mix-48k-1024/**", "SCHP/**", "DensePose/**"],
        ),
        (
            BASE_REPO, BASE_REVISION, assets / "base",
            [
                "model_index.json", "scheduler/scheduler_config.json",
                "unet/config.json", "unet/diffusion_pytorch_model.fp16.safetensors",
                "feature_extractor/preprocessor_config.json",
                "safety_checker/config.json", "safety_checker/model.fp16.safetensors",
            ],
        ),
        (
            VAE_REPO, VAE_REVISION, assets / "vae",
            ["config.json", "diffusion_pytorch_model.safetensors"],
        ),
    )
    for repository, revision, target, patterns in sources:
        target.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id=repository,
            revision=revision,
            local_dir=target,
            allow_patterns=patterns,
        )
        cache = target / ".cache"
        if cache.exists():
            shutil.rmtree(cache)

    files = sorted(path for path in assets.rglob("*") if path.is_file())
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "catvton_source_revision": SOURCE_REVISION,
        "catvton_source_sha256": source_tree_sha256(BACKEND / "vendor" / "CatVTON"),
        "catvton_model_revision": CATVTON_REVISION,
        "base_model_revision": BASE_REVISION,
        "vae_revision": VAE_REVISION,
        "licences": {
            "catvton": "CC-BY-NC-SA-4.0",
            "base": "CreativeML-OpenRAIL-M",
            "vae": "MIT",
        },
        "files": [
            {
                "path": path.relative_to(model_dir).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
    }
    (model_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps({"status": "ready", "files": len(files), "model_dir": str(model_dir)}))


if __name__ == "__main__":
    main()
