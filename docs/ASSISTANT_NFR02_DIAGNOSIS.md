# NFR-02 critical-path diagnosis and targeted correction

Phase 5F-2E-3C-3C. Experimental activation remains **not approved**. This is a performance investigation, not final FYP acceptance. Measurement results and verification are recorded below and in `storage/verification/phase5f2e3c3c/` (local generated evidence, not production data).

**Targeted correction verification: PASS WITH LIMITATIONS; ready for review. NFR-02 remains unmet on tested large workloads; formal acceptance is not established and production activation is NOT READY.** No further architecture or deployment change has been implemented.

## Authoritative requirement

Original Project I report, PDF page 180 / printed page 169, NFR-02:

> The system shall return either one outfit recommendation, a no-result response, or an unsupported-request response within five seconds after a valid NLP request is submitted under the baseline test environment.

PDF page 179 / printed page 168 refers to a baseline deployment environment and workload defined in the system test plan. Section 4.11.4 (PDF page 302 / printed page 291) discusses application-server processing, filtering before costly scoring, and verification in the final implementation/test environment. Neither passage defines 100 or 200 garments as the acceptance baseline, hardware, request/preference complexity, concurrency, or a percentile/median criterion. Submission to returned response is the stated boundary; this investigation additionally measures visible browser completion. A median below five seconds is not proof that every response meets this requirement. The original PDF SHA-256 is `5e5781cd739b696e63cd21a063b8e741daaa6fa93b20f4849b0b84a7c7e38669`; extracted evidence is `report-nfr.json`.

Formal baseline conditions remain incompletely specified. The requested 20/50/100/200/stress workloads are explicit reproducible scalability tests, not invented report conditions. Large-workload observed failures must not be reclassified as compliance by redefining the baseline or increasing timeouts.

## Reproduction and instrumentation

The disposable loopback test server uses the actual authentication, API, NLP, strict query, generation/filtering, scoring, ranking and transactional repository. All fixture garments are synthetic, owned, available and linked to confirmed items/jobs. There are no saved outfits. Every request is `Suggest an outfit with vintage style`; each workload stores one blue-colour preference. Primary colours are blue and style annotations vintage. This is a repeatable favourable-evidence workload, not a representative fashion-quality dataset.

| Garments | Tops | Bottoms | Dresses | Outerwear | Exhaustive candidates |
|---|---:|---:|---:|---:|---:|
| 20 | 8 | 8 | 2 | 2 | 198 |
| 50 | 20 | 20 | 5 | 5 | 2,430 |
| 100 | 40 | 40 | 10 | 10 | 17,710 |
| 200 | 80 | 80 | 20 | 20 | 134,820 |
| 200 stress | 67 | 67 | 0 | 66 | 300,763 |

Candidates equal `(tops * bottoms + dresses) * (1 + outerwear)`. Environment metadata is retained in `transport.json`: Windows, uv Python 3.12.10, Next 16.4.2 production server, Chromium, SQLite disposable database, one backend process. Source hashes and exact package versions accompany measurements. These are local measurements; no deployment hardware equivalence is asserted.

Profile A remains `compatibility_deferred`, `0.70R + 0C + 0.30P`. Profile B is explicitly selected `experimental_compatibility_decision_v1`, exactly `0.60R + 0.20C_decision + 0.20P`. Reference/trial pairs alternate order; six pairs per profile/layer at 100 and two at other sizes. All transport failures are retained. Backend jobs are drained before the next trial, so proxy timeouts cannot create accidental overlap. Direct HTTP, production proxy/browser, service wall time and process CPU time are distinct measurements. Diagnostic instrumentation and cProfile runs are separate from uninstrumented latency runs.

### Measured critical path before correction

`diagnostic-stages.json`: actual HTTP 100-garment reference runs, cumulative seconds (diagnostic overhead included). Each R/P/gate/ranking call count is 17,710. Spans overlap; **do not sum this table**. Independent mandatory recheck is inside the gate. Transaction queries are inside persistence; raw compatibility is inside decision scoring orchestration. Snapshot validation includes acquisition and transaction revalidation/readback (300 constructions).

| Stage | A seconds | B seconds | Calls / interpretation |
|---|---:|---:|---|
| Authentication | .000068 | .000053 | 1 |
| HTTP field validation | .000096 | .000050 | 3 |
| NLP | .010308 | .000892 | 1 |
| Query and projection | .007776 | .008560 | 1 acquisition query |
| Snapshot validation | .001580 | .002120 | 300 |
| Structural retrieval/preparation | .008067 | .008704 | 1 |
| Candidate generator next | .436602 | .490748 | 17,711 including completion |
| Mandatory filter | .458808 | .503618 | 17,710 |
| Independent mandatory recheck | .420867 | .431103 | 17,710, nested in gate |
| Independent gate | .644697 | .676020 | 17,710 |
| Request score | .386095 | .444020 | 17,710 |
| Raw compatibility | — | 1.650048 | 17,710 |
| Decision policy application | — | 1.052014 | 17,710 |
| Preference score | .689330 | .736723 | 17,710 |
| Final exact score validation | .558812 | .563917 | 17,710 / 17,712 including B codec reconstruction |
| Winner comparison | .219457 | .208574 | 17,710 |
| Request garment evidence | .271754 | .282273 | 103,010 / 103,110 calls |
| Raw compatibility garment evidence | — | .135215 | 51,410 calls |
| Persistence total | .014851 | .017377 | 1 |
| Revalidation checkpoint | .006503 | .006601 | includes transaction acquisition/idempotency/comparison |
| Transaction query and projection | .007153 | .009966 | 2, both before commit |
| API JSON rendering | .000199 | .000347 | 1 |
| Actual HTTP elapsed | 4.284 | 7.468 | instrumentation enabled |

The chat/recommendation/item/snapshot/metadata/submission/before-commit checkpoints are individually retained in the JSON. `_read` occurs before commit and rechecks current eligibility; it is not a post-commit query. Authentication, constant-size persistence and JSON rendering do not explain multi-second scaling.

Non-overlapping top-level measured scoring spans: A preference scoring, independent gate, final-score validation; B raw compatibility, decision application, preference scoring. Inclusive cProfile (`profile100.json`) instead identifies A request-stream iteration (2.348 s), final validation (1.571 s), preference scoring (1.370 s); B raw compatibility (3.789 s), decision application (2.664 s), request-stream iteration (2.494 s). Profiling overhead makes these unsuitable for acceptance timing. Nested decision validation and repeated mandatory verification remain real costs, not work removed by this phase.

## Retained correction

The only application replacement is the experimental factory selected in `assistant_scoring_selection.py`. The original prepared decision scorer remains intact as the differential oracle. The new coordinator copies its orchestration and substitutes a subclass of the existing cached raw scorer. A per-session, maximum-256-entry LRU reuses fully validated immutable numeric aggregate `ScoreEvidence` summaries. Keys contain ordered exact pair fractions/observed counts, never garment IDs, candidates, owners or eligibility proofs. Pair details and their garment-specific reasons remain freshly attached to each candidate. Unknown evidence and single-dress no-pair representation remain unchanged.

Structural validation, owner/policy binding, pair-evidence checks, all compatibility-decision validators, the independent scoring gate, exact final-score validation, full-stream completion and transaction revalidation still execute. Exact `Fraction` arithmetic, provenance, count semantics, winner tie-breaking and errors are unchanged. No new policy weights or compatibility conventions are introduced. The numeric cache captures immutable provenance rather than its owning scorer, avoiding a session-retaining reference cycle; a weak-reference regression test verifies release without waiting for cyclic GC.

Initial six-pair service measurements (reference → trial median seconds):

| Size | Reference | Trial | Notes |
|---|---:|---:|---|
| 20 | .083940 | .075963 | all six paired improvements |
| 50 | .970813 | .814032 | noisy; two pairs regressed |
| 100 | 5.284520 | 4.985675 | cold first pair regressed 44.5%; retained |
| 200 | 38.004595 | 32.943379 | all six improved; median reduction 13.3% |

Raw pair results, CPU values, fingerprints and score metadata are in `aggregation{20,50,100,200}.json`. The initial prototype used a bound-method cache; the final version removes that ownership cycle without changing keys, arithmetic or hits. Final HTTP/browser measurements use the final version. These separate runs must not be merged into one latency population. Even the improved large-workload service median remains far above five seconds.

A separate final-source diversity check uses six named colours and five existing style-annotation combinations (including an intentionally empty collection), a generic request, the same stored blue preference and all complete candidates. Six alternating pairs at each size have one identical fingerprint across all 12 runs: 50-garment median .696442 → .640312 s; 100-garment 4.525859 → 4.223693 s (`diverse-summary.json`). This reduces reliance on the favourable uniform-colour/style transport fixture. It does not establish benefit for every possible wardrobe or provide browser/NFR acceptance evidence. Cache eviction changes work only; no candidate is omitted.

Separate `tracemalloc` observation after scorer initialization, 1,024 distinct synthetic numeric vectors: capacity 0 retained 1,038 bytes / peak 2,862; capacity 256 retained **304,368 bytes** / peak 335,736; 1,024 misses and exactly 256 retained entries. This deliberately exercises a full cache with eviction. It excludes configuration initialization, existing pair/evidence caches, native allocations and process RSS. The weak-reference test separately proves the added numeric cache does not retain a dead scorer. Concurrent safety checks instantiate independent scorer sessions; no global mutable aggregate cache was added.

From `backend`, using the same uv Python/dependency arguments as the pytest command below:

```powershell
# Actual commands prefix: uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B
# Append each command suffix separately; sizes 20/50/100/200 each used repeats 6.
scripts/diagnose_integrated_assistant.py --size 100 --repeats 2 --profile --output ../storage/verification/phase5f2e3c3c/profile100.json
scripts/diagnose_integrated_assistant.py --size 200 --repeats 6 --trial --output ../storage/verification/phase5f2e3c3c/aggregation200.json
scripts/diagnose_integrated_assistant.py --size 50 --repeats 6 --trial --diverse --output ../storage/verification/phase5f2e3c3c/diverse50.json
scripts/diagnose_integrated_assistant.py --size 100 --repeats 6 --trial --diverse --output ../storage/verification/phase5f2e3c3c/diverse100.json
scripts/measure_aggregation_cache.py ../storage/verification/phase5f2e3c3c/cache-memory.json
```

These suffixes are shown without repeating the long interpreter prefix; they are not standalone PowerShell executables. The initial prototype's measurements predate the final selector wiring; the diagnostic script now explicitly forces the original reference factory, so rerunning does not accidentally compare the optimized implementation with itself.

## Files and verification scope

Application files:

- `backend/app/application/recommendation/prepared_compatibility_aggregation.py`: bounded exact numeric aggregate reuse.
- `backend/app/application/recommendation/aggregated_decision_scorer.py`: separate coordinator retaining the original prepared scorer as oracle.
- `backend/app/application/recommendation/assistant_scoring_selection.py`: experimental branch factory only; default remains deferred.

Verification/tooling files:

- `backend/scripts/diagnose_integrated_assistant.py`: disposable actual-service paired benchmark and cProfile export.
- `backend/scripts/summarize_assistant_critical_path.py`: retained-trial summaries, observed tail maxima and exact paired fingerprint checks; failed responses are not silently omitted.
- `backend/scripts/measure_aggregation_cache.py`: separately instrumented synthetic allocation observation, explicitly not whole-process RSS or acceptance latency.
- `backend/tests/test_prepared_aggregation.py`: exact raw/ranked/persisted differential tests, boundedness, invalid settings, release of dead sessions.
- `backend/tests/assistant_critical_path_server.py`: loopback-only diagnostic wrappers, completion telemetry, isolated profile control and late-failure injection. Never a production endpoint.
- `backend/tests/integration_source_guard.py`: chain the new separately approved source replacement; old pins remain authoritative.
- `backend/tests/fixtures/critical_path_sources.v1.json`: two new modules and one explicitly chained factory replacement.
- `backend/tests/fixtures/critical_path_reference/{app.zip,manifest.json}`: new immutable 176-file pre-phase application archive and hashes, not a rewrite of any earlier frozen archive.
- `frontend/playwright.critical-path.config.ts`: isolated production-build/browser test setup.
- `frontend/tests/phase5f/critical-path.spec.ts`: matched HTTP/browser timings, completion/fingerprint checks, actual timeout/retry/rollback/concurrency checks.
- This document and `docs/REPORT_TRACEABILITY.md`: findings and requirements linkage.

Generated build includes in `frontend/tsconfig.json` are removed after verification. No frontend application, dependency, database, CV, wardrobe, homepage or historical-data changes are part of this phase.

Source integrity (`integrity.json`): 181 of 182 pre-phase hashed files are byte-identical. The sole replacement is the explicitly pinned experimental selector; the two new application modules are separately pinned. All 22 previous fixture/manifest/archive files are byte-identical. All 176 entries of the new pre-phase archive match both its manifest and the pre-phase hashes. Archive SHA-256: `b25a99d68de442798188501fdf80c76109a7b25801e03b0f5123f567014ce71a`. AST comparison confirms the new coordinator differs only in its class name and substituted raw scorer (plus module documentation). Existing frozen-source guards pass in both broad runs; old archives/pins were not rewritten to accommodate the optimization.

### Verification commands

PowerShell, from `backend` (run twice: environment selector unset, then explicit experimental value):

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
Remove-Item Env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE -ErrorAction SilentlyContinue
# Second run instead sets:
# $env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='experimental_compatibility_decision_v1'
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests --ignore=tests/test_segmentation_geometry.py -q --tb=short
```

Final results: **1,547 passed, one failed** under each profile (234.51 s deferred; 247.39 s experimental). The failure is the existing `tests/test_report_architecture.py:28` assertion that `ai-services` must not exist. No folder or assertion was removed. `test_segmentation_geometry.py` was not executed because the required CV/torch environment is not provisioned; this phase does not modify those algorithms. FastAPI/Starlette emits an existing httpx deprecation warning. The 16 new aggregation tests are included in both broad runs.

An earlier focused command (before adding the final weak-reference test, which both final broad runs cover) was:

```powershell
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests/test_prepared_aggregation.py tests/test_assistant_decision_integration.py tests/test_prepared_decision_performance.py tests/test_compatibility_pair_cache.py -q --tb=short
```

Result: **458 passed**, 23.52 s. Raw/persisted equality includes all four structures, missing evidence, exact decision diagnostics and provenance. Synthetic fixture assertions are not fashion-quality validation.

Final rerun of that same focused command, including the added weak-reference test: **459 passed**, 32.23 s, one existing Starlette/httpx deprecation warning. Final TypeScript and ESLint reruns exit 0; TypeScript also exits 0 after removing only the four generated critical-path/history-build include entries. The final diagnostic-script smoke run (20 garments, one diverse reference/trial pair) exits 0 after explicitly pinning the reference factory for both profiling and trial modes.

From `frontend`:

```powershell
npx tsc --noEmit
npm run lint
$env:SMART_WARDROBE_BUILD_DIR='.next-integration-run/critical-path-production'
$env:SMART_WARDROBE_BACKEND_URL='http://127.0.0.1:3201'
npm run build
npx playwright test --config playwright.integration.config.ts --output .next-integration-run/critical-path-legacy
Remove-Item Env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE -ErrorAction SilentlyContinue
npx playwright test --config playwright.decision.config.ts --grep 'real Assistant|real controlled'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='experimental_compatibility_decision_v1'
npx playwright test --config playwright.decision.config.ts --grep 'real Assistant|real controlled'
```

Results: TypeScript exit 0; ESLint exit 0 with two existing navigation warnings (`app/extract/results/page.tsx:154`, `components/Layout.tsx:50`); isolated production build exit 0. Existing browser suite **35 passed** (4.2 min), including feature flags/authentication/cross-user/archival scenarios. Actual Assistant/History production browser tests **8 passed** under deferred (45.3 s), **8 passed** under experimental (43.6 s). The build uses its own directory; no unrelated cache directories were deleted. The old browser suite has its documented isolated build directories. Performance runs occur after these CPU-intensive checks finish.

Diagnostic and final timing commands (from `frontend`, diagnostics only uses sizes 100):

```powershell
$env:SMART_WARDROBE_CRITICAL_PATH_BENCHMARK='true'
$env:SMART_WARDROBE_CRITICAL_PATH_DIAGNOSTICS='true'
$env:SMART_WARDROBE_CRITICAL_PATH_SIZES='100'
npx playwright test --config playwright.critical-path.config.ts --grep 'matched paired'
# Copy transport.json to diagnostic-stages.json before the uninstrumented run.
$env:SMART_WARDROBE_CRITICAL_PATH_DIAGNOSTICS='false'
Remove-Item Env:SMART_WARDROBE_CRITICAL_PATH_SIZES -ErrorAction SilentlyContinue
npx playwright test --config playwright.critical-path.config.ts --grep 'matched paired'
```

The diagnostic test passed (57.6 s). Evidence collection intentionally records unsuccessful responses without declaring NFR acceptance. The test's successful exit certifies complete collection and fingerprints, not five-second responses.

## Root cause and transport interpretation

The 100-garment experimental delay is accumulated CPU/object-validation work over 17,710 candidates: existing stream/gate/R/P/total/ranking work plus raw compatibility aggregation and decision validation. It is not primarily authentication, SQL locking, a large API response, or a slow NLP model. The extra raw compatibility and decision spans alone explain much of the matched profile difference. Service `process_time` and wall times are retained; OS scheduling/thermal variation still affects local observations.

At 200 garments the experimental backend takes longer than the production rewrite proxy's unchanged default. Installed Next 16.4.2 `dist/server/lib/router-utils/proxy-request.js:37` configures `proxyTimeout: ... || 30000`. Browser requests return HTTP 500 / `ECONNRESET` around 30 seconds while the same job continues and returns `Selected` later. Direct backend HTTP, with a diagnostic client timeout, returns successfully after the full computation. The timeout is therefore the immediate transport failure; exhaustive backend latency is the underlying cause. No database-lock wait of comparable duration appears in the sequential diagnostic. The evidence does not establish behaviour on another deployment proxy, worker count or operating system.

For successful browser requests, the backend duration header and browser response arrival allow a **combined proxy/network/browser scheduling residual**, not a pure forwarding-only span. Visible UI completion is measured separately after the response. No claim is made that subtracting independently timed service-only trials isolates network time. There is no production-side Node profiler in this phase. Failed browser trials have no successful UI latency; their approximately 30-second elapsed failure time is explicitly retained as a failure, not substituted for backend completion time.

At 100 garments the successful browser-response-arrival medians are A 4.148 → 3.905 s and B 7.708 → 7.101 s. The combined residual medians are A .094 → .101 s, B .095 → .124 s (B trial maximum .961 s, retained). These are distinct from the visible-result medians in the main table. Both B response arrival and UI completion remain above five seconds; transport overhead is not the principal multi-second cause.

The normal synchronous service is not cooperatively cancelled by this tested proxy disconnect. A completed recommendation can consequently appear in history after the initiating browser has shown an error. This is existing behaviour, not a new asynchronous API or provisional success. Explicit timeout/idempotency/failure tests below verify the write safety. The current UI cannot receive a late backend error through a connection that has already failed; diagnostic job telemetry is test-only, not a deployed notification capability.

## Remaining acceptance decision

### Final-source paired transport results

Uninstrumented actual HTTP and production browser, seconds, reference → retained correction. At 100 each cell has six trials per arm; other sizes have two per arm. Browser timings include successful UI completion. A is a negative control: its reference/trial code is identical, so A timing differences are environment variation, **not** an optimization benefit.

| Size | Profile | Direct HTTP median | Browser median | Browser errors reference / trial |
|---|---|---:|---:|---:|
| 20 | A | .081 → .096 | .309 → .295 | 0/2 / 0/2 |
| 20 | B | .187 → .153 | .279 → .262 | 0/2 / 0/2 |
| 50 | A | .502 → .541 | .675 → .766 | 0/2 / 0/2 |
| 50 | B | .927 → .807 | 1.101 → .963 | 0/2 / 0/2 |
| 100 | A | 3.616 → 3.446 | 4.198 → 3.938 | 0/6 / 0/6 |
| 100 | B | 6.341 → 5.625 | 7.744 → 7.226 | 0/6 / 0/6 |
| 200 | A | 22.549 → 22.031 | 24.433 → 23.363 | 0/2 / 0/2 |
| 200 | B | 38.569 → 35.406 | no successful response | 2/2 / 2/2 |
| stress | A | 48.316 → 48.931 | no successful response | 2/2 / 2/2 |
| stress | B | 85.795 → 75.581 | no successful response | 2/2 / 2/2 |

For B at 100 the browser maxima are 10.311 → 8.746 s, direct HTTP maxima 8.377 → 6.362 s. All outliers remain. B at 200 fails near 30.1 s in both arms; that is elapsed failure time, not a successful response median. Full per-group backend service/CPU medians and observed maxima are generated in `transport-summary.json`; raw per-request score metadata, completion times, candidate counts and fingerprints remain in `transport.json`.

The prior integrated baseline browser medians were A100 4.373 s, B100 7.298 s, A200 22.387 s; B200 had 3/3 failures. Current matched B100 gains are 6.7% browser and 11.3% HTTP, while direct B200 gains are 8.2%. Comparing only the previous phase's B100 7.298 with current 7.226 gives a much smaller change; different runs have different scheduling conditions. Matched alternating pairs and the unchanged A control are the stronger evidence. No improvement is claimed from A's timing fluctuations. There is no demonstrated small-wardrobe regression in B, but two transport pairs alone are not a statistical generalization; the separate six-pair service runs supply additional evidence.

Final matrix: **112 trials, 100 successful client responses, 12 proxy failures**. All 112 backend jobs returned `Selected` after exhaustive completion. Every reference/trial pair has identical item/role/order, exact score and provenance fingerprints within its profile. All direct HTTP requests succeeded; browser failures comprise four B200 trials and all eight stress-browser trials. The aggregate error fraction is not directly comparable with the previous phase's 9/90 because workload sampling differs. Matrix collection passed in 32.3 minutes; this is explicitly not NFR acceptance.

### Timeout, retry and concurrent write safety

Both original and retained experimental scorer safety runs passed: **one test each**, 2.1 min / 1.8 min including server setup. `timeout-safety-reference.json` (also retained as the initial `timeout-safety.json`) and `timeout-safety-trial.json` contain raw evidence.

- Actual 200-garment browser requests failed at 30.315 / 30.168 s respectively; backend processing continued and committed exactly one recommendation and one completed chat. The real **Retry same request** button reused the original submission key and returned the stored result; a further direct retry had the same ID/exact score and no additional writes.
- Injecting a late exception at the repository metadata checkpoint, after preceding writes but before commit, produced late `PersistenceFailure`. Counts stayed at one recommendation/one chat from the earlier successful request: no new partial pair. The already-failed browser/proxy connection cannot deliver that later error; the test-only job endpoint observes it. Existing broad repository tests additionally cover individual write checkpoints and transaction-bound garment changes.
- Two concurrent same-key 100-garment submissions returned one shared recommendation ID, exactly one fresh result and one replay, equal score metadata, and a count increase of exactly one recommendation/chat pair. Overall elapsed time: 11.435 s reference, 9.551 s correction.
- Two concurrent distinct-key submissions returned two different IDs and exactly two new complete pairs: 10.298 s reference, 9.552 s correction.

Durable idempotency prevents duplicate writes, **not necessarily duplicate pre-commit computation**. Requests may both rank before one resolves the submission in the write transaction. The existing frontend single-flight guard covers its own key; it is not a server-wide scheduling mechanism. No new cancellation, in-progress reservation, background job or lock semantics were introduced. Enumeration remains outside the write transaction; strict snapshot comparison and atomic persistence remain inside it. These local two-request observations do not establish production load capacity.

```powershell
# From frontend; repeat with arm='trial'.
$env:SMART_WARDROBE_CRITICAL_PATH_SAFETY='true'
$env:SMART_WARDROBE_CRITICAL_PATH_ALLOW_FAILURE='true'
$env:SMART_WARDROBE_CRITICAL_PATH_DIAGNOSTICS='false'
$env:SMART_WARDROBE_CRITICAL_PATH_SAFETY_ARM='reference'
npx playwright test --config playwright.critical-path.config.ts --grep 'real timeout retry'
```

The first reference run used the same test before the explicit arm/output suffix was added; reference was hard-selected and its original output was copied byte-for-byte to the suffixed reference filename. The final trial run used the explicit selector. Synthetic failure injection and selector endpoints exist only in the disposable loopback test harness.

Final repository check, from repository root: `git diff --check` exits **0**. A separate whitespace scan covers the authored untracked text files, which Git's ordinary diff does not include. Generated evidence file names/hashes and the 16 authored source/test/config/documentation paths are listed in `storage/verification/phase5f2e3c3c/artifacts-inventory.json`; build/browser artifacts remain in the documented ignored `.next-integration-run/` directories. None were silently deleted. Raw timeout errors and unsuccessful timings remain available locally.

Git also reports LF-to-CRLF conversion notices for existing dirty `recommendation_service.py`, `frontend/app/history/page.tsx` and `frontend/tsconfig.json`; these are not whitespace-check failures. No unrelated source changes were made to silence them.

Backend service times for browser-originated jobs (median / observed maximum seconds, reference → correction):

| Size / profile | Backend service median | Backend service maximum | Process CPU median |
|---|---:|---:|---:|
| 100 A | 4.050 → 3.803 | 4.655 → 4.317 | 3.547 → 3.383 |
| 100 B | 7.600 → 6.543 | 10.148 → 8.577 | 6.141 → 5.461 |
| 200 A | 24.295 → 23.213 | 24.708 → 23.225 | 21.477 → 21.430 |
| 200 B | 42.247 → 36.499 | 43.032 → 36.801 | 39.008 → 33.617 |
| stress A | 54.923 → 58.929 | 55.309 → 63.831 | 49.422 → 50.531 |
| stress B | 101.702 → 90.034 | 102.500 → 93.103 | 92.789 → 81.563 |

These service times are **not** successful browser response times after a proxy failure. Native/process RSS was not sampled for the full matrix; the separate cache allocation observation has a narrower stated scope. Process CPU is meaningful for these sequential jobs, but concurrent-request process CPU spans overlap and must not be summed.

Measured improvements do not establish NFR-02 compliance or production readiness. Increasing the proxy timeout would change transport failure visibility while leaving the five-second problem unresolved. Independent fashion-quality validation also remains separate from arithmetic/differential correctness.

The smallest proposed next step, **not implemented**, is a separately reviewed session-preparation/verification design to reduce repeated immutable evidence traversal and object construction while preserving an independent mandatory gate and exact score validators. Benchmark a proof-of-equivalence prototype against the frozen reference before any contract change. Branch-and-bound, candidate pruning that changes exhaustive accounting, a new asynchronous API, additional workers, or altered cancellation/persistence semantics require separate approval. This investigation does not prove exhaustive enumeration is impossible on every baseline/hardware; it demonstrates that the current measured implementation plus this safe correction is insufficient for the tested large workloads.

A concrete architectural alternative for separate review is bounded parallel **exhaustive** scoring: prepare one immutable owner/request/preference snapshot, deterministically partition complete candidate ranges, run the full independent gate and original exact validators in each worker, and merge completed local winners with the existing tie-breaker. Sum examined/passed/decision counts and require every partition to complete before selecting or persisting anything; any worker/stream failure invalidates the entire result. The parent alone performs strict transactional revalidation and one atomic write. This needs an explicit contract for worker ownership, snapshot serialization, failure/cancellation and diagnostic aggregation. Startup, memory multiplication, contention and serialization may erase gains; no speedup is claimed without measurements on agreed hardware. It is a proposal, not an implemented optimization or approved deployment change.

For scale, final browser-originated B200 backend median 36.499 s requires more than a sevenfold reduction to reach five seconds; stress B90.034 s requires more than eighteenfold. The retained local cache does not supply that reduction. First agree the missing formal baseline test-plan conditions without weakening the requirement, then approve the smallest isolated preparation/worker feasibility experiment. Retain the current default-off selector until performance, deployment assumptions, timeout behaviour and independent recommendation-quality validation are reviewed.
