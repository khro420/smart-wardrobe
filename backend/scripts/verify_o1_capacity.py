"""Reproducible O1 capacity check against an isolated SQLite runtime.

Seeds the report's target of 500 garments and 1,000 outfits for one user,
exercises the real HTTP query surface, verifies integrity and schema stability,
and writes the same machine-readable result into backend/runs and
storage/verification. It never opens the normal development database.
"""

from __future__ import annotations

import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
import uuid


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
RUNS = ROOT / "backend" / "runs" / "o1"
VERIFICATION = ROOT / "storage" / "verification" / "o1"
RUNTIME_PARENT = RUNS / "isolated_runtime"
for directory in (RUNS, VERIFICATION, RUNTIME_PARENT):
    directory.mkdir(parents=True, exist_ok=True)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))]


def timing_summary(values: list[float]) -> dict[str, float]:
    return {
        "runs": len(values),
        "median_ms": round(statistics.median(values), 3),
        "p95_ms": round(percentile(values, 0.95), 3),
        "max_ms": round(max(values), 3),
    }


def schema_digest(conn) -> str:
    sql = "\n".join(
        row[0] or "" for row in conn.execute(
            "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name"
        ).fetchall()
    )
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="run-", dir=RUNTIME_PARENT) as runtime:
        os.environ["SMART_WARDROBE_DATA_DIR"] = runtime
        os.environ["SMART_WARDROBE_AI_MODE"] = "development"
        os.environ["SMART_WARDROBE_ALLOW_DEV_IDENTITY"] = "true"

        # Configuration-sensitive application imports must happen after the
        # isolated runtime has been selected.
        from fastapi.testclient import TestClient
        from app.main import app
        from app.infrastructure.media.protected_media_store import store_media_bytes
        from app.infrastructure.persistence.postgresql_repository import connection, ensure_user, initialise_database, utcnow

        from PIL import Image

        user_id = "o1-capacity-user"
        initialise_database()
        ensure_user(user_id)
        placeholder = BytesIO()
        Image.new("RGB", (32, 32), "navy").save(placeholder, "JPEG")
        media_id = store_media_bytes(placeholder.getvalue(), user_id, "garment_crop", content_type="image/jpeg")
        now = utcnow()
        garment_ids = [str(uuid.uuid4()) for _ in range(500)]
        outfit_ids = [str(uuid.uuid4()) for _ in range(1000)]
        categories = ["short_sleeve_top", "long_sleeve_top", "trousers", "shorts", "vest"]

        with connection() as conn:
            before_schema = schema_digest(conn)
            conn.executemany(
                "INSERT INTO garments (id, user_id, processing_item_id, preferred_media_id, name, category, primary_colour, pattern, attributes_json, status, is_favourite, created_at, updated_at, deleted_at, secondary_colour, style_tags, custom_tags, structural_scores, additional_attributes, embedding) "
                "VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, 'available', ?, ?, ?, NULL, NULL, ?, ?, ?, ?, NULL)",
                [
                    (
                        garment_id, user_id, media_id, f"Capacity garment {index:03d}", categories[index % len(categories)],
                        "navy" if index % 2 == 0 else "stone", "solid", json.dumps({"garment_type": "top" if index % 5 < 2 else "bottom", "fit": "regular"}),
                        int(index % 11 == 0), now, now, json.dumps(["casual"]), json.dumps(["capacity"]),
                        json.dumps({"garment_role": "garment", "layering_index": 2}), json.dumps({"fit": "regular"}),
                    )
                    for index, garment_id in enumerate(garment_ids)
                ],
            )
            conn.executemany(
                "INSERT INTO outfits VALUES (?, ?, ?, ?, 'manual', 'available', ?, ?, ?)",
                [
                    (outfit_id, user_id, f"Capacity outfit {index:04d}", f"Load-test collection {index % 10}", int(index % 17 == 0), now, now)
                    for index, outfit_id in enumerate(outfit_ids)
                ],
            )
            conn.executemany(
                "INSERT INTO outfit_items VALUES (?, ?, ?, ?)",
                [item for index, outfit_id in enumerate(outfit_ids) for item in (
                    (outfit_id, garment_ids[index % 500], "top", 1),
                    (outfit_id, garment_ids[(index + 101) % 500], "bottom", 2),
                )],
            )

        endpoints = {
            "garments_all": ("/api/v1/wardrobe/garments", 500),
            "garments_search": ("/api/v1/wardrobe/garments?query=garment%2042&sort=name_asc", 10),
            "garments_filter": ("/api/v1/wardrobe/garments?category=trousers&favourite=false&sort=favourites", 91),
            "outfits_all": ("/api/v1/wardrobe/outfits", 1000),
            "outfits_search": ("/api/v1/wardrobe/outfits?query=collection%207&sort=name_desc", 100),
            "outfits_filter": ("/api/v1/wardrobe/outfits?category=shorts&creation_type=manual", 400),
        }
        timings: dict[str, list[float]] = {name: [] for name in endpoints}
        observed: dict[str, int] = {}
        with TestClient(app, headers={"X-User-Id": user_id}) as client:
            for name, (endpoint, expected_count) in endpoints.items():
                for _ in range(10):
                    started = time.perf_counter()
                    response = client.get(endpoint)
                    timings[name].append((time.perf_counter() - started) * 1000)
                    if response.status_code != 200:
                        raise RuntimeError(f"{endpoint} returned {response.status_code}: {response.text}")
                observed[name] = len(response.json())
                if observed[name] != expected_count:
                    raise AssertionError(f"{name}: expected {expected_count}, got {observed[name]}")

        with connection() as conn:
            counts = {
                "garments": conn.execute("SELECT COUNT(*) FROM garments WHERE user_id=?", (user_id,)).fetchone()[0],
                "outfits": conn.execute("SELECT COUNT(*) FROM outfits WHERE user_id=?", (user_id,)).fetchone()[0],
                "outfit_items": conn.execute("SELECT COUNT(*) FROM outfit_items").fetchone()[0],
            }
            after_schema = schema_digest(conn)
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]

        if counts != {"garments": 500, "outfits": 1000, "outfit_items": 2000}:
            raise AssertionError(counts)
        if before_schema != after_schema or integrity != "ok":
            raise AssertionError("Capacity exercise changed the schema or database integrity.")

        result = {
            "objective": "O1 wardrobe capacity",
            "status": "passed",
            "isolated_runtime": True,
            "targets": {"garments_per_user": 500, "outfits_per_user": 1000},
            "counts": counts,
            "observed_api_result_counts": observed,
            "api_timings": {name: timing_summary(values) for name, values in timings.items()},
            "database_integrity": integrity,
            "schema_unchanged": before_schema == after_schema,
            "schema_sha256": after_schema,
            "completed_at": utcnow(),
        }
        for destination in (RUNS / "capacity.json", VERIFICATION / "capacity.json"):
            destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
