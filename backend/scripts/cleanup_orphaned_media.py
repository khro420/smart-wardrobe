"""Inspect or archive aged unreferenced private media.

Run without ``--apply`` first.  The apply mode deletes only opaque files that
have no retained workflow reference, then keeps their metadata as ``archived``.
"""

import argparse
import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.infrastructure.media.protected_media_store import purge_orphaned_media
from app.infrastructure.persistence.postgresql_repository import initialise_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean aged unreferenced Smart Wardrobe media.")
    parser.add_argument("--hours", type=int, default=24, help="Grace period before a file is eligible (default: 24).")
    parser.add_argument("--apply", action="store_true", help="Archive eligible files instead of only listing them.")
    args = parser.parse_args()
    initialise_database()
    candidates = purge_orphaned_media(args.hours, dry_run=not args.apply)
    print(json.dumps({"mode": "apply" if args.apply else "dry-run", "retention_hours": args.hours, "count": len(candidates), "media": candidates}, indent=2))


if __name__ == "__main__":
    main()
