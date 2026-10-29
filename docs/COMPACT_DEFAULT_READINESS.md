# Phase 5F-2E-3C-3G: compact default readiness

**Updated after resumed verification:** the96-trial matched matrix is complete. Earlier blocked-attempt sections below are historical; see the resumed results and current recommendation at the end. Both defaults remain unchanged.

This phase prepares an execution-only transition. It does not activate a production default or the experimental scoring profile. The current Python fallback, service constructor and composition defaults remain `reference` and `compatibility_deferred`. The Assistant feature flag is also unchanged. All application algorithms, policies, APIs, persistence and historical records are preserved.

## Requirements and evidence boundaries

The original report, SHA256 `5e5781cd739b696e63cd21a063b8e741daaa6fa93b20f4849b0b84a7c7e38669`, PDF p.179 / printed168 states that performance is evaluated using the baseline deployment environment and workload defined in the system test plan. PDF p.180 / printed169 gives NFR-02: a recommendation, no-result or unsupported-request response within **five seconds** after a valid NLP request is submitted under that baseline. The passages were re-extracted in `storage/verification/phase5f2e3c3g/report-nfr02.log`. The previous full-report baseline search and Phase3F observations remain unchanged.

RN-17 and section4.10.4 require scoring every valid candidate and preserving weighted deterministic ranking. No candidate pruning, approximate arithmetic, early successful termination or different scoring policy is a remedy adopted here. The report does not establish a numeric wardrobe size, deployment hardware, concurrency or percentile in the reviewed baseline passages. The acceptance specification below is a proposal requiring owner approval, not a new interpretation of NFR-02.

## Current configuration audit

| Setting | Actual default | Explicit alternative |
|---|---|---|
| `SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE` | `reference` | `compact_exhaustive` |
| `SMART_WARDROBE_ASSISTANT_SCORING_PROFILE` | `compatibility_deferred` | `experimental_compatibility_decision_v1` |
| `SMART_WARDROBE_ASSISTANT_ENABLED` | disabled | existing explicit feature opt-in |

The four engine/profile combinations remain supported. Compare engines **within** a profile; different profiles may legitimately select different winners. Deferred weights remain `7/10,0,3/10`; experimental weights remain `3/5,1/5,1/5`. The compatibility midpoint and single-dress NoPairReference conventions remain unchanged.

- `backend/app/application/recommendation/assistant_execution_selection.py`: frozen allowlisted selection; independent from scoring.
- `assistant_scoring_selection.py`: unchanged profile validation and reference scorer dispatch.
- `outfit_assistant_service.py`: original authenticated single-request orchestration, captured preferences, exact scoring, original repository writes and durable replay before new interpretation/ranking. Its constructor still defaults to reference/deferred.
- `backend/app/infrastructure/workflow_runtime.py:34`: reads/validates both environment settings during composition, even if the Assistant feature is disabled; unknown/empty/incorrect-case values fail startup rather than silently falling back.
- `compact_assistant_scorer.py` and `backend/app/domain/value_objects/assistant_execution_context.py`: unchanged immutable metadata bridge. No fabricated candidate-session completion; the compact ledger and independent reconstructed-winner verification remain authoritative.
- `backend/app/api/recommendation_routes.py`: authenticated owner and existing request/body validation; ordinary clients cannot choose internal executors or profiles. Unrecognised extra query keys do not override server configuration.
- `backend/app/infrastructure/persistence/recommendation_repository_adapter.py`: unchanged atomic idempotency/revalidation/write path. The scoring-display and Chat History readers restore stored metadata rather than reranking under current settings.

The checked `backend/.env.example` does not select an Assistant engine/profile. `frontend/next.config.ts` rewrites `/api/v1/*` to the configured backend and has no phase-specific proxy-timeout increase. Existing test fixtures use disposable databases and explicit trusted test controls. No checked-in production orchestrator configuration establishes the actual deployed hardware/process/worker topology; no real deployment database or live rollout was inspected.

`current-configuration.json` records an allowlisted, nonsecret local environment audit: the engine, scoring, Assistant-enabled and suitability-enabled keys are unset at process/user/machine scope, with no overrides found in the inspected common local environment-file locations. This confirms the local fallback configuration, not an unknown deployed process's environment. No active environment file or machine setting was edited.

## Versioned transition plan: prepared, not applied

`docs/config/assistant_execution_transition.v1.json` is a review-only deployment plan, version `assistant-execution-transition-1.0.0`, with `applied:false` and `status:pending_owner_approval`. **The application does not load this file.** It records current/proposed defaults, explicit rollout and rollback environment values, restart requirements and unchanged scoring/feature/history semantics. It neither edits an active `.env` nor changes the Python fallback.

The smallest eventual transition is an explicitly pinned deployment environment change followed by backend process replacement. No application algorithm, database migration or frontend rebuild is required merely to select the existing engine. Prefer the explicit deployment setting over relying on an absent-variable fallback. If a later approval also requires changing the Python fallback, that is a separate, concrete source change with new source-integrity pins and regression verification; it has not happened here.

### Proposed production rollout after separate approval

1. Freeze the code/dependency release, retain the previous process configuration and ensure durable database/media storage and the existing authentication/idempotency secrets are unchanged. Confirm the actual deployment shutdown/drain timeout and capacity; those are not known from local tests.
2. Keep the Assistant feature flag in its previously approved state. Pin the backend process environment to `SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE=compact_exhaustive` and `SMART_WARDROBE_ASSISTANT_SCORING_PROFILE=compatibility_deferred`. Do not change suitability, hex approximation or other flags.
3. Stop routing **new** work to the retiring process and drain in-flight requests where the deployment supports it. Start a replacement with the new environment; do not mutate a shared service's Python attributes in production. Startup must reject invalid configuration before serving.
4. Verify authenticated fresh recommendation, stored exact executor/profile provenance, same-key retry, historical chat read and cross-user rejection against an approved deployment test account. Do not regenerate or rewrite historical recommendations as a smoke test.
5. Observe response/error rates, backend duration and resource pressure against the approved workload. Keep all failed submissions/keys for diagnosis. The experimental scoring profile stays default-off regardless of engine readiness.

### Explicit reference rollback

Pin `SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE=reference` while keeping `SMART_WARDROBE_ASSISTANT_SCORING_PROFILE=compatibility_deferred`; drain and replace the backend process again. With a future compact fallback, **removing the variable would not be a reliable rollback**, hence the explicit reference value. No database restore, score recalculation, historical cleanup or submission-key reset is part of rollback.

That JSON plan targets the proposed deferred-default deployment. For a separately approved experimental-profile test deployment, change only its execution setting and retain its explicitly pinned profile; the four-way rollout tests verify that case too. Engine rollback does not inherently require changing scoring policy.

Configuration is read at process composition, not hot-reloaded from the environment. Each request captures immutable execution/scoring selections before ranking. Existing request objects retain the old service after a replacement; the new service receives new requests. In-flight tests pause real ranking, replace actual composition, and verify that contexts do not mix. Both directions and both profiles are tested. This validates application object/context behavior, not an untested production load balancer or operating-system termination policy.

Committed retries are scoped by authenticated user/operation/key, not executor. A retry after an engine/profile change returns the original ID, score and provenance. A failure before commit rolls back all writes; the same key can subsequently succeed under the other executor. Concurrent ranking may still be duplicated, but the original transactional idempotency policy commits one successful recommendation/chat. Abrupt process-kill/SQLite crash recovery and the actual production restart policy are not newly certified by an in-process test.

## Operational timeout and capacity assessment

The unchanged production Next rewrite timed out around30s in the Phase3F Windows runs. All seven affected reference browser requests were retained even though their backend jobs later settled/committed. A late backend commit is not a successful five-second browser response. The compact200/stress requests avoided that observed timeout but still exceeded five seconds. Proxy behavior may differ in deployment; no larger timeout is used to claim compliance.

The synchronous FastAPI route calls a CPU-bound scorer. Request handling can execute concurrently, but this phase does not introduce CPU parallelism, admission control or asynchronous jobs. Risks remain:

- Two simultaneous same-key submissions can both pass the initial lookup and compute before transactional idempotency resolves the write. The durable guarantee is one commit, not one computation.
- The route has no client-disconnect cancellation check within enumeration. Prior observed backend completion after proxy failure confirms that computation can continue after the browser has an error. Stopping a browser wait does not guarantee stopping CPU work.
- Simultaneous large wardrobes can compete for CPU and worker capacity. Bounded caches/streaming avoid materialising all candidates, but do not establish a response-time or aggregate-memory guarantee at untested concurrency.
- A restart that kills an old process before a long request finishes can lose its uncommitted computation. Database transactions protect writes; preserving the submission key lets a replacement retry. Graceful-drain limits must be verified in the actual deployment.

No exact production concurrency limit is claimed. These are rollout/capacity limitations rather than permission to add single-flight, background APIs, workers or a timeout extension in this phase. If multi-user capacity is required for initial deployment, separately approve a measured concurrency/cancellation/admission design after preserving the current exactness and idempotency contracts. At200 garments, the existing five-second failure is a known requirement gap; a default-engine switch alone does not resolve it.

## Proposed formal NFR-02 acceptance specification v1.1.0 — pending approval

The following choices are **proposed test-plan decisions**, not report-defined constants or already collected acceptance results. Freeze the specification, fixtures and measurement code before formal collection. Do not label the earlier homogeneous Phase3F benchmark as this dataset.

| Dimension | Proposed reproducible specification |
|---|---|
| Hardware | Intended deployment CPU/OS/RAM must be named and approved. The local Ryzen5 7235HS,8 logical processors, Windows11 and approximately19.69GiB OS-visible RAM can be a local baseline only if explicitly approved; do not assume it matches production. |
| Server | Frozen Python3.12/Next16.4.2/dependency-lock release; production `next start`, one Uvicorn process initially, same-origin browser proxy, durable SQLite for the current implementation. Freeze actual process/worker counts, browser version, storage placement, authentication configuration and proxy/network topology. No dev server or longer proxy timeout. PostgreSQL/deployed topology would require its own approved evidence. |
| Execution/profile | Explicit compact and reference comparisons for diagnosis; evaluate the proposed compact/deferred deployment baseline and compact/experimental separately. A pass in one profile does not certify the other. Preserve their existing formulas and policies. |
| Baseline100 | 40tops:10 each short_sleeve_top/long_sleeve_top/vest/sling;40bottoms:14shorts,13trousers,13skirt;10dresses:3short_sleeve_dress,3long_sleeve_dress,2vest_dress,2sling_dress;10outerwear:5each existing outwear category. Exactly17,710 structural candidates before mandatory request filtering. |
| Scalability200 | Double baseline category counts:80tops,80bottoms,20dresses,20outerwear;134,820 structures. Report separately; do not reclassify it as a passing baseline after observing results. |
| Outerwear stress200 | 67tops,67bottoms,0dresses,66outerwear;300,763 structures. Distribute across existing category members deterministically. Separate stress evidence, not hidden in an average. |
| Identity/structure | All baseline garment owners, confirmed processing items/jobs and availability satisfy Phase1. All13 categories represented in baseline100. Add separately labelled ineligible-owner/status/job decoys and verify they do not change eligible counts. No saved outfits required. |
| Attribute completeness | Proposed valid baseline colour mix:60% approved names,20% approved exact anchors,10% non-anchor hex (unknown mandatory evidence),10% missing. Style:70% one valid tag,20% multiple valid tags,10% missing. Use all existing controlled colours/styles cyclically with fixed seed20261021, not identical blue/vintage garments. These percentages are explicit test-design assumptions, not measured wardrobe population rates. Confirm them with representative garment data before approval. Malformed data has separate fault fixtures. |
| Suitability/other evidence | Keep suitability opt-in disabled and approximate hex/pattern scoring disabled. Occasion/formality requests must reach the existing controlled unavailable outcome, not fabricated matches. Existing patterns may be preserved in snapshots but do not contribute scores. |
| Preferences | Separate0,1 and3 stored-preference cases: existing supported colours; colours+styles+garment_categories. Freeze exact values/weights/IDs and fixture hashes. Current explicit request constraints remain mandatory; preferences remain soft. |
| Database state | Start each engine/profile/request/preference block from the same frozen isolated database, initially0 completed chats for the test owner; keep all30 fresh-key writes within that block and record growth rather than resetting after slow requests. Do not use the deployment database. History-heavy and concurrent workloads require separately labelled capacity cases. Record SQLite version, journal mode, filesystem and storage configuration. |
| Concurrency | One active submitted interaction for the first proposed latency baseline, with no overlapping CV/VTON tasks. This is an approval decision, not a proof of multi-user support. Measure concurrent capacity separately before any claim about simultaneous users. |
| Collection controls | Proposed quiet preflight: three consecutive idle CPU observations at most20% and at least4GiB free RAM. On8 logical processors,20% already permits about1.6 logical cores of unrelated activity; it is an operational check, not an NFR threshold or proof of isolation. Record before/after CPU/RAM/processes during collection and retain every disturbed population. Stop independent tests/builds before timing; do not close user applications automatically. |
| Warm/cold boundary | Start production servers and verify readiness before collection. Include the first actual recommendation interaction; no hidden ranking warm-up. Record first versus subsequent calls. Cold process startup/login/page navigation have separate measurements rather than being silently mixed or subtracted. |
| Timing boundary | Browser monotonic T0 at valid submission action through visible completed recommendation/no-result/unsupported state T1. Include NLP, retrieval, exhaustive ranking, commit, proxy/network and UI rendering. Separately record HTTP arrival and backend/service/CPU time. Login and pre-submission page load are outside this request-response boundary, explicitly. |
| Repetitions | Propose30 consecutive fresh-key submissions per supported request/profile/preference fixture; no replacement of slow trials. Five supported requests below give900 baseline calls for two profiles and three preference counts. Three terminal cases with0 preferences give180 additional calls. These1080 calls are proposed, not already performed; approve workload/cost before collection. Reference matching and200/stress have separately labelled alternating diagnostic repetitions. |
| Statistics/acceptance | Preserve NFR-02's literal five-second bound: report every baseline response and require each required submission to complete within5s with its correct terminal state, no failures/unfinished jobs. Also report count, median, observed maximum, and with30 observations any exploratory percentile with estimator/sample size disclosed. A passing median or later commit cannot conceal a slow/error response. Thirty samples do not prove a universal latency bound. |
| Artifacts | Freeze dataset labels/seed/materialised rows, reference expectations, policy/config/package hashes, hardware/OS/proxy settings and collection code; retain every raw trial, timeout, CPU/RAM snapshot and backend settlement outcome. Use separate versions/labels for any revised fixture or environment. |

Supported baseline requests (verify fixed expected NLP structure before freezing fixtures):

1. `Suggest an outfit` (no supplied fields).
2. `Suggest a vintage outfit` (style evidence with diverse competing garments).
3. `Suggest an outfit with blue and white colours` (global colour conditions).
4. `Suggest an outfit including outerwear` (category/group constraint).
5. `Suggest an outfit with vintage style and blue colours` (combined supported fields).

Terminal cases: a global four-colour request (`blue, red, green and yellow`) cannot be met by the supported maximum-three-garment structure using one authoritative primary colour per garment; the exact proposed wording was verified as Supported by the unchanged NLP interpreter. An outside-scope question exercises unsupported intent. A campus request exercises the explicitly unavailable default suitability policy. Actual NLP outputs are retained in `proposed-request-interpretation.log` and `proposed-combined-request-check.log`; validate the materialised fixture and UI outcomes before freezing final labels. Include separately labelled malformed/missing evidence, changed garments, interrupted streams and write-failure fixtures for correctness without averaging them into a faster latency population.

The originally considered phrase combining blue colours with outerwear was rejected by the current conservative garment-colour-binding guard. It is not claimed as supported or made supported by changing NLP in this phase. The approved scope's existing limitation is retained; the fifth supported example above was checked independently. A style-plus-outerwear request without a colour is also Supported, as recorded in the second log.

Fixture generation/materialisation and reviewed wardrobe realism remain to be frozen for the approved formal plan. The proposed mixed-evidence dataset is deliberately broader than the earlier homogeneous performance fixture; it must not be quietly replaced with easier attributes if timings fail. The final acceptance report must distinguish100 baseline,200 scalability and outerwear stress, both scoring profiles, zero/multiple preferences and controlled terminal outcomes.

## Phase files

- `docs/config/assistant_execution_transition.v1.json`: inactive, versioned rollout/rollback proposal.
- `backend/tests/test_compact_default_readiness.py`: actual composition defaults, in-flight transition/rollback, immutable history/replay, failed-write recovery and invalid settings.
- `frontend/playwright.compact-readiness.config.ts`: isolated production build/output; reuses the existing actual-service fixture and four-way browser suite.
- `frontend/tests/phase5f/compact-readiness.spec.ts`: retained Phase3F alternating collector with new evidence location/opt-in flag and an explicit resource preflight; no application or candidate algorithm change.
- This report and `docs/REPORT_TRACEABILITY.md`: requirement, acceptance, rollout and verification evidence.

Raw phase evidence is under `storage/verification/phase5f2e3c3g/`. Earlier Phase3F timing files and frozen references are preserved. Generated framework files stay under `.next-integration-run/`; generated TypeScript include changes are restored to the pre-phase bytes after verification.

## Functional and regression verification

The20 new readiness tests passed independently (8.20s). The final five-module focused run passed **291 tests**, one existing Starlette/httpx deprecation warning,44.74s. The new tests exercise both rollout directions and both scoring profiles through actual composition, not a replacement selection/persistence workflow. They check untouched defaults, captured in-flight contexts, identical scores within each profile, exact historical metadata/snapshot retention, replay without reranking, recovery after pre-commit failure, and rejected empty/unknown/case-mismatched settings even when the feature is disabled.

Retained four-way tests cover all four structures, every-candidate public oracle comparisons, mandatory Pass/Fail/Unknown evidence, all write-stage rollback points, current eligibility changes, concurrent same/different keys including cross-engine submissions, authenticated API isolation, historical actions and opt-in suitability. Executor identity remains the intentional provenance difference between engines; all policy/evidence/score fields compare exactly within each profile. Historical replay preserves its original executor identity without normalization.

| Check | Actual result |
|---|---|
| Focused five modules |291 passed,0failed,44.74s |
| Broad deferred-profile backend |1,797 passed,1known failure,224.29s |
| Broad experimental-profile backend |1,797 passed,1same known failure,316.15s |
| Actual-service four-way browser suite |28 passed,57.4s |
| Existing browser regressions |35 passed,4.0min |
| TypeScript, ESLint, isolated production build |exit0 each; no application source change |

The broad failure remains `tests/test_report_architecture.py::ReportArchitectureTests::test_single_backend_and_canonical_ml_locations`, asserting that `ai-services` should not exist. That assertion/directory was not changed or deleted. CV geometry is not run in this regression environment, which does not provide its dedicated torch/CV stack; no real CV/VTOFF/VTON model evaluation is claimed. Existing two ESLint navigation warnings remain at `frontend/app/extract/results/page.tsx:154` and `frontend/components/Layout.tsx:50`. The Starlette/httpx warning is unchanged. Browser Node `NO_COLOR`/`FORCE_COLOR` warnings are environmental and did not fail the suites.

Exact PowerShell commands from `backend` (all logs retained):

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
$env:SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE='reference'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='compatibility_deferred'
$phaseArgs=@('--no-project','--python','3.12','--with','pytest','--with','jsonschema','--with','fastapi==0.146.0','--with','httpx==0.28.1','--with','pillow==13.0.0','--with','python-multipart==0.0.32','--with','numpy==2.5.4')
uv run @phaseArgs python -B -m pytest -p no:cacheprovider tests/test_compact_default_readiness.py -q --tb=short
uv run @phaseArgs python -B -m pytest -p no:cacheprovider tests/test_compact_default_readiness.py tests/test_compact_assistant_integration.py tests/test_compact_exhaustive.py tests/test_compact_integration.py tests/test_assistant_decision_integration.py -q --tb=short
uv run @phaseArgs python -B -m pytest -p no:cacheprovider tests --ignore=tests/test_segmentation_geometry.py -q --tb=short
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='experimental_compatibility_decision_v1'
uv run @phaseArgs python -B -m pytest -p no:cacheprovider tests --ignore=tests/test_segmentation_geometry.py -q --tb=short
```

The broad commands have exit1 for the documented existing assertion; the focused commands exit0. Both broad collections contain exactly the same1,798 cases. Default-off settings are not changed by a test process's environment. The focused test itself explicitly composes all four combinations.

Exact frontend commands from `frontend`:

```powershell
npx tsc --noEmit
npm run lint
$env:SMART_WARDROBE_BUILD_DIR='.next-integration-run/compact-readiness-production'
$env:SMART_WARDROBE_BACKEND_URL='http://127.0.0.1:3201'
npm run build
npx playwright test --config playwright.compact-readiness.config.ts --grep 'integrated functional'
npx playwright test --config playwright.integration.config.ts --output .next-integration-run/compact-readiness-legacy-artifacts
```

The production build uses the installed Next16.4.2/React19.2.4 package lock without updating dependencies. The new isolated config reuses one local Uvicorn process on3201 and production Next on3200; the legacy suite retains its own3100/3101 fixture. Existing auth, feature-flag disabled/enabled behavior, Homepage, Assistant, Chat History, garment confirmation, save and visualisation-action regressions pass without editing their application implementations. Visualisation tests validate source/actions; they do not execute a real VTON model.

## Initial collection attempt: blocked at the first handoff

After both backend runs, the build and both browser suites finished, the isolated collector started production servers, allowed10s for startup to settle without a recommendation warm-up, and took three preflight observations. CPU load was **72%,82%,90%**, with free physical RAM approximately5.66-5.68GiB. RAM passed the proposed4GiB operational control; CPU did not pass the idle20% control. The collector retained all observations and terminated with `collection.state=resource_blocked` **before any timed recommendation**.

`transport-controlled-1.json`, its log/exit file and retained Playwright trace document the attempt. The Playwright collection reports **1 failed** for this explicit environment preflight, not a failed application recommendation or new scoring regression. There are **zero new timing trials**: median, tail and completion/error rates are unavailable, not0s or0% errors. The requested new matched20/50/100/200/stress matrix remains unexecuted until a low-contention collection is possible.

A later read-only3.14s idle process sample still observed54% OS CPU load; `RobloxPlayerBeta` consumed about1.32 logical-core equivalents and `ctfmon` about0.71. These diagnostic observations are retained in `idle-process-deltas.json`; they are not response-time samples. No unrelated user application was closed. No test/build/profiler was deliberately overlapped with the attempted latency collection.

The20%/4GiB/three-sample choices are versioned collection controls, not a newly approved FYP baseline or performance acceptance threshold. Even relaxing that specific CPU number would not establish minimal competing activity from72-90% observed idle load. The user was asked to pause heavy workloads; absent verified quiet conditions, this report does not assume that the environment became quiet.

Exact attempted command from `frontend`:

```powershell
$env:SMART_WARDROBE_READINESS_BENCHMARK='true'
$env:SMART_WARDROBE_COMPACT_DIAGNOSTICS='false'
$env:SMART_WARDROBE_COMPACT_RUN_LABEL='controlled-1'
npx playwright test --config playwright.compact-readiness.config.ts --grep 'resource-qualified matched'
```

For a later authorized quiet run, retain `controlled-1` and choose a new label, for example `controlled-2`. The collector refuses an existing output filename. It schedules alternating reference/compact pairs for both profiles and both transports, with three pairs at100/200 and two at20/50/stress, preserving every timeout and draining each backend job before the next trial. The original proxy timeout and exhaustive generation semantics remain unchanged. The existing `backend/scripts/summarize_compact_integration.py` can summarise a **completed nonempty** new population; do not present an empty blocked population as a successful latency report.

## Earlier Phase3F performance context ? not new stable measurements

The following successful median / observed maximum seconds are retained **Phase3F main-population** results, quoted only to show the current known requirement gap. A=deferred, B=experimental. CPU in that population ranged45-99%; these are not a substitute for the blocked Phase3G controlled run. Timeout cells list failed/all browser trials; backend eventual completion is not successful browser latency.

| Garments | Profile | HTTP reference | HTTP compact | Browser reference | Browser compact |
|---|---|---:|---:|---:|---:|
| 20 | A | 0.065 / 0.069 | 0.048 / 0.049 | 0.161 / 0.173 | 0.149 / 0.166 |
| 20 | B | 0.093 / 0.097 | 0.058 / 0.063 | 0.208 / 0.226 | 0.187 / 0.202 |
| 50 | A | 0.410 / 0.454 | 0.197 / 0.197 | 0.546 / 0.590 | 0.281 / 0.330 |
| 50 | B | 0.712 / 0.737 | 0.253 / 0.256 | 1.239 / 1.407 | 0.654 / 0.721 |
| 100 | A | 3.517 / 3.664 | 1.135 / 1.171 | 3.657 / 4.488 | 1.201 / 1.552 |
| 100 | B | 5.506 / 6.170 | 1.732 / 1.876 | 6.601 / 6.810 | 1.780 / 2.084 |
| 200 | A | 23.194 / 25.969 | 7.289 / 7.954 | 23.538 / 24.458 | 8.297 / 8.522 |
| 200 | B | 36.745 / 41.582 | 9.760 / 9.778 | timeout 3/3 | 10.605 / 10.985 |
| stress | A | 46.569 / 50.388 | 15.705 / 16.401 | timeout 2/2 | 12.976 / 13.348 |
| stress | B | 60.880 / 61.280 | 16.847 / 17.325 | timeout 2/2 | 17.108 / 17.272 |

Earlier main counts remain96 trials: reference7/48 transport errors, compact0/48; all backend jobs settled. The independent56-trial small-wardrobe repeat had0 transport errors. Its100-garment compact browser medians were1.071s /1.270s, with maxima1.244s /1.340s. Neither population is pooled with the new preflight or relabelled as formal acceptance. Backend service/CPU, HTTP arrival and browser measurements remain separately available in the unchanged Phase3F summaries/report.

**Current five-second status:** compact100-garment observations were below5s in those earlier populations, but not under a newly certified controlled baseline. All measured compact200-garment main cases exceeded5s, as did outerwear stress. The report-defined formal baseline still requires approval, and this phase has no new quiet timing evidence. NFR-02 and final FYP acceptance therefore remain **not established**.

## Source integrity and readiness assessment at the first handoff

The pre-phase hash inventory covers253 existing files. All186 application files and37 earlier fixture/archive/manifest files remain byte-identical. Package manifests/lockfile, frontend application/components and `AGENTS.md` are unchanged. The only intentionally changed captured file is the appended requirement traceability document. The earlier Phase3F evidence files remain unchanged; no old measurement, timeout, source pin or archive was replaced. `integrity-final.json` and the final `deliverables.json` record the checks and new phase file hashes.

Only the four generated TypeScript includes were removed; the original key order and line-ending bytes were preserved, verified against the pre-phase SHA256. A serialization-based reconstruction was rejected before writing because it did not reproduce those bytes. The final restored-config TypeScript check passes. Final lint passes with the same two existing warnings. `git diff --check` exits0; any Git LF/CRLF notices do not indicate a whitespace-check failure. A separate scan covers the newly created text files because untracked files are not included by ordinary `git diff --check`.

An additional idle follow-up, with all verification/server workloads finished, still observed70%,71%,84% CPU load (`idle-followup.json`). There is no evidence that a quiet window became available after the blocked attempt. No resource-affected trial was silently replaced with a faster one.

**Functional/default-preparation status: PASS WITH LIMITATIONS. Controlled-performance portion: BLOCKED BY HOST CONTENTION. Production-default transition: NOT READY FOR APPROVAL ON THIS EVIDENCE.** The application integration, four-way semantics and in-process rollout/rollback tests pass. No new application regression is detected; the existing architecture assertion and dedicated CV-test omission remain. A new quiet matched matrix, an approved formal baseline and actual deployment/drain/capacity confirmation remain outstanding. This is not a completed NFR-02 verification or final FYP acceptance.

Compact is technically qualified for explicitly selected development/test use and remains the stronger execution candidate based on the retained exactness and earlier speed evidence. Keep the production/source default at `reference` until the outstanding readiness evidence is reviewed and the owner separately approves activation. A default switch does not itself solve the200-garment latency gap or establish multi-user capacity.

Keep `compatibility_deferred` as the scoring default independently of that execution decision. Experimental arithmetic equivalence does not validate subjective colour/style coordination, partial-evidence midpoint choices, the no-pair convention, policy weights or general fashion quality. Independently reviewed ranking/quality evaluation is still required before a scoring-default decision. Suitability remains opt-in; unvalidated approximate hex and pattern scoring remain disabled.

**Next acceptance milestone:** review/freeze the proposed baseline and realistic dataset specification; resume the existing matched collector on a quiet approved host (retain the failed preflight under its original label), then run the separately approved formal workload and review every slow/failed terminal response. Confirm the actual deployment restart/drain configuration and capacity scope. Only then make a separate explicit default-transition decision. If measured exactness-preserving performance or admission/cancellation corrections are necessary, propose them separately; none is implemented here. No subsequent phase or default activation has begun.

## Resumed verification: resource preparation and tooling

The owner paused unnecessary CPU-heavy applications, then confirmed OneDrive syncing was paused. Initial resumed observations were12%,7%,22% CPU with about10.2GiB free RAM. A read-only process-delta sample showed the earlier game load had fallen substantially. `controlled-2` was still blocked at45%,19%,20% before timing; successive resident-process samples confirmed OneDrive consuming approximately one logical core. After pausing sync, its observed CPU deltas fell to zero. `controlled-3` retained35%,9%,19% and also stopped before timing. All prior observations, logs and failed preflights remain intact.

The only resumed code change is in the test-only collector `frontend/tests/phase5f/compact-readiness.spec.ts`: collection-controls1.1.0 waits up to120s for three consecutive qualifying samples, retaining **every** settling observation. CPU at most20%, free RAM at least4GiB, the initial10s server-settling wait, all workload/profile/transport combinations and response timing rules are unchanged. This avoids restarting servers after a single transient startup observation. It does not discard a timed request, relax NFR-02, change any algorithm, or perform a recommendation warm-up. The original collector bytes are archived in `compact-readiness-spec-before-resume.ts.txt`; the earlier delivered report/index/traceability are archived separately. TypeScript and collector ESLint both exit0.

`controlled-4` retained25 preflight observations before reaching14%,20%,7% CPU. It then completed all96 alternating matched trials (collector test19.6min, exit0). Test/build/profiler workloads did not overlap timing. Every backend job settled and selected; all10 workload/profile semantic fingerprint groups also agree with the retained Phase3F population after only the already documented executor-identity normalization. Candidate counts and96 distinct recommendation/chat IDs are verified in `resume-verification-analysis.json`.

Before/after resource snapshots during timing ranged **3-73% OS-reported CPU** and **9.19-10.07GiB free RAM**. Passing the preflight is not proof of continuous isolation. Some Code activity is visible; the limited resident-process samples cannot conclusively attribute every spike or exclude protected/nonresident processes. No trial is removed for those observations. Treat this as a resource-qualified matched local run with explicit residual variability, **not a certified continuously quiet formal-acceptance population**.

Post-run diagnostics are separate from latency. A replay of the observer recorded14%,10%,2% CPU, and six valid direct native `Processor(_Total)` samples ranged3.32-5.51%. The first background-job counter export did not retain usable per-process fields; it is preserved but excluded. `post-run-native-counters.json` contains the valid replacement (6sets,1,662samples,0counter errors). These later observations show low load at that later point; they do not retroactively explain all73% in-run readings or establish that the observer caused them. No unrelated process or security service was stopped by the agent.

### Exact resumed commands

From `frontend`:

```powershell
npx tsc --noEmit
npx eslint tests/phase5f/compact-readiness.spec.ts
$env:SMART_WARDROBE_READINESS_BENCHMARK='true'
$env:SMART_WARDROBE_COMPACT_DIAGNOSTICS='false'
$env:SMART_WARDROBE_COMPACT_RUN_LABEL='controlled-4'
npx playwright test --config playwright.compact-readiness.config.ts --grep 'resource-qualified matched'
```

The same collection command with labels `controlled-2` and `controlled-3` produced the retained resource-blocked exit1 attempts with zero timing trials. `controlled-1` remains the original blocked attempt. From `backend`:

```powershell
uv run --no-project --python 3.12 python -B scripts/summarize_compact_integration.py ../storage/verification/phase5f2e3c3g/transport-controlled-4.json ../storage/verification/phase5f2e3c3g/transport-controlled-4-summary.json
```

### Matched response results

A=deferred; B=experimental. Cells show **successful median / observed maximum seconds**. Each cell has2 trials at20/50/stress and3 at100/200. Timeout cells report failed/all trials, not successful latency. Observed maxima are the descriptive tail measure; these small samples do not support a reliable percentile SLA.

| Garments | Profile | HTTP reference | HTTP compact | Browser reference | Browser compact |
|---|---|---:|---:|---:|---:|
| 20 | A | 0.055 / 0.062 | 0.035 / 0.035 | 0.169 / 0.188 | 0.116 / 0.125 |
| 20 | B | 0.058 / 0.058 | 0.043 / 0.045 | 0.132 / 0.141 | 0.120 / 0.133 |
| 50 | A | 0.275 / 0.277 | 0.112 / 0.115 | 0.437 / 0.501 | 0.182 / 0.190 |
| 50 | B | 0.454 / 0.463 | 0.156 / 0.173 | 0.545 / 0.591 | 0.216 / 0.219 |
| 100 | A | 1.894 / 1.945 | 0.608 / 0.629 | 2.109 / 2.230 | 0.732 / 0.780 |
| 100 | B | 2.957 / 2.969 | 0.872 / 1.000 | 2.983 / 3.063 | 0.927 / 1.048 |
| 200 | A | 13.742 / 13.928 | 4.491 / 4.524 | 16.355 / 16.894 | 5.038 / 5.140 |
| 200 | B | 21.489 / 21.799 | 5.994 / 5.995 | 21.514 / 21.564 | 6.017 / 6.039 |
| stress | A | 30.969 / 31.155 | 9.932 / 9.966 | timeout 2/2 | 10.067 / 10.173 |
| stress | B | 47.895 / 48.293 | 13.482 / 13.673 | timeout 2/2 | 14.013 / 14.185 |

Completion/error counts: direct HTTP48/48 succeeded; compact browser24/24 succeeded; reference browser20/24 succeeded, with4/24 proxy failures (all four reference stress browser trials). Across transports, reference44/48 succeeded, compact48/48. Overall92/96 successful transport/UI responses (not necessarily within5s) and4 retained failures; all96 backend jobs later settled/committed. A collector test passing does not erase those failed browser responses. No proxy timeout was increased.

Backend service measurements below use the **direct-HTTP cohort**, median / maximum seconds, separately from end-to-end transport/UI. The JSON also retains browser-cohort backend time, process CPU, working-set/lifetime-peak observations and per-group resource envelopes.

| Garments | Profile | Reference service | Compact service |
|---|---|---:|---:|
| 20 | A | 0.047 / 0.054 | 0.028 / 0.029 |
| 20 | B | 0.052 / 0.053 | 0.036 / 0.038 |
| 50 | A | 0.269 / 0.270 | 0.106 / 0.110 |
| 50 | B | 0.448 / 0.456 | 0.151 / 0.167 |
| 100 | A | 1.888 / 1.939 | 0.602 / 0.623 |
| 100 | B | 2.951 / 2.963 | 0.864 / 0.992 |
| 200 | A | 13.737 / 13.923 | 4.486 / 4.519 |
| 200 | B | 21.482 / 21.792 | 5.987 / 5.990 |
| stress | A | 30.963 / 31.149 | 9.926 / 9.961 |
| stress | B | 47.890 / 48.288 | 13.475 / 13.665 |

Direct HTTP and browser are separate matched cohorts. At200 deferred, compact service median was4.486s in HTTP trials versus4.965s in browser trials. Therefore the entire difference between HTTP4.491s and visible-browser5.038s is **not** proven frontend overhead; backend runtime also varied. The response bound applies to the complete user-visible interaction, not a chosen faster layer.

### Five-second status and current readiness

At100 garments all six compact browser calls were below5s: deferred median0.732s/max0.780s; experimental median0.927s/max1.048s. At200 deferred, browser values were5.140267s,5.037962s,4.947148s: **2/3 exceed5s**, despite all three direct HTTP calls being below5s. At200 experimental, **3/3 exceed5s**, median6.017s/max6.039s. Stress compact browser calls exceed5s under both profiles; reference stress browser calls time out. These results preserve the original bound and all slow/failing trials.

**Formal NFR-02: NOT ACCEPTED / NOT ESTABLISHED.** The formal baseline proposal remains unapproved; this run uses the same homogeneous synthetic vintage/blue request and one preference as Phase3F, not the proposed diverse13-category/missing-evidence/0-1-3-preference baseline. No-result and unsupported latency cases were not newly timed. CPU snapshots retain residual variability. Neither a successful100-garment sample, a passing median, nor later stress backend commit establishes the report-wide acceptance requirement.

The proposed acceptance specification is nowv1.1.0 (still pending approval): it retains all workload, five-second and failure rules, clarifies consecutive preflight observations, and requires validating observer overhead plus low-overhead continuous native CPU/process monitoring for the formal run. It does not introduce a new NFR threshold or replace the earlier proposal/measurements; the prior document is archived.

**Engineering readiness: PASS WITH LIMITATIONS; ready for the owner's separately approved controlled default-transition decision on the verified stack, not blanket production/FYP sign-off.** The compact path preserves the previously verified exactness, security, atomicity, idempotency and rollback contracts. It has lower successful medians in every group where both arms succeeded; in stress browser groups it completed while reference timed out. The source/default remains `reference`; no activation is performed here. Retain explicit reference rollback, the deferred profile, and the deployment/drain/capacity checks. The200 browser latency gap and untested simultaneous-large-wardrobe capacity remain operational limitations, not solved requirements.

Experimental scoring should remain default-off: arithmetic/performance equivalence does not validate fashion heuristics, policy weights, midpoint/no-pair conventions or real-user ranking quality. Suitability remains opt-in; approximate hex/pattern scoring remain disabled. The next milestone is owner review of the controlled-transition decision and formal test specification, then the approved realistic acceptance workload on the agreed deployment. No later phase, default switch or unrelated performance optimisation has begun.

Resumed changes relative to the prior handoff are limited to the collector preflight, this report and the appended traceability update, plus new local evidence files. The earlier291-focused/1,797-per-profile backend and28/35 browser results are preserved, not falsely described as rerun. Application sources and frozen references are rechecked; only TypeScript/collector lint and the resumed measurements needed new execution.
