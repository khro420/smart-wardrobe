# Phase 5F-2E-3C-3F: controlled compact execution integration

This phase connects the already verified compact kernel to the existing Outfit Assistant service. **Both defaults remain unchanged.** No second recommendation/persistence workflow, migration, frontend application change or scoring-policy change is introduced. Performance acceptance remains distinct from functional integration.

## Authority and preserved contracts

Original PDF SHA-256 `5e5781cd739b696e63cd21a063b8e741daaa6fa93b20f4849b0b84a7c7e38669`; Chapter 3 PDF pp.179–180 / printed168–169 defines performance under a test-plan baseline and NFR-02's completed recommendation/no-result/unsupported response within five seconds. PDF p.188 / printed177 RN-17 requires scoring **each valid candidate**. Section4.10.4 (PDFp.287 / printed276) retains exact weighted ranking and stable ties; section4.11.4 (PDFp.302 / printed291) reiterates application-server response targets. The full-PDF baseline/test-plan search is retained under `storage/verification/phase5f2e3c3f/`.

`FYP_CONTEXT.md`, `GARMENT_DATA_CONTRACT.md`, `NLP_REQUEST_CONTRACT.md`, `RECOMMENDATION_RULES.md` and the Phase3E verification remain authoritative. Phase1 strict query/commit-time ownership, confirmed-item/job linkage and availability are unchanged. Phase2 request semantics, Phase3 structures/mandatory conditions, Phase4 preferences/scoring and Phase5 transaction/idempotency/history contracts are unchanged. Suitability remains opt-in; approximate hexadecimal and pattern scoring remain disabled. No CV/VTOFF/VTON or Digital Wardrobe algorithm changes.

## Server configuration

| Environment variable | Allowed values | Default |
|---|---|---|
| `SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE` | `reference`, `compact_exhaustive` | `reference` |
| `SMART_WARDROBE_ASSISTANT_SCORING_PROFILE` | `compatibility_deferred`, `experimental_compatibility_decision_v1` | `compatibility_deferred` |

All four combinations are supported. `WorkflowRuntime` validates both allowlists at startup, even if the Assistant feature is disabled. An unknown value raises `ValueError`; there is no silent fallback. This intentionally strengthens the previous invalid-profile startup behaviour, which formerly permitted a later `ProfileUnavailable` response. Direct service calls still give that controlled outcome for invalid selection on a new submission; historical idempotent replay is checked first and remains available independently of current settings.

No production request field chooses an engine or policy. Existing extra-body rejection remains; arbitrary extra query keys cannot override the server selection. The test fixture's loopback `/_test/compact-integrated/...` control exists only in the disposable test server, never the normal app entry point.

Reference execution still uses `AssistantScoringSelection` and its retained reference factories. Compact execution creates a fresh `CompactAssistantScorer` through the server selector, passing the selected profile explicitly. Deferred weights remain `7/10,0,3/10`; experimental weights remain `3/5,1/5,1/5`. Single-dress NoPairReference, genuine zero, unknown/partial raw evidence, exact bounds and midpoint conventions are unchanged.

## Prepared context and completion

`AssistantExecutionContext` is a frozen metadata value: owner, immutable request, evaluator name, optional suitability policy version and structural policy version. It is **not** a completion certificate. The service validates it against the reconstructed verified winner before persistence.

The compact adapter obtains the injected Phase1 query from the existing candidate-engine composition, rejects unsupported structural policies, and delegates to the unchanged compact kernel. It neither imports persistence nor writes records. The kernel still independently verifies mandatory conditions and exact scores for every valid candidate, completes/validates its exhaustive ledger, closes the stream and reconstructs/compares the original public winner. Only a complete `Selected` result receives prepared metadata.

The adapter reads evaluator metadata from the kernel's actual reconstruction session but never assigns that session to the captured reference engine, consumes/fakes its progress or fabricates `RequestGenerationResult`. A test explicitly verifies that the metadata session is incomplete while the kernel's independent ranking ledger is complete. Reference execution obtains the same metadata from its actual captured session. The previous Phase3E test-only session-assignment bridge is not used by production compact selection.

NLP, captured preferences, score-policy validation, `RecommendationWrite`, atomic repository persistence and final transactional revalidation remain in the original service. Enumeration stays outside the write transaction. Any bridge failure happens before insertion. Repository idempotency is resolved before interpretation/selection and again atomically at commit; engine/profile changes do not rerank or rewrite a committed submission.

## Provenance and response compatibility

Reference provenance is byte-semantically unchanged. New compact records preserve all existing scoring-policy/evaluator/preference/mandatory fields and add `assistant_execution_selection` with engine, selection version, executor implementation and digest. New experimental compact records correctly identify `scorer_implementation="compact-exhaustive-1.0.0"` instead of falsely identifying the retained prepared executor. Deferred compact records use the additive execution metadata without inventing compatibility measurements.

Thus executor identity is an intentional, necessary difference, not a scoring-policy mismatch. Differential tests compare every other provenance field exactly and explicitly validate these two executor-specific differences. Raw records retain their true identities; benchmark fingerprints normalize only those identity fields. Scores, explanations, coverage, policy versions/hashes, roles/order, request and selected garments remain exact. No historical row or stored provenance is rewritten; history/display restoration uses stored profile/metadata rather than current execution flags. Existing JSON provenance supports these additive fields, so no migration is needed.

## Phase-scoped files

- `backend/app/domain/value_objects/assistant_execution_context.py`: immutable metadata and winner/context validation.
- `backend/app/application/recommendation/compact_assistant_scorer.py`: actual-service compact adapter without fabricated stream completion.
- `backend/app/application/recommendation/assistant_execution_selection.py`: independent server execution allowlist and provenance.
- `backend/app/application/recommendation/outfit_assistant_service.py`: select execution and consume immutable context; preserve the original write/replay path.
- `backend/app/infrastructure/workflow_runtime.py`: startup validation and server-only configuration wiring.
- `backend/tests/test_compact_assistant_integration.py`: four-way service/API, full candidate oracle, evidence, preferences, strict eligibility, rollback, history, actions and opt-in suitability tests.
- `backend/tests/compact_integrated_server.py`: disposable actual-service HTTP fixture, completion telemetry, resource observations and test-only controls; no test scorer replacement.
- `backend/tests/integration_source_guard.py`: explicit new hash chain for only the two authorized application replacements plus three additions.
- `backend/tests/test_compact_exhaustive.py`: preserve archived bytes and validate authorized current replacements through the explicit hash chain.
- `backend/tests/test_assistant_decision_integration.py`: expect startup rejection of unknown server profile instead of a later endpoint response.
- `backend/tests/fixtures/compact_integration_reference/app.zip`, `manifest.json`: new pre-phase 183-file archive; no earlier archive is changed.
- `backend/tests/fixtures/compact_integration_sources.v1.json`: separately versioned additions, before/after hashes and unchanged defaults.
- `frontend/playwright.compact-integrated.config.ts`, `frontend/tests/phase5f/compact-integrated.spec.ts`: isolated production build/browser, four-way functional tests, alternating measurements and retry safety.
- `backend/scripts/summarize_compact_integration.py`: reproduce latency/observed-tail statistics with retained failures, service-stage times and per-population resource envelopes.
- This document and `docs/REPORT_TRACEABILITY.md`: implementation, verification and requirement evidence.

Ignored logs/JSON evidence are under `storage/verification/phase5f2e3c3f/`. Generated framework/browser files are grouped under `.next-integration-run/`. Only generated TypeScript includes are restored to pre-phase bytes; unrelated user edits are preserved.

## Verification methodology

The final focused corpus includes every actual-service candidate's public identity, primary outcome, independent verification, exact R/C/P/S, raw compatibility/decision data and ordering for representative mixed structures. It also retains Phase3E's much larger exhaustive differential corpus and verifies its unchanged five kernel sources. Four-way service cases exercise all structures, zero/partial/unknown evidence, three preferences, malformed attributes, actual startup/API auth, no-result/unsupported policies, all eight write-stage rollbacks, changed selected snapshots, same/different-key concurrency, strict processing status/job/owner filtering, stored history and existing save/visualisation validation. No fashion-quality accuracy is inferred from arithmetic tests.

The matched timing matrix uses the same synthetic distributions as Phase3E: 20 (198 candidates), 50 (2,430), 100 (17,710), 200 (134,820), heavy-outerwear200 (300,763). Every timed call uses a new key and real login/JWT/API/service/SQLite; no saved outfits are required. Three alternating pairs per arm/profile/transport at 100/200, two elsewhere, give 96 intended trials. The request is `Suggest an outfit with vintage style`, one stored blue preference, all synthetic garment colours blue/styles vintage. This homogeneous workload favours exact scalar reuse and does not establish real-wardrobe fashion quality or a performance distribution for diverse descriptors.

Before/after each trial the fixture records available RAM, backend process memory, OS CPU load, CPU hardware and top resident competing processes with cumulative CPU seconds. These are observations, not a guarantee of continuous isolation. Test/build workloads stop before timing. No user process is terminated. The existing Next production proxy timeout remains unchanged. Failed browser requests are retained even if the backend commits later; each job must settle before the next timing trial. An unsettled job stops collection rather than overlapping or hiding failure. Medians and observed maxima are descriptive; small samples do not establish a reliable percentile SLA.

## Proposed formal NFR-02 test plan — NOT YET APPROVED

The report refers to a system test plan but the reviewed original passages and full-text search do not establish numeric wardrobe size, hardware, concurrency or a measurement percentile. The current runs are exploratory integration/scalability evidence, not a retrospective definition of that baseline.

Propose for approval:

1. Freeze the intended deployment OS/CPU/RAM, Python/Next/dependency versions, production server/proxy setup and selected execution/profile. This machine can be a local baseline only if explicitly approved; it is not assumed equivalent to production.
2. Use 100 strictly eligible garments (40 tops,40 bottoms,10 dresses,10 outerwear;17,710 structures), with separate zero/one/three-preference cases. Keep 200 and heavy outerwear as separately labelled scalability cases. Include supported generic/partial requests, controlled no-result and unsupported terminal outcomes, plus a diverse reviewed-wardrobe set.
3. One active recommendation interaction, no concurrent CV/VTON jobs; initially propose at least4GiB available RAM and low competing CPU load before collection as operational controls, not report-defined requirements. Record resource variation; invalidate and retain a disturbed population rather than cherry-picking fast trials. Concurrency/capacity gets a separate approved workload.
4. Run already-ready production servers with the first submitted interaction included; no hidden ranking warm-up. Use authenticated actual browser submission through visible terminal result. Record backend, HTTP arrival and browser time separately. Propose30 consecutive submissions per case/configuration; retain every failure and retry under its own label.
5. Check the literal five-second response bound for every measured baseline submission and report observed maximum plus distribution; do not replace it with a passing median, an invented percentile, longer proxy timeout or later backend commit. A passing sample is evidence for the agreed baseline, not proof for every deployment/workload.

These workload, operating-control and sample choices require user approval. They are not new original-report constants. No automatic default switch or formal acceptance follows from this phase.

## Established verification results

Exact commands below are PowerShell. Backend prefix from `backend`:

```powershell
$env:SMART_WARDROBE_VTOFF_ENABLED='off'
$phaseArgs=@('--no-project','--python','3.12','--with','pytest','--with','jsonschema','--with','fastapi==0.146.0','--with','httpx==0.28.1','--with','pillow==13.0.0','--with','python-multipart==0.0.32','--with','numpy==2.5.4')
uv run @phaseArgs python -B -m pytest -p no:cacheprovider tests/test_compact_assistant_integration.py tests/test_compact_exhaustive.py tests/test_compact_integration.py tests/test_assistant_decision_integration.py -q --tb=short
```

Final focused run: **271 passed**, one existing Starlette/httpx warning,30.90s (`focused-complete.log`, exit0). This reruns all four listed modules after the supplemental cross-engine race tests. Earlier successful runs remain retained:269 passed and the separate two-profile race check2 passed. Actual-service representative every-candidate records match the original public oracle in both profiles, including unknown/failed mandatory conditions; score/count/provenance/winner comparisons supplement rather than replace that check. The new actual-service audit compares10 complete candidate records per profile; the five core compact source files remain unchanged from Phase3E's separately reported 305,060-record audit and cache/stream validation.

Broad commands, same prefix:

```powershell
$env:SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE='reference'
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='compatibility_deferred'
uv run @phaseArgs python -B -m pytest -p no:cacheprovider tests --ignore=tests/test_segmentation_geometry.py -q --tb=short
$env:SMART_WARDROBE_ASSISTANT_SCORING_PROFILE='experimental_compatibility_decision_v1'
uv run @phaseArgs python -B -m pytest -p no:cacheprovider tests --ignore=tests/test_segmentation_geometry.py -q --tb=short
```

- Deferred collection: **1,752 passed,one existing failure**,250.67s.
- Experimental collection: **1,771 passed,one existing failure**,166.34s.
- The different counts reflect supplemental new test cases added between collection snapshots; final focused coverage includes them. No production source/scoring-policy change separates the successful runs. The existing failure is `tests/test_report_architecture.py::ReportArchitectureTests::test_single_backend_and_canonical_ml_locations`; its `ai-services` assertion and directory remain untouched.
- CV geometry is not executed because its dedicated torch/CV environment is unavailable. No CV algorithm is changed; there is no claim of real CV/VTON model validation.
- Development failures remain logged: an incorrect garment-helper argument/fixture ID, two old-factory injection assertions that did not target the newly selected bridge, and an isolated history-reader import capturing a fixture lambda. They were corrected in test code; no scoring rule or frozen reference was changed to make a comparison pass.

Frontend commands from `frontend`:

```powershell
npx tsc --noEmit
npm run lint
$env:SMART_WARDROBE_BUILD_DIR='.next-integration-run/compact-integrated-production'
$env:SMART_WARDROBE_BACKEND_URL='http://127.0.0.1:3201'
npm run build
npx playwright test --config playwright.compact-integrated.config.ts --grep 'integrated functional'
npx playwright test --config playwright.integration.config.ts --output .next-integration-run/compact-integrated-legacy-artifacts
$env:SMART_WARDROBE_COMPACT_SAFETY='true'
$env:SMART_WARDROBE_COMPACT_ALLOW_FAILURE='true'
$env:SMART_WARDROBE_COMPACT_SAFETY_ARM='compact'
npx playwright test --config playwright.compact-integrated.config.ts --grep 'real timeout retry'
```

TypeScript, ESLint and isolated production build exit0. ESLint retains two existing internal-navigation warnings (`app/extract/results/page.tsx:154`, `components/Layout.tsx:50`). **28 four-way functional browser tests passed** (42.4s); **35 existing browser regressions passed** (3.0min), including auth/flags, Homepage/Assistant/history and historical actions. **Actual compact integration safety passed** (22.9s test /33.1s collection): controlled100ms browser abort, same-key visible retry/replay, atomic late write failure, same-key and distinct-key concurrent requests. The controlled abort is not a claim that compact incurred the real30s proxy timeout. Real proxy failure rates are reported by the timing matrix separately.

The isolated build procedure avoids changing/deleting unrelated build directories. The four generated TypeScript include entries were removed only after their removal reproduced the exact pre-phase SHA256. Existing frontend application source and API/display types remain unchanged. Frozen originals are preserved; current source changes are only the two explicitly approved application replacements and three new application modules.

## Source-integrity verification

`integrity-final.json` verifies all 183 original application files against the pre-phase snapshot: 181 remain identical, with only `outfit_assistant_service.py` and `workflow_runtime.py` replaced through the explicit before/after hash chain. The three new modules match their separately versioned manifest. Every original file in the new 183-entry archive matches its captured original hash. All 34 earlier fixture/archive/manifest files remain identical; no previous source baseline was rewritten. In particular, the five compact kernel/value-object/verifier sources and their original Phase3E manifest remain unchanged. Frontend `tsconfig.json` and `AGENTS.md` match their pre-phase bytes.

## Remaining capability and deployment limits

This is exact execution equivalence, not independent fashion-quality validation. The experimental compatibility decision still uses its approved subjective colour/style rules, explicit partial-evidence midpoint and single-dress no-pair convention. Those conventions are preserved, not newly validated by faster execution. Approximate hex evidence and pattern scoring remain disabled, and declaration-based suitability remains opt-in. Requests outside available downstream policies still return controlled unavailable outcomes.

Historical replay intentionally returns its captured preference/scoring/executor provenance. New persistence revalidates selected garments and scoring-relevant garment attributes transactionally, but the existing preference consistency remains a snapshot captured at ranking read, not at commit time. No historical record is repaired or reranked.

The integration does not introduce admission control, asynchronous jobs or parallel scoring. Simultaneous submissions can still compete for CPU; durable idempotency prevents duplicate committed results rather than eliminating duplicate computation. Latency/resource measurements are synthetic local Windows/SQLite observations and cannot be treated as deployment capacity guarantees. No real CV/VTOFF/VTON model execution or production database audit is claimed.

## Main measured population

Actual-service `transport.json` and `transport-summary.json`: **96 trials, 7 browser transport failures, zero unsettled jobs**. The Playwright evidence-collection test passed (25.8min); this means the collector preserved/drained all trials and exact semantic checks, not that every browser request succeeded. Reference: 7/48 failures (14.58%); compact: 0/48. Across direct HTTP there were 0/48 failures; browser reference 7/24 (29.17%), browser compact 0/24. Every backend job ultimately selected and committed; that does not repair a timed-out browser response. All matched semantic fingerprints agree after only the documented executor-identity normalization.

A = deferred; B = experimental compatibility decision. Each timing cell is **successful median / observed maximum in seconds**. A timeout cell gives failed/all trials, not successful latency. Two trials per cell at20/50/stress; three at100/200.

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

CPU observations ranged **45-99%**, with free physical memory **2.75-6.76GiB**. Resource variation and background application activity prevent calling this a quiet/stable acceptance population. The user offered to pause heavy workloads partway through; observations, not that intention, determine the qualification. Test/build processes were not running during these timings, and no unrelated application was terminated.

The backend working set observed after submissions reached83.16MiB; the maximum process-lifetime peak was94.38MiB. These are not per-request peak measurements and do not prove a deployment memory bound. The unchanged compact design uses streaming and bounded component caches rather than materialising candidate collections.

At100 garments every observed compact browser submission was below five seconds (A maximum1.552s, B maximum2.084s). At200 garments all measured compact requests exceeded five seconds; browser medians were8.297s and10.605s. Stress compact browser medians were12.976s and17.108s. These observations do not establish formal NFR-02 acceptance: the test-plan baseline is unapproved and resource conditions were contended.

Exact collection/summarisation commands, from `frontend` then `backend`:

```powershell
$env:SMART_WARDROBE_COMPACT_BENCHMARK='true'
$env:SMART_WARDROBE_COMPACT_DIAGNOSTICS='false'
npx playwright test --config playwright.compact-integrated.config.ts --grep 'matched paired'
uv run --no-project --python 3.12 python -B scripts/summarize_compact_integration.py ../storage/verification/phase5f2e3c3f/transport.json ../storage/verification/phase5f2e3c3f/transport-summary.json
```

Backend service measurements from the main direct-HTTP population are below (median / observed maximum seconds; CPU is process CPU median). Browser-timeout jobs also have separately retained completed service durations in the JSON; those durations are not successful browser responses.

| Garments | Profile | Engine | Service seconds | CPU seconds median |
|---|---|---|---:|---:|
| 20 | A | reference | 0.055 / 0.058 | 0.047 |
| 20 | A | compact | 0.040 / 0.040 | 0.031 |
| 20 | B | reference | 0.085 / 0.088 | 0.078 |
| 20 | B | compact | 0.049 / 0.054 | 0.039 |
| 50 | A | reference | 0.402 / 0.446 | 0.375 |
| 50 | A | compact | 0.190 / 0.190 | 0.148 |
| 50 | B | reference | 0.704 / 0.729 | 0.633 |
| 50 | B | compact | 0.244 / 0.247 | 0.219 |
| 100 | A | reference | 3.507 / 3.657 | 3.219 |
| 100 | A | compact | 1.125 / 1.161 | 1.078 |
| 100 | B | reference | 5.498 / 6.162 | 4.922 |
| 100 | B | compact | 1.722 / 1.867 | 1.375 |
| 200 | A | reference | 23.185 / 25.960 | 21.203 |
| 200 | A | compact | 7.279 / 7.945 | 6.672 |
| 200 | B | reference | 36.734 / 41.573 | 33.391 |
| 200 | B | compact | 9.749 / 9.769 | 8.703 |
| stress | A | reference | 46.560 / 50.379 | 42.094 |
| stress | A | compact | 15.696 / 16.391 | 14.273 |
| stress | B | reference | 60.871 / 61.271 | 57.898 |
| stress | B | compact | 16.839 / 17.316 | 15.727 |

## Separate post-pause small-wardrobe repeat

`transport-post-pause-small.json` / `transport-post-pause-small-summary.json` retain **56 additional trials, zero transport errors and zero unsettled jobs**. The evidence collector passed (5.1min). All six workload/profile semantic fingerprints also agree across both populations. This repeat is not pooled with the main matrix. CPU observations still ranged35-90%; free RAM was6.20-6.55GiB. Background workloads remained visible, so this is not claimed as a quiet formal acceptance run.

Each cell is median / observed maximum seconds, with the same A/B labels and two/three-pair method.

| Garments | Profile | HTTP reference | HTTP compact | Browser reference | Browser compact |
|---|---|---:|---:|---:|---:|
| 20 | A | 0.066 / 0.071 | 0.052 / 0.058 | 0.178 / 0.187 | 0.179 / 0.188 |
| 20 | B | 0.084 / 0.088 | 0.055 / 0.060 | 0.205 / 0.226 | 0.181 / 0.184 |
| 50 | A | 0.464 / 0.502 | 0.143 / 0.148 | 0.569 / 0.595 | 0.398 / 0.504 |
| 50 | B | 0.683 / 0.794 | 0.219 / 0.245 | 0.709 / 0.733 | 0.315 / 0.356 |
| 100 | A | 2.650 / 2.693 | 0.870 / 0.987 | 3.076 / 3.088 | 1.071 / 1.244 |
| 100 | B | 4.195 / 4.265 | 1.079 / 1.130 | 4.754 / 4.767 | 1.270 / 1.340 |

At100 garments the compact browser medians were1.071s /1.270s, with maxima1.244s /1.340s (A/B). All observed compact100 browser calls in either population were below five seconds. This is workload-specific evidence, not formal NFR-02 acceptance. The200/stress failures of the five-second target remain; those cases were not silently removed or reclassified as the formal baseline.

Additional repeat commands, from `frontend` then `backend`:

```powershell
$env:SMART_WARDROBE_COMPACT_BENCHMARK='true'
$env:SMART_WARDROBE_COMPACT_DIAGNOSTICS='false'
$env:SMART_WARDROBE_COMPACT_SIZES='20,50,100'
$env:SMART_WARDROBE_COMPACT_RUN_LABEL='post-pause-small'
npx playwright test --config playwright.compact-integrated.config.ts --grep 'matched paired'
uv run --no-project --python 3.12 python -B scripts/summarize_compact_integration.py ../storage/verification/phase5f2e3c3f/transport-post-pause-small.json ../storage/verification/phase5f2e3c3f/transport-post-pause-small-summary.json
```

## Final assessment and separate default recommendations

**Phase3F functional integration: PASS WITH LIMITATIONS. Formal NFR-02 and final FYP acceptance: NOT ESTABLISHED.** No new application/scoring/persistence regression was detected by these checks. The known architecture assertion, unavailable CV geometry verification, existing lint/deprecation warnings, synthetic workloads and non-quiet resource conditions remain limitations. `git diff --check` exits0; the final focused run and restored-tsconfig TypeScript check also exit0. Source and evidence hashes are recorded in `storage/verification/phase5f2e3c3f/deliverables.json`; raw observations and earlier failed development runs are retained rather than replaced by summaries.

**Execution default recommendation:** the exact-result and actual-service tests support compact execution as the preferred candidate for a separately approved default switch. The measured benefit is substantial at100/200/stress and both current policies work through the original persistence workflow. Nevertheless, keep `reference` as the current default until the proposed deployment/baseline acceptance plan is approved and run under controlled conditions, the200-garment capability limit is explicitly accepted or addressed, and rollout/rollback approval is given. This phase does not perform that switch or claim five-second performance at200 garments.

**Scoring default recommendation:** retain `compatibility_deferred`. Faster execution does not validate the experimental colour/style fashion heuristics, partial-evidence midpoint or single-dress convention. A change to `experimental_compatibility_decision_v1` needs separate approval supported by independently reviewed outfit/ranking evaluation and sensitivity analysis. Arithmetic equivalence and synthetic homogeneous benchmarks do not provide that evidence.

No subsequent phase, default activation, approximate hex matching, suitability activation or unrelated optimisation is included. The proposed formal test plan above and both default decisions are left for review.
