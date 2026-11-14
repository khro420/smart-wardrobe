"""Report local garment-processing prerequisites without exposing user data."""
import importlib.metadata
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.infrastructure.environment import load_local_environment
load_local_environment()


def main():
    from app.infrastructure.config import DATABASE_PATH, EMBEDDING_MODEL_DIR, MEDIA_DIR, VTOFF_MODEL_DIR
    print('Garment processing diagnostics')
    print('Python:', sys.version.split()[0])
    for package in ('torch', 'torchvision', 'ultralytics', 'opencv-python', 'transformers'):
        try:
            print(f'{package}: {importlib.metadata.version(package)}')
        except importlib.metadata.PackageNotFoundError:
            print(f'{package}: MISSING')
    try:
        import torch
        import torchvision
        print('CUDA available:', torch.cuda.is_available())
        # Check the actual compiled operator, not merely whether imports work.
        torchvision.ops.nms(torch.tensor([[0., 0., 1., 1.]]), torch.tensor([1.]), 0.5)
        print('TorchVision NMS operator: OK')
    except Exception as exc:
        print(f'Torch/TorchVision check FAILED: {type(exc).__name__}: {exc}')
    weights = BACKEND / 'models' / 'cv' / 'best.pt'
    print('Garment segmentation weights:', 'present' if weights.is_file() else 'MISSING; development fallback will be used')
    print('Optional visual embedding model:', 'present' if (EMBEDDING_MODEL_DIR / 'model.safetensors').is_file() else 'not installed; enrichment unavailable')
    print('Optional VTOFF manifest:', 'present' if (VTOFF_MODEL_DIR / 'manifest.json').is_file() else 'not installed; original crop retained')
    print('Database:', 'present' if DATABASE_PATH.is_file() else 'not created yet')
    print('Media directory:', 'present' if MEDIA_DIR.is_dir() else 'not created yet')
    print('For a failed job, check the backend terminal traceback. Do not send .env files, passwords, or personal images.')


if __name__ == '__main__':
    main()
