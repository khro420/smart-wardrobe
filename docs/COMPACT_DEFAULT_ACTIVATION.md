# Phase 5F-2E-3C-3H: compact execution default activation

Status: **PASS WITH LIMITATIONS - ready for owner review and Phase 3H closure**. The nine-request actual-default browser sanity check completed successfully after workload reduction. NFR-02 remains OPEN and formally unaccepted.

## Approved change and configuration

The Outfit Assistant execution default is now `compact_exhaustive` (the existing canonical configuration value for the compact engine). The scoring default remains `compatibility_deferred`. No scoring weights, algorithms, eligibility rules, frontend/API contracts, database schemas or historical records were changed. Assistant enablement remains independently controlled; changing its engine default does not enable a disabled feature.

| Execution environment setting | Scoring setting | Purpose |
|---|---|---|
| unset (`compact_exhaustive`) | unset (`compatibility_deferred`) | New default |
| `compact_exhaustive` | `experimental_compatibility_decision_v1` | Explicit experimental scoring |
| `reference` | `compatibility_deferred` | Rollback |
| `reference` | `experimental_compatibility_decision_v1` | Explicit comparison/rollback |

The execution variable is `SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE`; the scoring variable is `SMART_WARDROBE_ASSISTANT_SCORING_PROFILE`. These settings are server-only. The historical shorthand `compact` is not a newly accepted configuration alias: use `compact_exhaustive`. Invalid settings still reject startup, even when the Assistant feature is disabled.

## Rollback and restoration

Set the server environment and restart the backend (including each deployed worker/service instance):

```powershell
$env:SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE='reference'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='compatibility_deferred'
```

Keep the existing service launcher, feature flag and database. Do not change stored recommendations. Verify server configuration and a fresh authenticated submission after restart. To restore the new default, remove the execution setting from the server/service environment and restart again:

```powershell
Remove-Item Env:SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE -ErrorAction SilentlyContinue
```

Removing a PowerShell variable changes that shell and future children only; also remove any persistent deployment/service override. Unsetting the scoring setting retains deferred scoring. Environment edits are not hot reload. In-flight requests keep their captured selection; completed submission retries use persisted results before new selection. A terminated process cannot finish an in-flight request; atomic rollback and same-key retry remain the recovery mechanism.

## Integrity and boundaries

Only three application files change: execution selection's central default, the service constructor default and composition's environment fallback. Execution provenance versions are unchanged because the selected implementations and semantics are unchanged. Newly defaulted compact results identify compact provenance; historical reference/compact records retain their original provenance.

`backend/tests/fixtures/compact_default_sources.v1.json` records an explicit before/after hash transition. Earlier integration archives and hash manifests remain unchanged. The five compact-kernel modules, scoring profiles, independent verifier, Phase 1 query, persistence and action paths must remain byte-identical to the pre-phase snapshot.

The Phase 3G proposed transition configuration and reports remain historical review records; they are not runtime configuration. Approval for this phase supersedes the former pending approval for changing the default only.

## Acceptance limits

NFR-02 still requires the complete recommendation/no-result/unsupported response within five seconds under an approved baseline. That baseline still requires separate approval. Earlier 96-trial results and failures are retained: compact deferred 200-garment browser median 5.038 seconds, experimental 6.017 seconds; reference stress browser failures 4/48 versus compact 0/48. Default activation does not erase above-five-second evidence or establish final FYP acceptance.

Approximate hex matching remains disabled, suitability remains opt-in, experimental compatibility remains default-off, and Homepage random selection is unchanged. Reference ratings/calibration, suitability UX/policy limitations, independently reviewed recommendation quality, deployment verification and formal performance acceptance remain separate work.

## Verification results

Checks completed so far: focused differential/default/rollback suite **292 passed**; four-way production browser functional suite **28 passed**; TypeScript and isolated production build passed; ESLint passed with two existing navigation warnings. Raw commands and logs are retained under `storage/verification/phase5f2e3c3h/`. Initial functional checks ran under observed 94% CPU and approximately 1.05 GiB free RAM; these are not clean performance acceptance conditions. Browser timing is separately resource-qualified and does not rerun the 96-trial matrix.


## File inventory

| Path | Purpose |
|---|---|
| `backend/app/application/recommendation/assistant_execution_selection.py` | Central `DEFAULT_ENGINE=COMPACT`; selector defaults to it. Existing canonical values and provenance unchanged. |
| `backend/app/application/recommendation/outfit_assistant_service.py` | Constructor uses the same default; request capture, ranking and writes unchanged. |
| `backend/app/infrastructure/workflow_runtime.py` | Unset server environment uses central default; explicit reference/invalid handling retained. |
| `backend/tests/fixtures/compact_default_sources.v1.json` | Authorized three-file before/after hash transition, separate from historical pins. |
| `backend/tests/integration_source_guard.py` | Validate the new transition in addition to all previous frozen guards. |
| `backend/tests/test_compact_default_readiness.py` | Update current-default assertions while preserving historical proposal checks; add three real application-lifespan/API restarts against the same DB. |
| `backend/tests/test_compact_integration.py` | Explicit reference selection for old reference-factory checkpoint injection. |
| `backend/tests/test_outfit_assistant.py` | Explicit reference selection only for the existing reference-stream fault test. Other helper callers exercise the new default. |
| `backend/tests/test_assistant_decision_integration.py` | Explicit reference selection in historical reference-decision helper; four-way and default suites independently test compact. |
| `backend/tests/test_prepared_aggregation.py` | Explicit reference execution for the prepared-versus-aggregated reference-factory comparison. |
| `backend/tests/test_prepared_decision_performance.py` | Preserve direct/signature-adapted reference factory rejection tests under explicit reference execution. |
| `backend/tests/test_phase5f_audit.py` | Keep late reference-generator failure injection exercised at the real HTTP boundary. |
| `backend/tests/performance_worker.py` | Pin the retained reference hot-path trace oracle to reference on services supporting execution selection; older frozen services remain unchanged. |
| `frontend/playwright.compact-default.config.ts` | Isolated production build/artifact locations for this phase. |
| `frontend/tests/phase5f/compact-default.spec.ts` | Resource-qualified nine-call actual-default browser sanity collector; no engine override endpoint used. |
| `docs/config/assistant_execution_transition.v2.json` | Owner-approved code-activation record, separate from historical v1; does not claim deployment verification. |
| `docs/COMPACT_DEFAULT_ACTIVATION.md` | This implementation, rollback and verification report. |
| `docs/REPORT_TRACEABILITY.md` | Append phase traceability; preserve earlier records. |

Local evidence files under `storage/verification/phase5f2e3c3h/` include before hashes/raw source backups, generated application diff, commands and every initial/final log. They are verification artifacts, not runtime changes. The initial **283 passed / 8 failed** run is retained; its failures targeted reference-only injection paths bypassed by the newly selected compact engine. Tests now explicitly choose reference for those injections without weakening expected failures. Dedicated compact late-failure/revalidation tests continue unchanged.

The restart test uses three **real ASGI lifespans**, not operating-system process kills or a deployed multi-worker restart. It verifies default startup, authenticated persistence, reference startup, read-only historical score/provenance equality, cross-engine same-key replay and compact restoration. Existing tests separately cover in-flight captured contexts, write rollback, concurrent keys and retry recovery. Actual deployment/service-manager restart and multi-worker draining remain operational checks.


### Retained initial broad regression results

The first broad default run reported **1,793 passed / 6 failed**. Five failures
were reference-specific test instrumentation assumptions: two late-generator
HTTP cases, direct/signature-adapted reference-factory activation, and two large
reference-method transcript comparisons. Their numerical scores/winners were
not evidence of a changed scoring rule: compact does not call the instrumented
reference methods. Reference selection is now explicit for these older tools;
all expected failure assertions, 12,222-event transcript checks and exact-score
comparisons remain. The sixth failure is the known `ai-services` architecture
assertion. The entire broad suite is rerun after these test-only corrections.
No production changes followed the initial three-file activation.

Source check: **298 pre-existing files checked**, only the three authorized app
files changed; **37 existing fixture files** and **61 Phase 3G evidence files**
unchanged. Frontend app/components, package/lock, AGENTS and restored tsconfig
match the pre-phase hashes. `git diff --check` exit **0** (existing line-ending
warnings are retained in the log). All four configurations passed seven browser
structure/evidence cases each (28 total); the legacy browser suite passed 35.

The dedicated CV geometry suite is excluded from the pinned general-backend
command because it requires the separate CV/torch environment. Real GPU-backed
models, production databases, PostgreSQL locking and deployed worker restarts
are not certified by these disposable SQLite/development-AI tests.


### Final functional verification

| Command (working directory) | Result |
|---|---|
| Pinned pytest prefix in `storage/verification/phase5f2e3c3h/commands.txt`, focused five-file suffix (backend) | **292 passed**, 252.56s; includes default selection, four-way parity, rollback/replay and in-flight consistency. |
| Same pinned prefix, `tests --ignore=tests/test_segmentation_geometry.py -q --tb=short` (backend), both settings unset | **1,798 passed, 1 known failure**, 188.91s. |
| `npx tsc --noEmit` (frontend) | Exit 0, including final collector assertion changes. |
| `npm run lint` (frontend) | Exit 0; two unchanged navigation warnings at extract/results:154 and Layout:50. |
| `npx eslint tests/phase5f/compact-default.spec.ts playwright.compact-default.config.ts` | Exit 0. |
| `npm run build`, isolated `.next-integration-run/compact-default-production`, backend URL `http://127.0.0.1:3201` | Exit 0, Next.js 16.4.2. |
| `npx playwright test --config playwright.compact-default.config.ts --grep "integrated functional"` | **28 passed**, 3.5m. |
| `npx playwright test --config playwright.integration.config.ts --output .next-integration-run/compact-default-legacy-artifacts` | **35 passed**, 4.6m. |
| `git diff --check` (repo root) | Exit 0. |

The remaining backend failure is exactly
`tests/test_report_architecture.py::ReportArchitectureTests::test_single_backend_and_canonical_ml_locations`:
line 28 asserts that `ai-services` does not exist. The directory is retained;
the test is not weakened. This is the existing architecture-test inconsistency,
not a new compact-default regression. The initial failing runs are retained
alongside final results. No new application regression was reproduced.

The 28 browser cases cover each of the four configurations independently;
comparison is between engines **within a scoring profile**, never an assertion
that deferred and experimental profiles must choose the same winner. Backend
regressions cover strict query eligibility, independent validation, exact
Fraction arithmetic, deterministic ordering, atomic rollback/concurrency,
transaction-bound changes, immutable historical snapshots and idempotent replay.
Legacy browser checks cover enablement/disabled behaviour, no-result/unsupported
states, historical save/visualisation, cross-user access and authentication.


## Remaining FYP acceptance and operational work

- Obtain separate approval for the formal NFR-02 baseline and run realistic
  terminal-response cases against the unchanged five-second bound. Preserve all
  prior 200-garment and stress slow/failing results; simultaneous large-request
  capacity and resource isolation remain unproven.
- Independently review/evaluate compatibility heuristics, weights and rankings
  before any separate decision to activate experimental compatibility. Default
  deferred scoring does not establish measured compatibility quality or complete
  RN-17 acceptance on its own. Reviewed-reference coverage remains unavailable.
- Collect independently reviewed colour calibration/held-out validation before
  permitting approximate hex matching. Named/exact-anchor evidence is unchanged.
- Suitability remains opt-in and owner-declared, with existing unsupported policy
  values and annotation UX/provenance limitations. No dedicated selection UI is
  authorized here.
- Confirm the actual deployment's server environment, worker restart/drain and
  rollback procedure, database/transaction implementation and load capacity.
  SQLite tests do not establish PostgreSQL equivalence or deployment acceptance.
- Resolve the existing architecture assertion through a separate architecture
  decision; validate real CV/VTOFF/VTON in the appropriate model environment.
  Earlier confirmation/action integration fixes remain covered by the 35 browser
  tests; the old 422/409 issue is not newly claimed as an unfixed blocker here.

No further phase, experimental scoring activation, policy expansion, model
change or performance optimization is performed. Owner review is required after
this verification report.


## Initial performance attempt: RESOURCE BLOCKED (retained history)

The actual-default collector was attempted after the test/build workloads had
finished, with both engine and scoring settings unset. It planned three browser
submissions each at 50, 100 and 200 garments (2,430 / 17,710 / 134,820 candidates).
It never calls the test engine-selection endpoint. No request timeout or proxy
policy changed; the earlier 96-trial matrix was not repeated.

**40 preflight observations, 0 timed submissions.** CPU ranged **40 to 71%**;
available physical RAM ranged **2,005,608 to 2,653,156 KiB (1.91 to 2.53 GiB)**.
The retained Phase 3G collection gate requires three consecutive observations
at CPU <=20% and free RAM >=4 GiB within 120 seconds, after a 10-second startup
settle. These are measurement collection controls, not new FYP acceptance
thresholds. The gate failed, and Playwright correctly reported one failed
collector test with `Resource preflight blocked controlled timings`.
This is an environment-blocked verification, not a reproduced recommendation
failure. Raw observations, browser trace and the failure are retained.

A separate three-second CPU-delta diagnosis identified `wwm` PID 15264 consuming
3.594 CPU-seconds (more than one core) and approximately 7.17 GB working set,
alongside Spotify, Discord and other applications. Earlier functional checks had
observed 94% CPU / approximately 1.05 GiB free RAM. No user applications were
closed; workload relief was requested asynchronously. Resource contention
remained present after our test/build processes finished. The fresh CPU/RAM
observations do not support clean current performance comparisons.

Consequently **no new latency medians, regression claims or five-second passes
are reported**. The prior Phase 3G results and above-five-second/failing trials
remain unchanged. A quiet-machine retry of only this nine-call collector is
still required before final transition closure. It must use a new run label and
artifact directory to retain this blocked attempt. No full 96-trial rerun is
justified by this resource failure alone.

## Pre-resumption closure assessment (superseded below)

The approved code-default transition and functional regressions are verified;
no new application regression was reproduced. Explicit reference rollback,
deferred scoring, strict eligibility, immutable history, exact scoring and
all four configurations remain supported. **Final Phase 3H closure is not yet
recommended until the targeted actual-default performance sanity can run under
suitable resources.** This is separate from NFR-02, which remains formally
unaccepted even after a successful sanity run. Production deployment and final
FYP acceptance are not certified. Wait for owner review; no later phase begins.


## Resumed attempt after owner instruction to continue

The owner's manual load recheck showed CPU 11%, 9%, 16% and available RAM
10.32 to 10.34 GiB before resumption. A new collector run used label `resumed`
and `.next-integration-run/compact-default-sanity-resumed-artifacts`; earlier
logs, JSON, traces and the pre-resume report/traceability backups are preserved.

The fresh automated preflight did not stay quiet: **42 observations**, CPU
**15 to 90%**, available RAM **8,718,292 to 10,299,428 KiB** (about **8.31 to
9.82 GiB**). The run stopped as `resource_blocked` with **zero timed requests**.
RAM was sufficient; fluctuating CPU prevented three consecutive qualifying
observations. This is a second resource-blocked collector failure, not a
recommendation latency failure or evidence that NFR-02 passed.

A three-second process-delta sample during preflight found user Google Chrome
PID 13876 at 11.9% total machine CPU, OneDrive.Sync.Service PID 23892 at 10.7%,
Discord at 7.0%, and other browser/desktop processes. Chrome paths were confirmed
as the user's Google Chrome installation, not the Playwright browser. Pausing
OneDrive and unnecessary active browser/Discord workloads was requested; no
applications were terminated. No timeouts, collection gates or algorithms were
changed to force a pass.

Exact resumed command (frontend; both engine/profile variables unset):

```powershell
$env:SMART_WARDROBE_DEFAULT_SANITY='true'
$env:SMART_WARDROBE_COMPACT_RUN_LABEL='resumed'
npx playwright test --config playwright.compact-default.config.ts --grep 'compact default browser performance sanity' --output .next-integration-run/compact-default-sanity-resumed-artifacts
```

Result: one resource-gate failure, zero submissions. Raw evidence is
`browser-sanity-resumed.json`, `browser-sanity-resumed.log`,
`resumed-competing-processes.json` and `resumed-summary.json` in this phase's
verification folder. No functional suites were unnecessarily repeated: their
292 focused, 1,798 backend passes (one known architecture failure), 28/35 browser,
TypeScript, lint and build results remain the previous completed runs. Final
closure remains pending the targeted resource-qualified sanity verification;
NFR-02 stays formally unaccepted. No subsequent phase starts.


## Final quiet retry: PASS WITH LIMITATIONS

After the owner reduced workloads and requested a fresh check, CPU samples fell
from 24% to 15% to 8%, with 11.99 GiB free RAM and no dominant competing process.
The actual-default collector was retried with a new `quiet-retry` label and
separate artifact directory, preserving both blocked attempts. Automatic
preflight then passed at **19%, 11%, 16% CPU**, approximately **11.4 GiB free RAM**.
No test/build workloads ran concurrently with the timing trials.

**Nine of nine actual-browser requests succeeded (HTTP 201)**, with nine distinct
persisted recommendation IDs and chat IDs. All were `Selected` with complete
backend processing and the expected exhaustive candidate counts. Both server
selection variables were unset; recorded provenance confirms `compact_exhaustive`
and `compatibility_deferred`. No selection override endpoint was called.

| Garments | Candidates examined per request | Browser seconds, all trials | Median | Maximum | Prior Phase 3G compact/deferred browser median |
|---|---:|---|---:|---:|---:|
| 50 | 2,430 | 0.234, 0.185, 0.190 | 0.190 | 0.234 | 0.182 |
| 100 | 17,710 | 0.684, 0.677, 0.695 | 0.684 | 0.695 | 0.732 |
| 200 | 134,820 | 4.542, 4.573, 4.438 | 4.542 | 4.573 | 5.038 |

Every semantic fingerprint matches the corresponding retained Phase 3G
compact/deferred result (selected members, exact score and normalized semantic
provenance). The 50-garment median is about 8 ms higher; 100/200 medians are
lower. These small sequential samples support consistency with the previously
measured architecture and reveal no material regression in this sanity check.
They are not a new matched reference-engine study, statistical performance
validation, or evidence of another algorithm optimization. Resource conditions
changed between runs, so latency differences cannot be attributed solely to the
default switch. The earlier 96-trial matrix was not repeated.

Before/after observations, including preflight, ranged **9 to 34% CPU** and
**11,727,624 to 11,980,244 KiB free RAM** (about **11.18 to 11.43 GiB**).
These snapshots are not continuous process isolation. CPU activity during the
run includes the benchmark's own browser/backend work. No timeout, response
boundary, collection gate or scoring policy was relaxed. The homogeneous
synthetic vintage/blue request and one stored preference match the earlier
sanity workload; they do not replace the proposed diverse formal baseline.

Exact command (frontend; both engine/profile variables unset):

```powershell
$env:SMART_WARDROBE_DEFAULT_SANITY='true'
$env:SMART_WARDROBE_COMPACT_RUN_LABEL='quiet-retry'
npx playwright test --config playwright.compact-default.config.ts --grep 'compact default browser performance sanity' --output .next-integration-run/compact-default-sanity-quiet-artifacts
```

Result: **1 Playwright collector passed (1.2m), 9 timed submissions, 0 failures**.
Evidence: `browser-sanity-quiet-retry.json`, `browser-sanity-quiet-retry.log` and
`quiet-retry-summary.json`. Both initial resource-blocked collector failures,
all prior functional failures/fixes, earlier slow/failing Phase 3G trials and
original sources remain retained. The report before resumption is backed up as
`activation-before-resume.md`; its earlier pending assessment is superseded by
this completed retry, not erased.

### Final closure recommendation

**Phase 3H is ready for owner review/closure as PASS WITH LIMITATIONS.** The
approved compact-default transition is implemented, four-way functional and
backend regressions are complete, exact semantic fingerprints match, and the
required targeted default-path sanity now passes. The only broad backend
failure remains the unchanged ai-services architecture assertion. The separate
CV geometry suite, real model/deployment validation and operating-system worker
restart/drain verification were not performed; actual ASGI lifespan restart
and persistent-database replay were tested.

**NFR-02 remains OPEN / NOT FORMALLY ACCEPTED.** All nine new trials being under
five seconds does not approve the formal baseline or erase prior above-five-
second 200-garment/stress measurements. The formal baseline, diverse requests,
no-result/unsupported timing, deployment capacity and remaining evaluation work
still require their separate approval/testing. Experimental compatibility stays
default-off, suitability opt-in and approximate hex matching disabled. No later
phase or additional activation begins. Wait for owner review.
