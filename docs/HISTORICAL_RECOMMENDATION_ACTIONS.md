# Historical recommendation actions: Phase 5F-2E-Integration-UI

Verification date: 2026-10-20. Scope is frontend actions and tests. No production
backend files, schema, model, selection, scoring, performance implementation or
feature-flag defaults changed.

## Requirements and behavior

Original report PDF pp.167-168 (printed156-157), FR-DW-16-20, permits saving from
History into the normal Outfits collection using existing garment references.
PDF pp.173-175, FR-CH-01-16, keeps completed interactions read-only and owner scoped.
PDF p.176, FR-VIS-01-04, requires a source reference and current validation.
Section 4.6.4, PDF p.253 (printed242), explicitly permits independent saving and
visualisation without changing the historical chat or recommendation.

CompletedChatView explicitly enables historical actions on RecommendationResult.
Homepage replay remains read-only with actions suppressed. Current Homepage and
Assistant actions continue using the shared component. Original text, interpretation,
cards, item ordering, scores and provenance are not rewritten. No action invokes
recommendation generation or creates a chat.

Saving checks owner-protected GET /recommendations/{id}/saved-outfit, then uses
POST /recommendations/{id}/save-as-outfit. The selected recommendation identifier
is the stored historical ID. The backend retains IDs, roles and order and provides
durable repeat/concurrent-save behavior. Saving is disabled until state retrieval
succeeds; failures expose a retry. A synchronous submission lock prevents duplicate
clicks. Success is shown only after HTTP success. Legacy conflicts are shown
honestly rather than inventing an outfit identifier. State is reset by recommendation
identity; effect cleanup and mounted checks prevent old responses changing another
historical result. An already-saved indicator comes from the endpoint in history.

Visualisation uses /try-on?recommendation={id}, existing prepare/create/status APIs,
and the existing result page. The backend resolves current garments, validates
strict eligibility and processes the supported recorded roles/order. Historical
snapshots never authorize processing. Known outerwear remains visible with an
unsupported explanation and no partial visualisation link. The preparation page
also synchronously guards creation and checks preparation belongs to the source.
Queued/processing, cancellation, failure/retry and completion use existing behavior.

Known unavailable records retain their history/cards but expose no usable actions.
Changes after display are rejected by the existing strict backend. Missing,
archived, unavailable, unconfirmed, unlinked and foreign garments are exercised by
backend tests; owner access is tested on the real APIs. No invalid job is created.

## File inventory for this phase

| File | Purpose |
|---|---|
| frontend/components/RecommendationResult.tsx | Explicit historical action opt-in, saved-state/error/retry/success UI, duplicate and stale-response guards. |
| frontend/components/CompletedChatView.tsx | Enable actions only for completed-chat results. |
| frontend/app/try-on/page.tsx | Synchronous create guard and source/preparation consistency guard. |
| frontend/tests/recommendation.spec.ts | Existing mocks now implement saved-state endpoint. |
| frontend/tests/historical-actions.spec.ts | Synthetic fixtures for state, save, errors, outerwear, stale source, expiry, navigation, visualisation states and retry. |
| frontend/tests/historical-actions-real.spec.ts | Real login/upload/review/confirm/Assistant/history/save/visualisation/archival APIs; synthetic images and development adapters. |
| frontend/playwright.integration.config.ts | Intentional root-level config extending existing servers with an isolated ignored Next build directory. |
| backend/tests/test_historical_recommendation_actions.py | Existing APIs: concurrent saves, SQL/API history equality, stale sources, cross-user denial, legacy conflict, supported/unsupported preparation. |
| docs/HISTORICAL_RECOMMENDATION_ACTIONS.md | This contract and verification report. |
| docs/RECOMMENDATION_SOURCE_ACTIONS.md | Link from previous action contract to this completed frontend scope. |
| docs/REPORT_TRACEABILITY.md | Requirement evidence for these historical actions. |

The repository already contains substantial uncommitted work from previous phases.
That work was preserved. All 157 production backend Python/JSON files are compared
with a before-phase SHA256 manifest under ignored storage/verification; none changed.
Existing frozen performance archives and integration source manifests are unchanged.
The earlier generated .next-integration-run/playwright.config.ts stays ignored and
is not a source deliverable. The new frontend/playwright.integration.config.ts is
intentional source configuration. Isolated browser/production build directories are
ignored. Next-generated changes to AGENTS.md, tsconfig.json and next-env.d.ts are
restored byte-for-byte from this phase's pre-build backups after Next exits.

## Verification

Commands run from backend (PowerShell):

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests/test_historical_recommendation_actions.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider --ignore=tests/test_segmentation_geometry.py -q --tb=short
```

The additional focused regression command includes action/history/contract tests:

```powershell
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests/test_historical_recommendation_actions.py tests/test_recommendation_actions.py tests/test_chat_history.py tests/test_phase5f_audit.py tests/test_confirmed_garment_snapshot.py tests/test_vton_contracts.py -q --tb=short
```

Focused action/history/contract regressions: **135 passed, 1 warning (34.13s)**.
Focused new tests: **9 passed**, 1 dependency deprecation warning (3.11s). First development run
was8 failed/1 passed because the test history adapter opened the configured default
DB rather than the test DB; corrected in the fixture, with no production change.
Broad:757 passed,1 failed (143.23s),1 dependency deprecation warning. Sole failure:
test_report_architecture.py:28 asserts ai-services does not exist, the previously
reported architecture assertion. No folders/assertions were removed or altered.
CV segmentation geometry was not executed (requires separate cv2/torch environment).

Frontend commands (frontend cwd; production build and browser run serially):

```powershell
npx tsc --noEmit
npm run lint
$env:SMART_WARDROBE_BUILD_DIR='.next-integration-run/history-ui-production'
npm run build
# New process without the preceding build environment override:
npx playwright test --config playwright.integration.config.ts
```

TypeScript passed. ESLint passed with the two existing no-location-assign-relative-
destination warnings in extract/results/page.tsx:154 and Layout.tsx:50. Isolated
production build passed, including13 routes. Final browser suite: **35 passed (2.9m)**, including real historical save and
visualisation, 14 synthetic historical-action tests, and existing Homepage,
Assistant, History, auth, onboarding and save regressions. First browser run:
29 passed/4 failed due to test alert scope and development effect replay; corrected
fixtures scoped assertions to main, made status failure deterministic, served valid
synthetic media and added processing/retry cases. No production workaround was
introduced to satisfy these tests.

Final verification after restoring generated files: `npx tsc --noEmit`,
`npm run lint`, and repository-root `git diff --check` all passed (exit 0).
Lint retained the same two existing warnings; diff check reported no whitespace
errors. All 157 backend application hashes still match, with no added/removed files.
All three restored generated config files match their pre-run backups byte-for-byte.

**Readiness: PASS WITH LIMITATIONS**, subject to final user review. Known backend
architecture assertion, live-model/deployment evidence and the pre-existing
personal-image fallback issue remain separate limitations.

## Limitations and activation boundaries

Live GPU-backed VTON quality, CV extraction quality and deployed PostgreSQL are not
certified. Browser end-to-end visualisation uses synthetic images and explicitly
marked development fallback output. Mocked tests exercise asynchronous terminal
states independently; they do not claim real model failure/cancellation timing.

An existing personal-image error fallback renders ProtectedImage's Retry image
button inside the enclosing image-selection button. Missing-media fixtures exposed
React's nested-button warning. This predates the phase and is documented for a
separate shared-image/accessibility correction; it is not changed here. Normal
actual-media end-to-end preparation and creation passed.

Existing saved legacy records without a deterministic outfit mapping still produce
the controlled 409 conflict. Revalidation failure does not edit history or silently
resubmit a request. No deployment-data inspection is claimed. Suitability remains
opt-in; approximate hexadecimal matching and experimental compatibility activation
remain disabled. No further phase is started.
