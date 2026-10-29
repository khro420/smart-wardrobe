# Automatic garment admission: local activation and owner UAT

2026-10-27, Asia/Kuala_Lumpur. **ACTIVATED; ready for owner manual testing.**
The owner accepted the implementation as PASS WITH LIMITATIONS and requested local
activation. Section 3 of the attached activation request expressly requires approval
of the precise stop/start operation before either service is stopped. The owner then
answered **“Approve this exact automatic-admission restart.”** The approved operation
completed once, successfully. No private wardrobe inspection or modification occurred.

## Activated state

**The manual application is running; do not start another copy.** Open
**http://localhost:3000/auth** and sign in yourself. Backend health at
**http://127.0.0.1:8000/health** and frontend `/auth` return HTTP 200.

The existing helper stopped both old services with ordinary Ctrl+C and native exit 0.
`stop.ps1` and `start.ps1` each returned exit 0. New launch parents are **backend 26408 /
frontend 81248**; listeners are **backend 19772 on 8000 / frontend 2232 on 3000**.
Their creation identities match updated launcher records. These are observations for
this activation, not permanent future stop targets.

Both the immediately-before-stop and immediately-before-start gates passed. A further
read-only gate after startup also passes, with all four migration/backfill/recovery
target counts still zero. DB/media-directory/secret size and modification metadata
remain equal across the observed restart. This is bounded schema/aggregate/metadata
continuity, not inspection of private records or photos.

Fresh verification confirms:

- The live public API now exposes `automatic_structural_v1` on upload and ConfirmRequest;
  before restart both fields were absent. Omitted API mode remains legacy manual.
- All 22 accepted production hashes still match. Current registry is
  **context-registry-1.4.0**; the five ordinary policies are **appearance-2.0.0**.
  Wedding, presentation and interview binding objects remain equal.
- The new backend has all six requested feature selections, correct existing DB/data
  paths and development identity off. AI/embedding/VTOFF/VTON selections match the old
  process; no full environment or secret was printed or retained.
- Served frontend bundles contain automatic Add, explanation-1.4.0, exact stored
  ranking score and visible outcome code. The normal same-origin proxy works;
  unauthenticated protected access returns 401 through both frontend and backend.
- Launcher/settings bytes and generated `tsconfig.json`, `next-env.d.ts`, `AGENTS.md`
  bytes are unchanged. Runtime logs were appended. No global setting was edited.

No authenticated private capabilities or recommendation request was submitted.
Registry/policy confirmation here is based on exact accepted sources, fresh process
selection and disposable execution; the owner's normal authenticated UI tests remain
pending. The fresh two API checks and eight Chrome journeys below preceded this one
approved restart and use the same unchanged accepted sources; they are not represented
as private-account or post-restart manual writes.

## Before-activation inspection

| Item | Fresh finding |
|---|---|
|Accepted sources|All 22 production files match the accepted automatic-admission hashes: 20 existing files and two new helpers. No production code changes.|
|Registry on disk|`context-registry-1.4.0`, eight definitions. Date/dinner/campus/shopping/casual-outing policies are `appearance-2.0.0` with provisional saved-style evidence.|
|Strict policies|Wedding, university-presentation and job-interview binding objects equal their accepted originals.|
|Backend|Launch parent **89184**, creation FILETIME **134375546904466128**; listener **8528**, creation FILETIME **134375546968279955**, on `127.0.0.1:8000`.|
|Frontend|Launch parent **89048**, creation FILETIME **134375546907575072**; listener **88624**, creation FILETIME **134375546926904874**, on `::1:3000`.|
|Launcher identity|The two launch parents match current `processes.json` creation identities. Historical `running-status.json` still describes October 24 and is not used as current liveness or account-count evidence.|
|Live availability|Backend health and frontend `/auth` return 200. Unauthenticated garment access returns 401 through both backend and normal frontend proxy; capabilities also require authentication.|
|Old backend contract|Current public OpenAPI has neither upload nor ConfirmRequest `admission_mode`. This running process has not loaded the new automatic Add contract. API version 3.0.0 alone does not identify implementation currency.|
|Current frontend|Next dev/webpack serves the new automatic Add, explanation-1.4.0, outcome and ranking-score markers from current sources. This does not upgrade the Python process.|

The actual retained paths are:

```text
C:\Users\chong\AppData\Local\SmartWardrobe\manual-j22-20261024\data\smart_wardrobe.db
C:\Users\chong\AppData\Local\SmartWardrobe\manual-j22-20261024\data\media
C:\Users\chong\AppData\Local\SmartWardrobe\manual-j22-20261024\token-secret.txt
```

Inspection did not open or print the secret. The approved launcher reused it internally
for startup without copying it into evidence. Read-only inspection used schema,
migration metadata and startup-target counts, not private account/garment/chat rows
or images. DB/media-directory/secret size and modification metadata stayed equal
through the preflight. No SQLite sidecar was present during that gate.

## Startup-effects gate

The existing gate was copied into this task's evidence directory and rerun with
`mode=ro`, `query_only=ON` and a short consistent read transaction. It compares actual
schema against the current startup schema/migrations constructed only in memory.

- Required schema objects/columns/indexes and recommendation migration marker pass.
- Garment legacy backfill targets: **0**.
- Visualisation backfill targets: **0**.
- Queued/processing garment recovery targets: **0**.
- Queued/processing visualisation recovery targets: **0**.

The inspected startup functions match these gate predicates. Startup still executes
schema validation and recovery statements; the gate establishes zero current targets,
not the absence of startup transactions. A new submission can arrive after inspection.
The prepared operation therefore reruns the gate immediately before stopping and
again before starting. Any migration/backfill/recovery requirement stops the operation;
no data repair, replacement, migration or safeguard bypass is authorised.

## Approved operation and future restart boundary

The owner approved the exact operation below. The guarded script checked the 22 source
hashes, unchanged launcher/settings files, current launch records and all four process
creation identities. It then performed these steps once:

1. Reruns the read-only gate.
2. Calls the existing `stop.ps1` → creation-time-checked `stop.py`, which sends ordinary
   Ctrl+C only to the owned frontend parent **89048** and backend parent **89184**.
   Their current listeners are **88624** and **8528**. No forced kill is used.
3. Confirms 3000/8000 are free, repeats the gate and calls existing `start.ps1` once.
4. Preserves the existing DB/media/secret and AI-mode selections, with these six
   process-only feature flags; no User/Machine environment or launcher file is edited.

```powershell
$manualRuntime = Join-Path $env:LOCALAPPDATA 'SmartWardrobe\manual-j22-20261024'
# Historical approved sequence; do not run again while services are running:
& (Join-Path $manualRuntime 'stop.ps1')
# The prepared operation checks free ports and repeats the gate here.
$env:SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE = 'general_context_v1'
$env:SMART_WARDROBE_ASSISTANT_ENABLED = 'true'
$env:SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED = 'true'
$env:SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE = 'compact_exhaustive'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE = 'experimental_compatibility_decision_v1'
$env:SMART_WARDROBE_HOMEPAGE_ENABLED = 'true'
& (Join-Path $manualRuntime 'start.ps1')
```

All six values were present in the inspected old backend and are confirmed in the
new child. Development identity remains off. AI/embedding/VTOFF/VTON overrides
were absent in the inspected old process and remain absent; their source defaults
are not changed. Frontend `/api/v1` still proxies to `http://127.0.0.1:8000`, using
the retained `.next-integration-run/manual-j22-dev-20261024` dev cache. No cache deletion,
secret rotation, model download or additional application copy is included.

Health, public API mode schema, served frontend markers, allowlisted child flags/paths
and unchanged source hashes have now been verified. A public contract plus process
selection is operational evidence; no private-identity login or recommendation
submission was performed. A normal capabilities check after the owner's sign-in should
show `context-registry-1.4.0` and eight definitions. A future restart needs a fresh
startup-effects gate, current process identities and separate stop/start authority;
do not reuse historical PIDs or force-kill a port owner.

## Legacy garments and disposable verification

Fresh focused disposable API checks: **2 passed in 8.27s**, native exit 0. Fixture-authored
replicas of the eight named demo garments produce all five ordinary recommendations
without Edit/review, and their garment records remain equal after requests. The second
check proves that changing a linked completed job to failed excludes its garment even
when the item remains marked confirmed. This is not private-row inspection or repair.

The completed-job requirement **can exclude legacy records** if their job is missing,
belongs to another owner or is not completed, or if their processing item is missing/
unconfirmed. Available display alone does not establish this join. Current saved style
can remove the human-review barrier, but cannot fix a broken processing link or invent
a missing category/style. No actual demo-record eligibility claim is made yet.

No private inspection is necessary before the owner's initial UI tests. If those tests
show an unexplained eligibility failure, seek separate permission for minimal read-only
counts scoped to the account: available/non-archived garments; matching processing-item
and job owner; item confirmation; completed job status; supported category; singleton
saved-style state and applicable restriction/malformed-evidence counts. State exact
fields/queries before access. Do not retrieve photos, passwords, tokens, chat contents
or automatically change records.

Fresh automatic Add browser smoke: **8/8 Chrome journeys passed in 47.8s**, native
exit 0, on a fresh disposable database with synthetic processing fixtures. It reuses
the accepted production build **RSaXDpBomxBO68YWyceCb**, whose inputs still match current
sources. Ordinary Add saves without review/confirm POSTs; legacy replicas, correction,
Deny, optional review/withdrawal, exact scores/history, failed-save/Cancel, logout and
native 200% zoom pass. These are overlapping workflow checks, not independent fashion
validation. Development identity is off; VTOFF/VTON are off only in this disposable
runtime. The backend stops normally with exit 0; the owned Next process is terminated
by its harness with exit 1. This is not installed-service recovery certification.

## Owner tests now ready

Open **http://localhost:3000/auth** and sign in yourself with the existing account.
Confirm the wardrobe you recognise. Do not edit/review/re-upload the eight garments
merely to enable ordinary recommendations. In Assistant choose **New Chat** before
each request:

1. `I'm going shopping.`
2. `I'm going to class.`
3. `I'm going out with friends.`
4. `I'm going on a date tonight.`
5. `I'm meeting friends for dinner.`

Each fresh request evaluates supported saved styles provisionally. Current exact Deny,
matching requested codes, ownership/availability, completed/confirmed links and complete
structure still apply. Expect either one complete outfit with names/images, an exact
overall ranking fraction and contextual assumptions, or a visible no-result reason.
Missing style can correctly yield InsufficientEvidence; a structural shortage or known
restriction has its separate outcome. Do not relabel a correct uncovered style.

**Score-display limitation:** the current accepted UI shows the overall stored ranking
fraction and compatibility contribution/details. It does not render a complete separate
request-match and preference score breakdown, although exact component metadata is
stored. This requested UAT detail is therefore not fully supported. This activation task
does not change UI code or scoring to conceal that gap. Existing no-result guidance can
also be aggregate rather than identifying every excluded garment/field.

Normal Add, after activation, explicitly requests `automatic_structural_v1`. A valid
complete processed batch should show automatically added garments and an Open wardrobe
link without mandatory Accept candidate, Save selected garments or style-review actions.
Genuinely unknown category or invalid/incomplete processing still needs correction or
an honest no-save state. Missing style may allow storage but prevent a style-dependent
recommendation. Local development/unavailable model paths are not real model inference.

Do not manufacture private failures by archiving items or changing restrictions.
Record request, visible outcome, whether the explanation is understood, and any actual
usability issue. Existing completed history remains immutable. Await the owner's actual
results; no new implementation increment is proposed here.

## Evidence and disposition

Evidence and the guarded prepared operation are outside OneDrive:

```text
C:\Users\chong\AppData\Local\SmartWardrobe\reviews\automatic_admission_activation_20261027
```

The original accepted source report/labels/results remain unchanged. A preliminary
PowerShell inline helper failed quoting before its Python body executed; an explicit
helper file prepares the disposable smoke instead. No production or private record
was changed by that failed attempt.
The first smoke invocation selected no tests because its new grep expression anchored
the test name rather than Playwright's full title. Its nonzero result remains, with
no passing test count. Correcting only that selector produced the eight passing checks;
no retries, deadline extension, production change or oracle edit was used.
The final index helper initially looked for the untouched proposal in the implementation
index instead of its original review index. Selecting the correct retained authority
fixes that helper; no source, service or earlier evidence was changed for it.

**Activation complete; owner's real manual results pending.** New local services remain
running. Private data inspection/writes, schema migration/backfill/recovery targets, model/default
changes, deployment and extensive regression are excluded. The unchanged 155-row baseline
remains 144 Verified / 2 Partial / 9 Unverified / 0 Blocked; RN-13 remains Partial,
NFR-02 remains OPEN / NOT FORMALLY ACCEPTED, and whole-FYP acceptance remains NOT READY.
