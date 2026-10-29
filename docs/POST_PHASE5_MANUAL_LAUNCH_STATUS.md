# Post-Phase-5 approved local launch

2026-10-26, Asia/Kuala_Lumpur. **RUNNING; ready for manual interaction.**
This records the subsequently approved launch. The earlier
[UAT readiness review](POST_PHASE5_MANUAL_UAT_READINESS.md) remains the historical
pre-launch assessment and contains the full manual checklist, expected outcomes,
usability findings and prioritised proposals. Its original evidence is unchanged.

## Running application

- Website: **http://localhost:3000**
- Sign in: **http://localhost:3000/auth**
- Backend: **http://127.0.0.1:8000**
- Health: **http://127.0.0.1:8000/health**
- Backend launch parent PID 17584; Uvicorn listener PID 17200.
- Frontend launch parent PID 88824; Next listener PID 88964.

These identities describe this launch, not permanent stop targets. Use the existing
creation-time-checked launcher stop command below rather than killing remembered PIDs.
Both services remain running. The isolated smoke browser was closed.

The actual current working tree is loaded by a fresh ordinary Uvicorn worker and
Next development server. No old production build or verification harness serves
the application. The existing cache directory name containing `j22` is retained;
it does not pin the source to that phase.

## Approval, data and preflight

The owner explicitly answered **“Approve gated preflight and local start.”**
Before launching, immutable read-only schema/migration-metadata/aggregate inspection
checked 25 required schema objects and the existing recommendation migration v1 marker.
Exact revocation DDL/index validation passed. Startup target counts were:

| Potential startup write | Matching records |
|---|---:|
|Legacy garment field backfill|0|
|Legacy development visualisation metadata backfill|0|
|Queued/processing garment-job recovery|0|
|Queued/processing visualisation recovery|0|

The existing initializer therefore needed no new schema migration, backfill or
interrupted-record recovery. Its normal validation transactions still execute at
startup. No database contents, photos, credentials or bearer hashes were inspected;
only schema, migration metadata and these aggregate counts were read.

Retained paths:

```text
C:\Users\chong\AppData\Local\SmartWardrobe\manual-j22-20261024\data\smart_wardrobe.db
C:\Users\chong\AppData\Local\SmartWardrobe\manual-j22-20261024\data\media
C:\Users\chong\AppData\Local\SmartWardrobe\manual-j22-20261024\token-secret.txt
```

The DB, media-directory and secret-file size/mtime metadata remained equal before
preflight and after the HTTP smoke checks. This is metadata continuity, not a row-by-row
private-data audit. No synthetic database was substituted. No secret rotation,
account creation, form submission, recommendation generation or logout write was
performed by the smoke checks. Normal user interaction will persist the user's actions.

## Effective launch selection

| Process-only variable | Value |
|---|---|
|SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE|general_context_v1|
|SMART_WARDROBE_ASSISTANT_ENABLED|true|
|SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED|true|
|SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE|compact_exhaustive|
|SMART_WARDROBE_ASSISTANT_SCORING_PROFILE|experimental_compatibility_decision_v1|
|SMART_WARDROBE_HOMEPAGE_ENABLED|true|

The existing settings retain development identity **off**, the same DB/data/secret,
frontend `/api/v1` base and backend proxy to `http://127.0.0.1:8000`. No saved launcher,
User/Machine environment, production default or AI-mode setting was edited.
The context flag is inherited only by this launch; it must be supplied again later.

A separate pure composition probe with the same launch settings constructs
`GeneralContextInterpreter`, registry `context-registry-1.3.0`, eight active bindings,
Assistant/Homepage services, exact Fraction weights `3/5,1/5,1/5` and quota 100.
It performs no lifespan/database query/model operation. This supports configuration
validation; it is not a fresh authenticated capability request against the server.

## Lightweight smoke evidence

| Check | Result |
|---|---|
|Backend health and OpenAPI|200; expected account, logout, recommendation, Homepage, history and wardrobe routes present|
|Frontend sign-in page|200|
|Unauthenticated profile/capabilities/history/garments/quota|401 on backend and same-origin frontend proxy; no bypass|
|Installed Chrome 156.0.8078.48, isolated profile|Login/Register mode controls work; browser proxy returns 401; no captured page errors; no submitted forms|
|Application business sources|Unchanged against the pre-launch source snapshot|
|Generated development typing files|Next regenerated `frontend/tsconfig.json` includes and `frontend/next-env.d.ts` imports for the retained development build directory; these generated changes remain for the running dev server|

The first new browser helper searched for `Create account` instead of the actual
`Register` mode button and timed out. Its original helper and failure record remain;
correcting that helper selector produced the successful smoke result. No application
code, timeout or policy was changed for it.

Fresh authenticated recommendation, save/history/replay and durable copied-token
logout checks are **pending user interaction**. Existing Phase 5 and J-22 evidence
remains historical support; these unauthenticated smoke checks do not re-certify it.
No full regression, benchmark or model inference was run.

## Start using it

1. Open the sign-in URL and use your existing account. Select **Register** only if
   you want to create another real local account yourself.
2. Inspect Wardrobe and truthful reusable style reviews before submitting requests.
3. Try **“I'm going shopping.”** or **“I'm going to class.”** in a new Assistant chat.
4. Follow the detailed [manual checklist](POST_PHASE5_MANUAL_UAT_READINESS.md) for
   all contexts, evidence failures, preferences, history, saving and logout.

Wedding, Date/Dinner, ordinary campus/shopping/outings and bounded university
presentation/employment interview policies are available within their approved
limits. A result still depends on your current eligible garments, evidence and a
complete compatible structure. Interview requires explicit role/code and additional
appearance observations; presentation requires an explicit role. Missing evidence
may correctly produce no recommendation. Hiking, beach, graduation and travel remain
inactive in this profile; formal/specialised/comfort capabilities are not added.

CV/attribute processing currently has development fallbacks because required model
assets/runtime dependencies are missing. Real segmentation/attribute extraction and
VTOFF reconstruction are not established; real VTON is unavailable. The existing AI
modes are retained. No large dependency or model was installed/downloaded. See the
readiness review for the exact asset/dependency findings and fallback distinctions.

## Windows stop and future start commands

**Do not start another copy while these services are running.** When you choose to
stop this background launch, run in VS Code PowerShell:

```powershell
$manualRuntime = Join-Path $env:LOCALAPPDATA 'SmartWardrobe\manual-j22-20261024'
& (Join-Path $manualRuntime 'stop.ps1')
```

The existing stop helper checks recorded process creation times and requests Ctrl+C;
it does not force-kill unrelated/reused PIDs. Confirm shutdown before starting again.
If the user has left jobs running, startup can recover them; the current zero-count
preflight is not a guarantee about a future restart. Recheck the gate when needed.

After stopping, the same background launch selection is:

```powershell
$manualRuntime = Join-Path $env:LOCALAPPDATA 'SmartWardrobe\manual-j22-20261024'
$env:SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE = 'general_context_v1'
$env:SMART_WARDROBE_ASSISTANT_ENABLED = 'true'
$env:SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED = 'true'
$env:SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE = 'compact_exhaustive'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE = 'experimental_compatibility_decision_v1'
$env:SMART_WARDROBE_HOMEPAGE_ENABLED = 'true'
& (Join-Path $manualRuntime 'start.ps1')
```

For separate visible terminals instead, set those same six variables in the backend
terminal and run `& (Join-Path $manualRuntime 'backend.ps1')`. In a second terminal,
define `$manualRuntime` as above and run `& (Join-Path $manualRuntime 'frontend.ps1')`.
Stop each visible terminal with Ctrl+C. The wrappers supply the inspected offline
backend dependencies and frontend proxy; no secret needs to be pasted into a command.
Do not combine this alternative with the background launch.

Evidence: [approved local-start artifacts](../storage/verification/post_phase5_local_start_20261026/).
No new policy, UI implementation, staging/commit/reset or deployment occurred.
The original requirements remain **144 Verified / 2 Partial / 9 Unverified**;
RN-13 remains Partial, NFR-02 remains open, and whole-FYP acceptance remains NOT READY.
