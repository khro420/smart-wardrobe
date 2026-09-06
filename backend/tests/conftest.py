"""Select an isolated runtime before pytest imports any application module."""

import os
import tempfile


os.environ["SMART_WARDROBE_DATA_DIR"] = tempfile.mkdtemp(prefix="smart-wardrobe-pytest-")
os.environ["SMART_WARDROBE_AI_MODE"] = "development"
os.environ["SMART_WARDROBE_ALLOW_DEV_IDENTITY"] = "true"
