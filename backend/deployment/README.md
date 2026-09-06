# Deployment mapping - Figure 4.13

| Deployment node in the report | Repository responsibility |
| --- | --- |
| Registered User Device / Supported Web Browser | `frontend/` build served to a browser |
| FastAPI Application Runtime | `backend/app/main.py`, API/application/domain packages |
| GPU-capable Python AI Inference Runtime | `backend/app/infrastructure/ai/` and `backend/models/` |
| PostgreSQL + pgvector | Provision from `backend/migrations/001_initial_schema.sql` |
| Protected Image / File Storage | Configure private object/file storage through `backend/app/infrastructure/media/protected_media_store.py` |

The browser never accesses model weights, database credentials, PostgreSQL, or protected storage directly. It communicates only with the FastAPI HTTP boundary.

For a local PostgreSQL + pgvector Data Tier, run `docker compose -f backend/deployment/compose.postgres.yml up -d`. Set a non-default database password before any non-local deployment.

Verify that the deployment migration creates the required pgvector extension,
tables, embedding columns, and processing-state constraint:

```powershell
cd backend
python scripts/verify_postgres_migration.py
```

The local FastAPI prototype remains explicitly SQLite-backed. The verification
script validates the separately deployed PostgreSQL data tier; it does not claim
the prototype has been switched to PostgreSQL.
