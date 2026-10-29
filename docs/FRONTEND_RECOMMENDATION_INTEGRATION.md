# Phase 5E frontend integration

## Boundaries and requirements

The original report's FR-HR-01–12, FR-OA-01–12 and FR-CH-01–16 govern the
homepage, single-request Assistant and completed-history workflows (report
Chapters 3–4; FYP_CONTEXT.md). Phase 5E connects the completed Phase 5A–5D APIs;
it does not change garment eligibility, NLP, selection, ranking or persistence.
The existing shared Layout, protected media component and saved-outfit area are
retained. Extraction, wardrobe, account and visualisation pages are unchanged.

## Workflows and interaction identity

- Homepage automatically POSTs `/recommendations/homepage`, displaying one complete
  returned recommendation or an explicit controlled outcome. No recommendation
  refresh control or saved-result fallback exists. Saved outfits remain a separate
  existing collection. A UUID in the current browser history entry survives reload
  and component remounts. Navigating to a new Homepage entry begins a new flow.
  Shared navigation clears copied Homepage identity on other routes while
  preserving Next's own history fields and the original entry for reload/back.
  A replay is displayed as historical, without save/visualisation actions; replay
  alone never establishes current eligibility.
- `/assistant` keeps one draft per authenticated owner in sessionStorage. Submission
  locks the original text and key. Pending duplicate requests share a promise;
  network/server retries and reload recovery reuse the same key/text. Successful
  interactions restore through the completed-chat GET API. New Chat deliberately
  creates a new UUID. Unsupported/no-result conditions do not generate substitute
  outfits. Deferred compatibility is explicitly described as unmeasured.
- `/history` submits request-text search, requests limit 50, follows the returned
  cursor, displays total and invalidates earlier search responses. New searches
  discard the previous cursor. `/history/{chat_id}` only retrieves stored content:
  original text, interpretation and ordered historical garment snapshots. Missing
  media and unavailable garments remain visible. No edit, resubmit, save or
  visualisation action is offered on historical results.

All requests retain bearer authentication. Local owner namespaces are conveniences,
not authentication; backend ownership is authoritative. Sign-out clears draft and
Homepage identity state. Session data remains tab-local and does not promise
cross-device draft recovery. Completed server history remains durable.

## API boundary additions

Authenticated GET `/recommendations/capabilities` reports the actually composed
homepage/Assistant services without generating content. Two-argument
`createRecommendation(text, key)` checks this discovery endpoint and POSTs to the
existing recommendation resource with `?pipeline=integrated`. The server rejects
that explicit mode when integration is disabled, closing a discovery/submission
race that could otherwise persist a legacy placeholder. Existing one-argument
calls and unqualified legacy backend calls retain their behaviour. No database
or response-schema migration is introduced.

`ApiError` retains HTTP status, structured outcome and original error payload.
Known outcomes receive specific UI messages. Fresh eligible recommendations reuse
existing save/visualisation API operations; those algorithms are unchanged.
Outerwear is always displayed but the existing VTON limitation is explained and
the visualisation link is withheld for such outfits.

## Local enablement

Flags remain default-off. Set these in the PowerShell session **before** starting
the backend using the existing project environment:

```powershell
$env:SMART_WARDROBE_HOMEPAGE_ENABLED = 'true'
$env:SMART_WARDROBE_ASSISTANT_ENABLED = 'true'
# Leave SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED unset unless separately intended.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run the backend command from `backend`. In another terminal, from `frontend`:

```powershell
$env:SMART_WARDROBE_BACKEND_URL = 'http://127.0.0.1:8000'
npm run dev
```

Sign in through `/auth`; use confirmed, available, owned garments. Merely creating
a `.env` file does not establish that the Python process imports it. Restart the
backend after changing flags. Approximate mandatory hexadecimal classification
and unreviewed holistic compatibility remain disabled. Suitability remains a
separately selected backend capability.

## Verification tooling and retained limitations

`npm run test:browser` starts isolated ports 3100/3101 and a temporary SQLite
fixture with synthetic users and a confirmed dress. The fixture never opens the
application's normal database. Browser tests cover mocked controlled states and
an actual backend login → Homepage → Assistant → historical archive flow.
Test screenshots/traces belong under ignored test-results/playwright-report.
The fixture's missing image is intentional and not a claim about CV quality.

The existing garment review still submits `neckline` and `sleeve_length`, which
the backend rejects (422, followed by confirmation 409). The teammate must align
review payload/model fields; this phase does not repair that workflow. The isolated
browser fixture therefore establishes frontend/API integration, not successful
normal image-upload/review/confirmation end to end.

Large-wardrobe Assistant latency remains unresolved (prior Phase 5C measurement:
about 22.53 seconds for 134,820 candidates at 200 garments). This phase does not
claim NFR-01/02/03 capacity acceptance from small browser fixtures. Save and
visualisation strict-revalidation coordination remains as documented in Phase 5A.
No long-running VTON transaction or teammate algorithm is introduced.

## Verification commands

From `frontend`:

```powershell
.\node_modules\.bin\tsc.cmd --noEmit --pretty false
npm run lint
$env:SMART_WARDROBE_BUILD_DIR = '.next-phase5e-build'
npm run build
npm run test:browser
```

Build output is isolated from the browser-test development server. Next may add
these temporary build-directory includes to tsconfig while verifying; they are
not required source-contract changes. Test harness timeouts allow local cold
compilation and are not NFR response-time acceptance thresholds.

From `backend` (exact regression invocation):

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
uv run --no-project --python 3.12 --with pytest --with fastapi --with httpx --with pillow --with python-multipart --with numpy python -B -m pytest -p no:cacheprovider tests/test_frontend_recommendation_boundary.py tests/test_chat_history.py tests/test_outfit_assistant.py tests/test_homepage_recommendation.py tests/test_recommendation_persistence.py tests/test_holistic_compatibility.py tests/test_holistic_ranking.py tests/test_preference_modelling.py tests/test_recommendation_scoring.py tests/test_candidate_ranking.py tests/test_suitability_policy.py tests/test_suitability_tag_workflow.py tests/test_suitability_evaluation.py tests/test_colour_classification.py tests/test_request_candidates.py tests/test_structural_candidates.py tests/test_nlp_interpreter.py tests/test_nlp_evaluation.py tests/test_confirmed_garment_snapshot.py tests/test_workflow.py tests/test_o2_recommendation_boundary.py tests/test_o1_wardrobe.py tests/test_garment_workflow.py tests/test_vton_contracts.py tests/test_visual_embedding.py tests/test_vtoff_standardisation.py tests/test_report_architecture.py tests/test_vtoff_adapter.py tests/test_o2_evaluation_scripts.py -q --tb=short
```

From repository root: `git diff --check`.

The backend run returned **633 passed, 1 failed**, with one existing Starlette
httpx deprecation warning, in **46.09 seconds**. The failure remains
`test_report_architecture.py::ReportArchitectureTests::test_single_backend_and_canonical_ml_locations`
(line 28), which asserts that the existing `ai-services` directory is absent.
No folder or assertion was changed to satisfy it. This is not a clean full-suite
pass. The two new API-boundary tests are included in the 633 passing tests.

Dependency installation reported 14 npm audit findings (1 moderate, 12 high,
1 critical). No pre-install baseline was established, so these are not attributed
to the new test dependency. No unrelated package upgrade or automatic audit fix
was performed.

## Phase 5E file inventory

Only the following source/configuration files were changed for this phase;
pre-existing uncommitted Phase 1–5D work is not attributed to this phase.

| File | Purpose |
| --- | --- |
| `frontend/app/page.tsx` | Automatic Homepage component; preserves hero/saved-outfit collection; links to Assistant. |
| `frontend/app/assistant/page.tsx` | Assistant route in the existing layout. |
| `frontend/app/history/page.tsx` | Completed-history search, cursor pagination and response-race protection. |
| `frontend/app/history/[chat_id]/page.tsx` | Read-only completed interaction route. |
| `frontend/components/Layout.tsx` | Adds Assistant navigation; clears copied Homepage flow state on other routes. |
| `frontend/components/HomepageRecommendation.tsx` | Automatic generation, stable-key recovery and controlled states. |
| `frontend/components/OutfitAssistant.tsx` | Single request, processing lock, same-key retry, completion recovery and New Chat. |
| `frontend/components/CompletedChatView.tsx` | Restores original text, interpretation and historical items without generation. |
| `frontend/components/RecommendationResult.tsx` | Ordered garment/media display, historical eligibility, existing fresh save/visualisation actions and limitations. |
| `frontend/lib/api.ts` | Structured errors, new API response types/helpers, guarded integrated submission and sign-out cleanup; legacy helper overload preserved. |
| `frontend/lib/recommendation-session.ts` | Owner-scoped drafts, browser-entry identity and shared pending requests. |
| `frontend/lib/recommendation-messages.ts` | Specific controlled outcome messages. |
| `frontend/package.json` | Playwright test command/development dependency. |
| `frontend/package-lock.json` | Resolved test dependencies. |
| `frontend/playwright.config.ts` | Isolated backend/frontend browser harness. |
| `frontend/tests/recommendation.spec.ts` | Browser regressions and actual backend integration. |
| `frontend/.gitignore` | Excludes browser/build verification artifacts. |
| `backend/app/api/recommendation_routes.py` | Additive capabilities discovery and explicit integrated-only guard. |
| `backend/tests/test_frontend_recommendation_boundary.py` | Default-off/authentication/no-legacy-write and capability composition checks. |
| `backend/tests/frontend_integration_server.py` | Disposable synthetic browser fixture, never the deployment database. |
| `docs/FRONTEND_RECOMMENDATION_INTEGRATION.md` | Contract, enablement, boundaries, commands, results and limitations. |
| `docs/REPORT_TRACEABILITY.md` | Phase 5E requirement-to-code/test mapping. |

Shared changes are limited to frontend API/interaction cleanup, navigation and
test dependency configuration, plus the Recommendation-owned backend route guard.
No teammate-owned processing/saving/visualisation algorithm was changed. Root
layout and tsconfig have no intended source changes; temporary build-generated
include paths are removed after verification.

## Final verification result

- TypeScript: `.\node_modules\.bin\tsc.cmd --noEmit --pretty false` passed.
- Lint: `npm run lint` passed (zero errors/warnings).
- Production build: `SMART_WARDROBE_BUILD_DIR=.next-phase5e-build npm run build`
  (PowerShell environment syntax above) passed; all 13 static pages generated,
  including Assistant/History, with dynamic completed-chat detail.
- Chromium browser suite: `npm run test:browser` passed **17/17**, in **1.3 minutes**.
  This includes the actual disposable-backend flow and mocked controlled outcomes,
  duplicate click/retry/remount, navigation identity, save API reuse, historical
  replay, search races/pagination, outerwear, missing media and sign-out cleanup.
- Focused backend: the regression command above with only
  `tests/test_frontend_recommendation_boundary.py` passed **2/2** in **2.04 seconds**.
- Full selected backend regressions: **633 passed, 1 known architecture failure**
  as detailed above. Existing Phase 1–5D contracts and wardrobe/recommendation tests
  are included; no clean full-suite result is claimed.
- `git diff --check`: passed; Git emitted only Windows LF/CRLF conversion notices.

Earlier browser attempts timed out waiting for the existing development output
cache; the harness now isolates its build directory. Initial test failures
included ambiguous alert locators (Next's hidden route announcer), navigation
synchronization (Homepage also contains an Assistant heading), and an incomplete
synthetic style fixture overwritten by existing startup initialization. These
were corrected and the full suite rerun successfully. A production-build retry
against the earlier output directory hit Windows EPERM while cleaning generated
files; the final independent `.next-phase5e-build` build passed. No source files
were deleted to work around cache or permissions issues.

Status: **PASS WITH LIMITATIONS**, ready for user review for closure. The normal
upload/review/confirmation walkthrough remains blocked by the unchanged teammate
payload mismatch. Production/capacity response-time acceptance, live VTON, and
broader device/browser testing were not established. Phase 5F is not started.
