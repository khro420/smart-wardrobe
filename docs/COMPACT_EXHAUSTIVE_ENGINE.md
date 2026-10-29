# Phase 5F-2E-3C-3E: isolated compact exhaustive engine

The compact engine is experimental infrastructure, **not selected by production composition or the live Assistant factory**. Deferred remains the default; approximate hex matching remains disabled and suitability remains opt-in. No policy weights, schema, frontend application source, Homepage behaviour, NLP or teammate algorithms change.

## Authority and reference

Original report RN-11–RN-23, sections 4.4.3 and 4.10.4 require eligible wardrobe input, mandatory filtering, scoring each valid candidate, deterministic highest-ranked selection and one result. RN-17 explicitly requires a score for **each valid outfit candidate**. The internal representation and validator implementation are newly approved implementation decisions, not rules stated by the report.

The primary differential reference is the retained `AggregatedDecisionRecommendationScorer`; deferred comparisons use the existing `RecommendationScorer`. Before implementation all 178 existing application Python/JSON files were archived in `backend/tests/fixtures/compact_reference/`. The archive SHA-256 is `c6e6de4092635cb422206119147385b1d45a306e8119398b7e28a862f417eb6b`. Earlier archives and policy files remain unchanged. New source hashes are separately recorded in `compact_sources.v1.json`; existing manifests are not rewritten to make the compact implementation pass.

## Execution and representation

1. Load the selected existing profile and verify that its request policy is available.
2. Acquire immutable records only through injected `ConfirmedGarmentQuery`, using the unchanged retrieval service for snapshot validation, deduplication and exclusions.
3. Capture and normalize the user's preferences once. Preserve original failure precedence, including preference validation before consuming an empty structural stream.
4. Prepare immutable garment-index tables, approved request evidence, preference facts and colour/style facts. Primary and independent mandatory tables are built separately using fresh approved classifiers. Cached scalar inputs remain bound to this owner, immutable request, snapshot tuple, normalized preference set and frozen policy.
5. Enumerate every approved structure as `(roles, indexes)` tuples. Garment order comes from the existing sorted IDs; ranking uses actual role/ID strings rather than index order.
6. Check structural membership and strictly increasing composition/index positions, evaluate primary mandatory conditions, and independently recheck every passing candidate.
7. Calculate R/C/P and exact total for every independently passing candidate. Retain only the current best plus bounded diagnostics/caches.
8. Require successful exhaustion, close, exact independent expected count and ledger equality before reconstructing a winner.
9. Rebuild the winner using the original public candidate, mandatory evaluation, gate, scoring components and final score validators. Compare the reconstructed conditions, summaries, detail values/states/coverage, raw compatibility dimensions/atoms, decision basis/bounds and total with the compact result. Any mismatch fails; no alternate winner is returned.
10. The unchanged Assistant service/repository may persist this public winner only through the isolated test bridge in this phase. Atomic transactional revalidation remains outside the engine and after enumeration.

The supported count is `N=(T*B+D)*(1+O)`. Strict monotonic order plus valid slot membership and exactly N unique combinations proves full coverage of this finite product, without an O(N) deduplication set. Truncated, duplicated and reordered injected streams fail. All valid candidates still receive their scores; there is no top-one pruning or candidate limit.

## Mandatory and numerical equivalence

Primary conditions use immutable per-garment state tables and positional evidence masks. For category/colour/base-style conditions: any positive evidence passes; absent positive evidence is Unknown if any relevant evidence is unknown, otherwise Fail. For explicit suitability: any deny fails, otherwise any unknown is Unknown, otherwise all constituents pass. The original category-failure short circuit is preserved while suitability conditions are still appended. Missing attributes are not positive matches.

The independent verifier does not accept the primary aggregate flag. It independently validates ownership, availability, ID uniqueness and taxonomy at preparation, rechecks structural membership for passing index tuples, independently reduces separately prepared condition tables, and compares condition-level evidence with primary results. As with the original full-object gate, processing-item confirmation/job linkage is a guarantee of Phase 1 acquisition: those private database fields are absent from snapshots. Actual SQLite integration tests verify that ineligible links never reach this engine. Commit-time strict query/snapshot comparison remains unchanged.

Scalar R and P reproduce the original algorithms, including base-only styles, global preferred colours, collective category groups, explicit formality alternatives, importance weighting, missing evidence, unsupported preferences and no-preference states. Existing validated preference preparation helpers are reused without changing their source. Request fields other than style contribute one only after mandatory verification; style retains its base-member match fraction.

Pair colour and style facts implement the existing equal-or-achromatic proxy and exact Dice style overlap. No new fashion rule, pattern rule or approximate colour evidence is introduced. Ordered atomic facts determine measured/unknown raw evidence, known counts and exact interval midpoint decisions. A dress has no pair atoms and retains NotApplicable raw pair evidence plus the explicit 1/2 NoPairReference. Measured zero stays measured zero.

Compact decision certificates are frozen and validate their atom types, ranges, coverage, raw state, exact bounds, midpoint and basis. Session-local bounded memoization reuses only identical immutable numerical inputs; each candidate checks that its actual ordered atoms and pair count match its certificate. R/P summary factories validate their detail inputs and exact aggregation. Cache eviction causes recomputation, never omission.

Every valid candidate then passes `validate_total`: component state/range/coverage checks and an independent exact cross-product equality for `S=w_r*R+w_c*C+w_p*P`. Python unbounded integers avoid overflow; no float or denominator bound is used. Fixed weights are validated once during immutable session preparation. This replaces repeated public-object construction for losing candidates, not the logical validation obligations. Public reconstruction invokes the original validators again for the winner; audit mode does so for every valid candidate.

Profiles are unchanged: deferred `7/10,0,3/10`; experimental `3/5,1/5,1/5`. Positive `(S,R,C,P)` lexicographic maximisation followed by the existing role/ID key minimisation is equivalent to the original negative-score comparison. Preference-only unequal ties cannot arise with identical S/R/C under these fixed positive preference weights, but the comparator retains that documented level and has a synthetic comparator test.

## Isolation, memory and lifecycle

Prepared snapshot/fact collections are tuples/frozen values; prepared attributes cannot be rebound or deleted. Mutable LRU state is session-owned. Pair capacity is at most 19,900; each numeric aggregate cache is at most 256. Zero capacity and eviction retain exact results. No global user/request cache is introduced. Memory is O(G + G*P + bounded pair/aggregate caches), plus one compact incumbent and one reconstructed public winner, not O(N). An audit sink may choose to retain records in tests; normal execution has no such collection.

The kernel refuses concurrent use of the same scorer instance, resets its session state on a later sequential rank, and new service requests create independent instances. All streams close in finally paths. Failure, interruption, close failure or reconstruction mismatch prevents publication/persistence of a winner. This phase does not add cooperative network cancellation or server-wide admission control: a disconnected synchronous request may still finish and commit, recoverable by existing idempotency.

## Test-only integration boundary

`tests/compact_service_adapter.py` is an explicit bridge for the original Assistant's captured-session provenance access. It obtains the already injected Phase 1 query from the test's engine composition, runs the compact kernel, and supplies the original evaluator metadata carrier. The public reconstruction session is deliberately closed as an unconsumed public stream; it is **not misrepresented as exhausted**. The compact exhaustive ledger and `RankingOutcome.complete` certify completion. Production use requires a separately approved prepared-context/provenance port; merely changing the live scorer factory is insufficient.

`tests/compact_assistant_server.py` runs only on loopback with disposable data. Its selection endpoint, failure injection, memory observations and job telemetry are test controls, not production APIs. Current service, authentication, actual HTTP/browser rendering, persistence, history and replay paths remain in use. Existing policy/evidence provenance is preserved exactly for differential comparison; the new implementation source version is recorded separately in the experimental manifest and test arm, not silently written into old history.

## Authored files

- `backend/app/domain/value_objects/compact_recommendation.py`: immutable scalar measures/decisions/scores and exact validators.
- `backend/app/application/recommendation/compact_candidate_stream.py`: lazy index products and public candidate reconstruction.
- `backend/app/application/recommendation/compact_mandatory_verifier.py`: primary and independent immutable mandatory preparations/checks.
- `backend/app/application/recommendation/compact_scoring_facts.py`: exact R/P and pair/decision composition with bounded caches.
- `backend/app/application/recommendation/compact_exhaustive_scorer.py`: complete ledger, streaming ranking, audit and public reconstruction.
- `backend/tests/test_compact_exhaustive.py`: candidate-level differential audits, independent expected compositions, numerical/stream/immutability tests and frozen reference verification.
- `backend/tests/test_compact_integration.py`: actual strict query, original service, rollback, changed snapshots, concurrency and historical replay.
- `backend/tests/compact_service_adapter.py`: explicit isolated provenance bridge.
- `backend/tests/compact_assistant_server.py`: disposable actual HTTP/browser fixture.
- `backend/tests/integration_source_guard.py`: add only separately pinned new modules to source-set verification.
- `backend/tests/fixtures/compact_sources.v1.json`: new source/activation manifest.
- `backend/tests/fixtures/compact_reference/app.zip` and `manifest.json`: new immutable pre-phase archive, not modifications of earlier references.
- `backend/scripts/benchmark_compact_exhaustive.py`: alternating actual-service comparisons, labelled diagnostics/allocation runs and Windows memory observations.
- `backend/scripts/verify_compact_candidates.py`: bounded-memory, every-candidate public-evidence comparison on large actual-query fixtures, independently checking the winner.
- `backend/scripts/summarize_compact_exhaustive.py`: reproducible aggregation retaining failed trials and separating instrumented, service, HTTP and browser populations.
- `frontend/playwright.compact.config.ts` and `frontend/tests/phase5f/compact.spec.ts`: isolated production browser functional, transport and safety verification.
- This document and `docs/REPORT_TRACEABILITY.md`: implementation, measurement and requirement evidence.

Ignored raw logs/JSON evidence are retained under `storage/verification/phase5f2e3c3e/`; browser/build artifacts remain under ignored `.next-integration-run/` directories. Generated TypeScript build includes are removed after verification, preserving pre-phase source configuration.

## NFR-02 interpretation

Original PDF page 180 / printed 169: “The system shall return either one outfit recommendation, a no-result response, or an unsupported-request response within five seconds after a valid NLP request is submitted under the baseline test environment.” Chapter 3 refers to a test-plan baseline but does not establish its numeric wardrobe size, hardware, concurrency or response-time percentile in the reviewed passages. These omissions remain unresolved. 100 garments is benchmark evidence; 200 and outerwear-heavy 200 are additional scalability/stress cases, not retrospectively declared formal acceptance baselines.

Successful service timing is not browser acceptance. Diagnostic timings and tracemalloc observations are separately labelled and excluded from uninstrumented transport results. Failed proxy/client responses remain failures even if the backend later commits. A five-second median alone does not establish the report's acceptance requirement.

## Verification commands and established results

PowerShell from `backend`, selector unset for the first run and explicitly set to `experimental_compatibility_decision_v1` for the second; `SMART_WARDROBE_VTOFF_ENABLED=off`:

```powershell
uv run --no-project --python 3.12 --with pytest --with jsonschema --with fastapi==0.146.0 --with httpx==0.28.1 --with pillow==13.0.0 --with python-multipart==0.0.32 --with numpy==2.5.4 python -B -m pytest -p no:cacheprovider tests --ignore=tests/test_segmentation_geometry.py -q --tb=short
```

Both profiles: **1,666 passed, one existing failure**, 309.94 s deferred / 308.17 s experimental. The failure remains `tests/test_report_architecture.py::ReportArchitectureTests::test_single_backend_and_canonical_ml_locations` (the `ai-services` assertion). Neither directory nor assertion was changed. The CV geometry test module is not executed because its CV/torch environment is not provisioned; no CV algorithms change. Existing Starlette/httpx deprecation warnings remain.

Focused command with the same interpreter/dependency prefix:

```powershell
python -B -m pytest -p no:cacheprovider tests/test_compact_exhaustive.py tests/test_compact_integration.py -q --tb=short
```

**119 passed** in 18.79 s before the last reconstruction dimension check; both final broad runs include that check and the same 119 tests. Four subsequent explicit same-instance cross-owner/request/snapshot and simultaneous-reuse cases are covered by the final focused rerun rather than those earlier broad collections. Earlier failed development runs are retained: one pytest reserved-parameter collection error, malformed test preference fixtures, and two new isolation-test assertions expecting empty acquisition before foreign-preference validation. The latter correctly returned `InvalidPreferenceData`; the assertions now preserve that established security/failure precedence and separately check empty acquisition after clearing the foreign preferences. Those were test-expectation errors; neither the engine nor old reference changed to satisfy them.

From `frontend`:

```powershell
npx tsc --noEmit
npm run lint
$env:SMART_WARDROBE_BUILD_DIR='.next-integration-run/compact-production'
$env:SMART_WARDROBE_BACKEND_URL='http://127.0.0.1:3201'
npm run build
npx playwright test --config playwright.compact.config.ts --grep 'compact functional'
npx playwright test --config playwright.integration.config.ts --output .next-integration-run/compact-legacy-artifacts
```

TypeScript, lint and isolated production build exit 0. Lint retains two existing navigation warnings in `app/extract/results/page.tsx:154` and `components/Layout.tsx:50`. **14 compact actual-browser functional tests passed** (1.0 min): all four structures, missing/partial/zero compatibility, actual history rendering, cross-user denial and exact replay under both profiles. **35 existing browser regressions passed** (4.9 min), including authentication/flags, wardrobe confirmation, Homepage/Assistant/history and saving/visualisation boundaries. No frontend application file changed.

Source integrity (`integrity.json`): all **178** existing application files and **31** existing fixture/reference files are byte-identical to the pre-phase hashes. The 178-entry new archive matches those hashes. All five new module pins match. The live factory selector is unchanged.

## Matched timing methodology

The transport benchmark uses current retained deferred and aggregated scorers as reference arms and the compact counterparts as experimental arms. Actual authentication, the original service, strict queries, real SQLite writes, Next production proxy and browser rendering are used. The disposable wardrobe distributions match Phase 3C; no saved outfits exist. The request is `Suggest an outfit with vintage style`, with one stored blue preference. All garments are synthetic blue/vintage descriptors and valid for that request; this is not a fashion-quality dataset.

The primary matrix has six alternating reference/compact pairs at 100 and 200 garments, two elsewhere, independently for HTTP and browser and both profiles: **144 intended trials**. A unique submission key forces fresh processing for each timing trial. Every timed-out backend job must be drained before starting the next trial. Diagnostic counters/profilers and test/build workloads do not run alongside the matrix; read-only source/report review continues. No unsuccessful trial is removed. Windows/OS background variation is not claimed to be eliminated.

The primary collection stopped safely at **141 retained trials, nine transport errors**, including one unsettled reference job. All 20–200 groups and stress deferred/HTTP experimental groups completed. The first experimental stress browser reference hit the unchanged 30-second proxy timeout and remained unfinished after the 240-second drain limit; three planned browser trials were not started. Playwright therefore exited 1. The original JSON, log and trace remain intact. During the late stress stage, one system observation recorded only **135,400 KiB** free physical memory out of **20,648,664 KiB**, with **852,312 KiB** free virtual memory (`resource-pressure.json`). A trimmed process working set does not prove low allocation demand. This observed contention limits interpretation; it does not prove the cause of every timeout, which also occurred in earlier completed reference groups.

After the user reduced other workloads, the affected experimental stress browser population is repeated under a new run label and separate file, not pooled into or substituted for the failed original matrix. Initial recovery was about 6.4 GiB available; a later recorded observation during the repeat was about 2.7 GiB (`resource-recovery.json`). These are point observations, not controlled continuous resource monitoring. The harness now refuses to overwrite an existing benchmark JSON and supports explicit profile/layer/run-label selection for reproducible partial repeats. Missing service or candidate-count telemetry for an unsettled job remains missing rather than becoming zero.

```powershell
$env:SMART_WARDROBE_COMPACT_BENCHMARK='true'
$env:SMART_WARDROBE_COMPACT_DIAGNOSTICS='false'
npx playwright test --config playwright.compact.config.ts --grep 'matched paired'
```

At 100 garments, six trials per arm/layer, the completed uninstrumented results are:

| Profile | Direct HTTP median reference → compact | Browser visible-result median reference → compact | Compact browser maximum | Errors |
|---|---:|---:|---:|---:|
| Deferred | 3.785 → 1.214 s | 3.870 → 1.365 s | 1.457 s | 0 |
| Experimental | 5.782 → 1.614 s | 6.511 → 1.777 s | 2.130 s | 0 |

All complete-run fingerprints match within workload/profile across arms and transport layers. Fingerprints include selected garment IDs/roles/order, exact score metadata and persisted provenance, excluding intentionally fresh recommendation IDs and timestamps. They do not compare transient random verifier context IDs. Service-tool and browser-tool JSON canonicalization differs, so digest strings are compared within each tool population, not across different encodings.

### Complete main timing evidence

Windows 11 / Ryzen 5 7235HS (4 cores, 8 logical processors), Python 3.12.10, Next 16.4.2, React 19.2.4, Playwright 1.64.1. These installed versions were inspected; no package change is part of this phase. The disposable backend is single-process; timed trials are sequential, not a concurrency/capacity test. The installed environment and point-in-time memory conditions are retained in JSON.

Seconds below are successful-response medians, reference → compact; a timeout is never reported as successful latency. Each arm has six trials at 100/200 and two at 20/50/stress unless stated. The exact number examined and scored equals N for these all-mandatory-passing fixtures.

| Garments | N | Profile | Direct HTTP median | Browser visible-result median | Compact browser maximum |
|---:|---:|---|---|---|---:|
| 20 | 198 | Deferred | 0.111 → 0.076 | 0.312 → 0.261 | 0.296 |
| 20 | 198 | Experimental | 0.125 → 0.083 | 0.265 → 0.250 | 0.259 |
| 50 | 2,430 | Deferred | 0.602 → 0.198 | 0.792 → 0.443 | 0.455 |
| 50 | 2,430 | Experimental | 0.895 → 0.310 | 1.197 → 0.460 | 0.499 |
| 100 | 17,710 | Deferred | 3.785 → 1.214 | 3.870 → 1.365 | 1.457 |
| 100 | 17,710 | Experimental | 5.782 → 1.614 | 6.511 → 1.777 | 2.130 |
| 200 | 134,820 | Deferred | 21.851 → 7.399 | 23.287 → 8.139 | 9.362 |
| 200 | 134,820 | Experimental | 34.195 → 9.715 | 6/6 proxy failures → 10.705 | 11.494 |
| 200 heavy outerwear | 300,763 | Deferred | 48.002 → 15.146 | 2/2 proxy failures → 16.905 | 17.178 |
| 200 heavy outerwear | 300,763 | Experimental | 84.944 → 22.577 | Main: one unsettled reference failure, compact not started | — |

The separate recovered-resource experimental stress browser repeat has two trials per arm: compact median **22.491 s**, maximum **22.613 s**, both successful; reference **2/2 proxy failures** at about 30 s, backend service median **105.804 s** / maximum **109.133 s** before later commit. Both compact/reference persisted fingerprints match `44f3a8fe…`. Collection passed (4.9 min), despite its deliberately retained proxy failures; this is not response-time acceptance. Original failed evidence remains separate.

At 100 garments the browser median speedups are about **2.84× deferred** and **3.66× experimental**. At 200 garments deferred is about **2.86×**; experimental changes the observed outcome from proxy failures to successful responses, while still exceeding five seconds. There is no observed small-workload latency regression in this matrix; two trials at 20/50 cannot establish a general statistical bound. Every raw CPU time, service stage, response-arrival time, visible-result time, error, drain duration, count and fingerprint is retained in `transport.json` and the separate repeat. `transport-summary.json` and `transport-stress-browser-repeat-summary.json` reproduce the medians and maxima without dropping failures.

Main-process observed working-set maxima are **82.867 MiB reference / 82.840 MiB compact**. Both arms share the same **94.430 MiB process-lifetime high-water mark**, so it is not a per-arm allocation comparison. Point observations under memory pressure can understate resident demand. Compact caches remain bounded: at 200 ordinary garments 10,000 pairs are stored against capacity 19,900, with 380,800 pair hits; each numeric-summary cache is capped at 256, with only 2–3 entries in the homogeneous fixture. Stress and eviction tests preserve recomputation semantics. Memory grows with garment/preference preparation and bounded caches rather than the total number of candidates.

### Multiple preferences, diagnostics and transport safety

The separately labelled 100-garment workload has **three preferences**: blue, vintage and top group; it retains N=17,710 and the same request. Six alternating pairs per profile/layer produce **48 successful trials**, no transport errors and matching fingerprints. Browser median reference → compact: **4.693 → 1.759 s deferred**, **7.189 → 2.300 s experimental**. Compact maxima are **1.898 / 2.754 s**. Direct HTTP medians: **4.324 → 1.555 s** and **6.118 → 1.842 s**. Collection passed in 3.4 min; `transport-multi.json` and its summary retain all trials. These are not pooled with the one-preference or diagnostic populations.

The explicit instrumented 100-garment run passed with **eight successful trials**, one pair per profile/layer (47.2 s collection). One diagnostic HTTP compact trial reports:

| Stage (seconds, instrumented) | Deferred | Experimental |
|---|---:|---:|
| Preparation | 0.0229 | 0.0323 |
| Enumeration | 0.0119 | 0.0142 |
| Primary mandatory | 0.1453 | 0.1575 |
| Independent verifier | 0.1617 | 0.1907 |
| Exact scoring and validation | 0.6586 | 1.1294 |
| Ranking | 0.1862 | 0.1783 |
| Full winner reconstruction | 0.0008 | 0.0011 |
| Original transactional revalidation/write/commit span | 0.0195 | 0.0199 |

Reference diagnostic service times for these HTTP trials are 4.622 / 6.807 s; compact 1.316 / 1.913 s. Existing wrapper spans are **inclusive and nested** and must not be summed into wall time. Full gate/public score constructors run once for compact winner reconstruction, while the compact primary verifier, independent verifier, exact scalar checks and total validator still run for every applicable candidate. Lower public-constructor counts are not permission to skip validation. Reference raw aggregation, weighted arithmetic and other spans are retained in JSON. The first diagnostic startup failed due to instrumentation incorrectly treating an instance-assigned callable as a class method; `transport-diagnostic-startup.log` is retained. Only the new test wrapper was corrected, not any scoring code. Diagnostic timings are never used as NFR evidence.

The actual browser/HTTP safety test passed (47.1 s collection, 33.1 s test): a **controlled 100 ms browser fetch abort**, observed UI retry state and backend completion were followed by clicking the existing same-request retry button. It reused the submission key, returned the original durable ID/score and created no second chat/recommendation. This is a controlled client interruption, **not a claim that compact incurred a 30-second proxy timeout**. A separate 200-garment late metadata failure returned HTTP 503 after 11.270 s with `PersistenceFailure` and zero new chats/recommendations. Concurrent 100-garment same-key requests (3.503 s) returned one durable result and one replay; distinct keys (3.203 s) produced exactly two results. Full stored scores, provenance, counts and outcomes are in `timeout-safety-compact.json`. Focused tests separately inject rollback at all eight persistence stages, exercise both profiles, snapshot changes, strict eligibility and immutable historical replay.

The final focused command passed **123 tests**, one existing Starlette/httpx warning, **9.46 s** (`focused-verified.log`). Final frontend checks run after restoring exactly the four generated TypeScript includes; the restored file matches its pre-phase SHA-256, so no frontend configuration change is retained.

### Reproducing the additional verification

From `frontend`, each command starts/stops its own disposable servers; never run latency populations concurrently. Existing output JSON is protected from overwrite; use a new safe run label for a repeat.

```powershell
# Separate repeat of the original failed stress browser population.
$env:SMART_WARDROBE_COMPACT_BENCHMARK='true'
$env:SMART_WARDROBE_COMPACT_DIAGNOSTICS='false'
$env:SMART_WARDROBE_COMPACT_SIZES='stress'
$env:SMART_WARDROBE_COMPACT_PROFILES='experimental_compatibility_decision_v1'
$env:SMART_WARDROBE_COMPACT_LAYERS='browser'
$env:SMART_WARDROBE_COMPACT_RUN_LABEL='stress-browser-repeat'
npx playwright test --config playwright.compact.config.ts --grep 'matched paired'

# Separate three-preference, six-pair population.
Remove-Item Env:SMART_WARDROBE_COMPACT_RUN_LABEL -ErrorAction SilentlyContinue
Remove-Item Env:SMART_WARDROBE_COMPACT_PROFILES -ErrorAction SilentlyContinue
Remove-Item Env:SMART_WARDROBE_COMPACT_LAYERS -ErrorAction SilentlyContinue
$env:SMART_WARDROBE_COMPACT_SIZES='100'
$env:SMART_WARDROBE_COMPACT_MULTI='true'
npx playwright test --config playwright.compact.config.ts --grep 'matched paired'

# Diagnostic timings, one pair per profile/layer.
$env:SMART_WARDROBE_COMPACT_MULTI='false'
$env:SMART_WARDROBE_COMPACT_DIAGNOSTICS='true'
npx playwright test --config playwright.compact.config.ts --grep 'matched paired'

# Controlled abort/retry, failure injection and actual concurrent submissions.
$env:SMART_WARDROBE_COMPACT_DIAGNOSTICS='false'
$env:SMART_WARDROBE_COMPACT_SAFETY='true'
$env:SMART_WARDROBE_COMPACT_ALLOW_FAILURE='true'
$env:SMART_WARDROBE_COMPACT_SAFETY_ARM='compact'
npx playwright test --config playwright.compact.config.ts --grep 'real timeout retry'
```

From `backend`, exact interpreter/dependency arguments for the final focused run and non-latency audits:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
$phaseArgs=@('--no-project','--python','3.12','--with','pytest','--with','jsonschema','--with','fastapi==0.146.0','--with','httpx==0.28.1','--with','pillow==13.0.0','--with','python-multipart==0.0.32','--with','numpy==2.5.4','--with','uvicorn==0.54.0')
uv run @phaseArgs python -B -m pytest -p no:cacheprovider tests/test_compact_exhaustive.py tests/test_compact_integration.py -q --tb=short
uv run @phaseArgs python -B scripts/verify_compact_candidates.py --size 100 --diverse --output '../storage/verification/phase5f2e3c3e/audit100-diverse.json'
uv run @phaseArgs python -B scripts/verify_compact_candidates.py --size 200 --output '../storage/verification/phase5f2e3c3e/audit200.json'
uv run @phaseArgs python -B scripts/benchmark_compact_exhaustive.py --sizes 100 --repeats 1 --allocations --output '../storage/verification/phase5f2e3c3e/allocations100.json'
```

The audit tool refuses to overwrite output or write outside `storage`. It independently builds original public candidate/evaluation/gate/R/P/raw-C/decision/score records, compares each against the compact audit sink, hashes a length-delimited canonical JSON stream and maintains an independent exact maximum. It retains no candidate list. Complete outcome/winner checks supplement the every-candidate comparison. Unit tests additionally compare actual retained coordinator outcomes and diagnostics; transport tests compare persisted provenance. No transient verifier context UUID is treated as a stable semantic identity.

The **diverse 100-garment audit** passed both profiles, **17,710/17,710 candidates each**, no failures/unknown mandatory conditions for its generic request, exact complete-stream and independent winner equality. It uses three preferences and synthetic blue/red/white/missing/unrecognized-hex colours with vintage/classic/sporty/missing/empty/malformed style evidence. Mandatory filtering is separately covered by the focused request/suitability corpus. Experimental decision bases: **792 Computed, 14,316 PartiallyConventional, 2,592 FullyConventional, 10 NoPairReference**. Stream SHA-256: deferred `740d5a172092bdb64e95f60511389dd054336d88b8026367cf714a445b84d012`; experimental `5f1c02f6147395ae6924a36e3835f6a1227a21e8a5a17b06bbe20a6b9493c5d4`. Audit elapsed times (41.817 / 22.577 s) include full explanations, hashing, two oracle paths and concurrent non-performance frontend checks; they are **not latency benchmarks**.

The **200-garment audit** also passed both profiles, **134,820/134,820 candidates each**, no mismatches, successful complete-stream accounting and independent exact winner equality (`audit200.json`). Experimental bases: **134,800 Computed / 20 NoPairReference**. Stream SHA-256: deferred `5b843147ff8d233c57e86cf5849e610f6d5c6385f0a7f8d60f49b48315950b4f`; experimental `c6cfdebd48f890ed6f3f1c07fca6a3434ecc41f5ac7dd2230e1017a54349f69f`. Elapsed audit times are 233.705 / 159.620 s, not latency measurements. These two large audits compare **305,060 full candidate records** in total, in addition to the small focused corpus. Stress transport trials verify exhaustive scored counts and persisted semantic fingerprints; they do not independently reconstruct every stress candidate's public record a second time.

Final `npx tsc --noEmit` and `npm run lint` exit **0**, with only the two previously documented lint warnings. The isolated production build, 14 compact browser functional tests and 35 existing browser regressions remain successful; no frontend application code changed afterward. `tsconfig-restored.json` records exact pre-phase restoration, not a general reset of user changes.

### Allocation observation

The separate actual-service `--allocations` run completed successfully for all four arms at 100 garments / 17,710 scored candidates, with exact paired persisted fingerprints. `tracemalloc` starts/stops around each service call after fixture seeding and service construction. It measures traced Python allocations, not total RSS, native/browser allocations or deployment capacity. It is explicitly instrumented; elapsed times below must not replace the uninstrumented HTTP/browser measurements.

| Profile | Arm | Traced peak bytes | MiB | Instrumented service seconds |
|---|---|---:|---:|---:|
| Deferred | Reference | 1,131,698 | 1.079 | 16.561 |
| Deferred | Compact | 336,908 | 0.321 | 7.073 |
| Experimental | Reference | 3,413,689 | 3.256 | 25.311 |
| Experimental | Compact | 1,092,099 | 1.042 | 9.924 |

These observations support the bounded-memory architecture for the tested fixture; no formal memory acceptance budget was invented. Pair capacity is 19,900, aggregation capacities 256 each, and cache eviction recomputes exact values. Input preparation is O(garments × preferences); exhaustive time still scales with N. The largest full record audit is 134,820 candidates and the largest timed count is 300,763, without any candidate list materialization in the normal path.

## Retention and future integration constraints

This phase establishes an experimental replacement for internal enumeration/scoring work, not a new recommendation policy or API. Retention requires complete differential equality, bounded session memory and repeatable improvement. No production factory imports these five modules. The default deferred profile, optional decision profile, opt-in suitability and disabled approximate-hex evidence remain unchanged.

The test bridge deliberately preserves the existing policy/provenance JSON for parity, including the existing experimental `scorer_implementation="prepared-decision-1.0.0"`. That legacy label does **not accurately identify the new compact executor**; the separate `compact-exhaustive-1.0.0` source manifest and experiment records identify it during this isolated test. A future production integration needs an explicitly approved prepared-context/provenance port, an accurate executor identity that preserves historical readers, and regression tests before changing live wiring. The bridge must not be copied into production unchanged or claim that its unconsumed metadata-carrier session was exhausted.

There is no cancellation, admission-control, worker or asynchronous-API change. A disconnected browser can leave backend enumeration running and, after success, committing. Existing idempotency permits recovery with the same submission key; it does not remove the CPU cost of concurrent attempts. Sequential matched measurements do not establish concurrent capacity or deployment performance. Candidate growth remains exhaustive and can be cubic in the number of garments.

The homogeneous synthetic timing workload makes exact scalar-summary reuse particularly effective. It establishes no general performance distribution for diverse real wardrobes. Diverse candidate-level audits establish correctness rather than latency or fashion quality. Windows working-set high-water marks include interpreter, disposable fixture seeding and earlier trials; they cannot be attributed to an individual request. Separate allocation observations and explicit cache bounds are required alongside those figures.

Before any normal activation: approve the prepared-context/executor-provenance integration; define the actual NFR baseline and deployment capacity; verify representative diverse owner-reviewed wardrobes and concurrency; rerun transport, transaction, eligibility and history regressions; and explicitly approve the selected compatibility profile. This phase does not approve any of those later changes or final FYP acceptance.

## Final assessment

**PASS WITH LIMITATIONS — retain the isolated compact implementation for review.** Every executed differential comparison matches, all valid candidates remain scored, complete-stream/eligibility/transaction/history guarantees are preserved in the executed tests, allocation demand is bounded for the measured fixtures, and material paired speedups occur without an observed small-workload regression. There is no detected new functional regression. All 178 pre-existing application files and 31 earlier reference files remain unchanged. Phase-scoped authored changes are **18 new files and two modified files**, listed above; other pre-existing uncommitted work is preserved.

**NFR-02 is not formally accepted, and the application is not ready for final FYP acceptance.** Both compact profiles finish below five seconds in all tested 100-garment browser trials (including the separate three-preference population), but 200 ordinary and outerwear-heavy cases remain above five seconds. The baseline workload, operating conditions and percentile remain undefined. Exhaustive scaling, real-wardrobe diversity and concurrent capacity remain risks. The interrupted original stress collection, its missing three trials, reference proxy failures, resource pressure, separate repeat and all development failures remain recorded rather than erased.

Remaining verification limitations are the existing architecture assertion, unexecuted CV geometry module, existing lint/deprecation warnings, synthetic performance/evaluation fixtures and test-only provenance bridge. Compatibility fashion quality and deployment data are not validated by these tests. `git diff --check` exits **0**; Git's LF/CRLF warnings are distinct from whitespace failures. New untracked text files are separately checked for trailing whitespace. Full raw evidence and final source/artifact hashes are in `storage/verification/phase5f2e3c3e/`; ignored framework/build/browser outputs are grouped under `.next-integration-run/` rather than treated as authored source changes. No live integration or further phase is started.
