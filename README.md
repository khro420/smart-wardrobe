# Smart Wardrobe

This repository implements the Smart Wardrobe System described in `RSW_KhorHuaSheng_Project 1`. Its layout follows the report's three-tier deployment view and FastAPI package diagram.

## Repository layout

| Path | Report responsibility |
| --- | --- |
| `frontend/` | Mobile-responsive web Presentation Tier. It is independently built and must not be nested inside FastAPI. |
| `backend/` | The only FastAPI Application Runtime root. |
| `backend/app/` | Figure 4.8 packages: `api`, `application`, `domain`, `infrastructure`, and `shared_contracts`. |
| `backend/models/` | Versioned or locally supplied weights for the GPU-capable Python AI Inference Runtime; never application source. |
| `backend/datasets/`, `backend/scripts/`, `backend/runs/` | DeepFashion conversion inputs, reproducible training/evaluation scripts, and the one canonical experiment-output location. |
| `backend/migrations/` | PostgreSQL + pgvector schema assets for the report's Data Tier. |
| `storage/` | Generated, private local-development implementation of protected image/file storage and SQLite state. It is excluded from Git. |
| `docs/` | Report-to-repository traceability and deployment guidance. |
| `.vscode/` | Optional editor settings; no runtime or report-architecture role. |
| `venv/` | Local Python virtual environment; required only by a developer's chosen setup and excluded from Git. |

There is intentionally no root `database/`, `runs/`, duplicate Node project, or duplicate backend root. `.git/` is Git metadata; generated `frontend/node_modules/`, `frontend/.next/`, `backend/app/__pycache__/`, and `storage/` are tooling/runtime output, not report architecture.

## Run locally

The completed upload/review/save workflow, verification commands and remaining
report work are documented in [the garment workflow handoff](docs/GARMENT_WORKFLOW_HANDOFF.md).
The single-garment CatVTON runtime, contracts, measured RTX 5060 result and O3
acceptance matrix are documented in [the VTON handoff](docs/VTON_HANDOFF.md).

Open two terminals from the repository root.

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

```powershell
cd frontend
npm run dev
```

Visit `http://localhost:3000`. The image-addition workflow uploads a JPEG/PNG, creates a review-required processing job, then saves accepted candidates as garments or one outfit.

The homepage's Outfit Assistant persists the NLP request, recommendation, and recommendation items using confirmed wardrobe garments. A recommendation can be saved as an outfit or supplied directly to the visualisation workflow.

Create an account at `http://localhost:3000/auth`, then sign in. Passwords are salted and hashed; browser requests use signed, short-lived bearer tokens. The `X-User-Id` development identity exists only when `SMART_WARDROBE_ALLOW_DEV_IDENTITY=true` (the automated-test setting), never by default.

Copy `backend/.env.example` to `backend/.env` and replace `SMART_WARDROBE_TOKEN_SECRET` before any shared or public deployment.

## AI and data deployments

When weights are unavailable, the application uses a clearly marked development fallback that makes one review-required candidate; it is not presented as a segmentation prediction. Set `SMART_WARDROBE_AI_MODE=development` to force it. With `backend/models/cv/best.pt`, the YOLO pipeline under `backend/app/infrastructure/ai/cv/` is used. Its retained tight segmentation crop is kept separate from the deterministic, transparent 512 x 512 garment standardisation so the user can compare and choose the representation saved to the wardrobe.

The deployment PostgreSQL + pgvector schema is in `backend/migrations/001_initial_schema.sql`. The runnable local test configuration uses the same persistence boundary with private SQLite state in `storage/`; this avoids requiring a database server for test execution.

For real virtual try-on, install the additive dependencies and pinned local-only
assets from `backend/` with `python -m pip install -r requirements-vton.txt` and
`python scripts/setup_vton.py`. The production adapter supports exactly one top,
bottom, or dress at 768 × 1024 and clearly rejects unsupported combinations.

## Verification

```powershell
cd backend
python -m unittest tests.test_workflow
python scripts/verify_vtoff_standardisation.py --limit 15
```

```powershell
cd frontend
npm run lint
npm run build
```

## Reliability and deployment evidence

From `backend/`, inspect aged, unreferenced private media before archiving it:

```powershell
python scripts/cleanup_orphaned_media.py --hours 24
python scripts/cleanup_orphaned_media.py --hours 24 --apply
```

The first command is a dry run. The apply command archives only media with no
workflow reference after the retention period, and removes its opaque local file.

Record repeatable local API latency smoke evidence (not a capacity or model
accuracy benchmark):

```powershell
python scripts/benchmark_workflow.py --runs 5
```

When Docker is available, verify the separate PostgreSQL + pgvector deployment
migration:

```powershell
python scripts/verify_postgres_migration.py
```
