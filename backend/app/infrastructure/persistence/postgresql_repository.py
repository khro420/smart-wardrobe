"""Small SQLite persistence layer used by the academic prototype.

The repository boundary deliberately keeps SQL out of HTTP routes.  SQLite makes
the project runnable locally; this module can be replaced by PostgreSQL/pgvector
without changing route or service contracts.
"""

import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from app.infrastructure.config import DATABASE_PATH, ensure_runtime_directories


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, display_name TEXT NOT NULL,
  account_status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS media_assets (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, media_type TEXT NOT NULL,
  storage_key TEXT NOT NULL UNIQUE, content_type TEXT NOT NULL, size_bytes INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'available', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS processing_jobs (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, source_media_id TEXT NOT NULL,
  status TEXT NOT NULL, error_message TEXT, created_at TEXT NOT NULL,
  started_at TEXT, updated_at TEXT NOT NULL, completed_at TEXT
);
CREATE TABLE IF NOT EXISTS processing_items (
  id TEXT PRIMARY KEY, job_id TEXT NOT NULL, detected_category TEXT NOT NULL,
  confidence REAL NOT NULL, crop_media_id TEXT NOT NULL, preferred_media_id TEXT NOT NULL,
  attributes_json TEXT NOT NULL, review_status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL, FOREIGN KEY(job_id) REFERENCES processing_jobs(id)
);
CREATE TABLE IF NOT EXISTS garments (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, processing_item_id TEXT UNIQUE,
  preferred_media_id TEXT NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL,
  primary_colour TEXT, pattern TEXT, attributes_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'available', is_favourite INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT
);
CREATE TABLE IF NOT EXISTS outfits (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, name TEXT NOT NULL, description TEXT,
  creation_type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'available',
  is_favourite INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outfit_items (
  outfit_id TEXT NOT NULL, garment_id TEXT NOT NULL, role TEXT NOT NULL, item_order INTEGER NOT NULL,
  PRIMARY KEY(outfit_id, garment_id), FOREIGN KEY(outfit_id) REFERENCES outfits(id),
  FOREIGN KEY(garment_id) REFERENCES garments(id)
);
CREATE TABLE IF NOT EXISTS user_preferences (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, preference_type TEXT NOT NULL,
  preference_value_json TEXT NOT NULL, weight REAL, source TEXT, is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS nlp_chats (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, request_text TEXT NOT NULL,
  interpreted_intent TEXT, extracted_entities_json TEXT, status TEXT NOT NULL,
  created_at TEXT NOT NULL, completed_at TEXT
);
CREATE TABLE IF NOT EXISTS recommendations (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, chat_id TEXT, recommendation_type TEXT NOT NULL,
  status TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT,
  request_match_score REAL, compatibility_score REAL, preference_score REAL, total_score REAL
);
CREATE TABLE IF NOT EXISTS recommendation_items (
  recommendation_id TEXT NOT NULL, garment_id TEXT NOT NULL, garment_role TEXT NOT NULL,
  item_order INTEGER NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY(recommendation_id, garment_id)
);
CREATE TABLE IF NOT EXISTS person_images (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, media_id TEXT NOT NULL, display_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'available', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS visualisations (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, outfit_id TEXT, recommendation_id TEXT,
  source_type TEXT NOT NULL DEFAULT 'outfit', person_image_id TEXT NOT NULL,
  output_media_id TEXT, status TEXT NOT NULL, error_message TEXT, created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, completed_at TEXT,
  CHECK ((source_type = 'outfit' AND outfit_id IS NOT NULL AND recommendation_id IS NULL)
      OR (source_type = 'recommendation' AND recommendation_id IS NOT NULL AND outfit_id IS NULL))
);
CREATE TABLE IF NOT EXISTS visualisation_items (
  visualisation_id TEXT NOT NULL, garment_id TEXT NOT NULL, source_media_id TEXT NOT NULL,
  role TEXT NOT NULL, item_order INTEGER NOT NULL,
  PRIMARY KEY(visualisation_id, garment_id)
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialise_database() -> None:
    ensure_runtime_directories()
    with connection() as conn:
        conn.executescript(SCHEMA)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "password_hash" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")
        media_columns = {row[1] for row in conn.execute("PRAGMA table_info(media_assets)")}
        for name, sql_type in (("width", "INTEGER"), ("height", "INTEGER"), ("original_filename", "TEXT")):
            if name not in media_columns:
                conn.execute(f"ALTER TABLE media_assets ADD COLUMN {name} {sql_type}")
        visualisation_columns = {row[1] for row in conn.execute("PRAGMA table_info(visualisations)").fetchall()}
        # Keep local development databases created before recommendation support
        # compatible with the report's source-type model.
        if "recommendation_id" not in visualisation_columns:
            conn.execute("ALTER TABLE visualisations ADD COLUMN recommendation_id TEXT")
        if "source_type" not in visualisation_columns:
            conn.execute("ALTER TABLE visualisations ADD COLUMN source_type TEXT NOT NULL DEFAULT 'outfit'")
        for name, sql_type in (
            ("configuration_json", "TEXT"), ("model_version", "TEXT"),
            ("started_at", "TEXT"), ("person_media_id", "TEXT"),
            ("output_kind", "TEXT"), ("metrics_json", "TEXT"),
            ("error_code", "TEXT"),
        ):
            if name not in visualisation_columns:
                conn.execute(f"ALTER TABLE visualisations ADD COLUMN {name} {sql_type}")
        conn.execute(
            "UPDATE visualisations SET output_kind='development',"
            "model_version='development-copy-v1' WHERE output_kind IS NULL "
            "AND output_media_id IN (SELECT id FROM media_assets "
            "WHERE media_type='visualisation_output_development')"
        )
        item_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(visualisation_items)")
        }
        if "category" not in item_columns:
            conn.execute("ALTER TABLE visualisation_items ADD COLUMN category TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_visualisation_queue "
            "ON visualisations(status,created_at)"
        )
        candidate_columns = {row[1] for row in conn.execute("PRAGMA table_info(processing_items)")}
        for name, sql_type in (("bounding_box", "TEXT"), ("mask_media_id", "TEXT"), ("vtoff_media_id", "TEXT"), ("embedding", "TEXT")):
            if name not in candidate_columns:
                conn.execute(f"ALTER TABLE processing_items ADD COLUMN {name} {sql_type}")
        garment_columns = {row[1] for row in conn.execute("PRAGMA table_info(garments)")}
        for name in ("secondary_colour", "style_tags", "custom_tags", "structural_scores", "additional_attributes", "embedding"):
            if name not in garment_columns:
                conn.execute(f"ALTER TABLE garments ADD COLUMN {name} TEXT")
        # Preserve existing local records while materialising the report's
        # dedicated garment fields (Figure 4.14, Table 4.5).
        for row in conn.execute("SELECT id, attributes_json FROM garments WHERE additional_attributes IS NULL").fetchall():
            attrs = json.loads(row["attributes_json"])
            conn.execute("UPDATE garments SET style_tags=?, custom_tags=?, structural_scores=?, additional_attributes=?, embedding=? WHERE id=?", (
                json.dumps(attrs.get("style")), json.dumps(attrs.get("custom_tags", [])),
                json.dumps({"garment_role": attrs.get("garment_type"), "layering_index": attrs.get("layering_index")}),
                json.dumps(attrs), json.dumps(attrs.get("embedding")), row["id"],
            ))


def ensure_user(user_id: str) -> None:
    """Create the local development user record required by ownership tables."""
    now = utcnow()
    with connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, 'active', ?, ?)",
            (user_id, f"{user_id}@local.invalid", "", "Development user", now, now),
        )


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    ensure_runtime_directories()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
