"""Local development environment loading for the application composition root."""

import os
import re
from pathlib import Path


_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_BACKEND_DIR = Path(__file__).resolve().parents[2]


def load_local_environment(path: Path | None = None) -> None:
    """Load an optional backend/.env without overriding real process settings."""
    source = path or _BACKEND_DIR / ".env"
    if not source.is_file():
        return
    for number, raw_line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid environment entry in {source} at line {number}.")
        key, value = (part.strip() for part in line.split("=", 1))
        if not _KEY.fullmatch(key):
            raise ValueError(f"Invalid environment variable name in {source} at line {number}.")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)
