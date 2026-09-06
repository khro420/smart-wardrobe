"""Runtime configuration for the Smart Wardrobe modular monolith."""

from pathlib import Path
import os


APP_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = APP_DIR.parents[1]
DATA_DIR = Path(os.getenv("SMART_WARDROBE_DATA_DIR", PROJECT_DIR / "storage"))
DATABASE_PATH = Path(os.getenv("SMART_WARDROBE_DATABASE", DATA_DIR / "smart_wardrobe.db"))
MEDIA_DIR = DATA_DIR / "media"
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", 10 * 1024 * 1024))
MIN_IMAGE_DIMENSION = int(os.getenv("MIN_IMAGE_DIMENSION", 128))
ORPHAN_MEDIA_RETENTION_HOURS = int(os.getenv("SMART_WARDROBE_ORPHAN_MEDIA_RETENTION_HOURS", 24))
VTOFF_MODEL_DIR = Path(os.getenv("SMART_WARDROBE_VTOFF_MODEL_DIR", PROJECT_DIR / "backend" / "models" / "vtoff"))
VTOFF_ENABLED = os.getenv("SMART_WARDROBE_VTOFF_ENABLED", "auto").lower()
VTOFF_DEVICE = os.getenv("SMART_WARDROBE_VTOFF_DEVICE", "cuda")
VTOFF_INFERENCE_STEPS = int(os.getenv("SMART_WARDROBE_VTOFF_STEPS", 20))
VTOFF_GUIDANCE_SCALE = float(os.getenv("SMART_WARDROBE_VTOFF_GUIDANCE", 2.0))
VTOFF_SEED = int(os.getenv("SMART_WARDROBE_VTOFF_SEED", 42))
EMBEDDING_MODEL_DIR = Path(os.getenv("SMART_WARDROBE_EMBEDDING_MODEL_DIR", VTOFF_MODEL_DIR / "siglip-base-patch16-512"))
EMBEDDING_DEVICE = os.getenv("SMART_WARDROBE_EMBEDDING_DEVICE", "cuda")
EMBEDDING_ENABLED = os.getenv("SMART_WARDROBE_EMBEDDING_ENABLED", "auto").lower()
VTON_MODEL_DIR = Path(os.getenv("SMART_WARDROBE_VTON_MODEL_DIR", PROJECT_DIR / "backend" / "models" / "vton"))
VTON_ENABLED = os.getenv("SMART_WARDROBE_VTON_ENABLED", "auto").lower()
VTON_DEVICE = os.getenv("SMART_WARDROBE_VTON_DEVICE", "cuda")
VTON_WIDTH = int(os.getenv("SMART_WARDROBE_VTON_WIDTH", 768))
VTON_HEIGHT = int(os.getenv("SMART_WARDROBE_VTON_HEIGHT", 1024))
VTON_INFERENCE_STEPS = int(os.getenv("SMART_WARDROBE_VTON_STEPS", 50))
VTON_GUIDANCE_SCALE = float(os.getenv("SMART_WARDROBE_VTON_GUIDANCE", 2.5))
VTON_SEED = int(os.getenv("SMART_WARDROBE_VTON_SEED", 42))
VTON_QUEUE_LIMIT = int(os.getenv("SMART_WARDROBE_VTON_QUEUE_LIMIT", 8))


def ensure_runtime_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
