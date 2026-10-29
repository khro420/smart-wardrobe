# Phase 5F-2E Integration verification

Date: 2026-10-19. Explicit user and teammate authorization covers confirmation and
recommendation-source action corrections only. No schema migration, inference
algorithm, candidate generation, NLP, mandatory policy, scoring/ranking, arithmetic,
compatibility tooling or policy default is changed.

## Exact file inventory

| File | Change |
|---|---|
| frontend/app/extract/results/page.tsx | Remove unsupported review keys; retain supported lists/tags/null edits. |
| frontend/components/RecommendationResult.tsx | Independent saved-state lookup with safe late-response handling; historical controls stay disabled. |
| frontend/lib/api.ts | Typed read-only saved-outfit state endpoint client. |
| frontend/tests/recommendation-actions.spec.ts | Actual browser upload/review/confirm, save/retry/unchanged replay, saved UI and preserved read-only reload; synthetic image/development AI. |
| frontend/.gitignore | Exclude only the three new isolated integration build/scratch directories; keep artifacts locally. |
| backend/app/application/recommendation/recommendation_actions.py | NEW strict complete-source validation and deterministic save ID. |
| backend/app/application/recommendation/recommendation_service.py | Atomic strict saves, durable retry behavior, immutable historical rows and separate saved-state read. Legacy selection algorithm unchanged. |
| backend/app/application/ports/recommendation_runtime.py | Injected transaction-query factory, retaining existing query API. |
| backend/app/infrastructure/workflow_runtime.py | Composition wiring for the transaction-bound factory. |
| backend/app/api/recommendation_routes.py | Owner-protected saved-outfit state GET; existing save route retained. |
| backend/app/application/visualisation/outfit_identifier_validator.py | Strict recommendation-only revalidation and supported-role checks; consistent short prepare read. |
| backend/app/application/visualisation/outfit_visualisation_service.py | Transactional execution claim; recommendation revalidation/snapshot comparison before inference, controlled unprocessable error for invalid queued sources. |
| backend/tests/test_recommendation_actions.py | NEW focused review/action, concurrency, rollback, source, history and queued-job tests. |
| backend/tests/test_phase5f_audit.py | Replace three intentionally reproduced unsafe-action expectations with strict rejection/history-preservation assertions. |
| backend/tests/test_confirmed_garment_snapshot.py | Replace old unlinked-garment save acceptance expectation with approved 409 rejection; query contract tests unchanged. |
| backend/tests/integration_source_guard.py | NEW exact approved-integration source hash validation, preserving original archive/algorithm checks. |
| backend/tests/fixtures/integration_actions_sources.v1.json | NEW exact six changed/one added application file hashes. |
| backend/tests/test_assistant_performance_equivalence.py | Retain archive/behavior oracle; account for exact integration hashes in source comparison. |
| backend/tests/test_scoring_hot_path_equivalence.py | Same narrow source-guard adjustment; scoring assertions unchanged. |
| backend/tests/test_stream_progress_equivalence.py | Same adjustment; full-stream/progress assertions unchanged. |
| backend/tests/test_score_validation_equivalence.py | Same adjustment; independent original/trial/live numeric oracle unchanged. |
| docs/RECOMMENDATION_SOURCE_ACTIONS.md | NEW contract, root causes, transaction/idempotency and limitations. |
| docs/PHASE_5F_INTEGRATION_VERIFICATION.md | NEW this inventory and evidence. |
| docs/REPORT_TRACEABILITY.md | Current integration correction traceability; earlier audit preserved as historical evidence. |

Generated build/cache/verification files are not application changes. AGENTS.md,
tsconfig.json and next-env.d.ts are backed up before Next execution and restored
byte-for-byte after verification, preserving pre-existing user changes. No source
files are reverted to Git HEAD. Temporary isolated output directories are retained.

## Root causes and corrected invariants

1. Frontend sent neckline/sleeve_length attributes forbidden by ReviewItem. Remove
   those keys, keeping their ordinary descriptive tags. No backend schema expansion
   or confirmation bypass. Preserve unchanged fit/style/material arrays and existing
   valid custom tags. Corrected null values survive review/confirmation/snapshot.
2. Saving resolved owned/available garments outside the write transaction, ignoring
   strict processing confirmation/job ownership. It now reuses the injected Phase 1
   contract under BEGIN IMMEDIATE through insertion/commit, rejecting the whole save.
3. Saving set Recommendation.status=saved. It now creates only a separate Outfit
   and ordered OutfitItems. UUIDv5 user/recommendation targeting makes concurrent
   retries durable without changing schema or original recommendation records.
4. Visualisation accepted accepted/unlinked/foreign-job references. Recommendation
   preparation/creation now use strict validation, protected media and existing VTON
   category restrictions. Unsupported outerwear is not dropped. Execution repeats
   validation and compares queued media/category/roles/order before inference.
5. A derived saved-outfit GET separates current action state from history. Legacy
   saved records remain readable; unmappable legacy re-saves and archived deterministic
   save targets return controlled 409 instead of guessing/recreating duplicates.

Eight concurrent real SQLite connections return one saved outfit. An attempted
competing archive between strict validation and insertion is blocked by the write
transaction; an archive committed before a later retry is rejected. An injected
item insert failure leaves zero outfits and unchanged Recommendation. Whole-row
comparisons cover Recommendation/items/score metadata/display snapshots/chat and
garments before and after save. Corrupt duplicate and invalid second references
cannot be silently dropped. No database transaction spans long VTON inference.

These are SQLite guarantees at validation/commit or execution-claim boundaries,
not perpetual freshness during inference or PostgreSQL deployment certification.

## Exact commands

From backend:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests/test_recommendation_actions.py tests/test_phase5f_audit.py tests/test_confirmed_garment_snapshot.py tests/test_vton_contracts.py -q --tb=short
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider --ignore=tests/test_segmentation_geometry.py -q --tb=short
```

From frontend:

```powershell
npx tsc --noEmit
npm run lint
$env:SMART_WARDROBE_BUILD_DIR='.next-integration-verification'
npm run build
npm run test:browser
```

Build variable is scoped to its command process; the Playwright config independently
uses .next-browser-verification and disposable backend database/media with flags
enabled, suitability false and development AI. Existing browser suite includes
mocked disabled/controlled states and real-backend authentication/history checks.
No production database is used for verification.

At repository root: `git diff --check`. Additional direct whitespace and frozen
reference SHA checks cover untracked files and all unchanged backend app sources.

## Results and execution limits

Final broad backend: **748 passed, 1 failed, 1 warning, 91.78 seconds**. Failure:
test_report_architecture.py:28 asserts existing ai-services must be absent. It is
unchanged; no directory or assertion was deleted. All Phase 1-4/NLP/scoring,
persistence, Homepage/Assistant/history, wardrobe, garment workflow and VTON
contract tests in this suite passed. Existing Starlette TestClient deprecation
warning remains. CV segmentation geometry is excluded for unavailable cv2/torch;
real GPU/model accuracy and PostgreSQL deployment are not tested.

Initial verification mistakes were corrected rather than treated as regressions:
a misplaced UTF-8 BOM in a changed test guard interrupted collection; a workspace-
root pytest invocation accidentally collected vendor/CV tests. Correct backend-
directory commands completed above. Early browser runs used hidden/exact-label
selectors and an incorrect saved-button expectation after read-only Homepage
replay; failures also left a disposable active outfit blocking a subsequent
archive as designed. Tests now open the details, use the actual label behavior,
preserve read-only replay expectations and release their saved-outfit dependency.
One selector-debug run was deliberately stopped; it is not counted as passed.

Frontend build uses the documented isolated directory; no unrelated files/folders
are deleted. Lint has zero errors and the two existing location.assign warnings
in extract/results and Layout. Browser Fast Refresh/NO_COLOR notices are environment
warnings, not application correctness or response-time evidence.

Normal upload-to-confirmation is verified through real backend/browser APIs in
development AI mode using a synthetic image. Separate API tests use synthetic
detector/standardisation doubles and verify strict-query inclusion, upper/lower
categories, optional nulls, material, fit/style lists and custom tags. Neither
evidence type proves genuine model segmentation/attribute/VTOFF quality. Seeded
records are used for some action/history tests and are identified as fixtures.

Historical frontend actions remain disabled, live VTON inference remains unverified,
and style-clearing representation/CV colour provenance remain outside this scope.
No compatibility/suitability/approximate-colour activation or performance stage
is started. Final frontend/focused results and source checks follow below.

## Isolated Windows browser procedure

One normal-directory development startup stalled compiling the readiness page
after concurrent verification builds. Only that identified Playwright process tree
was stopped. No unrelated server/process or directory was deleted. A generated
scratch config under .next-integration-run imports the ORIGINAL Playwright config
and changes only absolute working/test paths and the isolated build directory.
It runs exactly the existing suite plus the three new tests, with the same flags,
backend fixture server, ports, browser and assertions. Recreate it if needed:

```typescript
// frontend/.next-integration-run/playwright.config.ts (local generated artifact)
import { defineConfig } from "@playwright/test";
import path from "node:path";
import base from "../playwright.config";
const frontend = path.resolve(__dirname, "..");
const servers = Array.isArray(base.webServer) ? base.webServer : [base.webServer!];
export default defineConfig({
  ...base,
  testDir: path.join(frontend, "tests"),
  webServer: servers.map((server, index) => ({
    ...server,
    cwd: index === 0 ? path.resolve(frontend, "../backend") : frontend,
    ...(index === 1 ? { env: { ...server.env,
      SMART_WARDROBE_BUILD_DIR: ".next-integration-browser-final" } } : {}),
  })),
});
```

Final browser command from frontend:

```powershell
npx playwright test --config .next-integration-run/playwright.config.ts
```

The last browser cleanup issue was reading a network Response body again after
navigation. The test now captures its JSON before navigation; no application
logic or UI permission was changed to satisfy that test. Historical Homepage
reload deliberately hides actions, rather than showing a mutable saved button.
The saved-state endpoint, fresh save indicator and immutable recommendation
replay are verified independently.

Final focused backend run: **102 passed, 1 warning, 16.44 seconds**, including
explicit fit-array/null material/colour/pattern and retained custom-tag assertions.
Final build: exit 0, Next.js 16.4.2, 13/13 pages generated. TypeScript and lint exit
0; lint retains the two pre-existing warnings, with no errors. No dependency
version changes were made.

Source audit: 157 application files: 150 original files byte-identical to completed
2D1, six authorized integration changes and one new helper. All seven integration
entries match the separate pinned manifest. The original score file is unchanged.
All five historical reference/trial archive SHA-256 hashes remain unchanged; full
arithmetic/ranking/stream differential tests pass without regenerating fingerprints.

Final browser suite: **20 passed (1.7 minutes), exit 0** using the isolated config
above. This includes all 17 existing tests and three new tests. Both actual
browser upload/review/confirmation cases and save/retry/unchanged-replay case pass.
Original authentication, cross-user history, feature-disabled/controlled outcomes,
read-only history, Homepage random-result display and archival restoration pass.
Controlled/disabled cases use their existing mocks; successful upload/save/login
and history/archival workflows use actual local backend APIs.

Next-generated AGENTS.md, tsconfig.json and next-env.d.ts are restored byte-for-byte
to their pre-phase backups after servers/builds exit. Verification artifacts remain
under storage/verification/phase5f2e-integration and the three explicitly ignored
isolated frontend directories. No unrelated cache or user file was deleted.

Closure assessment: **PASS WITH LIMITATIONS**, ready for user review. The approved
confirmation/action defects are corrected; the remaining architecture assertion,
real-model/GPU/PostgreSQL evidence, historical frontend controls and previously
deferred functionality are not claimed resolved. No later phase is started.

After restoring generated files, TypeScript and lint were rerun successfully.
Final git diff --check exited 0 (existing LF/CRLF notices only); a direct scan of
all 24 new/modified files found zero trailing-whitespace errors. The final source
hash and restored-file byte checks also passed. artifact_manifest.json under the
verification directory records the final 24 source/document hashes.
