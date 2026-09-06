"""Verify the report deployment migration against a live local PostgreSQL+pgvector service.

The FastAPI prototype intentionally uses SQLite locally.  This script validates
the separate deployment Data Tier without pretending that the local application
has switched persistence engines.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = ROOT / "backend" / "deployment" / "compose.postgres.yml"
COMPOSE = ["docker", "compose", "-f", str(COMPOSE_FILE)]
MIGRATION = ROOT / "backend" / "migrations" / "001_initial_schema.sql"
EVIDENCE = ROOT / "storage" / "verification" / "pgvector"
RUNS = ROOT / "backend" / "runs" / "pgvector"


def command(*args: str) -> str:
    result = subprocess.run([*COMPOSE, *args], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def query(sql: str) -> list[str]:
    output = command("exec", "-T", "postgres", "psql", "-U", "smart_wardrobe", "-d", "smart_wardrobe", "-Atq", "-v", "ON_ERROR_STOP=1", "-c", sql)
    return [line for line in output.splitlines() if line]


def persist(payload: dict) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    serialised = json.dumps(payload, indent=2)
    (EVIDENCE / "results.json").write_text(serialised, encoding="utf-8")
    (RUNS / "results.json").write_text(serialised, encoding="utf-8")


def static_audit() -> dict:
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    vector_columns = sql.count("embedding vector(768)")
    return {
        "migration": str(MIGRATION),
        "create_vector_extension": "create extension if not exists vector" in sql,
        "fixed_width_vector_768_columns": vector_columns,
        "expected_fixed_width_columns": 2,
        "docker_available": shutil.which("docker") is not None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Start and verify the local PostgreSQL + pgvector migration.")
    parser.add_argument("--audit-only", action="store_true", help="Run fail-closed static checks without starting PostgreSQL.")
    parser.add_argument("--no-start", action="store_true", help="Verify an already-running compose service only.")
    parser.add_argument("--leave-running", action="store_true", help="Do not stop the temporary service after verification.")
    args = parser.parse_args()
    static = static_audit()
    if not static["create_vector_extension"] or static["fixed_width_vector_768_columns"] != 2:
        payload = {"status": "failed", "created_at": datetime.now(timezone.utc).isoformat(), "static": static}
        persist(payload)
        raise RuntimeError("Static pgvector migration audit failed.")
    if args.audit_only:
        payload = {
            "status": "static_pass_live_pending" if not static["docker_available"] else "static_pass",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "static": static,
            "limitation": "A live PostgreSQL/pgvector round-trip was not run in audit-only mode.",
        }
        persist(payload)
        print(json.dumps(payload, indent=2))
        return
    if not static["docker_available"]:
        payload = {
            "status": "blocked",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "static": static,
            "blocker": "Docker is not installed or not on PATH; live PostgreSQL/pgvector verification cannot start.",
        }
        persist(payload)
        raise RuntimeError(payload["blocker"])
    started = False
    try:
        if not args.no_start:
            command("up", "-d", "postgres")
            started = True
        zero_vector = "[" + ",".join("0" for _ in range(768)) + "]"
        round_trip_sql = (
            "BEGIN;"
            "INSERT INTO app_user (user_id,email,password_hash,display_name) VALUES ('00000000-0000-0000-0000-000000000201','pgvector-audit@local.invalid','x','Audit');"
            "INSERT INTO media_asset (media_id,user_id,media_type,storage_key,mime_type,byte_size) VALUES ('00000000-0000-0000-0000-000000000202','00000000-0000-0000-0000-000000000201','garment','pgvector-audit','image/png',1);"
            "INSERT INTO processing_job (job_id,user_id,source_media_id,status) VALUES ('00000000-0000-0000-0000-000000000203','00000000-0000-0000-0000-000000000201','00000000-0000-0000-0000-000000000202','review_required');"
            f"INSERT INTO processing_item (processing_item_id,job_id,bounding_box,detected_category,confidence,preferred_media_id,embedding) VALUES ('00000000-0000-0000-0000-000000000204','00000000-0000-0000-0000-000000000203','{{}}','top',1,'00000000-0000-0000-0000-000000000202','{zero_vector}');"
            f"INSERT INTO garment (garment_id,user_id,preferred_media_id,processing_item_id,name,category,embedding) VALUES ('00000000-0000-0000-0000-000000000205','00000000-0000-0000-0000-000000000201','00000000-0000-0000-0000-000000000202','00000000-0000-0000-0000-000000000204','Audit garment','top','{zero_vector}');"
            "SELECT 'processing_item:' || vector_dims(embedding) FROM processing_item WHERE processing_item_id='00000000-0000-0000-0000-000000000204';"
            "SELECT 'garment:' || vector_dims(embedding) FROM garment WHERE garment_id='00000000-0000-0000-0000-000000000205';"
            "ROLLBACK;"
        )
        checks = {
            "pgvector_extension": query("SELECT extname FROM pg_extension WHERE extname = 'vector';"),
            "report_tables": query("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"),
            "embedding_columns": query("SELECT c.relname || '.' || a.attname || ':' || format_type(a.atttypid,a.atttypmod) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND a.attname='embedding' AND NOT a.attisdropped ORDER BY c.relname;"),
            "processing_states": query("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='processing_job'::regclass AND contype='c';"),
            "fixed_width_round_trip": query(round_trip_sql),
        }
        required_tables = {"app_user", "media_asset", "processing_job", "processing_item", "garment", "outfit", "outfit_item", "recommendation", "visualisation"}
        found_tables = set(checks["report_tables"])
        missing = sorted(required_tables - found_tables)
        expected_columns = ["garment.embedding:vector(768)", "processing_item.embedding:vector(768)"]
        expected_round_trip = ["processing_item:768", "garment:768"]
        if checks["pgvector_extension"] != ["vector"] or missing or checks["embedding_columns"] != expected_columns or checks["fixed_width_round_trip"] != expected_round_trip:
            raise RuntimeError(f"Migration verification failed; missing tables: {missing}")
        payload = {"status": "ok", "created_at": datetime.now(timezone.utc).isoformat(), "static": static, "checks": checks}
        persist(payload)
        print(json.dumps(payload, indent=2))
    finally:
        if started and not args.leave_running:
            command("down")


if __name__ == "__main__":
    main()
