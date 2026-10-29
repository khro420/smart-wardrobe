# Owner-confirmed style: manual activation and user checks

2026-10-27, Asia/Kuala_Lumpur. **ACTIVATED; ready for owner manual testing.**
The owner accepted the implementation as PASS WITH LIMITATIONS and requested local
activation. The attached activation request explicitly requires approval of the exact
stop/start operation before stopping either manual service. The owner subsequently
answered **“Approve this exact stop/start and verification.”** That operation completed
successfully. No private wardrobe modification was performed.

The accepted implementation sources match their retained hashes. The old launch
parents (88980/89016) and listeners (9532/89640) were replaced through the existing
creation-time-checked helper. Both old services stopped with ordinary Ctrl+C and exit 0.
New launch parents are **backend 89184 / frontend 89048**; new listeners are
**backend 8528 / frontend 88624**. Their creation identities match the updated launcher
records. These PIDs describe this activation, not permanent future stop targets.

## Approved operation and future stop/start

The read-only gate was rerun before stopping and before starting. Both passed with
zero migration/backfill/recovery targets. The existing `stop.ps1` and `start.ps1`
returned exit 0, and both services reached health readiness. No forced stop was used.

**Do not start another copy now; the manual services are running.** When you choose to
stop this background launch, use the existing helper:

```powershell
$manualRuntime = Join-Path $env:LOCALAPPDATA 'SmartWardrobe\manual-j22-20261024'
& (Join-Path $manualRuntime 'stop.ps1')
```

For a future start, first finish writes, confirm a normal stop/free ports and repeat
the startup-effects gate. Then supply the same six process-only flags:

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

The existing database, media, authentication secret and revocation state are retained:

```text
C:\Users\chong\AppData\Local\SmartWardrobe\manual-j22-20261024\data\smart_wardrobe.db
C:\Users\chong\AppData\Local\SmartWardrobe\manual-j22-20261024\data\media
C:\Users\chong\AppData\Local\SmartWardrobe\manual-j22-20261024\token-secret.txt
```

AI-mode variables are unchanged. The launcher/settings files and global defaults retain
bytes. DB, media-directory and secret-file size/mtime metadata remain equal across the
restart. This is schema/aggregate/metadata continuity, not inspection of private rows or
photos. No migration, backfill, recovery, secret rotation or record repair was applied.
Runtime logs were appended; generated tsconfig/next-env/AGENTS bytes remain unchanged.

## Current findings

- Website: **http://localhost:3000**; sign-in: **http://localhost:3000/auth**, HTTP 200.
- Backend health: **http://127.0.0.1:8000/health**, HTTP 200.
- The new live backend has all six requested feature values, development identity
  off and the correct existing DB/data paths. Selective process inspection recorded
  only allowlisted settings, never the complete environment or secret.
- Before restart, the old API process lacked the new action. After restart, public
  OpenAPI exposes strict `OwnerStyleConfirmation`, contract
  **owner-style-confirmation-1.0.0**, and `style_confirmation` on both Add review and
  normal Edit payloads. The overall API version remains 3.0.0; that unchanged version
  alone is not the source check. Accepted implementation hashes also match.
- The frontend is **Next 16.4.2 dev --webpack**, using current working-tree sources and
  the retained manual cache directory. Its live public JavaScript contains the
  confirmation contract, **No outfit generated** heading and **Recommendation outcome**
  region. The normal `/api/v1` proxy points to 8000. Unauthenticated garments and
  capabilities return 401 through both backend and frontend proxy.
- Read-only schema/migration and aggregate preflight passes. Garment backfill,
  visualisation backfill, processing recovery and visualisation recovery counts are
  all **0**. No queued/processing job or visualisation was found. Database metadata
  and aggregate state were unchanged across the observed interval. This cannot
  guarantee that a new user submission will not start afterward; finish uploads/saves
  before any future restart. The gate was checked immediately before this stop/start
  and again after startup; all target counts remain zero.

## Fresh disposable smoke verification

**4/4 Chrome journeys passed in 26.5s**, native exit 0, after the approved restart.
They exercise ordinary register/login, synthetic image upload, explicit style choice,
Accept/Save, immediate shopping/class selection without a separate contextual review,
cards and exact scores, history/saving, Deny, normal Edit, Cancel, failed-save draft
preservation, stale revision, controlled unavailable/insufficient outcomes, technical
retry and native 200% zoom. No retry or increased timeout was used.

These writes use separate app.main and production Next processes on 3180/3181 with
fresh disposable accounts/data outside OneDrive. The retained verified production
build **nHOJ8kW_WvWifbyPfRU69** was reused; its source inputs still match. Development
processing is disclosed, development identity is off, and VTOFF/VTON are off only in
that disposable runtime. Manual AI modes were preserved. The smoke backend stopped
with exit 0; its owned frontend was terminated by its harness (exit 1), and verification
ports are free. The manual 3000/8000 services remain running.

This is fresh source/workflow evidence, not a recommendation submitted as the owner's
private identity. Actual eight-garment outcomes are pending the owner's interface
actions. Real model operation, fashion accuracy and formal NFR acceptance are not added.

One diagnostic environment reader initially decoded bytes beyond the UTF-16 block
terminator; it now finds the aligned terminator before decoding. Its first helper and
the dependent missing-artifact attempt are retained. This required no service restart
retry or application change; final selective process inspection succeeds.
The final port-check helper also initially assumed IPv4 for localhost while Next
listens on ::1; its dual-stack check now agrees with HTTP readiness. The original
helper is retained. No additional manual stop/start was performed for these checks.

Current-task evidence and the prepared gated restart script are outside OneDrive:
`C:\Users\chong\AppData\Local\SmartWardrobe\reviews\owner_style_activation_20261027`.
Earlier launch and implementation evidence remain unchanged.

## User checks after activation

1. Open **http://localhost:3000/auth** and sign in yourself using the existing account.
   No automated private-account login or recommendation submission is performed.
2. For a new garment: **Add an outfit** → choose the image → **Edit details and review
   image** → correct category/colour and explicitly select one accurate supported
   **Style** → **Accept candidate** → **Save selected garments**. Preserving a suggestion
   intentionally creates no style confirmation. Local image processing limitations
   still apply; do not treat its fallback as verified extraction.
3. For an existing demo garment: **My wardrobe** → **Edit** → set **Style evidence** to
   **Assigned style tags** → ensure **Styles (comma-separated)** contains exactly the
   truthful supported style → **Save changes** once. Explicitly selecting the same
   correct value is sufficient. Keeping **Preserve current value** creates no new
   confirmation. No separate **I reviewed the current style** click is needed.
4. Repeat that normal Edit only for garments you intentionally want to confirm.
   The eight synthetic examples are not automatically reviewed. To test one complete
   outfit, start with an accurate one-piece, or an upper and lower garment. A selected
   outerwear member also needs its required evidence. Do not relabel a correct style
   merely to obtain a result or add permissive occasion tags.
5. In Assistant choose **New Chat** and submit **I'm going shopping.** Then use another
   **New Chat** for **I'm going to class.** Expect one complete eligible outfit with
   cards/scores, or an obvious **No outfit generated** message with actionable guidance
   before the situation details. Explicit Deny, missing evidence or incomplete
   structure can correctly prevent a result.
6. Open successful history records to check the saved scores/explanation. Existing
   historical records remain immutable. Record your visible outcome and any usability
   problem; do not share passwords, tokens, private photos or complete private responses.

## Status and limits

Activation is complete. **Owner-confirmed admission and the updated outcome interface
are active.** The previous manual issue has a verified correction: disposable Add/Edit
supplies style evidence once, and an unmet request visibly reports its outcome before
context details. The private account was neither signed into nor modified by this task.
The eight legacy synthetic garments retain their prior evidence until the owner
intentionally confirms accurate values through the steps above. A truthful complete
eligible structure is still required. Fresh manual usability/suitability results are
pending; no further development is proposed before those results.

The original 155-row baseline stays 144 Verified / 2 Partial / 9 Unverified / 0 Blocked.
RN-13 stays Partial; NFR-02 stays OPEN / NOT FORMALLY ACCEPTED. No new policy, model,
database migration, private garment edit, bulk review, deployment or development phase
starts. Wait for the owner's own manual test results.
