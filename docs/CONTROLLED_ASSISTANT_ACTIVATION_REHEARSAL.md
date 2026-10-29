# Phase 5F-2E-3J-13: controlled Assistant activation and rollback rehearsal

2026-10-23, Asia/Kuala_Lumpur. **PASS WITH LIMITATIONS; ready for owner review.**
J-12 is owner-closed PASS WITH LIMITATIONS. This phase activated only isolated
local child processes against disposable SQLite databases. Production sources,
unset defaults, installed deployment settings, real user records, database
provider and CV/VTON implementations remain unchanged. No capacity/optimisation
experiment or formal NFR-02 acceptance was performed.

## Actual application services and effective configuration

The successful `verified` rehearsal served untouched `app.main:app` through the
normal Uvicorn Server and its ordinary ASGI lifespan/composition. No service,
repository, adapter, scoring selection or route was replaced. There were no
`/_test` endpoints or profile/evaluator selection calls. The only backend wrapper,
`backend/tests/local_asgi_service.py`, watches a supervisor stop file and sets
Uvicorn's `should_exit`, allowing normal application shutdown. It controls
lifecycle only. Every phase starts a genuinely new backend process.

Production Next.js ran with the existing J-11/J-12 build
`QWKAiLQdQhaueWmL7ukvL`, normal same-origin API proxy and authentication. Frontend
PID14192 remained running across backend restarts. Source hashes still match
that build's verified application state, so no new build was needed.

The supervisor passes a process-local environment map; these are the exact five
release settings used at each startup:

|Setting|Activated and same-config restart|Rollback|Disabled-boundary demonstration|
|---|---|---|---|
|`SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE`|`compact_exhaustive`|`compact_exhaustive`|`compact_exhaustive`|
|`SMART_WARDROBE_ASSISTANT_SCORING_PROFILE`|`experimental_compatibility_decision_v1`|`compatibility_deferred`|`compatibility_deferred`|
|`SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED`|`true`|`false`|`false`|
|`SMART_WARDROBE_ASSISTANT_ENABLED`|`true`|`true`|`false`|
|`SMART_WARDROBE_HOMEPAGE_ENABLED`|`true`|`true`|`true`|

Isolation also pins DATA_DIR and DATABASE to one newly created OS temporary
directory per attempt, AI_MODE=development, VTOFF/VTON off and development
identity off. A generated non-default token secret is retained in the supervisor
environment for all four processes; it is not written to the evidence. Three
accounts are registered through the real account API and authenticated through
normal login. No copied real accounts/photos or deployment database are used.

## Activation, restart and rollback results

|Stage|Actual backend PID|Normal-route/browser result|
|---|---:|---|
|Activated|26656|Homepage, experimental Assistant, suitability controls, quota and saved-outfit/owner checks passed.|
|Restarted with the same flags|29508|Fresh experimental submission, exact historical replay/display and full-quota guard passed.|
|Rolled back; integrated Assistant retained|26176|New deferred recommendation, suitability-unavailable response, original experimental replay/history and full-quota guard passed.|
|Assistant disabled for legacy-risk demonstration|28088|Explicit fail-closed request, frontend guard and direct unqualified legacy behaviour verified.|

All four backend logs record startup, **Application shutdown complete** and
**Finished server process**, with exit0. The three intervening restarts preserve
the same database path and local secret; they are not merely composition
rebinding or fresh empty-database tests. `process-ledger.json` records commands,
flags, timestamps, launcher/application PIDs and stops. Backend processes and the
owned production frontend were stopped at the end. No unrelated process was
stopped. Synthetic temporary databases are retained at the paths in each attempt
ledger for audit; they are not a live deployment or approved production data store.

### Normal activated journey

The owner registers/logs in, uploads three synthetic development images and
reviews/confirms a top, trousers and dress through normal routes. Reviewed colour
is blue and style vintage. Real wardrobe controls explicitly set Campus and
Casual suitability to Allow on each garment. A supported colour preference with
weight1 is saved through the account API.

Homepage initiates its integrated flow and displays one valid owner outfit. Its
selection is assessed as random valid-candidate selection; no deterministic
winner or Assistant-score assertion is imposed on Homepage. It creates no chat.

The Assistant receives:

> Suggest a casual outfit for campus with vintage style using blue colours with
> a top and trousers

The normally routed request selects the confirmed top/trousers, with R=1, measured
pairwise compatibility decision C=1, P=1 and exact total1. Metadata stores
weights3/5,1/5,1/5, `Computed` compatibility basis, compact provenance,
`experimental_compatibility_decision_v1` and `SuitabilityRequestEvaluator`.
The recommendation, completed chat, item snapshots, score/policy metadata and
submission key are persisted atomically by the unchanged application.

Changing the mandatory bottom's Campus declaration to Deny produces
NoMatchingCandidates. Unknown and conflicting Allow+Deny produce
InsufficientEvidence. The UI is then used to restore explicit Allow. Exercise
and formal requests remain PolicyUnavailable. No unsupported value, missing
evidence or conflicting declaration is silently accepted. The focused backend
suite additionally covers all eight supported occasions/two formalities and
existing mandatory/unknown semantics.

The recommendation is saved as a separate outfit using the actual result UI.
Saved-outfit preparation succeeds before and after rollback using real current
confirmed owner links. A second authenticated owner receives404 for the first
owner's chat, saving action and saved-outfit visualisation source. Preparation
does not run inference; no CV/VTON quality or output-generation claim is made.

### Quota across the lifecycle

A separate synthetic quota account starts with99 deliberately unverified stored
rows, seeded only in the known disposable database. They have no fabricated
confirmation links and are not recommendation evidence. Two fresh development
uploads are reviewed through the real API while capacity remains99. The first
confirmation reaches100; the second returns typed409 WardrobeQuotaExceeded and
keeps its job review_required. A successful ordinary archive releases one slot;
retrying the second job succeeds and returns usage to100, with101 retained rows
because the archive remains stored. A new upload at full capacity returns409.

The full-quota check repeats after same-config restart, profile rollback and
Assistant disabling. Its result remains100 with no new upload/job admitted.
Pending jobs reserve no slots, source/default flags do not disable quota, and
archived rows release capacity. This is a functional boundary fixture, not a
100-garment performance population. Existing concurrent/batch/rollback tests
remain part of the focused regression evidence.

### Configuration rollback and immutable history

The backend is stopped cleanly and restarted with deferred scoring, suitability
off and integrated Assistant still on. A fresh style/colour/category request
uses `compatibility_deferred`, evaluator `RequestConstraintEvaluator` and exact
weights7/10,0,3/10. R=P=1 gives total1, while raw C remains NULL/Unavailable.
A fresh request requiring occasion/formality returns PolicyUnavailable.

Replaying the original experimental submission key returns HTTP200, the same
recommendation/chat IDs, original exact scores, experimental policy metadata and
original item references. Its original suitability-bearing request is restored,
not rescored under the new disabled evaluator. The completed-chat API and actual
historical UI retain the original experimental explanation/display text. The
saved outfit remains eligible for preparation. Annotation records are retained;
turning the evaluator off does not erase owner statements.

The supervisor reads SQLite in read-only mode after each stopped backend and
compares every earlier row against the next stage. All original rows are retained
unchanged; only new submissions append records:

|Snapshot|Recommendations|Chats|Metadata rows|Submission receipts|Item rows / item snapshots|
|---|---:|---:|---:|---:|---|
|After activation|2|1|2|2|3 /3|
|After same-config restart|3|2|3|3|5 /5|
|After rollback|4|3|4|4|7 /7|
|After disabled legacy demonstration|7|6|4|4|16 /7|

The last three rows are intentional new legacy results in the disposable
environment. They lack the integrated metadata/submission/snapshot additions;
they do not overwrite the earlier integrated rows. Raw stopped-stage row bundles
and successful subset comparisons are retained. No full-database hash equality
is claimed across legitimate appended results or intentional wardrobe edits.

## Legacy generation caller inventory

`caller-inventory.json` records530 reviewed first-party source/script/test/doc
files,48 matching files, line numbers and context. Dependencies/vendor code,
generated builds and raw logs/measurement JSON are excluded as non-callers.
The search includes bare imported/re-exported function names, not just literal
URLs. Unknown external API consumers cannot be inventoried from this checkout.

|Caller or reference group|Actual behaviour and compatibility implication|
|---|---|
|`frontend/components/OutfitAssistant.tsx`|The sole current production UI caller passes text plus submission key. The helper checks capabilities and sends explicit `pipeline=integrated`; it does not invoke legacy when disabled.|
|`frontend/lib/api.ts` one-argument overload|Still exports an unqualified POST without a key. No current production component calls that overload, but it remains a compatibility surface for old/imported callers.|
|`backend/app/api/recommendation_routes.py`|The only production caller of `recommendation_service.create_recommendation`. A valid unqualified POST with service None reaches legacy generation; an explicit integrated request returns404.|
|`recommendation_service.py`|Defines the legacy generator and still owns recommendation read/save functionality. Definition/exports are not additional active callers. Do not delete the whole module.|
|`test_workflow.py`, `test_o2_recommendation_boundary.py`, `test_confirmed_garment_snapshot.py`|Retained unqualified compatibility tests exercise legacy generation when integration is off; some are intentionally negative. A future fail-closed migration must explicitly adapt these tests' routing contract rather than mislabel their current results.|
|`test_outfit_assistant.py`, `test_assistant_decision_integration.py`, `test_release_configuration.py`|Unqualified tests cover integrated-on routing, missing keys, authentication and disabled legacy behaviour. The J-12 helper constructs qualified/unqualified paths dynamically.|
|`test_phase5f_audit.py`|Has a mocked disabled legacy dispatch assertion; it is diagnostic compatibility evidence, not an approved release behaviour.|
|New `activation-rehearsal.spec.ts`|Deliberately makes three unqualified disabled requests to prove the current risk. It never supplies selection/profile parameters.|
|Remaining recorded backend/browser tests and collectors|Assistant generation uses explicit integrated requests. Homepage uses its separate path. History/read/save/source-preparation calls and mock interceptors are not unqualified generation callers. Conditional Homepage/Assistant URLs select `/homepage` or `?pipeline=integrated`.|
|Docs, `assistant_critical_path_server.py`, frozen J-11 API backup and J-12 report backup|API descriptions, request-observation middleware or historical source references, not additional deployed callers. First-party backend scripts contain no other discovered unqualified generation caller.|

### Disposable demonstration of the current risk

With Assistant disabled, capabilities report false. A direct explicit integrated
request returns404 IntegrationDisabled. The normal frontend shows its mapped
disabled-feature message and makes **zero generation POSTs**.

Three authenticated unqualified requests nevertheless return201: one without a
key, then two with identical `submission_key=legacy-repeat` and identical text.
All three have distinct recommendation IDs, hardcoded legacy compatibility1 and
no integrated score metadata. The repeated key is ignored in this legacy path;
three recommendations/chats are appended. This is evidence of a compatibility
risk, not certification of legacy scoring or a reason to activate it. Original
experimental history remains readable and unchanged even while Assistant is off.

### Proposed fail-closed migration boundary; NOT IMPLEMENTED

After separate approval, change only the generation dispatch in
`backend/app/api/recommendation_routes.py` so service None produces the existing
IntegrationDisabled-style404 for both explicit and unqualified generation.
Keep authentication/model validation ordering, integrated key validation and
existing GET/history/save/VIS paths. Do not remove legacy historical rows or
read/action code. Enabled unqualified requests may continue reaching integrated
execution with valid keys; choose/document that compatibility behaviour explicitly.

Coordinate a narrow `frontend/lib/api.ts` deprecation/removal of the unkeyed
overload, or make its unsupported use fail explicitly after approval. Normal
OutfitAssistant already passes keys; no scoring/frontend redesign is indicated.
Confirm external callers with the owner before release, publish the disabled/
missing-key response contract, and migrate legitimate callers to explicit
integrated requests with durable keys. This intentionally breaks disabled legacy
generation compatibility and must not be presented as a transparent change.

Minimum migration regressions: enabled/disabled x explicit/unqualified; missing/
invalid/conflicting/repeated keys;401/404/422 distinctions; no recommendation,
chat, metadata, receipt or item writes while disabled; no legacy dispatch; current
frontend makes no disabled POST; concurrent keyed replay; preserved legacy
read/save/history and strict owner/VIS actions. Amend the named legacy-contract
tests under their owners' approval; do not alter frozen scoring expectations or
historical evidence. Add a narrowly scoped source-hash transition only for the
approved production files. No route or overload was changed in J-13.

## Exact configuration and restart steps

`rehearse.py --label verified` is the executed supervisor. Its backend command is
the pinned offline Python/Uvicorn environment recorded in `process-ledger.json`,
running `tests/local_asgi_service.py --stop-file <temporary-stage-file> --port3101`.
That runner loads `app.main:app` with Uvicorn Config/Server. The frontend command
is the installed Next CLI `start --hostname127.0.0.1 --port3100`, using the
verified production build and ordinary same-origin backend URL. It introduces no
application control endpoints or monkeypatches.

Equivalent application environment steps, in the **isolated service launcher**:

```powershell
$env:SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE='compact_exhaustive'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='experimental_compatibility_decision_v1'
$env:SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED='true'
$env:SMART_WARDROBE_ASSISTANT_ENABLED='true'
$env:SMART_WARDROBE_HOMEPAGE_ENABLED='true'
```

Keep the same explicit disposable DATA_DIR, DATABASE and authentication secret;
launch the normal application, e.g. from backend:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 3101
```

Stop the existing backend cleanly, wait for shutdown/process exit and port release,
then run it again with the same environment to rehearse same-config restart.
For the tested rollback, change only these two values before the next launch:

```powershell
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='compatibility_deferred'
$env:SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED='false'
```

Keep integrated Assistant and Homepage true. New requests then use deferred/off;
original keyed results and completed history remain stored experimental results.
The100 quota does not depend on this choice. Do not edit stored scores or
versioned JSON default_activation fields. Restart every affected instance; environment
editing is not hot reload. An execution-engine rollback to `reference` remains
available separately but was not needed for this scoring rollback.

These examples are not persistent deployment settings and were never applied to
the host's User/Machine environment. The executed supervisor supplies child
environment maps rather than `SetEnvironmentVariable` or an installed service
edit. A plain `.env` file is not proof of loading: config reads os.environ, and
README's development `uvicorn --reload`/`npm run dev` instructions are not this
production-frontend rehearsal. Persist actual deployment selections through its
approved launcher/environment mechanism; retain the secret/database path when
restarting. The installed service configuration is outside this phase.

## Deployment and database dependencies

- Local idle graceful stop/restart is now demonstrated with actual distinct
  processes and persisted data. Forced termination during writes, in-flight
  request drain, multiple deployed workers, operating-system service-manager
  persistence, proxy cutover and production recovery remain unverified. The
  stop-file supervisor is a local rehearsal tool, not a deployed service manager.
- Before deployment, obtain the separately approved read-only quota/status
  inventory for real accounts. Preserve existing over-limit records; agree
  support for unusual/non-visible statuses, archive dependencies and recovery.
  Do not mass-archive, invent confirmation links or change historical rows.
- The actual provider still uses sqlite3 with foreign keys and BEGIN IMMEDIATE.
  `backend/deployment/compose.postgres.yml` starts PostgreSQL/pgvector and schema
  assets, not a working replacement for the current application provider.
  Supervisor acceptance of a SQLite prototype deviation or separately approved
  shared PostgreSQL adapter/migration/locking work remains necessary. No Docker,
  PostgreSQL connection or migration was run in J-13.
- Handoffs report real CV/VTOFF/VTON and PostgreSQL schema smoke work. The named
  `segmentation/results.json`, `vtoff_standardisation/results.json`,
  `vtoff/smoke/results.json`, `vton/smoke/results.json` and `pgvector/results.json`
  artifacts remain absent locally at their referenced storage paths, as captured
  in `dependency-artifact-presence.json`. This does not mean the teammate never
  ran them. Transfer/audit existing raw/model/input/config hashes first, then
  agree missing authorised model coverage and supervisor VTON scope (outerwear
  remains unsupported). No new model or dataset acquisition is authorized here.
- RN-13 retains its bounded8-occasion/2-formality policy and non-anchor colour/
  provenance limitations. RN-17's bounded rule/midpoint/no-pair conventions are
  functionally exercised, not independent fashion-quality evidence. Global
  scoring remains deferred and suitability default-off. NFR-01/02/03 and final
  FYP acceptance remain separate; J-12 timings retain their original limits.

## Focused verification, evidence and integrity

**296 backend tests passed in89.67s** across startup/release configuration,
suitability, authentication/routing, Homepage/Assistant, persistence/history,
quota, historical actions, saved-outfit eligibility and frozen-source guards.
The final verified rehearsal passes **four production-browser stages** against
the actual services. TypeScript and scoped ESLint pass; `git diff --check` and
explicit new-file whitespace checks pass. No broad backend rerun, new production
build or capacity/performance matrix was needed after zero application changes.

All attempts are retained. `initial` selected no tests because a beginning-anchored
title filter did not match Playwright's full title. `discovery-retry` passed the
first three stages, then its new disabled-state locator expected an internal API
message instead of the existing mapped user message. Only the new filter/locator
were corrected; no existing expected outcome or production source was changed.
`verified` reran the complete four-stage cycle on a fresh disposable database,
preserving both partial attempts and their shutdown logs/traces. Earlier passes
are not added to the four final stage passes.

New additions are `backend/tests/local_asgi_service.py`,
`frontend/tests/phase5f/activation-rehearsal.spec.ts`,
`frontend/playwright.activation-rehearsal.config.ts`, this report and
`storage/verification/phase5f2e3j13/` supervisor/audit scripts and artifacts.
The source snapshot verifies1,807 captured pre-existing files and the58-file
accepted J-12 index. No application source/default, prior test, frozen reference,
manifest, route, provider, model, prior report or verification artifact changed.
No new source-guard transition is needed for additions confined to verification.

## Closure recommendation

**PASS WITH LIMITATIONS.** The intended configuration can be activated through
normal startup, used, gracefully restarted with the same settings, and rolled
back locally while retaining exact historical scores/display and replay. Quota,
source eligibility and owner protections remain active. The disabled legacy
generation risk is demonstrated and its narrow migration boundary is documented.

This is local release verification, not production deployment certification or
global activation approval. All rehearsal processes are stopped. Wait for owner
review; do not change the route/defaults or start the next phase automatically.
