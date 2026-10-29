# A1 context relevance: local activation and owner UAT

2026-10-27, Asia/Kuala_Lumpur. **ACTIVATED; ready for owner manual testing.**

The owner accepted the [source increment](A1_CONTEXT_RELEVANCE_RANKING_VERIFICATION.md)
as PASS WITH LIMITATIONS and requested activation. Section 4 of the attached request
explicitly requires approval of the precise operation before either manual service
stops. The owner subsequently answered **“Approve this exact A1 restart.”** The
approved operation completed once, successfully. No private account was signed into
and no private wardrobe record was inspected or modified.

## 1. Verified runtime identities and sources

These pre-restart identities were freshly inspected, not adopted from an old status report.
Actual GetProcessTimes creation identities match the retained launch records; the
listener-to-parent ancestry is verified, including the backend's intermediate Python
shim. Creation times in the table are UTC.

|Role|PID|Creation time UTC|Exact creation FILETIME|
|---|---|---|---|
|Backend launch parent, uv.exe|26408|2026-10-27 09:38:07.1850910|134375674871850914|
|Backend Python shim|2788|2026-10-27 09:38:10.6833370|134375674906833370|
|Backend worker/listener, 127.0.0.1:8000|19772|2026-10-27 09:38:10.7094860|134375674907094864|
|Frontend launch parent, node.exe|81248|2026-10-27 09:38:07.4951870|134375674874951875|
|Frontend listener, ::1:3000|2232|2026-10-27 09:38:08.0332860|134375674880332869|

Only launch parents **26408 and 81248** were stopped, using the existing
creation-time-checked helper and their dedicated consoles. Both stopped with ordinary
Ctrl+C and native exit 0. Their children were recorded for identity/readiness checks.
The replacement processes are running:

|Role|PID|Creation time UTC|Exact creation FILETIME|
|---|---|---|---|
|Backend launch parent, uv.exe|28700|2026-10-27 15:33:32.2848050|134375888122848050|
|Backend Python shim|86332|2026-10-27 15:33:35.9346990|134375888159346993|
|Backend worker/listener, 127.0.0.1:8000|90644|2026-10-27 15:33:35.9632300|134375888159632303|
|Frontend launch parent, node.exe|13376|2026-10-27 15:33:32.5939900|134375888125939903|
|Frontend listener, ::1:3000|16888|2026-10-27 15:33:33.0600270|134375888130600272|

Fresh parent creation identities match updated launcher records, and verified ancestry
binds the listeners to those parents. These PIDs describe this activation, not future
permanent stop targets. **Do not start another copy; the manual services are running.**

Fresh public checks return:

- Backend health **http://127.0.0.1:8000/health**: HTTP 200.
- Sign-in **http://localhost:3000/auth**: HTTP 200; website **http://localhost:3000**.
- Unauthenticated garments/capabilities through the backend and normal frontend proxy:
  HTTP 401. Authentication remains required; this is not a login failure.

All **26 accepted production source hashes match** the retained implementation copies
and exact manifest: twenty existing transitions and six additions. Startup schema/
migration sources match the previously established gate; the actual initialization
and recovery predicates were inspected. No source implementation changed for activation.

Before restart, the old backend's seventh ranking selection was absent. After restart,
the fresh backend selects **context_relevance_decision_v1** with the accepted sources.
API version 3.0.0 or the frontend's current source alone is not the currency check.
No authenticated private capabilities or recommendation request was submitted.

## 2. Feature configuration and paths to preserve

The existing six selections were preserved. The approved start supplied all seven
as process-only values, verified on the new backend and frontend children:

|Variable|Value|
|---|---|
|`SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE`|`general_context_v1`|
|`SMART_WARDROBE_ASSISTANT_ENABLED`|`true`|
|`SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED`|`true`|
|`SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE`|`compact_exhaustive`|
|`SMART_WARDROBE_ASSISTANT_SCORING_PROFILE`|`experimental_compatibility_decision_v1`|
|**New:** `SMART_WARDROBE_ASSISTANT_CONTEXT_RANKING_PROFILE`|**`context_relevance_decision_v1`**|
|`SMART_WARDROBE_HOMEPAGE_ENABLED`|`true`|

The old baseline setting deliberately remains: the separate new selector determines
when the five ordinary requests use relative ranking, while fallback, generic and
specialist dispatch retain their accepted meanings.

The actual composition probe uses `configure_local_workflow()` and the execution
factory, not just an environment-variable check. It constructs `OutfitAssistantService`
and **CompactAssistantScorer / compact-context-relevance-1.0.0**, with its context
ranking switch true. It resolves all five objectives and loads registry **1.4.0**,
eight definitions and the five ordinary **appearance-2.0.0** policies. This probe uses
disposable paths/secret and no database requests; fresh authenticated disposable API
checks also execute the actual ranker and exact display. Combined with fresh manual
process identities, exact accepted sources and child selections, these provide bounded
activation evidence without private authenticated requests. Wedding, presentation,
interview and generic dispatch remain as accepted; no policy or source changed here.

Existing retained runtime:

```text
C:\Users\chong\AppData\Local\SmartWardrobe\manual-j22-20261024
  data\smart_wardrobe.db
  data\media
  token-secret.txt
```

Only schema/migration metadata, aggregate startup eligibility counts and filesystem
size/mtime were inspected. No private account, garment contents, preferences, chat,
image or bearer/revocation row was read. The secret's contents were not opened,
printed or copied into evidence. The existing launcher reused it internally.

Selective process inspection records only an explicit allowlist. AI/model/device,
security, data paths, proxy and other inspected nonfeature selections are preserved
for each child; absent overrides remain absent. Development identity stays off on
the backend. No manual AI-mode shortcut, auth bypass or model change occurred.
The seven launcher/settings files retain bytes; the global environment was not edited.

Frontend remains Next dev/webpack with `/api/v1` proxied to 127.0.0.1:8000 and retained
cache `.next-integration-run/manual-j22-dev-20261024`. No production build replaces
the manual development service and no cache is deleted.

## 3. Read-only startup gate and completed approved operation

The read-only gate **passes**: required schema objects/columns/indexes/triggers and
recommendation migration metadata match the current initialization requirements.

|Potential startup change|Aggregate targets|
|---|---|
|Legacy garment backfill|0|
|Visualisation backfill|0|
|Queued/processing garment recovery|0|
|Queued/processing visualisation recovery|0|

The private connection uses `mode=ro`, `query_only=ON`, a short consistent read
transaction and immediate busy failure. Expected schema/migrations are constructed
only in memory. No sidecar was present; database/media-directory/secret metadata and
the same-connection data-version observation stayed unchanged during the gate.

This proves no observed current startup targets, not permanent quiescence. It cannot
certify an unseen in-flight preference/save request will never commit afterward.
Future restarts require finishing uploads, saves and other manual writes first.

After the owner's exact approval, the guarded operation executed once:

1. Verified all recorded creation identities, unchanged launcher/settings bytes,
   accepted sources and current allowlisted selections; repeated the read-only gate.
2. Ran existing `stop.ps1` → `stop.py`, sending ordinary Ctrl+C only to the dedicated
   frontend parent **81248** and backend parent **26408**. No forced manual stop.
3. Confirmed 3000/8000 free, repeated the gate, then ran existing `start.ps1` once with
   all seven selections and preserved nonfeature configuration.
4. Verified public health/auth/proxy, fresh process creation identities, source and
   selections; inspected served full R/C/P UI markers and repeated the aggregate gate.
   Automated write smoke checks remain disposable; the owner signs in personally.

Both immediately-before-stop and immediately-before-start gates passed with all four
target counts zero. `stop.ps1` and `start.ps1` each returned native exit 0; health
readiness passed. No forced manual termination or restart retry was used. The
post-start gate also passes with all target counts zero. No migration, backfill,
private-data recovery or record repair was applied.

Observed runtime effects include log append, `last-stop.json` / `processes.json`
updates, normal startup schema-validation transactions with zero observed target
changes, and Next development cache activity. Root `tsconfig.json`, `next-env.d.ts`
and `AGENTS.md` retain their before bytes. Database, media-directory and secret-file
size/mtime metadata remain equal across the observed restart. This is bounded
schema/aggregate/metadata continuity, not inspection of private rows or photos.
These effects are distinct from application logic, schema/data migration or defaults.

The concrete guarded script is outside OneDrive at the evidence path below. It
requires an explicit approval record and refuses to repeat an attempted operation.
Its approval and native operation results are retained. It now records completed
health readiness and refuses another attempt. Do not rerun it for a future restart.

## 4. Fresh disposable readiness checks and shutdown limitation

These checks precede activation and are not post-restart/private-account results:

- Actual factory probe: native exit 0; confirms supported seven-setting composition,
  active A1 scorer construction, five objectives and retained admission versions.
- Focused disposable authenticated APIs: **2 passed in 8.82s**, native exit 0. Five
  exact winners/components, full display, unchanged garment records, immutable replay,
  normal automatic Add and disclosed supported-code fallback pass.
- Actual Chrome / accepted production Next build: **8/8 journeys passed in 47.5s**,
  native Playwright exit 0. Covers normal UI, all five contexts, full exact display,
  Unknown/fallback, preferences, Deny, history/logout, retry, narrow bounds and zoom.
  Reused build **sn7xVAp2Z2-xW4-fYg7iq** has unchanged accepted source inputs. Synthetic
  processing is disclosed; no real CV/VTOFF/VTON or private identity is used.

**The browser harness itself ended with native exit 1 during cleanup.** Its stop
sentinel requested disposable backend shutdown, but the uv/Python chain did not exit
within its 30-second wait. Its log contains Windows proactor `ConnectionResetError`
(WinError 10054); the exact cause is not established. Eight browser passes do not
turn that shutdown failure into a clean service-lifecycle result.

Cleanup verified the unique disposable command/data paths and exact creation
identities, then terminated only its owned frontend 88788 and disposable Python
worker 74480. The uv/shim parents exited afterward. No manual PID was targeted;
3100/3101 are now free. Native logs, the timeout and identity-checked cleanup are
retained. This limitation was reported before asking for manual stop/start approval.
The approved manual stop subsequently completed normally with Ctrl+C and exit 0
for both services; that does not erase this earlier disposable failure. Formal
shutdown/recovery and NFR acceptance remain open; no source fix is bundled into this task.

One inspection-helper attempt also assumed a direct uv-to-listener relationship.
The actual intermediate shim was then verified through bounded parent ancestry and
creation order. Its failed helper is retained. No service changed during that correction.

## 5. Executed post-start checks

Fresh process inspection confirms all seven selections and preservation of the
inspected nonfeature AI/security/proxy/path values. All 26 accepted production hashes
still match. Backend health, frontend `/auth` and `/assistant` return HTTP 200.
Protected garments/capabilities return 401 through both backend and same-origin proxy.
Served public JavaScript contains **assistant-scoring-display-2.0.0**, **Context
relevance ranking**, **Full R C P breakdown**, **baseline_disclosed_v1** and
**prototype defaults**. Full component rendering was exercised in the retained
disposable browser journeys; the owner's actual result view is still pending.

Protected capabilities require authentication. No private login/token fabrication
will be used to bypass that boundary. Accepted current sources, fresh child selection,
actual factory/disposable execution and public operational checks supply bounded
activation evidence. The owner's normal authenticated capabilities/result view will
provide the private manual observation; it is not pre-reported as passed.

After the approved restart, the focused disposable API smoke was repeated:
**2 passed in 6.22s**, native exit 0 (collector elapsed 10.875s). It verifies all five
requests, exact component display, no review requirement, immutable replay, automatic
Add and disclosed no-objective fallback. This overlaps the pre-start smoke and is
not an additional independent evaluation. No post-start browser run or broad regression
was added. All write checks use disposable data outside OneDrive, not the manual DB.
Live private recommendations, pictures, history and preferences remain uninspected.

## 6. Owner UAT after activation

Open **http://localhost:3000/auth** and sign
in yourself using the existing account. Confirm the wardrobe you recognise. Do not
review, edit, re-upload, add occasion tags or configure occasion profiles merely to
enable the eight existing garments.

Open **New Chat** for each request:

1. `I'm going shopping.`
2. `I'm going to class.`
3. `I'm going out with friends.`
4. `I'm going on a date tonight.`
5. `I'm meeting friends for dinner.`

Expect the understood situation and automatic casual goal for the first three,
smart-casual goal for the latter two, or your explicit supported style where supplied.
The result should contain one complete eligible outfit, constituent images/names,
exact R/C/P raw states and contributions, 3/5 / 1/5 / 1/5 weights and weighted terms,
exact total, objective authority, source limits, tie basis and coverage/fallback notes.
Unknown raw compatibility is distinct from its midpoint/no-pair decision contribution;
no preferences is not evidence that you dislike an outfit. The ranking fraction is
not a fashion-confidence percentage.

Synthetic no-preference reference expectations are Blue T-shirt / Blue Jeans for
shopping/class/outings and Navy Dress / Grey Jacket for date/dinner. **Actual private
outcomes are not guaranteed**: saved labels, current eligibility, restrictions and
global preferences were not inspected. A complete supported structure and current
owned/available/confirmed/completed links remain necessary. Missing facts can yield a
clear controlled no-result; a valid fallback must visibly identify the legacy profile.

If all five still select the same outfit, first check fresh New Chat versus history,
the displayed objective, actual profile/mode, exact components and any disclosed
fallback. Equivalent or preference-dominated winners can be legitimate. Record the
request, visible outcome and usability issue; do not relabel correct garments or
change restrictions to manufacture variety. Any account-specific inspection needs
separately named minimal read-only permission; no private repair is authorised here.

## 7. Safe stop/start guidance

**Do not execute another start while the manual services are running.** This document
does not itself authorise stopping them. For the current background launch, a later
authorised clean stop uses the existing creation-time-checked helper:

```powershell
$manualRuntime = Join-Path $env:LOCALAPPDATA 'SmartWardrobe\manual-j22-20261024'
& (Join-Path $manualRuntime 'stop.ps1')
```

For a later separately approved start, finish writes, verify actual current identities,
free ports and a fresh zero-target startup gate, then use all seven settings:

```powershell
$manualRuntime = Join-Path $env:LOCALAPPDATA 'SmartWardrobe\manual-j22-20261024'
$env:SMART_WARDROBE_ASSISTANT_CONTEXT_PROFILE = 'general_context_v1'
$env:SMART_WARDROBE_ASSISTANT_ENABLED = 'true'
$env:SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED = 'true'
$env:SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE = 'compact_exhaustive'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE = 'experimental_compatibility_decision_v1'
$env:SMART_WARDROBE_HOMEPAGE_ENABLED = 'true'
$env:SMART_WARDROBE_ASSISTANT_CONTEXT_RANKING_PROFILE = 'context_relevance_decision_v1'
& (Join-Path $manualRuntime 'start.ps1')
```

Do not run the bare Uvicorn command without the retained data/secret configuration,
delete caches/data, rotate the secret, stop processes by name, force-kill a port
owner or reuse the table's PIDs for a future launch. The guarded prepared operation
also preserves actual nonfeature child selections; an unrelated terminal's overrides
must not silently change AI/security settings during a later manual launch.

## 8. Evidence and current disposition

```text
C:\Users\chong\AppData\Local\SmartWardrobe\reviews\a1_context_relevance_activation_20261027
```

`before-runtime.json`, `source-confirmation.json`, `preflight.json`,
`operation-plan.json`, factory/API/browser outputs, cleanup evidence and prepared
`restart.py` / `verify_after.py` are retained there, together with exact approval,
stop/start results, before/after runtime identities, three operation gates, post-start
API logs and final integrity/delivery index. The original prepared report/index retain
their earlier pending state as historical evidence. No complete environment or secret
is printed. Source/launcher hashes remain reviewable.

Final integrity verifies all **555 starting scoped paths unchanged**, all 26 accepted
production hashes and seven launcher/settings hashes unchanged. This activation report
is the sole new scoped repository file. Staging is empty and its whitespace check
passes. The prepared and final evidence indexes distinguish the earlier pending state
from the completed operation; no historical implementation report was rewritten.

**Activation complete; owner's actual manual UAT results pending.** A1 selection and
the full R/C/P interface are active. The manual services remain running. No private
garment review, edit, inventory, re-upload or preference setup was performed or required
by this activation. Source closure is owner-accepted PASS WITH LIMITATIONS. No new implementation,
private wardrobe transition, model change, migration, global activation, deployment,
Git operation or next policy phase occurs here. The 155-row baseline remains
144 Verified / 2 Partial / 9 Unverified / 0 Blocked; RN-13 remains Partial, NFR-02
OPEN / NOT FORMALLY ACCEPTED and whole-FYP acceptance NOT READY. Independent human
appropriateness validation remains OPEN.
